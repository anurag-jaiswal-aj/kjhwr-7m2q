import React from 'react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts';
import type { PairedInterval, ResolutionMode } from '../api/types';
import { formatMw, formatMwWithSign, formatDateTime, formatTimeOnly } from '../utils/formatters';
import { Layers, MousePointerClick } from 'lucide-react';

interface TimeSeriesChartProps {
  data: PairedInterval[];
  loading: boolean;
  resolution: ResolutionMode;
  onSelectInterval?: (startTime: string) => void;
  selectedStartTime?: string | null;
}

export const TimeSeriesChart: React.FC<TimeSeriesChartProps> = ({
  data,
  loading,
  resolution,
  onSelectInterval,
  selectedStartTime,
}) => {
  if (loading) {
    return (
      <div className="card chart-card">
        <div className="chart-header">
          <div className="skeleton" style={{ height: 20, width: 240 }} />
        </div>
        <div className="skeleton" style={{ height: 350, width: '100%', marginTop: 20 }} />
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <div className="card chart-card empty-chart">
        <p className="empty-text">No time-series observations available for this date window.</p>
      </div>
    );
  }

  // Format ticks cleanly depending on dataset size
  const sampleStride = Math.max(1, Math.floor(data.length / 14));

  return (
    <div className="card chart-card">
      <div className="chart-header">
        <div>
          <h3 className="chart-title">Day-Ahead Wind Forecast vs. Actual Generation</h3>
          <p className="chart-subtitle">
            National GB outturn (Elexon FUELHH) compared against D-1 day-ahead forecast (WINDFOR).
          </p>
        </div>
        <div className="chart-header-badges">
          <div className="badge badge-neutral">
            <Layers size={12} />
            <span>
              {resolution === 'native_half_hour'
                ? 'Native 30-min Resolution (48 SPs/day)'
                : 'Hourly Aggregated Resolution (24 intervals/day)'}
            </span>
          </div>
          <div className="badge badge-neutral" style={{ color: '#0284c7' }}>
            <MousePointerClick size={12} />
            <span>Click any data point to inspect revisions</span>
          </div>
        </div>
      </div>

      <div className="chart-body" style={{ width: '100%', height: 380 }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={data}
            margin={{ top: 15, right: 25, left: 10, bottom: 25 }}
            onClick={(e: any) => {
              if (e && e.activePayload && e.activePayload.length > 0) {
                const interval = e.activePayload[0].payload as PairedInterval;
                if (interval && interval.start_time && onSelectInterval) {
                  onSelectInterval(interval.start_time);
                }
              }
            }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
            <XAxis
              dataKey="start_time"
              tickFormatter={(val: string) => {
                const dt = new Date(val);
                if (data.length <= 48) {
                  return formatTimeOnly(val);
                }
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
              tickFormatter={(v: number) => `${(v / 1000).toFixed(0)}k`}
              label={{
                value: 'Generation (MW)',
                angle: -90,
                position: 'insideLeft',
                offset: 5,
                style: { fill: '#64748b', fontSize: 11, textAnchor: 'middle' },
              }}
            />
            <Tooltip
              content={({ active, payload }) => {
                if (!active || !payload || payload.length === 0) return null;
                const item = payload[0].payload as PairedInterval;
                const isSelected = item.start_time === selectedStartTime;

                return (
                  <div className="chart-custom-tooltip">
                    <div className="tooltip-header">
                      <span>{formatDateTime(item.start_time)}</span>
                      <span className="mono">SP {item.settlement_period}</span>
                    </div>
                    <div className="tooltip-row">
                      <span style={{ color: '#38bdf8' }}>Actual Generation:</span>
                      <strong className="mono">{formatMw(item.actual_generation)}</strong>
                    </div>
                    <div className="tooltip-row">
                      <span style={{ color: '#fbbf24' }}>Day-Ahead Forecast:</span>
                      <strong className="mono">{formatMw(item.forecast_generation)}</strong>
                    </div>
                    <div className="tooltip-row highlight">
                      <span>Forecast Error (F − A):</span>
                      <strong
                        className="mono"
                        style={{
                          color: (item.error ?? 0) > 0 ? '#fb923c' : '#818cf8',
                        }}
                      >
                        {formatMwWithSign(item.error)}
                      </strong>
                    </div>
                    {item.forecast_publish_time && (
                      <div className="tooltip-row" style={{ fontSize: '0.72rem', color: '#94a3b8', marginTop: 4 }}>
                        <span>Published: {formatDateTime(item.forecast_publish_time)}</span>
                      </div>
                    )}
                    {isSelected && (
                      <div style={{ marginTop: 4, color: '#38bdf8', fontSize: '0.72rem', fontWeight: 600 }}>
                        ✓ Selected for Evolution View
                      </div>
                    )}
                  </div>
                );
              }}
            />
            <Legend
              verticalAlign="top"
              align="right"
              wrapperStyle={{ paddingBottom: 10, fontSize: 12 }}
            />
            <Line
              type="monotone"
              dataKey="actual_generation"
              name="Actual Generation"
              stroke="#0284c7"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 5, fill: '#0284c7' }}
            />
            <Line
              type="monotone"
              dataKey="forecast_generation"
              name="Day-Ahead Forecast"
              stroke="#d97706"
              strokeWidth={2}
              strokeDasharray={resolution === 'native_half_hour' ? '4 2' : undefined}
              dot={false}
              activeDot={{ r: 5, fill: '#d97706' }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="chart-footer-note">
        <span className="note-label">Resolution Note:</span>{' '}
        {resolution === 'native_half_hour'
          ? 'Native half-hourly mode pairs both :00 and :30 actual settlement periods to the prevailing hourly forecast published on or before D-1 11:00 UTC.'
          : 'Hourly mode averages both half-hourly actuals within each hour to pair with the single hourly forecast vintage.'}
      </div>
    </div>
  );
};
