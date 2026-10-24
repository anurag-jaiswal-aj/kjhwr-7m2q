import pytest
import sqlite3
from datetime import datetime, timedelta

from backend.app.services.forecast_selector import ForecastSelector


def test_forecast_selector_zero_lookahead_and_boundary(temp_db: sqlite3.Connection):
    cursor = temp_db.cursor()
    # Insert actuals for 2026-01-05
    # SP 1: 00:00 to 00:30
    cursor.execute("""
        INSERT INTO actual_generation (start_time, publish_time, settlement_date, settlement_period, fuel_type, generation)
        VALUES ('2026-01-05T00:00:00Z', '2026-01-05T00:30:00Z', '2026-01-05', 1, 'WIND', 10000);
    """)

    # Insert multiple forecast vintages published on D-1 (2026-01-04) forecasting 2026-01-05T00:00:00Z
    # 1. Early morning: 09:30
    cursor.execute("""
        INSERT INTO forecast_generation (publish_time, start_time, generation)
        VALUES ('2026-01-04T09:30:00Z', '2026-01-05T00:00:00Z', 12000);
    """)
    # 2. Exact boundary: 11:00:00
    cursor.execute("""
        INSERT INTO forecast_generation (publish_time, start_time, generation)
        VALUES ('2026-01-04T11:00:00Z', '2026-01-05T00:00:00Z', 12500);
    """)
    # 3. Post-cutoff: 11:00:01 (1 second after deadline)
    cursor.execute("""
        INSERT INTO forecast_generation (publish_time, start_time, generation)
        VALUES ('2026-01-04T11:00:01Z', '2026-01-05T00:00:00Z', 13000);
    """)
    # 4. Afternoon: 15:30
    cursor.execute("""
        INSERT INTO forecast_generation (publish_time, start_time, generation)
        VALUES ('2026-01-04T15:30:00Z', '2026-01-05T00:00:00Z', 14000);
    """)
    temp_db.commit()

    selector = ForecastSelector(db_conn=temp_db)

    # Cutoff 1: 11:00 on D-1
    # Eligible: 09:30 (12000) and 11:00:00 (12500)
    # The 11:00:01 and 15:30 forecasts MUST NOT be selected
    pairs_11 = selector.select_forecasts_for_delivery_period(
        start_date="2026-01-05",
        end_date="2026-01-05",
        cutoff_time="11:00",
    )
    assert len(pairs_11) == 1
    p11 = pairs_11[0]
    assert p11.is_matched is True
    assert p11.forecast_publish_time == "2026-01-04T11:00:00Z"
    assert p11.forecast_generation == 12500.0
    assert p11.error == 2500.0  # 12500 - 10000

    # Cutoff 2: 10:00 on D-1
    # Only 09:30 is eligible
    pairs_10 = selector.select_forecasts_for_delivery_period(
        start_date="2026-01-05",
        end_date="2026-01-05",
        cutoff_time="10:00",
    )
    assert len(pairs_10) == 1
    p10 = pairs_10[0]
    assert p10.is_matched is True
    assert p10.forecast_publish_time == "2026-01-04T09:30:00Z"
    assert p10.forecast_generation == 12000.0

    # Cutoff 3: 16:00 on D-1
    # 15:30 is eligible and is the latest
    pairs_16 = selector.select_forecasts_for_delivery_period(
        start_date="2026-01-05",
        end_date="2026-01-05",
        cutoff_time="16:00",
    )
    assert len(pairs_16) == 1
    p16 = pairs_16[0]
    assert p16.is_matched is True
    assert p16.forecast_publish_time == "2026-01-04T15:30:00Z"
    assert p16.forecast_generation == 14000.0


def test_no_eligible_forecast_leaves_null(temp_db: sqlite3.Connection):
    cursor = temp_db.cursor()
    cursor.execute("""
        INSERT INTO actual_generation (start_time, publish_time, settlement_date, settlement_period, fuel_type, generation)
        VALUES ('2026-01-05T00:00:00Z', '2026-01-05T00:30:00Z', '2026-01-05', 1, 'WIND', 10000);
    """)
    # Only insert a forecast published on D (2026-01-05T02:30:00Z) - completely intraday
    cursor.execute("""
        INSERT INTO forecast_generation (publish_time, start_time, generation)
        VALUES ('2026-01-05T02:30:00Z', '2026-01-05T00:00:00Z', 11000);
    """)
    temp_db.commit()

    selector = ForecastSelector(db_conn=temp_db)
    pairs = selector.select_forecasts_for_delivery_period(
        start_date="2026-01-05",
        end_date="2026-01-05",
        cutoff_time="11:00",
    )
    assert len(pairs) == 1
    p = pairs[0]
    assert p.is_matched is False
    assert p.forecast_generation is None
    assert p.error is None
    assert p.actual_generation == 10000.0
    # Crucial assertion: never converted to 0 MW!
    assert p.forecast_generation != 0


