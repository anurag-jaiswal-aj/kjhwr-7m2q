import React from 'react';
import { Calendar, Clock, Layers, RotateCcw, Info } from 'lucide-react';
import type { ResolutionMode } from '../api/types';

interface FiltersBarProps {
  startDate: string;
  endDate: string;
  resolution: ResolutionMode;
  cutoffTime: string;
  onStartDateChange: (val: string) => void;
  onEndDateChange: (val: string) => void;
  onResolutionChange: (val: ResolutionMode) => void;
  onCutoffTimeChange: (val: string) => void;
  onReset: () => void;
}

export const FiltersBar: React.FC<FiltersBarProps> = ({
  startDate,
  endDate,
  resolution,
  cutoffTime,
  onStartDateChange,
  onEndDateChange,
  onResolutionChange,
  onCutoffTimeChange,
  onReset,
}) => {
  const isFullMonth = startDate === '2026-01-01' && endDate === '2026-01-31';

  const setPreset = (start: string, end: string) => {
    onStartDateChange(start);
    onEndDateChange(end);
  };

  return (
    <div className="card filters-card">
      <div className="filters-header">
        <div className="filters-title">
          <Calendar size={16} className="filter-title-icon" />
          <span>Evaluation Controls & Parameters</span>
        </div>
        <button
          className="reset-button"
          onClick={onReset}
          title="Reset to January 2026 Baseline (Native 30m, 11:00 UTC D-1 Cutoff)"
        >
          <RotateCcw size={13} />
          <span>Reset Defaults</span>
        </button>
      </div>

      <div className="filters-grid">
        {/* Preset Date Ranges */}
        <div className="filter-group">
          <label className="filter-label">Quick Periods</label>
          <div className="preset-buttons">
            <button
              className={`preset-btn ${isFullMonth ? 'active' : ''}`}
              onClick={() => setPreset('2026-01-01', '2026-01-31')}
            >
              Full Jan
            </button>
            <button
              className={`preset-btn ${startDate === '2026-01-01' && endDate === '2026-01-07' ? 'active' : ''}`}
              onClick={() => setPreset('2026-01-01', '2026-01-07')}
            >
              W1 (1–7)
            </button>
            <button
              className={`preset-btn ${startDate === '2026-01-08' && endDate === '2026-01-14' ? 'active' : ''}`}
              onClick={() => setPreset('2026-01-08', '2026-01-14')}
            >
              W2 (8–14)
            </button>
            <button
              className={`preset-btn ${startDate === '2026-01-15' && endDate === '2026-01-21' ? 'active' : ''}`}
              onClick={() => setPreset('2026-01-15', '2026-01-21')}
            >
              W3 (15–21)
            </button>
            <button
              className={`preset-btn ${startDate === '2026-01-22' && endDate === '2026-01-28' ? 'active' : ''}`}
              onClick={() => setPreset('2026-01-22', '2026-01-28')}
            >
              W4 (22–28)
            </button>
            <button
              className={`preset-btn ${startDate === '2026-01-29' && endDate === '2026-01-31' ? 'active' : ''}`}
              onClick={() => setPreset('2026-01-29', '2026-01-31')}
            >
              End (29–31)
            </button>
          </div>
        </div>

        {/* Custom Date Pickers */}
        <div className="filter-group">
          <label className="filter-label">Date Window</label>
          <div className="date-input-pair">
            <input
              type="date"
              className="date-input"
              value={startDate}
              min="2026-01-01"
              max={endDate}
              onChange={(e) => onStartDateChange(e.target.value)}
            />
            <span className="date-sep">to</span>
            <input
              type="date"
              className="date-input"
              value={endDate}
              min={startDate}
              max="2026-01-31"
              onChange={(e) => onEndDateChange(e.target.value)}
            />
          </div>
        </div>

        {/* Resolution Mode Switch */}
        <div className="filter-group">
          <div className="filter-label-row">
            <label className="filter-label">
              <Layers size={13} style={{ display: 'inline', marginRight: 4 }} />
              Resolution
            </label>
            <span
              className="info-hint"
              title="Native mode retains all 48 half-hour settlement periods per day paired to prevailing hourly forecasts. Hourly mode aggregates both half-hour actuals into a 1h average."
            >
              <Info size={12} />
            </span>
          </div>
          <div className="segmented-control">
            <button
              className={`segment-btn ${resolution === 'native_half_hour' ? 'active' : ''}`}
              onClick={() => onResolutionChange('native_half_hour')}
            >
              Native Half-Hour (30m)
            </button>
            <button
              className={`segment-btn ${resolution === 'hourly_aggregated' ? 'active' : ''}`}
              onClick={() => onResolutionChange('hourly_aggregated')}
            >
              Hourly Aggregated (1h)
            </button>
          </div>
        </div>

        {/* Decision Cutoff Selector */}
        <div className="filter-group">
          <div className="filter-label-row">
            <label className="filter-label">
              <Clock size={13} style={{ display: 'inline', marginRight: 4 }} />
              D-1 Decision Cutoff
            </label>
            <span
              className="info-hint"
              title="Cutoff time on Day D-1 (UTC). Modeled on GB Day-Ahead auction closure (11:00 UTC). Forecasts published after this deadline are strictly excluded to avoid lookahead bias."
            >
              <Info size={12} />
            </span>
          </div>
          <select
            className="select-input"
            value={cutoffTime}
            onChange={(e) => onCutoffTimeChange(e.target.value)}
          >
            <option value="09:00">09:00 UTC (Early DA Gate)</option>
            <option value="11:00">11:00 UTC (Baseline - DA Auction)</option>
            <option value="12:00">12:00 UTC (Midday DA)</option>
            <option value="14:00">14:00 UTC (Afternoon Run)</option>
            <option value="16:00">16:00 UTC (Late DA Run)</option>
          </select>
        </div>
      </div>
    </div>
  );
};
