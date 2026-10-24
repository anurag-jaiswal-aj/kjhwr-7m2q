import pytest
import sqlite3
import httpx

from backend.app.services.elexon_client import ElexonClient
from backend.app.services.ingestion import IngestionService


def test_fuelhh_deduplication_and_validation(temp_db: sqlite3.Connection):
    # Simulated payload with:
    # 1. Valid record A
    # 2. Duplicate of record A with newer publishTime (should overwrite)
    # 3. Invalid record (fuelType != WIND)
    # 4. Invalid record (negative generation)
    raw_actuals = [
        {
            "dataset": "FUELHH",
            "publishTime": "2026-01-01T00:30:00Z",
            "startTime": "2026-01-01T00:00:00Z",
            "settlementDate": "2026-01-01",
            "settlementPeriod": 1,
            "fuelType": "WIND",
            "generation": 10000,
        },
        {
            "dataset": "FUELHH",
            "publishTime": "2026-01-01T01:00:00Z",  # Newer publish time
            "startTime": "2026-01-01T00:00:00Z",
            "settlementDate": "2026-01-01",
            "settlementPeriod": 1,
            "fuelType": "WIND",
            "generation": 10500,  # Updated generation
        },
        {
            "dataset": "FUELHH",
            "publishTime": "2026-01-01T00:30:00Z",
            "startTime": "2026-01-01T00:00:00Z",
            "settlementDate": "2026-01-01",
            "settlementPeriod": 1,
            "fuelType": "NUCLEAR",  # Invalid fuelType
            "generation": 5000,
        },
        {
            "dataset": "FUELHH",
            "publishTime": "2026-01-01T00:30:00Z",
            "startTime": "2026-01-01T00:30:00Z",
            "settlementDate": "2026-01-01",
            "settlementPeriod": 2,
            "fuelType": "WIND",
            "generation": -100,  # Invalid negative generation
        },
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=raw_actuals)

    client = ElexonClient(client=httpx.Client(transport=httpx.MockTransport(handler)))
    service = IngestionService(client=client, db_conn=temp_db)

    stats = service.ingest_actuals("2026-01-01", "2026-01-01", "WIND")

    assert stats.retrieved_count == 4
    assert stats.valid_count == 2  # The 2 WIND records with non-negative generation
    assert stats.unique_count == 1  # Deduplicated on (start_time, fuel_type)

    cursor = temp_db.cursor()
    cursor.execute("SELECT generation, publish_time FROM actual_generation WHERE start_time = '2026-01-01T00:00:00Z';")
    row = cursor.fetchone()
    assert row is not None
    assert row["generation"] == 10500  # The newer publish time record won
    assert row["publish_time"] == "2026-01-01T01:00:00Z"


def test_windfor_deduplication_and_validation(temp_db: sqlite3.Connection):
    raw_forecasts = [
        {
            "dataset": "WINDFOR",
            "publishTime": "2025-12-31T09:30:00Z",
            "startTime": "2026-01-01T00:00:00Z",
            "generation": 14000,
        },
        {
            "dataset": "WINDFOR",
            "publishTime": "2025-12-31T09:30:00Z",
            "startTime": "2026-01-01T00:00:00Z",  # Duplicate (pub, start) pair
            "generation": 14000,
        },
        {
            "dataset": "WINDFOR",
            "publishTime": "2025-12-31T11:30:00Z",  # Different vintage for same delivery hour
            "startTime": "2026-01-01T00:00:00Z",
            "generation": 14500,
        },
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=raw_forecasts)

    client = ElexonClient(client=httpx.Client(transport=httpx.MockTransport(handler)))
    service = IngestionService(client=client, db_conn=temp_db)

    stats = service.ingest_forecasts("2025-12-31T00:00:00Z", "2025-12-31T23:59:59Z")

    assert stats.retrieved_count == 3
    assert stats.valid_count == 3
    assert stats.unique_count == 2  # The 2 distinct (publishTime, startTime) vintages

    cursor = temp_db.cursor()
    cursor.execute("SELECT COUNT(*) FROM forecast_generation;")
    count = cursor.fetchone()[0]
    assert count == 2
