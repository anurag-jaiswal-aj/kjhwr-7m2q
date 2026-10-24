import pytest
import sqlite3
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.api.endpoints import get_db_conn


def seed_standard_test_data(conn: sqlite3.Connection):
    """
    Seeds a controlled, reproducible test fixture spanning 2 days:
    - 2026-01-05 (4 half-hour settlement periods: SP 25, 26, 27, 28)
    - 2026-01-06 (2 half-hour settlement periods: SP 1, 2)
    And multiple forecast vintages on D-1.
    """
    cursor = conn.cursor()

    # 1. Actuals for 2026-01-05
    # Hour 12:00: SP 25 (10,000 MW), SP 26 (12,000 MW)
    cursor.execute("""
        INSERT INTO actual_generation (start_time, publish_time, settlement_date, settlement_period, fuel_type, generation)
        VALUES ('2026-01-05T12:00:00Z', '2026-01-05T12:30:00Z', '2026-01-05', 25, 'WIND', 10000);
    """)
    cursor.execute("""
        INSERT INTO actual_generation (start_time, publish_time, settlement_date, settlement_period, fuel_type, generation)
        VALUES ('2026-01-05T12:30:00Z', '2026-01-05T13:00:00Z', '2026-01-05', 26, 'WIND', 12000);
    """)
    # Hour 13:00: SP 27 (14,000 MW), SP 28 (16,000 MW)
    cursor.execute("""
        INSERT INTO actual_generation (start_time, publish_time, settlement_date, settlement_period, fuel_type, generation)
        VALUES ('2026-01-05T13:00:00Z', '2026-01-05T13:30:00Z', '2026-01-05', 27, 'WIND', 14000);
    """)
    cursor.execute("""
        INSERT INTO actual_generation (start_time, publish_time, settlement_date, settlement_period, fuel_type, generation)
        VALUES ('2026-01-05T13:30:00Z', '2026-01-05T14:00:00Z', '2026-01-05', 28, 'WIND', 16000);
    """)

    # 2. Forecasts published on D-1 (2026-01-04)
    # Target 12:00: Published at 09:30 (11,000 MW), Published at 15:30 (13,000 MW)
    cursor.execute("""
        INSERT INTO forecast_generation (publish_time, start_time, generation)
        VALUES ('2026-01-04T09:30:00Z', '2026-01-05T12:00:00Z', 11000);
    """)
    cursor.execute("""
        INSERT INTO forecast_generation (publish_time, start_time, generation)
        VALUES ('2026-01-04T15:30:00Z', '2026-01-05T12:00:00Z', 13000);
    """)
    # Target 13:00: Published at 09:30 (15,000 MW)
    cursor.execute("""
        INSERT INTO forecast_generation (publish_time, start_time, generation)
        VALUES ('2026-01-04T09:30:00Z', '2026-01-05T13:00:00Z', 15000);
    """)

    conn.commit()


# --- Requirement 1 & 2: Health Check ---

def test_health_check_success_and_dataset_availability(api_client: TestClient, temp_db: sqlite3.Connection):
    # Empty DB: dataset_available should be false
    resp = api_client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"
    assert data["dataset_available"] is False

    # Seed data
    seed_standard_test_data(temp_db)
    resp = api_client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["dataset_available"] is True


def test_health_check_database_failure(temp_db: sqlite3.Connection):
    # Simulate database failure by overriding dependency with a broken connection
    def broken_conn():
        bad = sqlite3.connect(":memory:")
        bad.close()  # Immediately closed connection causes sqlite3.ProgrammingError
        yield bad

    app.dependency_overrides[get_db_conn] = broken_conn
    with TestClient(app) as client:
        resp = client.get("/api/health")
        assert resp.status_code == 503
        data = resp.json()
        assert data["status"] == "unhealthy"
        assert data["database"] == "disconnected"
        assert data["dataset_available"] is False
    app.dependency_overrides.clear()


# --- Requirement 3: Summary Endpoint ---

