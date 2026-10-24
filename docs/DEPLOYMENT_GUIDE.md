# Gridbricks | Wind Intelligence — Production Deployment Guide

## 1. Executive Summary & Architecture

The Gridbricks Wind Intelligence system provides UK wholesale electricity market analytics evaluating Day-Ahead National Wind Generation Forecasts (`WINDFOR`) against Settlement Period Outturn Generation (`FUELHH`) for January 2026.

```
+----------------------------------------------------------------------------------+
|                              Production Topology                                  |
+----------------------------------------------------------------------------------+
                                                                                    
      [ Client Browser / Procurement Team ]                                         
                        |                                                           
                        | HTTP (Port 80 / 3001)                                     
                        v                                                           
         +-----------------------------+                                            
         |      Nginx Web Server       |                                            
         |   (Alpine Reverse Proxy)    |                                            
         +-----------------------------+                                            
           |                         |                                              
           | Static Assets           | /api/* (HTTP Proxy)                          
           v                         v                                              
   +---------------+      +----------------------+                                  
   | React / Vite  |      |   FastAPI Service    |                                  
   | Production SPA|      | (Uvicorn - 2 workers)|                                  
   +---------------+      +----------------------+                                  
                                     |                                              
                                     | Local I/O                                    
                                     v                                              
                          +---------------------+                                   
                          | SQLite Database     |                                   
                          | (analytics.db)      |                                   
                          | [analytics_data vol]|                                   
                          +---------------------+                                   
```

### Key Architectural Tenets
1. **Separation of Concerns:** React frontend is pre-compiled to minified static assets and served by Nginx with gzip compression, caching, and security headers.
2. **Reverse Proxy Connectivity:** In Docker, Nginx proxies `/api/*` directly to `http://backend:8000/api/` using internal Docker bridge networking (`gridbricks-net`). The frontend uses relative `/api` paths, eliminating CORS overhead and brittle host IP bindings.
3. **Data Persistence:** The pre-seeded January 2026 SQLite database (`5.2 MB`, containing 1,488 actuals and 19,272 forecasts) is packaged into the backend image and mounted to named Docker volume `analytics_data` (`/app/backend/data`). Restarts or redeployments retain data without re-fetching from external APIs.

---

## 2. Local Docker Deployment (Quickstart)

### Prerequisites
- Docker Engine 24.0+ and Docker Compose v2.0+
- Ports 8001 and 3001 available (customizable via `.env`)

### Step-by-Step Commands

1. **Clone and enter repository:**
   ```bash
   cd ~/Developer/gridbricks-challenge
   ```

2. **Configure environment (optional):**
   ```bash
   cp .env.example .env
   # Default ports: BACKEND_PORT=8001, FRONTEND_PORT=3001
   ```

3. **Build container images:**
   ```bash
   docker compose build
   ```

4. **Launch services in detached mode:**
   ```bash
   docker compose up -d
   ```

5. **Verify runtime health:**
   ```bash
   # Check container status (both should report 'healthy')
   docker compose ps

   # Test backend health endpoint via Nginx
   curl -s http://127.0.0.1:3001/api/health
   # Expected: {"status":"healthy","database":"connected","dataset_available":true,"dataset_period":"2026-01-01 to 2026-01-31"}

   # Test baseline January metrics
   curl -s "http://127.0.0.1:3001/api/metrics?cutoff_time=11:00&resolution=native_half_hour"
   # Expected: MAE=2126.12, RMSE=2620.80, MBE=+1840.30, Coverage=100.0%
   ```

