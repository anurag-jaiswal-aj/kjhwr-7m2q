# Gridbricks | Wind Intelligence

**UK National Wind Generation Day-Ahead Forecast Reliability & Market Analytics (January 2026)**

An analytics platform built for an energy utility's day-ahead electricity procurement desk. The system evaluates Great Britain national wind generation outturn against day-ahead meteorological forecasts from Elexon BMRS across January 2026.

---

## Submission Deliverables & Live Links

- **Live Deployed Web Application:** [https://kjhwr-7m2q.vercel.app](https://kjhwr-7m2q.vercel.app/)
- **Live Deployed REST API:** [https://kjhwr-7m2q.onrender.com/api](https://kjhwr-7m2q.onrender.com/api) *(Health Check: [`https://kjhwr-7m2q.onrender.com/api/health`](https://kjhwr-7m2q.onrender.com/api/health))*
- **Public GitHub Repository:** [https://github.com/anurag-jaiswal-aj/kjhwr-7m2q](https://github.com/anurag-jaiswal-aj/kjhwr-7m2q)
- **Unlisted YouTube Video Demonstration:** [https://youtu.be/9WV7mk6LWbw](https://youtu.be/9WV7mk6LWbw) *(Duration: ~8:58)*
  - *Part 1:* Customer pitch and live dashboard walkthrough for an energy utility day-ahead electricity procurement desk.
  - *Part 2:* Technical walkthrough covering architecture, data ingestion, zero-lookahead forecast selection, and test suite.

---

## AI-Tooling & Engineering Methodology Disclosure

In accordance with Section 2 of the challenge brief (*"You are free to use AI tools to assist with building this application (please mention it explicitly in the README if you've used AI tools)"*):

- **AI Tools Employed:** Google DeepMind's **Antigravity agentic coding assistant** (powered by Gemini models).
- **Assisted Workflows:**
  - Automated initial exploratory research on Elexon BMRS API streams (`FUELHH` and `WINDFOR`).
  - Scaffolding Python FastAPI route signatures, Pydantic v2 validation models, and automated test fixtures.
  - Structuring the React 19 + TypeScript component hierarchy and drafting Vanilla CSS styling tokens.
  - Multi-stage Docker containerization and Nginx reverse proxy configuration.
- **Human Oversight & Engineering Verification:**
  - Independent verification of native half-hourly temporal resolution preservation (all 1,488 SPs).
  - Mathematical audit and verification of error sign convention ($e_i = F_i - A_i$) and statistical metrics (MAE, RMSE, MBE).
  - Explicit classification of the D-1 11:00 UTC cutoff as an analytical assumption (modeled on GB Day-Ahead auction conventions; not an official Elexon rule).
  - Full automated regression test suite (34 tests) and live containerized browser audit.

---

## Current Status: Stage 6 Complete (Docker Containerization & Production-Readiness Verified)

The platform comprises an end-to-end analytical stack:
1. **Stage 1 (Data Investigation):** Comprehensive data audit in [`docs/DATA_INVESTIGATION.md`](docs/DATA_INVESTIGATION.md).
2. **Stage 2 (Ingestion & Persistence):** Bounded Elexon API streaming client with retry/backoff, SQLite persistence (`backend/data/analytics.db`) storing 1,488 half-hourly actuals and 19,272 forecast records across 264 distinct publication runs.
3. **Stage 3 (Analytical Core Engine):** Lookahead-free forecast selector and statistical metric engine computing MAE, RMSE, MBE, and coverage.
4. **Stage 4 (REST API Service Layer):** Production-quality FastAPI application (`backend/app/`) with 6 analytical endpoints, typed Pydantic models, parameter validation, and 34 automated tests. Detailed specification in [`docs/API_GUIDE.md`](docs/API_GUIDE.md).
5. **Stage 5 (React Analytics Dashboard):** High-performance React + TypeScript interface (`frontend/`) built with Vite, Vanilla CSS design system, Recharts data visualizations, dynamic parameter filtering, and forecast vintage evolution inspection.
6. **Stage 6 (Docker Containerization & Deployment):** Multi-stage production container setup with Docker Compose, Nginx reverse proxy, automatic SQLite volume persistence, and verified zero-downtime container restarts. Production guide in [`docs/DEPLOYMENT_GUIDE.md`](docs/DEPLOYMENT_GUIDE.md).

---

## Quickstart: Docker (Recommended)

The fastest way to run the verified full-stack application is with Docker Compose:

```bash
# Clone and enter directory
cd ~/Developer/gridbricks-challenge

# Build and start services in detached mode
docker compose up --build -d

# Check service health
docker compose ps
```
- **Web Dashboard:** [http://localhost:3001](http://localhost:3001)
- **Backend API Direct:** [http://localhost:8001/api/health](http://localhost:8001/api/health)
- **API via Nginx Reverse Proxy:** [http://localhost:3001/api/health](http://localhost:3001/api/health)

To stop services:
```bash
docker compose down
```

For full deployment architectures and cloud configuration, see [`docs/DEPLOYMENT_GUIDE.md`](docs/DEPLOYMENT_GUIDE.md).

---

## Key Metrics Summary (January 2026 Outturn at D-1 11:00 UTC Baseline)

Under the baseline analytical assumption (D-1 11:00 UTC decision cutoff modeled on the Great Britain Day-Ahead auction order book closure):

| Metric | Native Half-Hour Resolution | Hourly Aggregated Mode | Interpretation |
|---|---|---|---|
| **Coverage** | 100.0% (1,488 / 1,488 SPs) | 100.0% (744 / 744 Hours) | Full dataset completeness across all 31 days |
| **Mean Outturn** | 11,580.74 MW | 11,580.74 MW | Average national wind generation outturn |
| **Mean Forecast** | 13,421.03 MW | 13,421.03 MW | Average day-ahead expected generation |
| **MAE** | **2,126.12 MW** (18.36%) | **2,122.81 MW** (18.33%) | Mean absolute forecasting error magnitude |
| **RMSE** | **2,620.80 MW** (22.63%) | **2,616.69 MW** | Penalizes large forecasting misses |
| **MBE ($F - A$)** | **+1,840.30 MW** | **+1,840.30 MW** | Systematic meteorological over-forecasting |

*Sign convention: $\text{Error} = \text{Forecast} - \text{Actual}$. Positive MBE confirms that day-ahead forecasts systematically exceeded actual generation across January 2026.*

> [!NOTE]
> **Commercial Interpretation Boundary:** Demonstrating that national wind forecasts exceeded actual generation (+1,840.30 MW MBE) does *not* prove utility financial loss or net energy shortfalls. Under Elexon Balancing and Settlement Code (BSC) rules, financial exposure depends on half-hourly System Buy/Sell Prices (cashout prices), supplier retail demand profile, and the participant's overall portfolio imbalance across all technologies.

---

## Local Development (Without Docker)

### 1. Prerequisites
- **Python:** 3.10+ (tested on Python 3.14 on macOS)
- **Node.js:** 20+ (tested on Node v24.10.0 and npm 11.6.0)

---

### 2. Backend Setup & Startup
```bash
# Navigate to repository root
cd ~/Developer/gridbricks-challenge

# Set up virtual environment and install dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

# Start FastAPI backend (port 8000)
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```
- **API Base:** `http://localhost:8000/api`
- **Interactive Swagger UI:** `http://localhost:8000/docs`
- **ReDoc Documentation:** `http://localhost:8000/redoc`

---

### 3. Frontend Setup & Startup
In a separate terminal:
```bash
# Navigate to frontend directory
cd ~/Developer/gridbricks-challenge/frontend

# Install frontend dependencies
npm install

# Start Vite development server (port 5173)
npm run dev
```
- **Dashboard URL:** `http://localhost:5173`

---

### 4. Configuring the API Base URL
The frontend includes a built-in proxy in `vite.config.ts` mapping `/api` directly to `http://127.0.0.1:8000`.

To point the frontend to a remote or non-standard API host, set the `VITE_API_BASE_URL` environment variable:
```bash
# Example override
export VITE_API_BASE_URL="http://api.internal.gridbricks.com/api"
npm run dev
```

---

## Implemented Product Features

- **Branding & Availability Header:** Real-time health badge querying `/api/health` with connectivity indicator and January 2026 dataset readiness.
- **Evaluation Controls:**
  - Quick period presets (Full Month, W1, W2, W3, W4, Final Days) and custom start/end date inputs.
  - Resolution mode switch (Native 30-minute settlement periods vs. Hourly aggregated).
  - D-1 Decision Cutoff dropdown (`09:00`, `11:00`, `12:00`, `14:00`, `16:00` UTC) with zero-lookahead enforcement.
- **Statistical KPI Cards:** Displays MAE (MW and % of mean outturn), RMSE, MBE (with explicit sign convention callout), observation coverage %, and mean generation outturn vs. forecast.
- **Time-Series Visualization:** Interactive dual-series line chart (Sky Blue actual outturn vs. Amber day-ahead forecast) with custom tooltips formatting delivery timestamp, settlement period (SP 1–48), generation, and forecast error.
- **Forecast Error Distribution:** Error bar chart with prominent zero reference line, color-coded over-forecasting (+, warm orange) and under-forecasting (−, cool indigo), and extrema pills (`Max Over` and `Max Under`). Includes commercial disclaimer separating meteorological error from utility imbalance financial settlement.
- **Daily Performance Breakdown:** Sortable daily evaluation table listing all 31 days with `Complete (48/48)` vs `Incomplete` badges, MAE, RMSE, MBE, and outturn. Clicking any day row filters the dashboard to that day.
- **Forecast Revision History (Evolution):** Selectable target delivery hour displaying historical forecast publication runs from 2.5 days ahead down to gate closure, complete with step chart, delta shifts ($\Delta\text{ MW}$), and lead time calculations.
- **Methodology & Context Modal:** Deep-dive modal explaining data sources, the D-1 11:00 UTC auction assumption, resolution alignment mechanics, mathematical formulas, and commercial boundary conditions.

---

## Verification & Testing Commands

### Backend Automated Test Suite (34 Tests)
```bash
source .venv/bin/activate
python -m pytest backend/tests -v
```
*Current test suite: **34 passed in ~0.25s**.*

### Frontend Production Build & TypeScript Type-Check
```bash
cd frontend
npm run build
```
*Compiles TypeScript (`tsc -b`) and bundles client assets via Vite with zero errors.*

### Frontend Code Quality Check
```bash
cd frontend
npm run lint
```
*Runs `oxlint` with 0 errors and 0 warnings.*

---

## Repository Structure

```
gridbricks-challenge/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── endpoints.py     # FastAPI route handlers
│   │   │   ├── schemas.py       # Pydantic response models
│   │   │   └── validation.py    # Query parameter validators (HTTP 400)
│   │   ├── db/
│   │   │   ├── database.py      # SQLite connection & schema initialization
│   │   │   └── models.py        # Core domain models
│   │   ├── services/
│   │   │   ├── elexon_client.py # HTTP client with retry & rate-limit backoff
│   │   │   ├── forecast_selector.py # Lookahead-free forecast selection logic
│   │   │   ├── ingestion.py     # Batch ingestion pipeline
│   │   │   └── metrics.py       # Statistical error metric calculations
│   │   ├── config.py            # System configuration & environment defaults
│   │   └── main.py              # FastAPI app factory & CORS middleware
│   ├── data/
│   │   └── analytics.db         # Persistent SQLite database (WAL mode)
│   ├── Dockerfile               # Production Python 3.11-slim container
│   ├── requirements.txt         # Backend Python dependencies
│   └── tests/                   # 34 automated unit & integration tests
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   │   ├── client.ts        # Typed API client with AbortController
│   │   │   └── types.ts         # TypeScript interfaces matching backend
│   │   ├── components/          # Reusable analytics components
│   │   ├── utils/               # Formatters for MW, dates, and percentages
│   │   ├── App.tsx              # Main dashboard state coordinator
│   │   ├── App.css              # Layouts and responsive styling
│   │   └── index.css            # Design tokens & typography
│   ├── Dockerfile               # Multi-stage build (Node 20 -> Nginx alpine)
│   ├── nginx.conf               # Nginx reverse proxy & static asset server
│   ├── package.json             # React 19, TypeScript, Recharts, Lucide
│   └── vite.config.ts           # Vite bundler and backend proxy config
├── docs/
│   ├── API_GUIDE.md             # Complete REST API specification & usage
│   ├── DATA_INVESTIGATION.md    # Stage 1 Elexon data investigation report
│   ├── DEPLOYMENT_GUIDE.md      # Docker container & cloud deployment manual
│   └── IMPLEMENTATION_PLAN.md   # Architectural roadmap and gate verification
├── docker-compose.yml           # Production multi-container orchestration
├── .dockerignore                # Container build context filter
├── .env.example                 # Safe environment configuration template
├── run_ingestion.py             # CLI script to seed/update local SQLite DB
└── README.md                    # Project overview & quickstart
```