def test_summary_counts_derived_from_test_data(api_client: TestClient, temp_db: sqlite3.Connection):
    seed_standard_test_data(temp_db)
    resp = api_client.get("/api/summary")
    assert resp.status_code == 200
    data = resp.json()

    assert data["actual_observation_count"] == 4
    assert data["forecast_observation_count"] == 3
    assert data["distinct_forecast_publication_timestamps"] == 2  # 09:30 and 15:30
    assert data["first_delivery_timestamp"] == "2026-01-05T12:00:00Z"
    assert data["last_delivery_timestamp"] == "2026-01-05T13:30:00Z"
    assert data["missing_or_invalid_actual_count"] == 0
    assert data["missing_or_invalid_forecast_count"] == 0
    assert data["baseline_decision_cutoff"] == "11:00"
    assert "Analytical assumption" in data["cutoff_assumption_status"]


# --- Requirement 4, 5 & 6: Metrics & Resolution ---

def test_metrics_native_half_hour_resolution(api_client: TestClient, temp_db: sqlite3.Connection):
    seed_standard_test_data(temp_db)
    # Cutoff 11:00 UTC on D-1:
    # Hour 12:00 selected forecast = 11,000 MW (09:30 vintage; 15:30 is excluded)
    #   - SP 25 (10,000 actual): error = 11,000 - 10,000 = +1,000 MW
    #   - SP 26 (12,000 actual): error = 11,000 - 12,000 = -1,000 MW
    # Hour 13:00 selected forecast = 15,000 MW
    #   - SP 27 (14,000 actual): error = 15,000 - 14,000 = +1,000 MW
    #   - SP 28 (16,000 actual): error = 15,000 - 16,000 = -1,000 MW
    # Expected:
    # Mean actual = (10k + 12k + 14k + 16k) / 4 = 13,000 MW
    # Mean forecast = (11k + 11k + 15k + 15k) / 4 = 13,000 MW
    # Errors: [+1000, -1000, +1000, -1000]
    # MAE = (|1000| + |-1000| + |1000| + |-1000|) / 4 = 1,000 MW
    # RMSE = sqrt(4 * 1000^2 / 4) = 1,000 MW
    # MBE = (1000 - 1000 + 1000 - 1000) / 4 = 0.0 MW
    resp = api_client.get("/api/metrics?start_date=2026-01-05&end_date=2026-01-05&cutoff_time=11:00&resolution=native_half_hour")
    assert resp.status_code == 200
    data = resp.json()

    assert data["matched_intervals"] == 4
    assert data["mean_actual"] == 13000.0
    assert data["mean_forecast"] == 13000.0
    assert data["mae"] == 1000.0
    assert data["rmse"] == 1000.0
    assert data["mbe"] == 0.0
    assert data["normalized_mae_percentage"] == round((1000.0 / 13000.0) * 100, 2)


def test_metrics_hourly_aggregated_mode(api_client: TestClient, temp_db: sqlite3.Connection):
    seed_standard_test_data(temp_db)
    # Hour 12:00 avg actual = (10,000 + 12,000) / 2 = 11,000 MW; forecast = 11,000 MW; error = 0
    # Hour 13:00 avg actual = (14,000 + 16,000) / 2 = 15,000 MW; forecast = 15,000 MW; error = 0
    resp = api_client.get("/api/metrics?start_date=2026-01-05&end_date=2026-01-05&cutoff_time=11:00&resolution=hourly_aggregated")
    assert resp.status_code == 200
    data = resp.json()

    assert data["matched_intervals"] == 2
    assert data["mean_actual"] == 13000.0
    assert data["mean_forecast"] == 13000.0
    assert data["mae"] == 0.0
    assert data["rmse"] == 0.0
    assert data["mbe"] == 0.0


# --- Requirement 7: Cutoff Lookahead Exclusion ---

def test_metrics_cutoff_excludes_post_deadline_forecasts(api_client: TestClient, temp_db: sqlite3.Connection):
    seed_standard_test_data(temp_db)
    # If cutoff is 11:00 on D-1, forecast published at 15:30 (13,000 MW) is excluded -> uses 09:30 (11,000 MW)
    resp11 = api_client.get("/api/metrics?start_date=2026-01-05&end_date=2026-01-05&cutoff_time=11:00")
    assert resp11.status_code == 200
    assert resp11.json()["mean_forecast"] == 13000.0  # (11k + 11k + 15k + 15k) / 4

    # If cutoff is moved to 16:00 on D-1, 15:30 forecast becomes eligible -> selected for hour 12:00
    # Mean forecast becomes (13k + 13k + 15k + 15k) / 4 = 14,000 MW
    resp16 = api_client.get("/api/metrics?start_date=2026-01-05&end_date=2026-01-05&cutoff_time=16:00")
    assert resp16.status_code == 200
    assert resp16.json()["mean_forecast"] == 14000.0


