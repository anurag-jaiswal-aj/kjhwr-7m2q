import React, { useState } from 'react';
import type { DailyMetricsItem } from '../api/types';
import { formatMw, formatMwWithSign, formatDate } from '../utils/formatters';
import { CheckCircle2, AlertTriangle, ArrowUpDown, Calendar } from 'lucide-react';

interface DailyMetricsTableProps {
  days: DailyMetricsItem[];
  loading: boolean;
  onSelectDay?: (date: string) => void;
  selectedDate?: string | null;
}

type SortField = 'date' | 'mae' | 'rmse' | 'mbe' | 'mean_actual' | 'mean_forecast';
type SortOrder = 'asc' | 'desc';

export const DailyMetricsTable: React.FC<DailyMetricsTableProps> = ({
  days,
  loading,
  onSelectDay,
  selectedDate,
}) => {
  const [sortField, setSortField] = useState<SortField>('date');
  const [sortOrder, setSortOrder] = useState<SortOrder>('asc');

  if (loading) {
    return (
      <div className="card daily-table-card">
        <div className="skeleton" style={{ height: 24, width: 220, marginBottom: 16 }} />
        <div className="skeleton" style={{ height: 250, width: '100%' }} />
      </div>
    );
  }

  if (!days || days.length === 0) {
    return null;
  }

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortOrder(field === 'date' ? 'asc' : 'desc');
    }
  };

  const sortedDays = [...days].sort((a, b) => {
    let aVal = a[sortField];
    let bVal = b[sortField];

    if (aVal === null || aVal === undefined) aVal = -Infinity;
    if (bVal === null || bVal === undefined) bVal = -Infinity;

    if (aVal < bVal) return sortOrder === 'asc' ? -1 : 1;
    if (aVal > bVal) return sortOrder === 'asc' ? 1 : -1;
    return 0;
  });

  return (
    <div className="card daily-table-card">
      <div className="chart-header">
        <div>
          <h3 className="chart-title">Daily Reliability Breakdown</h3>
          <p className="chart-subtitle">
            Day-by-day accuracy evaluation distinguishing full 48-interval days from partial coverage.
          </p>
        </div>
        <div className="daily-stats-summary">
          <span className="badge badge-neutral">
            <Calendar size={13} />
            <span>{days.length} Days in Period</span>
          </span>
        </div>
      </div>

      <div className="table-responsive">
        <table className="daily-table">
          <thead>
            <tr>
              <th onClick={() => handleSort('date')} className="sortable">
                <div className="th-content">
                  <span>Date</span>
                  <ArrowUpDown size={12} />
                </div>
              </th>
              <th>Status</th>
              <th onClick={() => handleSort('mae')} className="sortable text-right">
                <div className="th-content justify-end">
                  <span>MAE</span>
                  <ArrowUpDown size={12} />
                </div>
              </th>
              <th onClick={() => handleSort('rmse')} className="sortable text-right">
                <div className="th-content justify-end">
                  <span>RMSE</span>
                  <ArrowUpDown size={12} />
                </div>
              </th>
              <th onClick={() => handleSort('mbe')} className="sortable text-right">
                <div className="th-content justify-end">
                  <span>MBE (F − A)</span>
                  <ArrowUpDown size={12} />
                </div>
              </th>
              <th onClick={() => handleSort('mean_actual')} className="sortable text-right">
                <div className="th-content justify-end">
                  <span>Mean Outturn</span>
                  <ArrowUpDown size={12} />
                </div>
              </th>
              <th onClick={() => handleSort('mean_forecast')} className="sortable text-right">
                <div className="th-content justify-end">
                  <span>Mean Forecast</span>
                  <ArrowUpDown size={12} />
                </div>
              </th>
              <th className="text-right">Coverage</th>
            </tr>
          </thead>
          <tbody>
            {sortedDays.map((d) => {
              const isSelected = selectedDate === d.date;
              const isOver = (d.mbe ?? 0) > 0;

              return (
                <tr
                  key={d.date}
                  className={`${isSelected ? 'selected-row' : ''} ${onSelectDay ? 'clickable-row' : ''}`}
                  onClick={() => onSelectDay && onSelectDay(d.date)}
                  title={onSelectDay ? `Click to filter charts to ${d.date}` : undefined}
                >
                  <td className="mono font-semibold">{formatDate(d.date)}</td>
                  <td>
                    {d.is_complete ? (
                      <span className="badge badge-healthy">
                        <CheckCircle2 size={12} />
                        <span>Complete</span>
                      </span>
                    ) : (
                      <span className="badge badge-warning">
                        <AlertTriangle size={12} />
                        <span>Incomplete ({d.matched_intervals}/{d.total_intervals})</span>
                      </span>
                    )}
                  </td>
                  <td className="mono text-right">{formatMw(d.mae)}</td>
                  <td className="mono text-right">{formatMw(d.rmse)}</td>
                  <td
                    className={`mono text-right ${isOver ? 'text-amber' : 'text-indigo'}`}
                    style={{ fontWeight: 500 }}
                  >
                    {formatMwWithSign(d.mbe)}
                  </td>
                  <td className="mono text-right text-muted">{formatMw(d.mean_actual)}</td>
                  <td className="mono text-right text-muted">{formatMw(d.mean_forecast)}</td>
                  <td className="mono text-right">
                    {d.matched_intervals} / {d.total_intervals}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};
