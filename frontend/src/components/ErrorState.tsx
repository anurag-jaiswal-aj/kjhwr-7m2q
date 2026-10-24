import React from 'react';
import { AlertOctagon, Terminal, RefreshCw } from 'lucide-react';

interface ErrorStateProps {
  error: string;
  onRetry: () => void;
  retrying?: boolean;
}

export const ErrorState: React.FC<ErrorStateProps> = ({ error, onRetry, retrying = false }) => {
  return (
    <div className="card error-banner-card">
      <div className="error-banner-header">
        <AlertOctagon size={24} className="text-unhealthy" />
        <div>
          <h3 className="error-banner-title">Backend REST Service Unavailable</h3>
          <p className="error-banner-subtitle">{error}</p>
        </div>
      </div>

      <div className="backend-start-instructions">
        <p className="instructions-title">
          <Terminal size={14} style={{ display: 'inline', marginRight: 6 }} />
          To start the local FastAPI service, run the following in your terminal:
        </p>
        <pre className="command-box mono">
          cd ~/Developer/gridbricks-challenge<br />
          source .venv/bin/activate<br />
          uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
        </pre>
      </div>

      <div className="error-actions">
        <button className="primary-button" onClick={onRetry} disabled={retrying}>
          <RefreshCw size={14} className={retrying ? 'pulse' : ''} />
          <span>{retrying ? 'Reconnecting to API...' : 'Retry Connection'}</span>
        </button>
      </div>
    </div>
  );
};
