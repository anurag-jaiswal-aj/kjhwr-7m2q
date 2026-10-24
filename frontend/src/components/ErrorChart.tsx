import React from 'react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  ReferenceLine,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Cell,
} from 'recharts';
import type { PairedInterval } from '../api/types';
import { formatMwWithSign, formatDateTime, formatTimeOnly } from '../utils/formatters';
import { AlertCircle, ArrowUpRight, ArrowDownRight } from 'lucide-react';

interface ErrorChartProps {
  data: PairedInterval[];
  loading: boolean;
}

export const ErrorChart: React.FC<ErrorChartProps> = ({ data, loading }) => {
  // Calculate extrema unconditionally at top of component
  const { maxOver, maxUnder } = React.useMemo(() => {
    let over: PairedInterval | null = null;
    let under: PairedInterval | null = null;
    if (data && data.length > 0) {
      for (const d of data) {
        if (d.error !== null) {
          if (!over || d.error > (over.error ?? -Infinity)) {
            over = d;
          }
          if (!under || d.error < (under.error ?? Infinity)) {
            under = d;
          }
        }
      }
    }
    return { maxOver: over, maxUnder: under };
  }, [data]);

  if (loading) {
    return (
      <div className="card chart-card">
        <div className="skeleton" style={{ height: 20, width: 200 }} />
        <div className="skeleton" style={{ height: 260, width: '100%', marginTop: 20 }} />
      </div>
    );
  }

  if (!data || data.length === 0) {
    return null;
  }

  const sampleStride = Math.max(1, Math.floor(data.length / 14));

  return (
    <div className="card chart-card">
      <div className="chart-header">
        <div>
          <h3 className="chart-title">Forecast Error Distribution Over Time</h3>
          <p className="chart-subtitle">
            Error sign convention: <strong className="mono">Error = Forecast − Actual</strong>. Positive values denote over-forecasting.
          </p>
        </div>

        <div className="error-summary-pills">
          {maxOver && (
            <div className="pill pill-over" title={`Occurred on ${formatDateTime(maxOver.start_time)}`}>
              <ArrowUpRight size={13} />
              <span>Max Over: <strong>{formatMwWithSign(maxOver.error)}</strong></span>
            </div>
          )}
          {maxUnder && (
            <div className="pill pill-under" title={`Occurred on ${formatDateTime(maxUnder.start_time)}`}>
              <ArrowDownRight size={13} />
              <span>Max Under: <strong>{formatMwWithSign(maxUnder.error)}</strong></span>
            </div>
          )}
        </div>
      </div>

      <div className="chart-body" style={{ width: '100%', height: 260 }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 15, right: 25, left: 10, bottom: 25 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
            <XAxis
              dataKey="start_time"
              tickFormatter={(val: string) => {
                const dt = new Date(val);
                if (data.length <= 48) return formatTimeOnly(val);
                return `${dt.getUTCDate()} ${dt.toLocaleString('en-GB', { month: 'short', timeZone: 'UTC' })}`;
              }}
              interval={sampleStride}
              stroke="#64748b"
              fontSize={11}
              dy={8}
            />
            <YAxis
              stroke="#64748b"
              fontSize={11}
              tickFormatter={(v: number) => `${(v / 1000).toFixed(1)}k`}
              label={{
                value: 'Error (MW)',
                angle: -90,
                position: 'insideLeft',
                offset: 5,
                style: { fill: '#64748b', fontSize: 11, textAnchor: 'middle' },
              }}
            />
            <ReferenceLine y={0} stroke="#334155" strokeWidth={1.5} />
            <Tooltip
              content={({ active, payload }) => {
                if (!active || !payload || payload.length === 0) return null;
                const item = payload[0].payload as PairedInterval;
                const err = item.error ?? 0;
                const isOver = err > 0;

                return (
                  <div className="chart-custom-tooltip">
                    <div className="tooltip-header">
                      <span>{formatDateTime(item.start_time)}</span>
                      <span className="mono">SP {item.settlement_period}</span>
                    </div>
                    <div className="tooltip-row">
                      <span>Direction:</span>
                      <strong style={{ color: isOver ? '#fb923c' : '#818cf8' }}>
                        {isOver ? 'Over-Forecast (+)' : err < 0 ? 'Under-Forecast (−)' : 'Zero Error'}
                      </strong>
                    </div>
                    <div className="tooltip-row highlight">
                      <span>Error (F − A):</span>
                      <strong className="mono">{formatMwWithSign(item.error)}</strong>
                    </div>
                    <div className="tooltip-row" style={{ fontSize: '0.72rem', color: '#cbd5e1' }}>
                      <span>Actual: {item.actual_generation?.toLocaleString()} MW | Forecast: {item.forecast_generation?.toLocaleString()} MW</span>
                    </div>
                  </div>
                );
              }}
            />
            <Bar dataKey="error" radius={[2, 2, 0, 0]}>
              {data.map((entry, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={(entry.error ?? 0) >= 0 ? '#ea580c' : '#6366f1'}
                  opacity={0.85}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="chart-footer-note disclaimer">
        <AlertCircle size={14} className="disclaimer-icon" />
        <span>
          <strong>Commercial Context:</strong> Physical wind forecast error does not automatically establish financial loss. Settlement cashout impacts depend on half-hourly imbalance prices (System Buy/Sell Prices) and the utility's net portfolio position.
        </span>
      </div>
    </div>
  );
};
