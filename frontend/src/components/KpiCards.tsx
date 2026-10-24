import React from 'react';
import { Target, TrendingUp, BarChart3, CheckSquare, Zap } from 'lucide-react';
import type { MetricsSummary } from '../api/types';
import { formatMw, formatMwWithSign, formatPercent } from '../utils/formatters';

interface KpiCardsProps {
  metrics: MetricsSummary | null;
  loading: boolean;
}

export const KpiCards: React.FC<KpiCardsProps> = ({ metrics, loading }) => {
  if (loading) {
    return (
      <div className="kpi-grid">
        {[1, 2, 3, 4, 5].map((idx) => (
          <div key={idx} className="card kpi-card">
            <div className="skeleton" style={{ height: 16, width: '60%', marginBottom: 12 }} />
            <div className="skeleton" style={{ height: 32, width: '80%', marginBottom: 8 }} />
            <div className="skeleton" style={{ height: 14, width: '40%' }} />
          </div>
        ))}
      </div>
    );
  }

  if (!metrics) {
    return null;
  }

  const isOverforecast = (metrics.mbe ?? 0) > 0;

  return (
    <div className="kpi-grid">
      {/* 1. MAE Card */}
      <div className="card kpi-card">
        <div className="kpi-header">
          <span className="kpi-title">Mean Absolute Error (MAE)</span>
          <Target size={16} className="kpi-icon text-sky" />
        </div>
        <div className="kpi-value mono">{formatMw(metrics.mae)}</div>
        <div className="kpi-footer">
          <span className="kpi-subtext">
            {metrics.normalized_mae_percentage !== null
              ? `${formatPercent(metrics.normalized_mae_percentage)} of mean outturn`
              : 'Average magnitude of miss'}
          </span>
        </div>
      </div>

      {/* 2. RMSE Card */}
      <div className="card kpi-card">
        <div className="kpi-header">
          <span className="kpi-title">Root Mean Squared Error (RMSE)</span>
          <TrendingUp size={16} className="kpi-icon text-indigo" />
        </div>
        <div className="kpi-value mono">{formatMw(metrics.rmse)}</div>
        <div className="kpi-footer">
          <span className="kpi-subtext">Penalizes large forecast excursions</span>
        </div>
      </div>

      {/* 3. MBE (Bias) Card */}
      <div className={`card kpi-card ${isOverforecast ? 'border-amber-subtle' : 'border-indigo-subtle'}`}>
        <div className="kpi-header">
          <span className="kpi-title">Mean Bias Error (MBE)</span>
          <BarChart3 size={16} className={`kpi-icon ${isOverforecast ? 'text-amber' : 'text-indigo'}`} />
        </div>
        <div className={`kpi-value mono ${isOverforecast ? 'text-amber' : 'text-indigo'}`}>
          {formatMwWithSign(metrics.mbe)}
        </div>
        <div className="kpi-footer">
          <span className="kpi-subtext">
            <strong>Convention:</strong> Forecast − Actual ({isOverforecast ? 'Over-forecast' : 'Under-forecast'})
          </span>
        </div>
      </div>

      {/* 4. Coverage Card */}
      <div className="card kpi-card">
        <div className="kpi-header">
          <span className="kpi-title">Observation Coverage</span>
          <CheckSquare size={16} className="kpi-icon text-emerald" />
        </div>
        <div className="kpi-value mono">{formatPercent(metrics.coverage_percentage)}</div>
        <div className="kpi-footer">
          <span className="kpi-subtext mono">
            {metrics.matched_intervals.toLocaleString()} / {metrics.total_expected_intervals.toLocaleString()} intervals
          </span>
        </div>
      </div>

      {/* 5. Mean Generation Card */}
      <div className="card kpi-card">
        <div className="kpi-header">
          <span className="kpi-title">Mean Generation Outturn</span>
          <Zap size={16} className="kpi-icon text-sky" />
        </div>
        <div className="kpi-value mono">{formatMw(metrics.mean_actual)}</div>
        <div className="kpi-footer">
          <span className="kpi-subtext mono">
            Forecast Mean: <strong>{formatMw(metrics.mean_forecast)}</strong>
          </span>
        </div>
      </div>
    </div>
  );
};