# --- Requirement 8: Month-Boundary Dates ---

def test_month_boundary_dates(api_client: TestClient, temp_db: sqlite3.Connection):
    cursor = temp_db.cursor()
    # Actual on 2026-01-01 (Jan 1)
    cursor.execute("""
        INSERT INTO actual_generation (start_time, publish_time, settlement_date, settlement_period, fuel_type, generation)
        VALUES ('2026-01-01T00:00:00Z', '2026-01-01T00:30:00Z', '2026-01-01', 1, 'WIND', 12000);
    """)
    # Forecast on Dec 31 2025 (D-1) at 09:30
    cursor.execute("""
        INSERT INTO forecast_generation (publish_time, start_time, generation)
        VALUES ('2025-12-31T09:30:00Z', '2026-01-01T00:00:00Z', 13000);
    """)
    temp_db.commit()

    resp = api_client.get("/api/metrics?start_date=2026-01-01&end_date=2026-01-01&cutoff_time=11:00")
    assert resp.status_code == 200
    data = resp.json()
    assert data["matched_intervals"] == 1
    assert data["mae"] == 1000.0


# --- Requirement 9: Parameter Validation & HTTP 400 ---

def test_invalid_dates_return_400(api_client: TestClient):
    resp = api_client.get("/api/metrics?start_date=invalid-date")
    assert resp.status_code == 400
    assert "Invalid start_date format" in resp.json()["detail"]

    # Reversed date range
    resp = api_client.get("/api/metrics?start_date=2026-01-10&end_date=2026-01-05")
    assert resp.status_code == 400
    assert "start_date must be before or equal to end_date" in resp.json()["detail"]


def test_invalid_resolution_returns_400(api_client: TestClient):
    resp = api_client.get("/api/metrics?resolution=unsupported_res")
    assert resp.status_code == 400
    assert "Unsupported resolution" in resp.json()["detail"]


def test_invalid_cutoff_time_returns_400(api_client: TestClient):
    resp = api_client.get("/api/metrics?cutoff_time=25:00")
    assert resp.status_code == 400
    assert "Invalid cutoff_time" in resp.json()["detail"]


# --- Requirement 10: Empty / Missing Data Safety ---

def test_empty_dataset_safe_response(api_client: TestClient):
    # Query a range with no data
    resp = api_client.get("/api/metrics?start_date=2026-05-01&end_date=2026-05-02")
    assert resp.status_code == 200
    data = resp.json()
    assert data["matched_intervals"] == 0
    assert data["coverage_percentage"] == 0.0
    assert data["mae"] is None
    assert data["rmse"] is None
    assert data["mbe"] is None


# --- Requirement 11: Timeseries Ordering & Format ---

def test_timeseries_chronological_ordering(api_client: TestClient, temp_db: sqlite3.Connection):
    seed_standard_test_data(temp_db)
    resp = api_client.get("/api/timeseries?start_date=2026-01-05&end_date=2026-01-05")
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 4
    data = body["data"]

    # Verify chronological order
    timestamps = [d["start_time"] for d in data]
    assert timestamps == sorted(timestamps)
    assert data[0]["start_time"] == "2026-01-05T12:00:00Z"
    assert data[0]["settlement_period"] == 25
    assert data[0]["actual_generation"] == 10000.0
    assert data[0]["forecast_generation"] == 11000.0
    assert data[0]["error"] == 1000.0
    assert data[0]["is_matched"] is True


# --- Requirement 12: Daily Metrics & Incomplete Coverage ---

def test_daily_metrics_identifies_incomplete_coverage(api_client: TestClient, temp_db: sqlite3.Connection):
    seed_standard_test_data(temp_db)
    resp = api_client.get("/api/daily-metrics?start_date=2026-01-05&end_date=2026-01-05&resolution=native_half_hour")
    assert resp.status_code == 200
    days = resp.json()["days"]
    assert len(days) == 1
    d = days[0]
    assert d["date"] == "2026-01-05"
    assert d["matched_intervals"] == 4
    # In native mode, a complete day has 48 intervals; 4 intervals is incomplete
    assert d["is_complete"] is False


# --- Requirement 13: Forecast Evolution ---

