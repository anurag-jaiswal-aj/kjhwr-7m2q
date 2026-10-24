import pytest

from backend.app.db.models import PairedInterval
from backend.app.services.metrics import calculate_metrics


def test_missing_values_excluded_and_never_zero_filled():
    # 3 intervals:
    # Interval 1: valid actual=1000, valid forecast=1100 (error = 100)
    # Interval 2: valid actual=2000, valid forecast=2200 (error = 200)
    # Interval 3: missing forecast (None), actual=1500
    paired = [
        PairedInterval(
            start_time="2026-01-01T00:00:00Z",
            actual_generation=1000.0,
            forecast_generation=1100.0,
            error=100.0,
            is_matched=True,
        ),
        PairedInterval(
            start_time="2026-01-01T00:30:00Z",
            actual_generation=2000.0,
            forecast_generation=2200.0,
            error=200.0,
            is_matched=True,
        ),
        PairedInterval(
            start_time="2026-01-01T01:00:00Z",
            actual_generation=1500.0,
            forecast_generation=None,  # Missing forecast
            error=None,
            is_matched=False,
        ),
    ]

    metrics = calculate_metrics(paired, cutoff_time="11:00", alignment_mode="native_half_hour", total_expected_intervals=3)

    assert metrics.total_expected_intervals == 3
    assert metrics.matched_intervals == 2
    assert metrics.available_actuals == 3
    assert metrics.available_forecasts == 2
    assert metrics.coverage_percentage == round((2 / 3) * 100, 2)

    # MAE should be (100 + 200) / 2 = 150.0
    assert metrics.mae == 150.0
    # RMSE should be sqrt((100^2 + 200^2) / 2) = sqrt(25000) = 158.11
    assert metrics.rmse == 158.11
    # MBE should be (100 + 200) / 2 = 150.0
    assert metrics.mbe == 150.0

    # If missing interval 3 had been silently converted to zero:
    # error would be (0 - 1500) = -1500, causing MAE to falsely explode to (100+200+1500)/3 = 600.0!
    # We verify that our MAE is strictly 150.0, proving zero-filling was avoided.
    assert metrics.mae != 600.0


def test_legitimate_zero_generation_is_included():
    # Legitimate calm period: wind generation is actually 0 MW
    paired = [
        PairedInterval(
            start_time="2026-01-01T00:00:00Z",
            actual_generation=0.0,  # Legitimate zero outturn
            forecast_generation=300.0,
            error=300.0,
            is_matched=True,
        ),
    ]

    metrics = calculate_metrics(paired, cutoff_time="11:00", alignment_mode="native_half_hour", total_expected_intervals=1)
    assert metrics.matched_intervals == 1
    assert metrics.mae == 300.0
    assert metrics.mbe == 300.0
    assert metrics.mean_actual == 0.0
    assert metrics.mean_forecast == 300.0


def test_all_missing_intervals_returns_none_metrics():
    paired = [
        PairedInterval(
            start_time="2026-01-01T00:00:00Z",
            actual_generation=None,
            forecast_generation=None,
            error=None,
            is_matched=False,
        )
    ]
    metrics = calculate_metrics(paired, cutoff_time="11:00", alignment_mode="native_half_hour", total_expected_intervals=1)
    assert metrics.matched_intervals == 0
    assert metrics.coverage_percentage == 0.0
    assert metrics.mae is None
    assert metrics.rmse is None
    assert metrics.mbe is None
