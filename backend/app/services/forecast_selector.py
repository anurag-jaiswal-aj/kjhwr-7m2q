import sqlite3
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Tuple
from collections import defaultdict

from backend.app.db.models import PairedInterval
from backend.app.config import (
    DELIVERY_MONTH_START,
    DELIVERY_MONTH_END,
    DEFAULT_DECISION_CUTOFF_TIME,
)


class ForecastSelector:
    """
    Deterministic forecast selection engine that enforces the decision cutoff deadline,
    eliminates lookahead bias, and preserves native half-hourly actual resolution.
    """

    def __init__(self, db_conn: sqlite3.Connection):
        self.conn = db_conn

    def _get_decision_deadline(self, delivery_date_str: str, cutoff_time: str) -> str:
        """
        Computes the decision deadline timestamp (ISO UTC).
        Decision deadline is (Delivery Day - 1 day) at <cutoff_time> UTC.
        Example: Delivery 2026-01-05 with cutoff 11:00 -> 2026-01-04T11:00:00Z.
        """
        deliv_dt = datetime.strptime(delivery_date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        prev_day = deliv_dt - timedelta(days=1)
        # Parse cutoff_time (e.g. "11:00" or "11:00:00")
        parts = cutoff_time.strip().split(":")
        hour = int(parts[0])
        minute = int(parts[1]) if len(parts) > 1 else 0
        second = int(parts[2]) if len(parts) > 2 else 0
        deadline_dt = prev_day.replace(hour=hour, minute=minute, second=second)
        return deadline_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    def _load_forecast_index(
        self,
        min_start: Optional[str] = None,
        max_start: Optional[str] = None,
    ) -> Dict[str, List[Tuple[str, int]]]:
        """
        Loads forecast generation records into a dictionary indexed by target start_time.
        Value is a sorted list of (publish_time, generation) in descending publish_time order.
        Optionally bounded by min_start and max_start.
        """
        cursor = self.conn.cursor()
        if min_start and max_start:
            cursor.execute(
                """
                SELECT start_time, publish_time, generation
                FROM forecast_generation
                WHERE start_time >= ? AND start_time <= ?
                ORDER BY start_time, publish_time DESC;
                """,
                (min_start, max_start),
            )
        else:
            cursor.execute("SELECT start_time, publish_time, generation FROM forecast_generation ORDER BY start_time, publish_time DESC;")
        index: Dict[str, List[Tuple[str, int]]] = defaultdict(list)
        for row in cursor.fetchall():
            index[row["start_time"]].append((row["publish_time"], row["generation"]))
        return index


    def select_forecasts_for_delivery_period(
        self,
        start_date: str = DELIVERY_MONTH_START,
        end_date: str = DELIVERY_MONTH_END,
        cutoff_time: str = DEFAULT_DECISION_CUTOFF_TIME,
        alignment_mode: str = "native_half_hour",
    ) -> List[PairedInterval]:
        """
        Selects the active day-ahead forecast for each delivery interval in the period.
        
        Alignment Modes:
        1. 'native_half_hour' (Recommended Primary):
           Evaluates all half-hourly settlement actuals (48 periods/day).
           Because WINDFOR is published on hourly boundaries (:00), each 30-minute interval T
           maps to parent hour H = floor_to_hour(T).
           Retains 100% of actual generation records (1,488 for Jan 2026).
           
        2. 'hourly_aggregated' (Secondary / Analytical Comparison):
           Aggregates the two half-hour actuals in each clock hour into an average actual
           value (mean of :00 and :30) and compares against the hourly forecast.
           
        Strict Invariants Enforced:
        - No forecast with publish_time > decision_deadline is EVER selected (zero lookahead).
        - Missing or unforecasted intervals remain null and are NEVER converted to zero.
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT start_time, settlement_date, settlement_period, generation
            FROM actual_generation
            WHERE settlement_date >= ? AND settlement_date <= ? AND fuel_type = 'WIND'
            ORDER BY start_time ASC;
            """,
            (start_date, end_date),
        )
        actual_rows = cursor.fetchall()
        min_start = f"{start_date}T00:00:00Z"
        max_start = f"{end_date}T23:59:59Z"
        forecast_index = self._load_forecast_index(min_start=min_start, max_start=max_start)

        paired_intervals: List[PairedInterval] = []

        if alignment_mode == "hourly_aggregated":
            # Group actuals by parent hour: mean of :00 and :30
            hourly_actuals: Dict[str, Dict[str, Any]] = {}
            for r in actual_rows:
                t_str = r["start_time"]
                t_dt = datetime.fromisoformat(t_str.replace("Z", "+00:00"))
                hour_start = t_dt.strftime("%Y-%m-%dT%H:00:00Z")
                deliv_date = r["settlement_date"]
                if hour_start not in hourly_actuals:
                    hourly_actuals[hour_start] = {
                        "settlement_date": deliv_date,
                        "generations": [],
                        "start_time": hour_start,
                    }
                hourly_actuals[hour_start]["generations"].append(r["generation"])

            for hour_start in sorted(hourly_actuals.keys()):
                group = hourly_actuals[hour_start]
                deliv_date = group["settlement_date"]
                gens = group["generations"]
                avg_actual = sum(gens) / len(gens) if gens else None
                deadline = self._get_decision_deadline(deliv_date, cutoff_time)

                # Find candidate forecast for hour_start
                candidates = forecast_index.get(hour_start, [])
                # Candidates are sorted by publish_time DESC
                eligible = [c for c in candidates if c[0] <= deadline]

                if eligible and avg_actual is not None:
                    selected_pub, selected_gen = eligible[0]
                    error = float(selected_gen) - float(avg_actual)
                    paired_intervals.append(
                        PairedInterval(
                            start_time=hour_start,
                            settlement_period=None,
                            actual_generation=avg_actual,
                            forecast_generation=float(selected_gen),
                            error=error,
                            forecast_publish_time=selected_pub,
                            is_matched=True,
                        )
                    )
                else:
                    paired_intervals.append(
                        PairedInterval(
                            start_time=hour_start,
                            settlement_period=None,
                            actual_generation=avg_actual,
                            forecast_generation=None,
                            error=None,
                            forecast_publish_time=None,
                            is_matched=False,
                        )
                    )

        else:
            # native_half_hour mode: Preserves all 48 settlement periods per day
            for r in actual_rows:
                t_str = r["start_time"]
                deliv_date = r["settlement_date"]
                sp = r["settlement_period"]
                act_gen = float(r["generation"]) if r["generation"] is not None else None

                t_dt = datetime.fromisoformat(t_str.replace("Z", "+00:00"))
                hour_start = t_dt.strftime("%Y-%m-%dT%H:00:00Z")
                deadline = self._get_decision_deadline(deliv_date, cutoff_time)

                # Candidates for parent hour H
                candidates = forecast_index.get(hour_start, [])
                eligible = [c for c in candidates if c[0] <= deadline]

                if eligible and act_gen is not None:
                    selected_pub, selected_gen = eligible[0]
                    # Absolute invariant check: verify no lookahead
                    assert selected_pub <= deadline, f"Invariant violation: {selected_pub} > {deadline}"
                    error = float(selected_gen) - act_gen
                    paired_intervals.append(
                        PairedInterval(
                            start_time=t_str,
                            settlement_period=sp,
                            actual_generation=act_gen,
                            forecast_generation=float(selected_gen),
                            error=error,
                            forecast_publish_time=selected_pub,
                            is_matched=True,
                        )
                    )
                else:
                    paired_intervals.append(
                        PairedInterval(
                            start_time=t_str,
                            settlement_period=sp,
                            actual_generation=act_gen,
                            forecast_generation=None,
                            error=None,
                            forecast_publish_time=None,
                            is_matched=False,
                        )
                    )

        return paired_intervals
