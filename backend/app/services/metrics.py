import math
from typing import List, Dict, Any, Optional
from collections import defaultdict

from backend.app.db.models import PairedInterval, MetricsSummary


def calculate_metrics(
    paired_intervals: List[PairedInterval],
    cutoff_time: str,
    alignment_mode: str,
    total_expected_intervals: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> MetricsSummary:
    """
    Computes MAE, RMSE, Mean Bias Error (MBE), and data coverage statistics.
    
    Guarantees:
    - Missing forecasts or missing actuals are strictly excluded from paired error metrics.
    - Missing values are NEVER converted to zero.
    - Normalized MAE is calculated safely against mean actual generation.
    """
    if total_expected_intervals is None:
        total_expected_intervals = 1488 if alignment_mode == "native_half_hour" else 744

    available_actuals = sum(1 for p in paired_intervals if p.actual_generation is not None)
    available_forecasts = sum(1 for p in paired_intervals if p.forecast_generation is not None)

    # Matched intervals have both valid actual and valid forecast
    matched = [
        p for p in paired_intervals
        if p.is_matched and p.error is not None and p.actual_generation is not None and p.forecast_generation is not None
    ]
    matched_count = len(matched)

    coverage_pct = (matched_count / total_expected_intervals * 100.0) if total_expected_intervals > 0 else 0.0

    if matched_count == 0:
        return MetricsSummary(
            cutoff_time=cutoff_time,
            alignment_mode=alignment_mode,
            start_date=start_date,
            end_date=end_date,
            mae=None,
            rmse=None,
            mbe=None,
            normalized_mae_percentage=None,
            mean_actual=None,
            mean_forecast=None,
            total_expected_intervals=total_expected_intervals,
            available_actuals=available_actuals,
            available_forecasts=available_forecasts,
            matched_intervals=0,
            coverage_percentage=round(coverage_pct, 2),
        )

    errors = [p.error for p in matched]
    actuals = [p.actual_generation for p in matched]
    forecasts = [p.forecast_generation for p in matched]

    mae = sum(abs(e) for e in errors) / matched_count
    rmse = math.sqrt(sum(e ** 2 for e in errors) / matched_count)
    mbe = sum(errors) / matched_count
    mean_actual = sum(actuals) / matched_count
    mean_forecast = sum(forecasts) / matched_count

    normalized_mae = round((mae / mean_actual) * 100.0, 2) if mean_actual > 0 else None

    return MetricsSummary(
        cutoff_time=cutoff_time,
        alignment_mode=alignment_mode,
        start_date=start_date,
        end_date=end_date,
        mae=round(mae, 2),
        rmse=round(rmse, 2),
        mbe=round(mbe, 2),
        normalized_mae_percentage=normalized_mae,
        mean_actual=round(mean_actual, 2),
        mean_forecast=round(mean_forecast, 2),
        total_expected_intervals=total_expected_intervals,
        available_actuals=available_actuals,
        available_forecasts=available_forecasts,
        matched_intervals=matched_count,
        coverage_percentage=round(coverage_pct, 2),
    )


def calculate_daily_metrics(
    paired_intervals: List[PairedInterval],
    alignment_mode: str = "native_half_hour",
) -> List[Dict[str, Any]]:
    """
    Groups paired intervals by delivery date and calculates daily MAE, RMSE, MBE, and coverage.
    Incomplete days are explicitly flagged with is_complete: False.
    """
    expected_day = 48 if alignment_mode == "native_half_hour" else 24

    by_day = defaultdict(list)
    for p in paired_intervals:
        date_str = p.start_time[:10]
        by_day[date_str].append(p)

    daily_results: List[Dict[str, Any]] = []
    for date_str in sorted(by_day.keys()):
        intervals = by_day[date_str]
        matched = [p for p in intervals if p.is_matched and p.error is not None]
        matched_count = len(matched)
        total_intervals = len(intervals)
        is_complete = (matched_count >= expected_day and total_intervals >= expected_day)

        if matched_count > 0:
            errors = [p.error for p in matched]
            actuals = [p.actual_generation for p in matched]
            forecasts = [p.forecast_generation for p in matched]
            mae = sum(abs(e) for e in errors) / matched_count
            rmse = math.sqrt(sum(e ** 2 for e in errors) / matched_count)
            mbe = sum(errors) / matched_count
            mean_act = sum(actuals) / matched_count
            mean_fcst = sum(forecasts) / matched_count
        else:
            mae = rmse = mbe = mean_act = mean_fcst = None

        daily_results.append({
            "date": date_str,
            "total_intervals": total_intervals,
            "matched_intervals": matched_count,
            "is_complete": is_complete,
            "mae": round(mae, 2) if mae is not None else None,
            "rmse": round(rmse, 2) if rmse is not None else None,
            "mbe": round(mbe, 2) if mbe is not None else None,
            "mean_actual": round(mean_act, 2) if mean_act is not None else None,
            "mean_forecast": round(mean_fcst, 2) if mean_fcst is not None else None,
        })

    return daily_results

