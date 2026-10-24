import React from 'react';
import { Wind, Activity, HelpCircle, CheckCircle2, AlertTriangle, XCircle } from 'lucide-react';
import type { HealthResponse } from '../api/types';

interface HeaderProps {
  health: HealthResponse | null;
  healthLoading: boolean;
  onOpenMethodology: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  health,
  healthLoading,
  onOpenMethodology,
}) => {
  return (
    <header className="header-container">
      <div className="header-left">
        <div className="brand-logo">
          <Wind className="brand-icon" size={24} />
          <div className="brand-titles">
            <div className="brand-name">
              <span className="brand-bold">Gridbricks</span>
              <span className="brand-divider">/</span>
              <span className="brand-product">Wind Intelligence</span>
            </div>
            <span className="brand-subtitle">
              UK National Wind Generation Day-Ahead Forecast Reliability & Market Analytics
            </span>
          </div>
        </div>
      </div>

      <div className="header-right">
        <div className="header-badge-group">
          <div className="badge badge-neutral mono">
            <span className="badge-label">Period:</span>
            <strong>Jan 1–31, 2026</strong>
          </div>

          <div
            className={`badge ${
              healthLoading
                ? 'badge-warning'
                : health?.status === 'healthy' && health.dataset_available
                ? 'badge-healthy'
                : 'badge-unhealthy'
            }`}
            title={
              healthLoading
                ? 'Checking API connectivity...'
                : health?.status === 'healthy'
                ? `FastAPI Connected • SQLite DB Active • Dataset: ${health.dataset_period || 'Available'}`
                : 'API or database connection failed'
            }
          >
            {healthLoading ? (
              <>
                <Activity size={13} className="pulse" />
                <span>Checking API...</span>
              </>
            ) : health?.status === 'healthy' && health.dataset_available ? (
              <>
                <CheckCircle2 size={13} />
                <span>API Live (Jan 2026 Seeded)</span>
              </>
            ) : health?.status === 'healthy' && !health.dataset_available ? (
              <>
                <AlertTriangle size={13} />
                <span>DB Connected (No Jan Data)</span>
              </>
            ) : (
              <>
                <XCircle size={13} />
                <span>API Offline</span>
              </>
            )}
          </div>
        </div>

        <button
          className="methodology-button"
          onClick={onOpenMethodology}
          aria-label="View methodology and assumptions"
        >
          <HelpCircle size={15} />
          <span>Methodology & Baseline</span>
        </button>
      </div>
    </header>
  );
};
