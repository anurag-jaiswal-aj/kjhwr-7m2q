from typing import Optional
from pydantic import BaseModel, Field, field_validator
from datetime import datetime


class ActualRecord(BaseModel):
    start_time: str
    publish_time: str
    settlement_date: str
    settlement_period: int = Field(ge=1, le=50)
    fuel_type: str
    generation: int = Field(ge=0)

    @field_validator("fuel_type")
    @classmethod
    def validate_fuel_type(cls, v: str) -> str:
        if v.upper() != "WIND":
            raise ValueError(f"Invalid fuel_type: expected WIND, got {v}")
        return v.upper()

    @field_validator("start_time", "publish_time")
    @classmethod
    def validate_iso_timestamp(cls, v: str) -> str:
        # Verify it parses as an ISO timestamp
        try:
            datetime.fromisoformat(v.replace("Z", "+00:00"))
        except Exception as e:
            raise ValueError(f"Invalid ISO timestamp {v}: {e}")
        return v


class ForecastRecord(BaseModel):
    publish_time: str
    start_time: str
    generation: int = Field(ge=0)

    @field_validator("start_time", "publish_time")
    @classmethod
    def validate_iso_timestamp(cls, v: str) -> str:
        try:
            datetime.fromisoformat(v.replace("Z", "+00:00"))
        except Exception as e:
            raise ValueError(f"Invalid ISO timestamp {v}: {e}")
        return v


class IngestionStats(BaseModel):
    dataset: str
    date_range_start: str
    date_range_end: str
    retrieved_count: int
    valid_count: int
    unique_count: int


class PairedInterval(BaseModel):
    start_time: str
    settlement_period: Optional[int] = None
    actual_generation: Optional[float] = None
    forecast_generation: Optional[float] = None
    error: Optional[float] = None  # forecast - actual
    forecast_publish_time: Optional[str] = None
    is_matched: bool


class MetricsSummary(BaseModel):
    cutoff_time: str
    alignment_mode: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    mae: Optional[float] = None
    rmse: Optional[float] = None
    mbe: Optional[float] = None
    normalized_mae_percentage: Optional[float] = None
    mean_actual: Optional[float] = None
    mean_forecast: Optional[float] = None
    total_expected_intervals: int
    available_actuals: int
    available_forecasts: int
    matched_intervals: int
    coverage_percentage: float
    error_convention: str = "forecast - actual"
    cutoff_assumption: str = "Analytical assumption (modeled on GB Day-Ahead auction conventions; not an official Elexon rule)"

