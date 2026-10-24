/**
 * TypeScript interfaces matching the backend FastAPI schemas.
 */

export interface HealthResponse {
  status: 'healthy' | 'unhealthy';
  database: 'connected' | 'disconnected';
  dataset_available: boolean;
  dataset_period: string | null;
}

export interface DatasetSummaryResponse {
  evaluation_period: {
    start_date: string;
    end_date: string;
  };
  actual_observation_count: number;
  forecast_observation_count: number;
  distinct_forecast_publication_timestamps: number;
  first_delivery_timestamp: string | null;
  last_delivery_timestamp: string | null;
  missing_or_invalid_actual_count: number;
  missing_or_invalid_forecast_count: number;
  baseline_decision_cutoff: string;
  cutoff_assumption_status: string;
}

export interface PairedInterval {
  start_time: string;
  settlement_period: number;
  actual_generation: number | null;
  forecast_generation: number | null;
  error: number | null;
  forecast_publish_time: string | null;
  is_matched: boolean;
}

export interface MetricsSummary {
  cutoff_time: string;
  alignment_mode: 'native_half_hour' | 'hourly_aggregated' | string;
  start_date: string;
  end_date: string;
  mae: number | null;
  rmse: number | null;
  mbe: number | null;
  normalized_mae_percentage: number | null;
  mean_actual: number | null;
  mean_forecast: number | null;
  total_expected_intervals: number;
  available_actuals: number;
  available_forecasts: number;
  matched_intervals: number;
  coverage_percentage: number;
  error_convention: string;
  cutoff_assumption: string;
}

export interface TimeSeriesResponse {
  resolution: string;
  cutoff_time: string;
  start_date: string;
  end_date: string;
  count: number;
  data: PairedInterval[];
}

export interface DailyMetricsItem {
  date: string;
  total_intervals: number;
  matched_intervals: number;
  is_complete: boolean;
  mae: number | null;
  rmse: number | null;
  mbe: number | null;
  mean_actual: number | null;
  mean_forecast: number | null;
}

export interface DailyMetricsResponse {
  cutoff_time: string;
  resolution: string;
  start_date: string;
  end_date: string;
  days_count: number;
  days: DailyMetricsItem[];
}

export interface ForecastRevisionItem {
  publish_time: string;
  start_time: string;
  generation: number;
}

export interface ForecastEvolutionResponse {
  target_start_time: string;
  revisions_count: number;
  revisions: ForecastRevisionItem[];
}

export type ResolutionMode = 'native_half_hour' | 'hourly_aggregated';
