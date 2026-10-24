import React from 'react';
import { X, BookOpen, Clock, Layers, Calculator, AlertTriangle, ShieldCheck } from 'lucide-react';

interface MethodologyModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const MethodologyModal: React.FC<MethodologyModalProps> = ({ isOpen, onClose }) => {
  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content card" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div className="modal-title-row">
            <BookOpen className="text-sky" size={20} />
            <h2 className="modal-title">Methodology, Assumptions & Market Context</h2>
          </div>
          <button className="modal-close-btn" onClick={onClose} aria-label="Close modal">
            <X size={18} />
          </button>
        </div>

        <div className="modal-body">
          {/* Section 1: Data Sources & Scope */}
          <section className="methodology-section">
            <h4 className="section-title">
              <ShieldCheck size={16} className="text-emerald" />
              1. Official Data Sources & Audit Scope
            </h4>
            <p className="section-text">
              This analytics engine evaluates national-level wind generation in Great Britain across the full month of <strong>January 2026 (Jan 1, 00:00 UTC to Jan 31, 23:30 UTC)</strong> using official Elexon BMRS streaming APIs:
            </p>
            <ul className="methodology-list">
              <li>
                <strong>Actual Outturn (<code className="mono">FUELHH</code>):</strong> Half-hourly settlement period generation filtered strictly for <code className="mono">fuelType=WIND</code>. Exactly <strong>1,488</strong> half-hourly records (31 days × 48 settlement periods) with zero missing intervals.
              </li>
              <li>
                <strong>Wind Generation Forecasts (<code className="mono">WINDFOR</code>):</strong> Historical day-ahead forecasts preserving all publication runs (<strong>19,272</strong> total records spanning <strong>264</strong> distinct publication vintages).
              </li>
            </ul>
          </section>

          {/* Section 2: D-1 11:00 UTC Baseline Cutoff */}
          <section className="methodology-section">
            <h4 className="section-title">
              <Clock size={16} className="text-amber" />
              2. Baseline Decision Cutoff (Analytical Assumption)
            </h4>
            <p className="section-text">
              The analytical engine applies a baseline cutoff deadline of <strong>11:00 UTC on Day D-1</strong>:
            </p>
            <div className="callout callout-warning">
              <strong>Explicit Status:</strong> This is a modeled <em>analytical assumption</em> reflecting GB wholesale power market mechanics (EPEX SPOT and Nord Pool Day-Ahead auction order books close at 11:00 GMT/UTC). It is <strong>not</strong> an official Elexon statutory rule.
            </div>
            <p className="section-text" style={{ marginTop: 8 }}>
              <strong>Lookahead Prohibition:</strong> For any delivery day D, the selector strictly selects the latest forecast published on or before Day D-1 at 11:00 UTC. Any forecast vintage published after 11:00 on D-1 is inadmissible for day-ahead position setting to eliminate lookahead bias.
            </p>
          </section>

          {/* Section 3: Resolution Alignment Modes */}
          <section className="methodology-section">
            <h4 className="section-title">
              <Layers size={16} className="text-sky" />
              3. Resolution Alignment Modes
            </h4>
            <p className="section-text">
              Because Elexon actuals operate at 30-minute settlement granularity while WINDFOR forecasts are published at 60-minute boundaries, two explicit evaluation modes are supported:
            </p>
            <ul className="methodology-list">
              <li>
                <strong>Native Half-Hour Mode (Primary, 1,488 intervals):</strong> Preserves both settlement periods in an hour (e.g. 12:00–12:30 SP 25 and 12:30–13:00 SP 26). Each half-hour is paired against the parent hour's prevailing forecast. This preserves true market settlement volatility without artificial smoothing.
              </li>
              <li>
                <strong>Hourly Aggregated Mode (744 intervals):</strong> Averages the two half-hour actuals within each clock hour (Mean Actual = (Actual :00 + Actual :30) / 2) and compares against the hourly forecast.
              </li>
            </ul>
          </section>

          {/* Section 4: Statistical Metric Formulas */}
          <section className="methodology-section">
            <h4 className="section-title">
              <Calculator size={16} className="text-indigo" />
              4. Error Sign Convention & Statistical Metrics
            </h4>
            <p className="section-text">
              All error metrics follow the standard forecasting convention:
            </p>
            <div className="formula-box mono">
              Error = Forecast − Actual
            </div>
            <ul className="methodology-list" style={{ marginTop: 8 }}>
              <li>
                <strong>Mean Absolute Error (MAE):</strong> Mean of |Forecast − Actual|. Measures overall forecast miss magnitude (January 2026: <strong>2,126.12 MW</strong> / 18.36%).
              </li>
              <li>
                <strong>Root Mean Squared Error (RMSE):</strong> Square root of Mean((Forecast − Actual)²). Heavily penalizes large forecasting excursions (January 2026: <strong>2,620.80 MW</strong>).
              </li>
              <li>
                <strong>Mean Bias Error (MBE):</strong> Mean of (Forecast − Actual) (January 2026: <strong>+1,840.30 MW</strong>). <em>A positive MBE confirms systematic national wind over-forecasting by ~1.84 GW across January 2026.</em>
              </li>
              <li>
                <strong>Strict Null Handling:</strong> Missing intervals are excluded from denominators and are never zero-filled.
              </li>
            </ul>
          </section>

          {/* Section 5: Commercial & Financial Interpretation Boundary */}
          <section className="methodology-section">
            <h4 className="section-title">
              <AlertTriangle size={16} className="text-amber" />
              5. Commercial Interpretation Boundary
            </h4>
            <div className="callout callout-disclaimer">
              <p>
                <strong>Essential Caution:</strong> Demonstrating that national wind forecasts exceeded actual generation (+1,840 MW MBE) does <em>not</em> prove utility financial loss or net procurement deficit.
              </p>
              <p style={{ marginTop: 6 }}>
                Under Elexon Balancing and Settlement Code (BSC) rules, financial exposure depends on half-hourly System Buy/Sell Prices (cashout prices), supplier retail demand profile, and the participant's overall portfolio imbalance across all technologies.
              </p>
            </div>
          </section>
        </div>

        <div className="modal-footer">
          <button className="primary-button" onClick={onClose}>
            Got it, return to Dashboard
          </button>
        </div>
      </div>
    </div>
  );
};
