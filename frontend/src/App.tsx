import React, { useState, useEffect, useCallback, useTransition } from 'react';
import { api } from './api/client';
import type {
  HealthResponse,
  MetricsSummary,
  TimeSeriesResponse,
  DailyMetricsResponse,
  ResolutionMode,
} from './api/types';
import { Header } from './components/Header';
import { FiltersBar } from './components/FiltersBar';
import { KpiCards } from './components/KpiCards';
import { TimeSeriesChart } from './components/TimeSeriesChart';
import { ErrorChart } from './components/ErrorChart';
import { DailyMetricsTable } from './components/DailyMetricsTable';
import { ForecastEvolution } from './components/ForecastEvolution';
import { MethodologyModal } from './components/MethodologyModal';
import { ErrorState } from './components/ErrorState';
import './App.css';

export const App: React.FC = () => {
  // Query parameters state
  const [startDate, setStartDate] = useState<string>('2026-01-01');
  const [endDate, setEndDate] = useState<string>('2026-01-31');
  const [resolution, setResolution] = useState<ResolutionMode>('native_half_hour');
  const [cutoffTime, setCutoffTime] = useState<string>('11:00');

  // Selected delivery timestamp for Forecast Evolution view
  const [selectedInterval, setSelectedInterval] = useState<string>('2026-01-15T12:00:00Z');

  // UI state
  const [methodologyOpen, setMethodologyOpen] = useState<boolean>(false);
  const [, startTransition] = useTransition();

  // Data states
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthLoading, setHealthLoading] = useState<boolean>(true);
  const [metrics, setMetrics] = useState<MetricsSummary | null>(null);
  const [timeseries, setTimeseries] = useState<TimeSeriesResponse | null>(null);
  const [dailyMetrics, setDailyMetrics] = useState<DailyMetricsResponse | null>(null);

  const [loading, setLoading] = useState<boolean>(true);
  const [globalError, setGlobalError] = useState<string | null>(null);

  // 1. Fetch Health Status on Mount
  const fetchHealth = useCallback(async () => {
    setHealthLoading(true);
    try {
      const res = await api.getHealth();
      setHealth(res);
      if (res.status === 'unhealthy') {
        setGlobalError('Backend health check reports database disconnection.');
      } else {
        setGlobalError(null);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Unable to connect to backend REST service.';
      setGlobalError(msg);
      setHealth({
        status: 'unhealthy',
        database: 'disconnected',
        dataset_available: false,
        dataset_period: null,
      });
    } finally {
      setHealthLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchHealth();
  }, [fetchHealth]);

  // 2. Coordinated Analytics Fetch
  const fetchAnalytics = useCallback(() => {
    const controller = new AbortController();
    setLoading(true);

    const params = {
      startDate,
      endDate,
      resolution,
      cutoffTime,
    };

    Promise.all([
      api.getMetrics(params, controller.signal),
      api.getTimeSeries(params, controller.signal),
      api.getDailyMetrics(params, controller.signal),
    ])
      .then(([metricsRes, timeseriesRes, dailyRes]) => {
        startTransition(() => {
          setMetrics(metricsRes);
          setTimeseries(timeseriesRes);
          setDailyMetrics(dailyRes);
          setGlobalError(null);
          setLoading(false);

          // If current selectedInterval is not in this new timeseries window, select first interval
          if (
            timeseriesRes.data.length > 0 &&
            !timeseriesRes.data.some((d) => d.start_time === selectedInterval)
          ) {
            setSelectedInterval(timeseriesRes.data[0].start_time);
          }
        });
      })
      .catch((err) => {
        if (err.name !== 'AbortError') {
          setGlobalError(err.message || 'Failed to load analytical metrics.');
          setLoading(false);
        }
      });

    return () => controller.abort();
  }, [startDate, endDate, resolution, cutoffTime, selectedInterval]);

  useEffect(() => {
    const cancel = fetchAnalytics();
    return cancel;
  }, [fetchAnalytics]);

  // Handle Reset to Default Baseline
  const handleReset = () => {
    setStartDate('2026-01-01');
    setEndDate('2026-01-31');
    setResolution('native_half_hour');
    setCutoffTime('11:00');
    setSelectedInterval('2026-01-15T12:00:00Z');
  };

  // Extract available timestamps for evolution dropdown
  const availableTimestamps = (timeseries?.data || [])
    .filter((d) => d.start_time.endsWith(':00:00Z'))
    .map((d) => d.start_time);

  return (
    <div className="app-container">
      {/* Top Navigation & Branding Header */}
      <Header
        health={health}
        healthLoading={healthLoading}
        onOpenMethodology={() => setMethodologyOpen(true)}
      />

      {/* Main Dashboard Workspace */}
      <main className="dashboard-content">
        {globalError ? (
          <ErrorState
            error={globalError}
            onRetry={() => {
              fetchHealth();
              fetchAnalytics();
            }}
          />
        ) : (
          <>
            {/* Control & Filter Strip */}
            <FiltersBar
              startDate={startDate}
              endDate={endDate}
              resolution={resolution}
              cutoffTime={cutoffTime}
              onStartDateChange={setStartDate}
              onEndDateChange={setEndDate}
              onResolutionChange={setResolution}
              onCutoffTimeChange={setCutoffTime}
              onReset={handleReset}
            />

            {/* Core Statistical KPI Cards */}
            <KpiCards metrics={metrics} loading={loading} />

            {/* Time-Series Actual vs Forecast Chart */}
            <TimeSeriesChart
              data={timeseries?.data || []}
              loading={loading}
              resolution={resolution}
              selectedStartTime={selectedInterval}
              onSelectInterval={(ts) => setSelectedInterval(ts)}
            />

            {/* Forecast Error Analysis Chart */}
            <ErrorChart data={timeseries?.data || []} loading={loading} />

            {/* Two-Column Grid: Daily Breakdown & Forecast Revision Evolution */}
            <div className="analytics-split-grid">
              <DailyMetricsTable
                days={dailyMetrics?.days || []}
                loading={loading}
                selectedDate={startDate === endDate ? startDate : null}
                onSelectDay={(dayDate) => {
                  setStartDate(dayDate);
                  setEndDate(dayDate);
                }}
              />

              <ForecastEvolution
                selectedStartTime={selectedInterval}
                onStartTimeChange={setSelectedInterval}
                availableTimestamps={availableTimestamps}
                cutoffTime={cutoffTime}
              />
            </div>
          </>
        )}
      </main>

      {/* Methodology & Analytical Baseline Modal */}
      <MethodologyModal
        isOpen={methodologyOpen}
        onClose={() => setMethodologyOpen(false)}
      />

      {/* Footer */}
      <footer className="app-footer">
        <div className="footer-content">
          <span>Gridbricks Wind Intelligence • Stage 5 Analytics Implementation</span>
          <span className="mono">Evaluated Period: Jan 1–31, 2026 (1,488 Half-Hour SPs)</span>
          <button className="footer-link" onClick={() => setMethodologyOpen(true)}>
            Methodology & Assumptions
          </button>
        </div>
      </footer>
    </div>
  );
};

export default App;
