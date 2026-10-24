import sqlite3
import logging
from typing import Generator
from fastapi import APIRouter, Depends, Query, Response, status, HTTPException

from backend.app.config import (
    DEFAULT_DB_PATH,
    DELIVERY_MONTH_START,
    DELIVERY_MONTH_END,
    DEFAULT_DECISION_CUTOFF_TIME,
)
from backend.app.db.database import get_connection
from backend.app.db.models import MetricsSummary
from backend.app.services.forecast_selector import ForecastSelector
from backend.app.services.metrics import calculate_metrics, calculate_daily_metrics
from backend.app.api.schemas import (
    HealthResponse,
    DatasetSummaryResponse,
    TimeSeriesResponse,
    DailyMetricsResponse,
    DailyMetricsItem,
    ForecastEvolutionResponse,
    ForecastRevisionItem,
)
from backend.app.api.validation import (
    validate_date_str,
    validate_date_range,
    validate_resolution,
    validate_cutoff_time,
    validate_iso_timestamp,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def get_db_conn() -> Generator[sqlite3.Connection, None, None]:
    """
    FastAPI dependency that yields a managed SQLite connection.
    Overridable in automated test suites with isolated test databases.
    """
    conn = get_connection(DEFAULT_DB_PATH)
    try:
        yield conn
    finally:
        conn.close()


@router.get("/health", response_model=HealthResponse, summary="API and Database Health Check")
def health_check(response: Response, db: sqlite3.Connection = Depends(get_db_conn)) -> HealthResponse:
    """
    Checks API status, database connectivity, and dataset availability.
    A database failure is explicitly reported as unhealthy with HTTP 503.
    Does not expose sensitive credentials, filesystem paths, or stack traces.
    """
    try:
        cursor = db.cursor()
        cursor.execute("SELECT 1;")
        cursor.fetchone()

        # Check if required January 2026 dataset is available
        cursor.execute(
            """
            SELECT COUNT(*) FROM actual_generation
            WHERE settlement_date >= ? AND settlement_date <= ? AND fuel_type = 'WIND';
            """,
            (DELIVERY_MONTH_START, DELIVERY_MONTH_END),
        )
        count = cursor.fetchone()[0]
        dataset_available = bool(count > 0)
        dataset_period = f"{DELIVERY_MONTH_START} to {DELIVERY_MONTH_END}" if dataset_available else None

        return HealthResponse(
            status="healthy",
            database="connected",
            dataset_available=dataset_available,
            dataset_period=dataset_period,
        )
    except Exception as e:
        logger.error("Health check database failure: %s", e)
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return HealthResponse(
            status="unhealthy",
            database="disconnected",
            dataset_available=False,
            dataset_period=None,
        )


@router.get("/summary", response_model=DatasetSummaryResponse, summary="Dataset Key Facts and Metadata")
def get_dataset_summary(db: sqlite3.Connection = Depends(get_db_conn)) -> DatasetSummaryResponse:
    """
    Returns core dataset facts computed dynamically from the persisted database:
    observation counts, delivery timestamp boundaries, missing data statistics,
    and baseline cutoff assumption details.
    """
    cursor = db.cursor()

    cursor.execute("SELECT COUNT(*) FROM actual_generation WHERE fuel_type = 'WIND';")
    actual_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM forecast_generation;")
    forecast_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(DISTINCT publish_time) FROM forecast_generation;")
    distinct_pubs = cursor.fetchone()[0]

    cursor.execute("SELECT MIN(start_time), MAX(start_time) FROM actual_generation WHERE fuel_type = 'WIND';")
    first_deliv, last_deliv = cursor.fetchone()

    cursor.execute("SELECT COUNT(*) FROM actual_generation WHERE generation IS NULL OR generation < 0;")
    invalid_actual = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM forecast_generation WHERE generation IS NULL OR generation < 0;")
    invalid_forecast = cursor.fetchone()[0]

    return DatasetSummaryResponse(
        evaluation_period={"start_date": DELIVERY_MONTH_START, "end_date": DELIVERY_MONTH_END},
        actual_observation_count=actual_count,
        forecast_observation_count=forecast_count,
        distinct_forecast_publication_timestamps=distinct_pubs,
        first_delivery_timestamp=first_deliv,
        last_delivery_timestamp=last_deliv,
        missing_or_invalid_actual_count=invalid_actual,
        missing_or_invalid_forecast_count=invalid_forecast,
        baseline_decision_cutoff=DEFAULT_DECISION_CUTOFF_TIME,
        cutoff_assumption_status="Analytical assumption (modeled on GB Day-Ahead auction conventions; not an official Elexon rule)",
    )


@router.get("/metrics", response_model=MetricsSummary, summary="Forecast Accuracy Statistical Metrics")
def get_forecast_metrics(
    start_date: str = Query(DELIVERY_MONTH_START, description="Evaluation start date (YYYY-MM-DD)"),
    end_date: str = Query(DELIVERY_MONTH_END, description="Evaluation end date (YYYY-MM-DD)"),
    resolution: str = Query("native_half_hour", description="Resolution: 'native_half_hour' (or 'half_hour') or 'hourly_aggregated' (or 'hourly')"),
    cutoff_time: str = Query(DEFAULT_DECISION_CUTOFF_TIME, description="Decision deadline time in UTC (HH:MM) on Day D-1"),
    db: sqlite3.Connection = Depends(get_db_conn),
) -> MetricsSummary:
    """
    Computes MAE, RMSE, MBE, and coverage metrics for the requested window.
    Strictly enforces zero lookahead bias and preserves nulls without zero-filling.
    """
    valid_start = validate_date_str(start_date, "start_date")
    valid_end = validate_date_str(end_date, "end_date")
    validate_date_range(valid_start, valid_end)
    valid_res = validate_resolution(resolution)
    valid_cutoff = validate_cutoff_time(cutoff_time)

    selector = ForecastSelector(db_conn=db)
    paired = selector.select_forecasts_for_delivery_period(
        start_date=valid_start,
        end_date=valid_end,
        cutoff_time=valid_cutoff,
        alignment_mode=valid_res,
    )

    metrics = calculate_metrics(
        paired_intervals=paired,
        cutoff_time=valid_cutoff,
        alignment_mode=valid_res,
        start_date=valid_start,
        end_date=valid_end,
    )
    return metrics


@router.get("/timeseries", response_model=TimeSeriesResponse, summary="Chronological Paired Actual and Forecast Observations")
def get_timeseries(
    start_date: str = Query(DELIVERY_MONTH_START, description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(DELIVERY_MONTH_END, description="End date (YYYY-MM-DD)"),
    resolution: str = Query("native_half_hour", description="Resolution: 'native_half_hour' or 'hourly_aggregated'"),
    cutoff_time: str = Query(DEFAULT_DECISION_CUTOFF_TIME, description="Decision deadline time in UTC (HH:MM) on Day D-1"),
    db: sqlite3.Connection = Depends(get_db_conn),
) -> TimeSeriesResponse:
    """
    Returns paired chronological observations of actual generation and selected day-ahead forecasts
    suitable for frontend charting. Does not interpolate or fabricate missing values.
    """
    valid_start = validate_date_str(start_date, "start_date")
    valid_end = validate_date_str(end_date, "end_date")
    validate_date_range(valid_start, valid_end)
    valid_res = validate_resolution(resolution)
    valid_cutoff = validate_cutoff_time(cutoff_time)

    selector = ForecastSelector(db_conn=db)
    paired = selector.select_forecasts_for_delivery_period(
        start_date=valid_start,
        end_date=valid_end,
        cutoff_time=valid_cutoff,
        alignment_mode=valid_res,
    )

    return TimeSeriesResponse(
        resolution=valid_res,
        cutoff_time=valid_cutoff,
        start_date=valid_start,
        end_date=valid_end,
        count=len(paired),
        data=paired,
    )


@router.get("/daily-metrics", response_model=DailyMetricsResponse, summary="Daily Accuracy Breakdown")
def get_daily_metrics(
    start_date: str = Query(DELIVERY_MONTH_START, description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(DELIVERY_MONTH_END, description="End date (YYYY-MM-DD)"),
    resolution: str = Query("native_half_hour", description="Resolution: 'native_half_hour' or 'hourly_aggregated'"),
    cutoff_time: str = Query(DEFAULT_DECISION_CUTOFF_TIME, description="Decision deadline time in UTC (HH:MM) on Day D-1"),
    db: sqlite3.Connection = Depends(get_db_conn),
) -> DailyMetricsResponse:
    """
    Returns day-by-day aggregated accuracy metrics, distinguishing complete days from incomplete days.
    """
    valid_start = validate_date_str(start_date, "start_date")
    valid_end = validate_date_str(end_date, "end_date")
    validate_date_range(valid_start, valid_end)
    valid_res = validate_resolution(resolution)
    valid_cutoff = validate_cutoff_time(cutoff_time)

    selector = ForecastSelector(db_conn=db)
    paired = selector.select_forecasts_for_delivery_period(
        start_date=valid_start,
        end_date=valid_end,
        cutoff_time=valid_cutoff,
        alignment_mode=valid_res,
    )

    daily_raw = calculate_daily_metrics(paired_intervals=paired, alignment_mode=valid_res)
    daily_items = [DailyMetricsItem(**item) for item in daily_raw]

    return DailyMetricsResponse(
        cutoff_time=valid_cutoff,
        resolution=valid_res,
        start_date=valid_start,
        end_date=valid_end,
        days_count=len(daily_items),
        days=daily_items,
    )


@router.get("/forecast-evolution", response_model=ForecastEvolutionResponse, summary="Historical Forecast Revisions for Target Hour")
def get_forecast_evolution(
    start_time: str = Query(..., description="Target delivery interval (ISO 8601 UTC timestamp, e.g. '2026-01-15T12:00:00Z')"),
    db: sqlite3.Connection = Depends(get_db_conn),
) -> ForecastEvolutionResponse:
    """
    Returns all historical forecast revisions in chronological publication order for a target delivery hour.
    Demonstrates the progression of meteorological model runs from 2.5 days ahead down to gate closure.
    """
    valid_time = validate_iso_timestamp(start_time, "start_time")

    cursor = db.cursor()
    # Query exact target start_time
    cursor.execute(
        """
        SELECT publish_time, start_time, generation
        FROM forecast_generation
        WHERE start_time = ?
        ORDER BY publish_time ASC;
        """,
        (valid_time,),
    )
    rows = cursor.fetchall()

    # If no exact match and minutes were ':30', check parent hour ':00'
    if not rows and valid_time[14:16] != "00":
        hour_parent = valid_time[:14] + "00:00Z"
        cursor.execute(
            """
            SELECT publish_time, start_time, generation
            FROM forecast_generation
            WHERE start_time = ?
            ORDER BY publish_time ASC;
            """,
            (hour_parent,),
        )
        rows = cursor.fetchall()

    revisions = [
        ForecastRevisionItem(
            publish_time=r["publish_time"],
            start_time=r["start_time"],
            generation=r["generation"],
        )
        for r in rows
    ]

    return ForecastEvolutionResponse(
        target_start_time=valid_time,
        revisions_count=len(revisions),
        revisions=revisions,
    )