def test_month_boundary_december_to_january(temp_db: sqlite3.Connection):
    """
    Verifies that for delivery on 2026-01-01 (New Year's Day), the day-ahead
    deadline is correctly computed as 2025-12-31 at cutoff, and eligible
    forecasts published in December 2025 are selected.
    """
    cursor = temp_db.cursor()
    # SP 1 on Jan 1 2026
    cursor.execute("""
        INSERT INTO actual_generation (start_time, publish_time, settlement_date, settlement_period, fuel_type, generation)
        VALUES ('2026-01-01T00:00:00Z', '2026-01-01T00:30:00Z', '2026-01-01', 1, 'WIND', 13756);
    """)

    # Forecast published Dec 31 2025 at 09:30
    cursor.execute("""
        INSERT INTO forecast_generation (publish_time, start_time, generation)
        VALUES ('2025-12-31T09:30:00Z', '2026-01-01T00:00:00Z', 19960);
    """)
    # Forecast published Dec 31 2025 at 15:30 (after 11:00 cutoff)
    cursor.execute("""
        INSERT INTO forecast_generation (publish_time, start_time, generation)
        VALUES ('2025-12-31T15:30:00Z', '2026-01-01T00:00:00Z', 18500);
    """)
    temp_db.commit()

    selector = ForecastSelector(db_conn=temp_db)
    pairs = selector.select_forecasts_for_delivery_period(
        start_date="2026-01-01",
        end_date="2026-01-01",
        cutoff_time="11:00",
    )
    assert len(pairs) == 1
    p = pairs[0]
    assert p.is_matched is True
    assert p.forecast_publish_time == "2025-12-31T09:30:00Z"
    assert p.forecast_generation == 19960.0
    assert p.error == 19960.0 - 13756.0


def test_full_january_dataset_lookahead_invariant():
    """
    Verifies that across all 1,488 half-hour settlement periods in January 2026
    in the seeded SQLite database, EVERY selected forecast has publish_time <= deadline.
    """
    from backend.app.config import DEFAULT_DB_PATH
    import os
    if not os.path.exists(DEFAULT_DB_PATH):
        pytest.skip("Database not seeded yet")

    conn = sqlite3.connect(DEFAULT_DB_PATH)
    conn.row_factory = sqlite3.Row
    selector = ForecastSelector(db_conn=conn)

    pairs = selector.select_forecasts_for_delivery_period(
        start_date="2026-01-01",
        end_date="2026-01-31",
        cutoff_time="11:00",
        alignment_mode="native_half_hour",
    )
    conn.close()

    assert len(pairs) == 1488
    for p in pairs:
        assert p.is_matched is True
        # Target day
        deliv_date = p.start_time[:10]
        deliv_dt = datetime.strptime(deliv_date, "%Y-%m-%d")
        deadline = (deliv_dt - timedelta(days=1)).strftime("%Y-%m-%dT11:00:00Z")
        assert p.forecast_publish_time <= deadline, f"Lookahead violation: {p.forecast_publish_time} > {deadline}"


def test_january_15_1200_ground_truth_selection():
    """
    Focused regression test resolving the Stage 5 vs Stage 6 audit inquiry for delivery hour
    2026-01-15T12:00:00Z under the D-1 11:00 UTC cutoff:
    - 2026-01-13T04:30:00Z (D-2) published 11,888 MW (superseded by later D-1 publications)
    - 2026-01-14T09:30:00Z (D-1 pre-cutoff) published 11,178 MW (LATEST eligible vintage)
    - 2026-01-14T11:30:00Z (D-1 post-cutoff) published 11,351 MW (excluded by cutoff)
    The selected forecast MUST be 11,178.0 MW published at 2026-01-14T09:30:00Z.
    """
    from backend.app.config import DEFAULT_DB_PATH
    import os
    if not os.path.exists(DEFAULT_DB_PATH):
        pytest.skip("Database not seeded yet")

    conn = sqlite3.connect(DEFAULT_DB_PATH)
    conn.row_factory = sqlite3.Row
    selector = ForecastSelector(db_conn=conn)

    pairs = selector.select_forecasts_for_delivery_period(
        start_date="2026-01-15",
        end_date="2026-01-15",
        cutoff_time="11:00",
        alignment_mode="native_half_hour",
    )
    conn.close()

    # Find SP 25 (12:00 to 12:30) and SP 26 (12:30 to 13:00)
    sp25 = next(p for p in pairs if p.settlement_period == 25)
    sp26 = next(p for p in pairs if p.settlement_period == 26)

    # Both half-hours map to the parent 12:00:00Z hour
    assert sp25.forecast_generation == 11178.0
    assert sp25.forecast_publish_time == "2026-01-14T09:30:00Z"
    assert sp25.actual_generation == 9742.0
    assert sp25.error == 11178.0 - 9742.0  # +1436.0 MW

    assert sp26.forecast_generation == 11178.0
    assert sp26.forecast_publish_time == "2026-01-14T09:30:00Z"
    assert sp26.actual_generation == 9839.0
    assert sp26.error == 11178.0 - 9839.0  # +1339.0 MW

