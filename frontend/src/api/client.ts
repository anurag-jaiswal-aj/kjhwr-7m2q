/**
 * Central typed API client for Gridbricks Wind Intelligence.
 */

import type {
  HealthResponse,
  DatasetSummaryResponse,
  MetricsSummary,
  TimeSeriesResponse,
  DailyMetricsResponse,
  ForecastEvolutionResponse,
  ResolutionMode,
} from './types';

// Read API base URL from environment or default to relative '/api'
// Relative path '/api' works seamlessly with both Vite dev/preview proxies and production Nginx reverse proxies.
const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || '/api'
).replace(/\/+$/, '');

export class ApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(`API Error ${status}: ${detail}`);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
  }
}

async function request<T>(endpoint: string, signal?: AbortSignal): Promise<T> {
  const url = `${API_BASE_URL}${endpoint.startsWith('/') ? endpoint : `/${endpoint}`}`;
  try {
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        Accept: 'application/json',
      },
      signal,
    });

    if (!response.ok) {
      let detail = response.statusText;
      try {
        const errorJson = await response.json();
        detail = errorJson.detail || detail;
      } catch {
        // Fallback to response status text
      }
      throw new ApiError(response.status, detail);
    }

    return (await response.json()) as T;
  } catch (err: unknown) {
    if (err instanceof ApiError) {
      throw err;
    }
    if (err instanceof DOMException && err.name === 'AbortError') {
      throw err;
    }
    const message = err instanceof Error ? err.message : 'Unknown network failure';
    throw new ApiError(0, `Network error reaching ${url}: ${message}`);
  }
}

export const api = {
  getHealth: (signal?: AbortSignal): Promise<HealthResponse> => {
    return request<HealthResponse>('/health', signal);
  },

  getSummary: (signal?: AbortSignal): Promise<DatasetSummaryResponse> => {
    return request<DatasetSummaryResponse>('/summary', signal);
  },

  getMetrics: (
    params: {
      startDate?: string;
      endDate?: string;
      resolution?: ResolutionMode;
      cutoffTime?: string;
    } = {},
    signal?: AbortSignal
  ): Promise<MetricsSummary> => {
    const query = new URLSearchParams();
    if (params.startDate) query.set('start_date', params.startDate);
    if (params.endDate) query.set('end_date', params.endDate);
    if (params.resolution) query.set('resolution', params.resolution);
    if (params.cutoffTime) query.set('cutoff_time', params.cutoffTime);
    const qs = query.toString();
    return request<MetricsSummary>(`/metrics${qs ? `?${qs}` : ''}`, signal);
  },

  getTimeSeries: (
    params: {
      startDate?: string;
      endDate?: string;
      resolution?: ResolutionMode;
      cutoffTime?: string;
    } = {},
    signal?: AbortSignal
  ): Promise<TimeSeriesResponse> => {
    const query = new URLSearchParams();
    if (params.startDate) query.set('start_date', params.startDate);
    if (params.endDate) query.set('end_date', params.endDate);
    if (params.resolution) query.set('resolution', params.resolution);
    if (params.cutoffTime) query.set('cutoff_time', params.cutoffTime);
    const qs = query.toString();
    return request<TimeSeriesResponse>(`/timeseries${qs ? `?${qs}` : ''}`, signal);
  },

  getDailyMetrics: (
    params: {
      startDate?: string;
      endDate?: string;
      resolution?: ResolutionMode;
      cutoffTime?: string;
    } = {},
    signal?: AbortSignal
  ): Promise<DailyMetricsResponse> => {
    const query = new URLSearchParams();
    if (params.startDate) query.set('start_date', params.startDate);
    if (params.endDate) query.set('end_date', params.endDate);
    if (params.resolution) query.set('resolution', params.resolution);
    if (params.cutoffTime) query.set('cutoff_time', params.cutoffTime);
    const qs = query.toString();
    return request<DailyMetricsResponse>(`/daily-metrics${qs ? `?${qs}` : ''}`, signal);
  },

  getForecastEvolution: (startTime: string, signal?: AbortSignal): Promise<ForecastEvolutionResponse> => {
    const query = new URLSearchParams({ start_time: startTime });
    return request<ForecastEvolutionResponse>(`/forecast-evolution?${query.toString()}`, signal);
  },
};
