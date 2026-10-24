import math
import pytest
import sqlite3

from backend.app.config import DEFAULT_DB_PATH
from backend.app.db.models import PairedInterval
from backend.app.services.metrics import calculate_metrics, calculate_daily_metrics
from backend.app.services.forecast_selector import ForecastSelector


def test_metric_mathematical_invariants():
    # Test across an arbitrary synthetic distribution of errors
    synthetic_errors = [-500.0, 200.0, -100.0, 450.0, 0.0, 800.0, -250.0, 300.0]
    paired = [
        PairedInterval(
            start_time=f"2026-01-01T{i:02d}:00:00Z",
            actual_generation=1000.0,
            forecast_generation=1000.0 + err,
            error=err,
            is_matched=True,
        )
        for i, err in enumerate(synthetic_errors)
    ]

    metrics = calculate_metrics(paired, cutoff_time="11:00", alignment_mode="native_half_hour", total_expected_intervals=len(synthetic_errors))

    # Invariant 1: Non-negativity
    assert metrics.mae >= 0
    assert metrics.rmse >= 0

    # Invariant 2: Cauchy-Schwarz inequality (RMSE >= MAE)
    assert metrics.rmse >= metrics.mae

    # Invariant 3: Triangular inequality (MAE >= |MBE|)
    assert metrics.mae >= abs(metrics.mbe)

    # Invariant 4: Independent dynamic computation matches
    expected_mae = sum(abs(e) for e in synthetic_errors) / len(synthetic_errors)
    expected_rmse = math.sqrt(sum(e ** 2 for e in synthetic_errors) / len(synthetic_errors))
    expected_mbe = sum(synthetic_errors) / len(synthetic_errors)

    assert metrics.mae == round(expected_mae, 2)
    assert metrics.rmse == round(expected_rmse, 2)
    assert metrics.mbe == round(expected_mbe, 2)


def test_daily_metrics_breakdown():
    paired = [
        PairedInterval(
            start_time="2026-01-01T12:00:00Z",
            actual_generation=1000.0,
            forecast_generation=1200.0,
            error=200.0,
            is_matched=True,
        ),
        PairedInterval(
            start_time="2026-01-01T12:30:00Z",
            actual_generation=1000.0,
            forecast_generation=1100.0,
            error=100.0,
            is_matched=True,
        ),
        PairedInterval(
            start_time="2026-01-02T12:00:00Z",
            actual_generation=2000.0,
            forecast_generation=2300.0,
            error=300.0,
            is_matched=True,
        ),
    ]

    daily = calculate_daily_metrics(paired)
    assert len(daily) == 2

    d1 = next(d for d in daily if d["date"] == "2026-01-01")
    assert d1["matched_intervals"] == 2
    assert d1["mae"] == 150.0  # (200 + 100) / 2
    assert d1["mbe"] == 150.0

    d2 = next(d for d in daily if d["date"] == "2026-01-02")
    assert d2["matched_intervals"] == 1
    assert d2["mae"] == 300.0


def test_dynamic_recalculation_on_january_2026_data():
    """
    Tests dynamic calculation directly on processed SQLite data without
    relying on hardcoded metrics as expectations.
    """
    conn = sqlite3.connect(DEFAULT_DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM actual_generation;")
    count = cursor.fetchone()[0]

    if count == 0:
        pytest.skip("SQLite database has not been seeded yet. Run run_ingestion.py first.")

    selector = ForecastSelector(db_conn=conn)
    pairs = selector.select_forecasts_for_delivery_period(
        start_date="2026-01-01",
        end_date="2026-01-31",
        cutoff_time="11:00",
        alignment_mode="native_half_hour",
    )
    conn.close()

    metrics = calculate_metrics(pairs, cutoff_time="11:00", alignment_mode="native_half_hour")

    # Verify data coverage
    assert metrics.total_expected_intervals == 1488
    assert metrics.matched_intervals == 1488
    assert metrics.coverage_percentage == 100.0

    # Verify mathematical invariants hold dynamically on real data
    assert metrics.mae > 0
    assert metrics.rmse >= metrics.mae
    assert metrics.mae >= abs(metrics.mbe)

    # Dynamic calculation check: compute directly and assert exact equality
    raw_errors = [p.error for p in pairs if p.is_matched]
    assert len(raw_errors) == 1488
    dyn_mae = sum(abs(e) for e in raw_errors) / len(raw_errors)
    dyn_rmse = math.sqrt(sum(e ** 2 for e in raw_errors) / len(raw_errors))
    dyn_mbe = sum(raw_errors) / len(raw_errors)

    assert metrics.mae == round(dyn_mae, 2)
    assert metrics.rmse == round(dyn_rmse, 2)
    assert metrics.mbe == round(dyn_mbe, 2)
