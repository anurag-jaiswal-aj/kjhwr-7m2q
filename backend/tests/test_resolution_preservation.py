import pytest
import sqlite3

from backend.app.services.forecast_selector import ForecastSelector


def test_native_half_hour_resolution_preserves_both_half_hours(temp_db: sqlite3.Connection):
    cursor = temp_db.cursor()
    # Insert two 30-minute settlement periods for the hour 12:00-13:00 on 2026-01-10
    # SP 25: 12:00 to 12:30
    cursor.execute("""
        INSERT INTO actual_generation (start_time, publish_time, settlement_date, settlement_period, fuel_type, generation)
        VALUES ('2026-01-10T12:00:00Z', '2026-01-10T12:30:00Z', '2026-01-10', 25, 'WIND', 8000);
    """)
    # SP 26: 12:30 to 13:00
    cursor.execute("""
        INSERT INTO actual_generation (start_time, publish_time, settlement_date, settlement_period, fuel_type, generation)
        VALUES ('2026-01-10T12:30:00Z', '2026-01-10T13:00:00Z', '2026-01-10', 26, 'WIND', 9000);
    """)

    # Insert prevailing hourly forecast for 12:00:00Z published on D-1 09:30
    cursor.execute("""
        INSERT INTO forecast_generation (publish_time, start_time, generation)
        VALUES ('2026-01-09T09:30:00Z', '2026-01-10T12:00:00Z', 10000);
    """)
    temp_db.commit()

    selector = ForecastSelector(db_conn=temp_db)

    # 1. Native Half-Hour Mode
    pairs_hh = selector.select_forecasts_for_delivery_period(
        start_date="2026-01-10",
        end_date="2026-01-10",
        cutoff_time="11:00",
        alignment_mode="native_half_hour",
    )
    # Both half-hour intervals must be present (none discarded!)
    assert len(pairs_hh) == 2
    
    # SP 25 (:00)
    sp25 = next(p for p in pairs_hh if p.settlement_period == 25)
    assert sp25.start_time == "2026-01-10T12:00:00Z"
    assert sp25.actual_generation == 8000.0
    assert sp25.forecast_generation == 10000.0
    assert sp25.error == 2000.0  # 10000 - 8000

    # SP 26 (:30) - preserved and associated with prevailing hourly forecast!
    sp26 = next(p for p in pairs_hh if p.settlement_period == 26)
    assert sp26.start_time == "2026-01-10T12:30:00Z"
    assert sp26.actual_generation == 9000.0
    assert sp26.forecast_generation == 10000.0
    assert sp26.error == 1000.0  # 10000 - 9000

    # 2. Hourly Aggregated Mode
    pairs_hourly = selector.select_forecasts_for_delivery_period(
        start_date="2026-01-10",
        end_date="2026-01-10",
        cutoff_time="11:00",
        alignment_mode="hourly_aggregated",
    )
    assert len(pairs_hourly) == 1
    p_hour = pairs_hourly[0]
    assert p_hour.start_time == "2026-01-10T12:00:00Z"
    # Average of 8000 and 9000 is 8500
    assert p_hour.actual_generation == 8500.0
    assert p_hour.forecast_generation == 10000.0
    assert p_hour.error == 1500.0  # 10000 - 8500