def test_forecast_evolution_chronological_revisions(api_client: TestClient, temp_db: sqlite3.Connection):
    seed_standard_test_data(temp_db)
    resp = api_client.get("/api/forecast-evolution?start_time=2026-01-05T12:00:00Z")
    assert resp.status_code == 200
    data = resp.json()
    assert data["target_start_time"] == "2026-01-05T12:00:00Z"
    assert data["revisions_count"] == 2
    revs = data["revisions"]
    # Earliest published first
    assert revs[0]["publish_time"] == "2026-01-04T09:30:00Z"
    assert revs[0]["generation"] == 11000
    assert revs[1]["publish_time"] == "2026-01-04T15:30:00Z"
    assert revs[1]["generation"] == 13000


def test_forecast_evolution_multi_vintage_cutoff_isolation(api_client: TestClient, temp_db: sqlite3.Connection):
    """
    Audit Test: Verifies that forecast evolution returns all historical vintages for
    a delivery interval in publication order, but the day-ahead metrics strictly use
    only the vintage satisfying the configured D-1 cutoff (zero lookahead bias).
    """
    cursor = temp_db.cursor()
    delivery_time = "2026-01-15T12:00:00Z"
    delivery_time_half = "2026-01-15T12:30:00Z"

    # Actuals for both half-hours
    cursor.execute("""
        INSERT INTO actual_generation (start_time, publish_time, settlement_date, settlement_period, fuel_type, generation)
        VALUES ('2026-01-15T12:00:00Z', '2026-01-15T12:30:00Z', '2026-01-15', 25, 'WIND', 9742);
    """)
    cursor.execute("""
        INSERT INTO actual_generation (start_time, publish_time, settlement_date, settlement_period, fuel_type, generation)
        VALUES ('2026-01-15T12:30:00Z', '2026-01-15T13:00:00Z', '2026-01-15', 26, 'WIND', 9839);
    """)

    # Vintages published across multiple days:
    # 1. D-2 run (eligible)
    cursor.execute("INSERT INTO forecast_generation (publish_time, start_time, generation) VALUES ('2026-01-13T09:30:00Z', '2026-01-15T12:00:00Z', 11749);")
    # 2. D-1 pre-cutoff run at 09:30 (latest eligible under 11:00 cutoff)
    cursor.execute("INSERT INTO forecast_generation (publish_time, start_time, generation) VALUES ('2026-01-14T09:30:00Z', '2026-01-15T12:00:00Z', 11178);")
    # 3. D-1 post-cutoff run at 15:30 (ineligible under 11:00 cutoff)
    cursor.execute("INSERT INTO forecast_generation (publish_time, start_time, generation) VALUES ('2026-01-14T15:30:00Z', '2026-01-15T12:00:00Z', 11854);")
    # 4. Delivery day run at 04:30 (ineligible)
    cursor.execute("INSERT INTO forecast_generation (publish_time, start_time, generation) VALUES ('2026-01-15T04:30:00Z', '2026-01-15T12:00:00Z', 10693);")
    temp_db.commit()

    # 1. Check Evolution endpoint returns all 4 vintages in publication order
    resp_evo = api_client.get(f"/api/forecast-evolution?start_time={delivery_time}")
    assert resp_evo.status_code == 200
    evo_data = resp_evo.json()
    assert evo_data["revisions_count"] == 4
    revs = evo_data["revisions"]
    assert [r["generation"] for r in revs] == [11749, 11178, 11854, 10693]
    # Verify every vintage belongs to the exact same target start_time
    for r in revs:
        assert r["start_time"] == delivery_time

    # 2. Check Timeseries endpoint with cutoff 11:00 on D-1
    # MUST select vintage 2 (11,178 MW) published at 09:30, NOT 11,854 MW (15:30) or 10,693 MW (delivery day)
    resp_ts = api_client.get("/api/timeseries?start_date=2026-01-15&end_date=2026-01-15&cutoff_time=11:00")
    assert resp_ts.status_code == 200
    ts_data = resp_ts.json()["data"]
    assert len(ts_data) == 2
    for interval in ts_data:
        assert interval["forecast_generation"] == 11178.0
        assert interval["forecast_publish_time"] == "2026-01-14T09:30:00Z"
    # SP 25 actual = 9,742 -> error = 11,178 - 9,742 = +1,436 MW
    assert ts_data[0]["error"] == 1436.0
    # SP 26 actual = 9,839 -> error = 11,178 - 9,839 = +1,339 MW
    assert ts_data[1]["error"] == 1339.0
