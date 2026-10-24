#!/usr/bin/env python3
"""
CLI script to execute the Elexon data ingestion and caching pipeline.
Records and prints retrieved, valid, unique, and matched record counts.
"""
import sys
import logging
from backend.app.config import (
    DEFAULT_DB_PATH,
    DELIVERY_MONTH_START,
    DELIVERY_MONTH_END,
    FORECAST_FETCH_START,
    FORECAST_FETCH_END,
)
from backend.app.db.database import init_db, get_connection
from backend.app.services.elexon_client import ElexonClient
from backend.app.services.ingestion import IngestionService
from backend.app.services.forecast_selector import ForecastSelector
from backend.app.services.metrics import calculate_metrics

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("run_ingestion")


def main():
    logger.info("Initializing database at %s...", DEFAULT_DB_PATH)
    init_db(DEFAULT_DB_PATH)
    conn = get_connection(DEFAULT_DB_PATH)

    with ElexonClient() as client:
        service = IngestionService(client=client, db_conn=conn)

        logger.info("=== STEP 1: Ingesting FUELHH Actuals (January 2026) ===")
        fuel_stats = service.ingest_actuals(
            settlement_date_from=DELIVERY_MONTH_START,
            settlement_date_to=DELIVERY_MONTH_END,
            fuel_type="WIND",
        )

        logger.info("=== STEP 2: Ingesting WINDFOR Historical Forecasts ===")
        wind_stats = service.ingest_forecasts(
            publish_date_time_from=FORECAST_FETCH_START,
            publish_date_time_to=FORECAST_FETCH_END,
        )

    # Database table verification
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM actual_generation;")
    db_actuals_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM forecast_generation;")
    db_forecasts_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(DISTINCT publish_time) FROM forecast_generation;")
    db_forecast_vintages = cursor.fetchone()[0]

    print("\n" + "=" * 70)
    print("INGESTION PIPELINE RECORD ACCOUNTING")
    print("=" * 70)
    print(f"Dataset: FUELHH Actuals (Wind)")
    print(f"  - Retrieved: {fuel_stats.retrieved_count}")
    print(f"  - Valid:     {fuel_stats.valid_count}")
    print(f"  - Unique:    {fuel_stats.unique_count}")
    print(f"  - In SQLite: {db_actuals_count}")
    print("-" * 70)
    print(f"Dataset: WINDFOR Forecasts (Historical Vintages)")
    print(f"  - Retrieved: {wind_stats.retrieved_count}")
    print(f"  - Valid:     {wind_stats.valid_count}")
    print(f"  - Unique:    {wind_stats.unique_count}")
    print(f"  - In SQLite: {db_forecasts_count}")
    print(f"  - Vintages:  {db_forecast_vintages} distinct publication runs")
    print("=" * 70)

    # Run analytical engine verification
    selector = ForecastSelector(db_conn=conn)

    print("\n" + "=" * 70)
    print("ANALYTICAL ENGINE VERIFICATION (January 2026)")
    print("=" * 70)

    # 1. Native Half-Hour Mode
    native_pairs = selector.select_forecasts_for_delivery_period(
        start_date=DELIVERY_MONTH_START,
        end_date=DELIVERY_MONTH_END,
        cutoff_time="11:00",
        alignment_mode="native_half_hour",
    )
    native_metrics = calculate_metrics(native_pairs, cutoff_time="11:00", alignment_mode="native_half_hour")

    print(f"Mode 1: Native Half-Hour Resolution (Preserves all 1,488 SPs)")
    print(f"  - Cutoff:          {native_metrics.cutoff_time} UTC on Day D-1")
    print(f"  - Total Expected:  {native_metrics.total_expected_intervals}")
    print(f"  - Matched:         {native_metrics.matched_intervals} ({native_metrics.coverage_percentage}%)")
    print(f"  - Mean Actual:     {native_metrics.mean_actual} MW")
    print(f"  - Mean Forecast:   {native_metrics.mean_forecast} MW")
    print(f"  - MAE:             {native_metrics.mae} MW")
    print(f"  - RMSE:            {native_metrics.rmse} MW")
    print(f"  - MBE (Bias):      {native_metrics.mbe} MW (Forecast - Actual)")
    print("-" * 70)

    # 2. Hourly Aggregated Mode
    hourly_pairs = selector.select_forecasts_for_delivery_period(
        start_date=DELIVERY_MONTH_START,
        end_date=DELIVERY_MONTH_END,
        cutoff_time="11:00",
        alignment_mode="hourly_aggregated",
    )
    hourly_metrics = calculate_metrics(hourly_pairs, cutoff_time="11:00", alignment_mode="hourly_aggregated")

    print(f"Mode 2: Hourly Aggregated Actuals (Mean of :00 and :30)")
    print(f"  - Cutoff:          {hourly_metrics.cutoff_time} UTC on Day D-1")
    print(f"  - Total Expected:  {hourly_metrics.total_expected_intervals}")
    print(f"  - Matched:         {hourly_metrics.matched_intervals} ({hourly_metrics.coverage_percentage}%)")
    print(f"  - Mean Actual:     {hourly_metrics.mean_actual} MW")
    print(f"  - Mean Forecast:   {hourly_metrics.mean_forecast} MW")
    print(f"  - MAE:             {hourly_metrics.mae} MW")
    print(f"  - RMSE:            {hourly_metrics.rmse} MW")
    print(f"  - MBE (Bias):      {hourly_metrics.mbe} MW (Forecast - Actual)")
    print("=" * 70 + "\n")

    conn.close()


if __name__ == "__main__":
    main()
