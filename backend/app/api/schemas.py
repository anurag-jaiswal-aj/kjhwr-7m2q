from typing import Optional, List, Dict
from pydantic import BaseModel
from backend.app.db.models import PairedInterval, MetricsSummary


class HealthResponse(BaseModel):
    status: str
    database: str
    dataset_available: bool
    dataset_period: Optional[str] = None


class DatasetSummaryResponse(BaseModel):
    evaluation_period: Dict[str, str]
    actual_observation_count: int
    forecast_observation_count: int
    distinct_forecast_publication_timestamps: int
    first_delivery_timestamp: Optional[str] = None
    last_delivery_timestamp: Optional[str] = None
    missing_or_invalid_actual_count: int
    missing_or_invalid_forecast_count: int
    baseline_decision_cutoff: str
    cutoff_assumption_status: str


class TimeSeriesResponse(BaseModel):
    resolution: str
    cutoff_time: str
    start_date: str
    end_date: str
    count: int
    data: List[PairedInterval]


class DailyMetricsItem(BaseModel):
    date: str
    total_intervals: int
    matched_intervals: int
    is_complete: bool
    mae: Optional[float] = None
    rmse: Optional[float] = None
    mbe: Optional[float] = None
    mean_actual: Optional[float] = None
    mean_forecast: Optional[float] = None


class DailyMetricsResponse(BaseModel):
    cutoff_time: str
    resolution: str
    start_date: str
    end_date: str
    days_count: int
    days: List[DailyMetricsItem]


class ForecastRevisionItem(BaseModel):
    publish_time: str
    start_time: str
    generation: int


class ForecastEvolutionResponse(BaseModel):
    target_start_time: str
    revisions_count: int
    revisions: List[ForecastRevisionItem]
