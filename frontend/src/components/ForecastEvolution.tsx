import React, { useEffect, useState } from 'react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from 'recharts';
import { api } from '../api/client';
import type { ForecastEvolutionResponse } from '../api/types';
import {
  formatMw,
  formatMwWithSign,
  formatDateTime,
  calculateLeadHours,
} from '../utils/formatters';
import { History, Clock, AlertCircle } from 'lucide-react';

interface ForecastEvolutionProps {
  selectedStartTime: string;
  onStartTimeChange: (newTime: string) => void;
  availableTimestamps?: string[];
  cutoffTime?: string;
}

export const ForecastEvolution: React.FC<ForecastEvolutionProps> = ({
  selectedStartTime,
  onStartTimeChange,
  availableTimestamps = [],
  cutoffTime = '11:00',
}) => {
  const [data, setData] = useState<ForecastEvolutionResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!selectedStartTime) return;
    const controller = new AbortController();
    setLoading(true);
    setError(null);

    api
      .getForecastEvolution(selectedStartTime, controller.signal)
      .then((res) => {
        setData(res);
        setLoading(false);
      })
      .catch((err) => {
        if (err.name !== 'AbortError') {
          setError(err.message || 'Failed to load forecast evolution.');
          setLoading(false);
        }
      });

    return () => controller.abort();
  }, [selectedStartTime]);

  // Determine D-1 cutoff deadline timestamp for the target delivery date
  const cutoffDeadline = React.useMemo(() => {
    if (!selectedStartTime) return null;
    try {
      const datePart = selectedStartTime.slice(0, 10);
      const dt = new Date(`${datePart}T00:00:00Z`);
      dt.setUTCDate(dt.getUTCDate() - 1);
      const dMinus1 = dt.toISOString().slice(0, 10);
      const ct = (cutoffTime || '11:00').trim();
      const cleanCutoff = ct.length === 5 ? `${ct}:00` : ct;
      return `${dMinus1}T${cleanCutoff}Z`;
    } catch {
      return null;
    }
  }, [selectedStartTime, cutoffTime]);

  // Compute revision deltas (change from previous vintage)
  const revisionsWithDelta = (data?.revisions || []).map((rev, idx, arr) => {
    const prev = idx > 0 ? arr[idx - 1] : null;
    const delta = prev ? rev.generation - prev.generation : null;
    return {
      ...rev,
      delta,
      stepIndex: idx + 1,
    };
  });

  // Identify the latest revision eligible under the configured D-1 cutoff
  const eligibleRevisions = revisionsWithDelta.filter(
    (r) => !cutoffDeadline || r.publish_time <= cutoffDeadline
  );
  const selectedDayAheadVintage =
    eligibleRevisions.length > 0 ? eligibleRevisions[eligibleRevisions.length - 1] : null;

  return (
    <div className="card evolution-card">
      <div className="chart-header">
        <div>
          <div className="title-with-badge">
            <h3 className="chart-title">Forecast Revision History (Evolution)</h3>
            <span className="badge badge-neutral mono">
              <History size={12} />
              <span>{data?.revisions_count ?? 0} Vintages Recorded</span>
            </span>
          </div>
          <p className="chart-subtitle">
            Progression of NGESO/Elexon meteorological forecasts published from 2.5 days ahead down to delivery gate.
          </p>
        </div>

        {/* Timestamp Selector */}
        <div className="evolution-selector">
          <label className="selector-label">
            <Clock size={13} style={{ display: 'inline', marginRight: 4 }} />
            Target Delivery Interval:
          </label>
          {availableTimestamps.length > 0 ? (
            <select
              className="select-input mono"
              value={selectedStartTime}
              onChange={(e) => onStartTimeChange(e.target.value)}
            >
              {availableTimestamps.slice(0, 48).map((ts) => (
                <option key={ts} value={ts}>
                  {formatDateTime(ts)}
                </option>
              ))}
            </select>
          ) : (
            <input
              type="text"
              className="date-input mono"
              value={selectedStartTime}
              onChange={(e) => onStartTimeChange(e.target.value)}
              placeholder="2026-01-15T12:00:00Z"
            />
          )}
        </div>
      </div>

      {loading ? (
        <div style={{ padding: '2rem 0' }}>
          <div className="skeleton" style={{ height: 200, width: '100%', marginBottom: 16 }} />
          <div className="skeleton" style={{ height: 100, width: '100%' }} />
        </div>
      ) : error ? (
        <div className="empty-chart">
          <AlertCircle size={20} className="text-amber" style={{ marginBottom: 8 }} />
          <p className="empty-text">{error}</p>
        </div>
      ) : revisionsWithDelta.length === 0 ? (
        <div className="empty-chart">
          <p className="empty-text">No forecast revisions found for target interval {selectedStartTime}.</p>
        </div>
      ) : (
        <>
          {/* Trend Chart */}
          <div className="chart-body" style={{ width: '100%', height: 220 }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart
                data={revisionsWithDelta}
                margin={{ top: 15, right: 25, left: 10, bottom: 20 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                <XAxis
                  dataKey="publish_time"
                  tickFormatter={(val: string) => {
                    const dt = new Date(val);
                    return `${dt.getUTCDate()} ${dt.toLocaleString('en-GB', { month: 'short', timeZone: 'UTC' })} ${dt.getUTCHours().toString().padStart(2, '0')}:${dt.getUTCMinutes().toString().padStart(2, '0')}`;
                  }}
                  stroke="#64748b"
                  fontSize={10}
                  dy={6}
                />
                <YAxis
                  stroke="#64748b"
                  fontSize={10}
                  tickFormatter={(v: number) => `${(v / 1000).toFixed(1)}k`}
                  label={{
                    value: 'Forecast (MW)',
                    angle: -90,
                    position: 'insideLeft',
                    offset: 5,
                    style: { fill: '#64748b', fontSize: 10, textAnchor: 'middle' },
                  }}
                />
                <Tooltip
                  content={({ active, payload }) => {
                    if (!active || !payload || payload.length === 0) return null;
                    const item = payload[0].payload as typeof revisionsWithDelta[0];
                    const isSelected = selectedDayAheadVintage?.publish_time === item.publish_time;
                    return (
                      <div className="chart-custom-tooltip">
                        <div className="tooltip-header">
                          <span>Revision #{item.stepIndex} {isSelected ? '(★ DA Baseline)' : ''}</span>
                          <span className="mono">{calculateLeadHours(item.publish_time, item.start_time)}</span>
                        </div>
                        <div className="tooltip-row">
                          <span>Published At:</span>
                          <strong className="mono">{formatDateTime(item.publish_time)}</strong>
                        </div>
                        <div className="tooltip-row highlight">
                          <span>Forecast Value:</span>
                          <strong className="mono" style={{ color: '#fbbf24' }}>
                            {formatMw(item.generation)}
                          </strong>
                        </div>
                        {item.delta !== null && (
                          <div className="tooltip-row">
                            <span>Revision Shift:</span>
                            <strong
                              className="mono"
                              style={{ color: item.delta >= 0 ? '#fb923c' : '#818cf8' }}
                            >
                              {formatMwWithSign(item.delta)}
                            </strong>
                          </div>
                        )}
                      </div>
                    );
                  }}
                />
                <Line
                  type="stepAfter"
                  dataKey="generation"
                  name="Forecast Revision"
                  stroke="#d97706"
                  strokeWidth={2}
                  dot={{ r: 3, fill: '#d97706' }}
                  activeDot={{ r: 5, fill: '#b45309' }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* Revisions Table */}
          <div className="table-responsive" style={{ maxHeight: 220, overflowY: 'auto', marginTop: 12 }}>
            <table className="daily-table evolution-table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Publication Run (UTC)</th>
                  <th>Lead Time</th>
                  <th className="text-right">Forecast (MW)</th>
                  <th className="text-right">Revision Shift (Δ)</th>
                </tr>
              </thead>
              <tbody>
                {revisionsWithDelta.map((rev) => {
                  const isSelected = selectedDayAheadVintage?.publish_time === rev.publish_time;
                  const isPostCutoff = cutoffDeadline ? rev.publish_time > cutoffDeadline : false;

                  return (
                    <tr key={rev.publish_time} className={isSelected ? 'selected-row' : ''}>
                      <td className="mono text-muted">{rev.stepIndex}</td>
                      <td className="mono">
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', flexWrap: 'wrap' }}>
                          <span>{formatDateTime(rev.publish_time)}</span>
                          {isSelected && (
                            <span className="badge badge-healthy" style={{ fontSize: '0.68rem', padding: '1px 6px' }}>
                              ★ Day-Ahead Baseline
                            </span>
                          )}
                          {isPostCutoff && (
                            <span className="badge badge-neutral" style={{ fontSize: '0.68rem', padding: '1px 6px' }}>
                              Post-Cutoff
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="text-muted">{calculateLeadHours(rev.publish_time, rev.start_time)}</td>
                      <td className="mono text-right font-semibold">{formatMw(rev.generation)}</td>
                      <td
                        className={`mono text-right ${
                          rev.delta === null
                            ? 'text-muted'
                            : rev.delta > 0
                            ? 'text-amber'
                            : rev.delta < 0
                            ? 'text-indigo'
                            : 'text-muted'
                        }`}
                      >
                        {rev.delta !== null ? formatMwWithSign(rev.delta) : 'Baseline'}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </>
      )}

      <div className="chart-footer-note">
        <span className="note-label">Lookahead Prevention Policy:</span> Only forecasts published on or before Day D-1 at {cutoffTime} UTC (marked with ★) are eligible for Day-Ahead market positions and accuracy metrics. Later revisions show meteorological model convergence leading into delivery but are excluded from day-ahead KPIs to guarantee zero lookahead bias.
      </div>
    </div>
  );
};
