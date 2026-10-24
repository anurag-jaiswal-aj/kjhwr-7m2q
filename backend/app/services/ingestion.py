import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple
import sqlite3

from backend.app.db.models import ActualRecord, ForecastRecord, IngestionStats
from backend.app.services.elexon_client import ElexonClient
from backend.app.config import (
    DELIVERY_MONTH_START,
    DELIVERY_MONTH_END,
    FORECAST_FETCH_START,
    FORECAST_FETCH_END,
)

logger = logging.getLogger(__name__)


class IngestionService:
    """
    Ingests and normalizes Elexon datasets into SQLite with deterministic
    deduplication and explicit record state accounting (retrieved, valid, unique).
    """

    def __init__(self, client: ElexonClient, db_conn: sqlite3.Connection):
        self.client = client
        self.conn = db_conn

    def ingest_actuals(
        self,
        settlement_date_from: str = DELIVERY_MONTH_START,
        settlement_date_to: str = DELIVERY_MONTH_END,
        fuel_type: str = "WIND",
    ) -> IngestionStats:
        """
        Retrieves, validates, and stores actual wind generation (FUELHH).
        Deduplication rule: Primary key is (start_time, fuel_type).
        If duplicate keys occur, retain the record with the latest publish_time.
        """
        logger.info("Ingesting FUELHH actuals from %s to %s (fuelType=%s)...", settlement_date_from, settlement_date_to, fuel_type)
        raw_records = self.client.fetch_actuals_stream(
            settlement_date_from=settlement_date_from,
            settlement_date_to=settlement_date_to,
            fuel_type=fuel_type,
        )
        retrieved_count = len(raw_records)

        # 1. Validation step
        valid_records: List[ActualRecord] = []
        for raw in raw_records:
            try:
                # Normalize keys
                rec = ActualRecord(
                    start_time=raw["startTime"],
                    publish_time=raw["publishTime"],
                    settlement_date=raw["settlementDate"],
                    settlement_period=int(raw["settlementPeriod"]),
                    fuel_type=raw["fuelType"],
                    generation=int(raw["generation"]),
                )
                valid_records.append(rec)
            except Exception as e:
                logger.warning("Skipping invalid FUELHH record %s: %s", raw, e)

        valid_count = len(valid_records)

        # 2. In-memory deterministic deduplication
        # Key: (start_time, fuel_type) -> Record with latest publish_time
        dedup_map: Dict[Tuple[str, str], ActualRecord] = {}
        for rec in valid_records:
            key = (rec.start_time, rec.fuel_type)
            if key not in dedup_map:
                dedup_map[key] = rec
            else:
                existing = dedup_map[key]
                if rec.publish_time > existing.publish_time:
                    dedup_map[key] = rec
                elif rec.publish_time == existing.publish_time and rec.generation > existing.generation:
                    dedup_map[key] = rec

        unique_records = list(dedup_map.values())
        unique_count = len(unique_records)

        # 3. Batch SQLite insertion
        cursor = self.conn.cursor()
        cursor.executemany(
            """
            INSERT INTO actual_generation (start_time, publish_time, settlement_date, settlement_period, fuel_type, generation)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(start_time, fuel_type) DO UPDATE SET
                publish_time = excluded.publish_time,
                settlement_date = excluded.settlement_date,
                settlement_period = excluded.settlement_period,
                generation = excluded.generation
            WHERE excluded.publish_time >= actual_generation.publish_time;
            """,
            [
                (r.start_time, r.publish_time, r.settlement_date, r.settlement_period, r.fuel_type, r.generation)
                for r in unique_records
            ],
        )

        # 4. Audit logging
        now_iso = datetime.now(timezone.utc).isoformat()
        cursor.execute(
            """
            INSERT INTO ingestion_audit (dataset, date_range_start, date_range_end, retrieved_count, valid_count, unique_count, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?);
            """,
            ("FUELHH", settlement_date_from, settlement_date_to, retrieved_count, valid_count, unique_count, now_iso),
        )
        self.conn.commit()

        stats = IngestionStats(
            dataset="FUELHH",
            date_range_start=settlement_date_from,
            date_range_end=settlement_date_to,
            retrieved_count=retrieved_count,
            valid_count=valid_count,
            unique_count=unique_count,
        )
        logger.info("FUELHH ingestion complete: %s", stats)
        return stats

    def ingest_forecasts(
        self,
        publish_date_time_from: str = FORECAST_FETCH_START,
        publish_date_time_to: str = FORECAST_FETCH_END,
    ) -> IngestionStats:
        """
        Retrieves, validates, and stores historical wind forecast publication vintages (WINDFOR).
        Deduplication rule: Primary key is (publish_time, start_time).
        """
        logger.info("Ingesting WINDFOR forecasts from %s to %s...", publish_date_time_from, publish_date_time_to)
        raw_records = self.client.fetch_forecasts_stream(
            publish_date_time_from=publish_date_time_from,
            publish_date_time_to=publish_date_time_to,
        )
        retrieved_count = len(raw_records)

        # 1. Validation step
        valid_records: List[ForecastRecord] = []
        for raw in raw_records:
            try:
                rec = ForecastRecord(
                    publish_time=raw["publishTime"],
                    start_time=raw["startTime"],
                    generation=int(raw["generation"]),
                )
                valid_records.append(rec)
            except Exception as e:
                logger.warning("Skipping invalid WINDFOR record %s: %s", raw, e)

        valid_count = len(valid_records)

        # 2. In-memory deterministic deduplication
        # Key: (publish_time, start_time) -> First received record wins
        dedup_map: Dict[Tuple[str, str], ForecastRecord] = {}
        for rec in valid_records:
            key = (rec.publish_time, rec.start_time)
            if key not in dedup_map:
                dedup_map[key] = rec

        unique_records = list(dedup_map.values())
        unique_count = len(unique_records)

        # 3. Batch SQLite insertion
        cursor = self.conn.cursor()
        cursor.executemany(
            """
            INSERT OR IGNORE INTO forecast_generation (publish_time, start_time, generation)
            VALUES (?, ?, ?);
            """,
            [
                (r.publish_time, r.start_time, r.generation)
                for r in unique_records
            ],
        )

        # 4. Audit logging
        now_iso = datetime.now(timezone.utc).isoformat()
        cursor.execute(
            """
            INSERT INTO ingestion_audit (dataset, date_range_start, date_range_end, retrieved_count, valid_count, unique_count, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?);
            """,
            ("WINDFOR", publish_date_time_from, publish_date_time_to, retrieved_count, valid_count, unique_count, now_iso),
        )
        self.conn.commit()

        stats = IngestionStats(
            dataset="WINDFOR",
            date_range_start=publish_date_time_from,
            date_range_end=publish_date_time_to,
            retrieved_count=retrieved_count,
            valid_count=valid_count,
            unique_count=unique_count,
        )
        logger.info("WINDFOR ingestion complete: %s", stats)
        return stats