6. **Open the web dashboard:**
   Visit [http://localhost:3001](http://localhost:3001) in your browser.

7. **Stopping containers:**
   ```bash
   docker compose down
   # To stop and wipe persisted volumes: docker compose down -v
   ```

---

## 3. SQLite Dataset & Persistence Approach

### Why SQLite is Appropriate for This Workload
- **Analytical Read Pattern:** The January 2026 evaluation dataset is static once seeded (1,488 half-hour actuals, 19,272 forecast publications). Querying involves indexed aggregations, lead-time calculations, and deterministic joins. SQLite handles this in sub-millisecond query times with zero client-server network latency.
- **Self-Contained Portability:** Zero external database server dependencies (no Postgres/MySQL server administration needed).

### Persistence in Containerized Environments
1. **Container Image Pre-seeding:** The pre-seeded database at `backend/data/analytics.db` is copied into the backend Docker image at `/app/backend/data/analytics.db` during image build.
2. **Named Volume Mapping:** In `docker-compose.yml`, volume `analytics_data` is mounted to `/app/backend/data`. When Docker creates the volume, it initializes it with the pre-existing contents of `/app/backend/data/`.
3. **Restart Invariance:** Subsequent container restarts reuse the populated volume. The database is never re-downloaded or duplicated on startup.

---

## 4. Cloud Production Deployment Options

### Recommended Architecture: Decoupled Backend & Static Frontend

Because static website hosts (Vercel, Cloudflare Pages, Netlify) cannot execute Python/FastAPI runtimes, we recommend deploying the Python backend as a containerized web service and the React frontend as either a static bundle or an Nginx container.

---

### Option A: Render / Railway / Fly.io (Simplest Managed PaaS)

#### 1. Backend Deployment (Render or Railway)
- **Runtime:** Docker (`backend/Dockerfile`)
- **Instance Type:** Starter (512 MB RAM, 0.5 CPU is ample)
- **Environment Variables:**
  - `PORT=8000`
  - `DATABASE_PATH=backend/data/analytics.db`
  - `CORS_ORIGINS=https://your-frontend.pages.dev,https://your-custom-domain.com`
- **Health Check Path:** `/api/health`
- **Disk Persistence:** Attach a 1 GB persistent disk mounted to `/app/backend/data` (optional on Render if using the pre-seeded image, mandatory if writing new data in-cloud).

#### 2. Frontend Deployment (Cloudflare Pages or Vercel)
- **Build Command:** `npm run build`
- **Build Output Directory:** `dist`
- **Root Directory:** `frontend`
- **Environment Variables:**
  - `VITE_API_BASE_URL=https://your-backend-api.onrender.com/api`

---

### Option B: Single VM Stack (Docker Compose on AWS / DigitalOcean / Hetzner)

For procurement utilities desiring private cloud deployment within an internal VPC:

1. Provision an Ubuntu 24.04 VM ($4-6/month, 1 vCPU, 1 GB RAM).
2. Install Docker: `curl -fsSL https://get.docker.com | sh`
3. Clone repository and run:
   ```bash
   # Set production ports
   export FRONTEND_PORT=80
   export BACKEND_PORT=8000
   docker compose up -d --build
   ```
4. Configure DNS to point your domain to the server IP.
5. (Optional) Put Certbot / Let's Encrypt in front of Nginx for automated HTTPS termination.

---

## 5. Security & Operational Checklist

| Item | Status | Verification Method |
| :--- | :--- | :--- |
| **Non-root container user** | Configured | Python backend runs isolated inside standard slim container; Nginx runs under unprivileged worker processes |
| **No secrets embedded** | Verified | Images build from public packages; `.dockerignore` excludes `.env`, secrets, `.git`, `node_modules`, and `.venv` |
| **CORS restriction** | Verified | Backend restricts origins via `CORS_ORIGINS` environment variable |
| **Security Headers** | Active | Nginx transmits `X-Content-Type-Options: nosniff`, `X-Frame-Options: SAMEORIGIN`, `X-XSS-Protection: 1; mode=block` |
| **Asset compression** | Active | Nginx gzip compression enabled for JSON, CSS, and JS |
| **Health monitoring** | Active | Docker healthcheck monitors `urllib.request` on `:8000/api/health` every 15 seconds |
| **Resource foot-print** | Lightweight | Total memory consumption < 120 MB across both containers |

---

## 6. Manual Hosting Configuration Still Required Prior to Public Launch

1. **Domain & DNS:** Point your public domain (e.g. `gridbricks.energy.co.uk`) to the host or reverse proxy.
2. **TLS / SSL Certificates:** Terminate TLS using Let's Encrypt, Cloudflare Edge Certificates, or AWS ACM.
3. **CORS Origins:** Set `CORS_ORIGINS` on the backend to match the exact frontend production URL.
4. **Elexon Ingestion Automation (Optional):** If live month-to-date ingestion is desired in the future, configure a daily cron job running `python -m backend.app.services.ingestion_pipeline` (requires outgoing HTTPS to `https://data.elexon.co.uk`).
