# Gridbricks Wind Intelligence — Demonstration Video Script

**Target Duration:** 10:00 Maximum (Planned Runtime: ~9:30 to accommodate natural pauses)<br>
**Distribution:** Unlisted YouTube Video<br>
**Audience Structure:**
- **Part 1 (0:00 – 4:35):** Commercial Stakeholder / Energy Utility Procurement Desk (Customer Pitch & Live Portal Walkthrough)
- **Part 2 (4:35 – 9:30):** Engineering Lead / Technical Auditor (Architecture, Ingestion, Lookahead Prevention & Testing)

---

## 1. Pre-Recording Setup & Best Practices Checklist

To ensure a seamless, professional, single-take recording:

- [ ] **Warm Up the Render Backend:** Render's free tier spins down after 15 minutes of inactivity. Run `curl https://kjhwr-7m2q.onrender.com/api/health` 2 minutes prior to recording so the service responds instantly during the demo.
- [ ] **Browser Window Preparation:**
  - Open a clean **Incognito / Private Window** at standard `1920x1080` resolution.
  - Set browser zoom to `100%` (or `110%` for enhanced metric readability).
  - Hide bookmarks bar, extensions, and personal browser tabs.
  - **Tab 1:** [https://kjhwr-7m2q.vercel.app/](https://kjhwr-7m2q.vercel.app/) (Live Dashboard)
  - **Tab 2:** [https://kjhwr-7m2q.onrender.com/api/health](https://kjhwr-7m2q.onrender.com/api/health) (Live Health Endpoint)
  - **Tab 3:** [https://github.com/anurag-jaiswal-aj/kjhwr-7m2q](https://github.com/anurag-jaiswal-aj/kjhwr-7m2q) (Public GitHub Repository)
- [ ] **Terminal / IDE Setup:**
  - Open terminal at repository root with clean git status ready.
  - Pre-type or prepare command: `.venv/bin/python -m pytest backend/tests -v`
- [ ] **Audio & Environment:**
  - Test microphone audio levels to avoid clipping or echo.
  - Enable "Do Not Disturb" on your desktop to prevent popups or notification sounds.
- [ ] **Pacing Guideline:** Aim for a steady ~130–140 words per minute. Do not rush; speak with commercial clarity in Part 1 and structured engineering precision in Part 2.

---

## Part 1: Customer Pitch & Dashboard Walkthrough (0:00 – 4:35)

**Target Audience:** Energy Utility Day-Ahead Electricity Procurement Desk<br>
**Goal:** Demonstrate how the platform evaluates day-ahead wind generation forecasts against settlement actuals, provides operational visibility before auction order-book gate closure, and quantifies historical model bias.

---

### Segment 1.1: The Procurement Challenge & Executive Introduction (0:00 – 1:10)

- **On Screen:** Start at the top of the live dashboard at [https://kjhwr-7m2q.vercel.app/](https://kjhwr-7m2q.vercel.app/). Cursor hovers over the header title and the green **"Live API Connected • Healthy • Jan 1 - Jan 31"** badge.
- **Spoken Script:**
  > "Hello everyone. Welcome to this walkthrough of the Gridbricks Wind Intelligence platform, designed for an energy utility's day-ahead electricity procurement desk.
  >
  > In the Great Britain wholesale electricity market, day-ahead power procurement involves significant volume uncertainty. Wind generation now supplies a major portion of national demand, but procurement managers must commit to forward contracts and generation schedules before day-ahead auction order books close.
  >
  > To reflect this operational reality, our platform models an analytical decision cutoff at 11:00 UTC on the day prior to delivery—modeled after day-ahead auction submission timings like EPEX SPOT and Nord Pool. While this 11:00 UTC cutoff is an analytical modeling assumption rather than a statutory Elexon rule, it gives traders an objective snapshot of the information available at decision time.
  >
  > Gridbricks Wind Intelligence bridges this gap by evaluating Great Britain national wind generation outturn—directly from Elexon BMRS settlement data—against the official day-ahead forecasts published before that decision cutoff.
  >
  > It is important to note upfront: this platform specifically measures physical forecasting accuracy. It does not calculate financial losses, imbalance cashout penalties, or overall portfolio risk."
- **Key Facts to Mention:**
  - Great Britain wholesale power context: day-ahead procurement decisions locked in on Day D-1.
  - The D-1 11:00 UTC cutoff is an analytical modeling assumption modeled on wholesale auction conventions, not a statutory Elexon rule.
  - The green status badge confirms live SQLite connection and decoupled architecture.
- **What to Avoid Overstating:**
  - Do NOT claim the utility's private customer demand or retail portfolio is modeled here. The data evaluates national wind generation.
  - Do NOT claim that forecast errors directly prove financial cashout penalties, net energy shortfall, or portfolio imbalance costs.

---

### Segment 1.2: Core Accuracy KPIs & Bias Convention (1:10 – 2:25)

- **On Screen:** Scroll slightly down to frame the 5 Statistical KPI Cards prominently. Point the cursor at each card in sequence: MAE, RMSE, MBE, Observation Coverage, and Mean Outturn.
- **Spoken Script:**
  > "Let's examine our quantitative baseline across the complete month of January 2026.
  >
  > First, looking at our coverage card: we evaluate **all 1,488 half-hourly settlement periods** with **100% complete data coverage** and zero missing intervals.
  >
  > Across January, actual national wind generation averaged **11,581 megawatts**, while the baseline day-ahead forecast expected **13,421 megawatts**.
  >
  > We quantify forecast performance using three standard industry metrics:
  > - Our **Mean Absolute Error (MAE)** is **2,126 megawatts**, which represents an average miss of **18.4%** relative to mean actual outturn.
  > - Our **Root Mean Squared Error (RMSE)** is **2,621 megawatts**, which penalizes large forecasting excursions during severe winter wind ramps.
  > - And looking at the **Mean Bias Error (MBE)**: **+1,840 megawatts**.
  >
  > In accordance with standard energy forecasting convention, error is defined as **Forecast minus Actual**. A positive MBE of +1,840 megawatts indicates that day-ahead forecasts systematically over-estimated national wind generation across January 2026.
  >
  > While this provides clear historical insight into model over-prediction during this winter month, this metric is an empirical retrospective observation on national wind data, rather than a proven trading rule or automatic hedging formula."
- **Exact Verified Metrics to State:**
  - Mean Absolute Error (MAE): **2,126.12 MW** (Normalized MAE: **18.36%**)
  - Root Mean Squared Error (RMSE): **2,620.80 MW**
  - Mean Bias Error (MBE): **+1,840.30 MW** ($e_i = F_i - A_i$)
  - Coverage: **1,488 / 1,488 settlement periods (100.0%)**
  - Mean Actual Generation: **11,580.74 MW** vs. Mean Forecast: **13,421.03 MW**
- **What to Avoid Overstating:**
  - Do NOT describe the +1,840 MW bias as a validated trading haircut or financial adjustment rule.

---

### Segment 1.3: Visualizing Volatility & Error Distribution (2:25 – 3:25)

- **On Screen:** Scroll down to the dual-series **Time-Series Chart** (Sky Blue actual outturn vs. Amber day-ahead forecast) and then down to the **Forecast Error Distribution** bar chart. Hover over storm peaks and calm periods to show interactive tooltips.
- **Spoken Script:**
  > "Here in the time-series chart, the sky-blue line shows actual half-hourly generation outturn, while the dashed amber line shows the day-ahead forecast locked in before the D-1 11:00 UTC cutoff.
  >
  > Notice the significant temporal volatility: wind generation swings from calm periods under 2,000 megawatts up to storm peaks exceeding 17,000 megawatts.
  >
  > Immediately below, our Error Distribution chart visually maps every interval's error across the month. Amber bars indicate over-forecasting—where the forecast exceeded actual outturn—and indigo bars indicate under-forecasting.
  >
  > Notice our clear commercial disclaimer below this chart: while national wind was over-forecasted by an average of 1.84 gigawatts, **physical forecast error alone does not prove financial losses, a net energy shortfall, or portfolio imbalance costs**. Under Elexon BSC settlement arrangements, final imbalance cashout depends on half-hourly system prices and an organization's net portfolio balance across all its assets."
- **Key Facts to Emphasize:**
  - Dual-series line chart retains true 30-minute settlement period volatility without smoothing.
  - Reiterate clearly that physical error does not equal financial loss or net energy deficit.
- **What to Avoid Overstating:**
  - Do NOT claim that over-forecasting automatically cost the market money.

---

### Segment 1.4: Dynamic Controls & Daily Performance Breakdown (3:25 – 4:35)

- **On Screen:** Scroll back up to the **Filters Bar**. Click `W1 (1–7)` preset button to demonstrate dynamic filtering. Click **Hourly Aggregated (1h)** resolution toggle. Click **Reset Defaults**. Then scroll to the **Daily Reliability Breakdown** table.
- **Spoken Script:**
  > "The platform gives procurement analysts interactive exploration tools:
  > - We can filter down to specific weeks—for instance, clicking **Week 1 (Jan 1–7)** recalculates metrics to an MAE of 2,158 megawatts across 336 settlement periods.
  > - We can toggle between **Native Half-Hour Mode (30m)** and **Hourly Aggregated Mode (1h)**. In hourly mode, the two half-hours in each clock hour are averaged, yielding an MAE of 2,123 megawatts across 744 hours.
  > - We can also test sensitivity to different decision deadlines—from 09:00 UTC up to 16:00 UTC—to analyze how later forecast releases perform.
  >
  > Clicking **Reset Defaults** smoothly restores our full January baseline.
  >
  > Below the charts, our **Daily Reliability Breakdown** grades all 31 days with complete 48-out-of-48 interval coverage, allowing analysts to sort by daily MAE or bias to immediately identify outlier days."
- **Transition to Part 2:**
  > "Now, having reviewed the analytical interface, let's transition to Part 2 for our engineering lead to inspect the technical architecture, data pipeline, lookahead-free forecast selection, and test suite."

---

## Part 2: Technical Walkthrough for Engineering Lead (4:35 – 9:30)

**Target Audience:** Engineering Lead / Technical Evaluator<br>
**Goal:** Demonstrate clean software engineering architecture, robust data pipelines, zero-lookahead mathematical guarantees, automated testing, and reproducible containerization.

---

### Segment 2.1: System Architecture & Decoupled Topology (4:35 – 5:35)

- **On Screen:** Switch to browser Tab 2 ([https://kjhwr-7m2q.onrender.com/api/health](https://kjhwr-7m2q.onrender.com/api/health)) showing the live JSON response. Then switch briefly to VS Code showing `backend/app/main.py`.
- **Spoken Script:**
  > "For our technical lead, let's examine the system architecture.
  >
  > The platform uses a decoupled, production-grade cloud topology:
  > 1. **Frontend:** React 19 + TypeScript + Vite, served as static compiled assets via Vercel's global edge network at `kjhwr-7m2q.vercel.app`. It features a curated Vanilla CSS design system with HSL variables, avoiding heavy CSS framework dependencies.
  > 2. **Backend:** FastAPI REST service running with Python 3.11 and Uvicorn, containerized on Render at `kjhwr-7m2q.onrender.com`.
  > 3. **Persistence Layer:** Embedded SQLite database with Write-Ahead Logging (WAL mode) and composite indices on delivery timestamps and publication runs.
  > 4. **Decoupled Ingestion & Serving:** The REST API never queries external Elexon endpoints during user requests. Ingestion is executed out-of-band, caching clean, validated records in SQLite. User dashboard queries run against indexed local tables with fast, predictable response times."
- **Key Technical Details:**
  - Show live `/api/health` JSON: `{"status":"healthy","database":"connected","dataset_available":true}`.
  - Highlight WAL mode and composite indexing.
- **What to Avoid Overstating:**
  - Do NOT claim 'sub-millisecond' latency without qualification; emphasize decoupled architecture and local SQLite indexing.

---

### Segment 2.2: Data Ingestion & Deterministic Deduplication (5:35 – 6:35)

- **On Screen:** In VS Code, navigate to [`backend/app/services/elexon_client.py`](backend/app/services/elexon_client.py) and [`backend/app/services/ingestion.py`](backend/app/services/ingestion.py).
- **Spoken Script:**
  > "Let's inspect our data pipeline.
  >
  > In `elexon_client.py`, we implement a resilient HTTP streaming client for Elexon BMRS API v1. It features configurable timeouts, bounded exponential backoff on HTTP 429 rate limits and 5xx errors, and explicit typing.
  >
  > In `ingestion.py`, we ingest two distinct datasets:
  > - **Actual Outturn (`FUELHH`):** Filtered strictly for `fuelType = 'WIND'`. Deduplicated on composite key `(start_time, fuel_type)` where the latest publication timestamp wins. This yields exactly **1,488 unique valid half-hour intervals** covering every single settlement period of January 2026.
  > - **Wind Forecasts (`WINDFOR`):** Ingested from December 30, 2025 through January 31, 2026, capturing **19,272 unique valid forecast records** spanning **264 distinct publication runs**.
  >
  > All ingestion runs write audit records to an `ingestion_audit` SQLite table for full data provenance."
- **Key Facts to Emphasize:**
  - Exactly 1,488 actuals, 19,272 forecasts, 264 distinct publication vintages.
  - Deterministic deduplication with composite SQLite uniqueness constraints.

---

### Segment 2.3: Zero Lookahead & Forecast Vintage Selection (6:35 – 7:50)

- **On Screen:** In VS Code, open [`backend/app/services/forecast_selector.py`](backend/app/services/forecast_selector.py). Then switch to the dashboard's **Forecast Revision History (Evolution)** card for interval `2026-01-15 12:00 UTC`.
- **Spoken Script:**
  > "Now, let's examine the heart of our analytical engine: eliminating lookahead bias.
  >
  > In power market analytics, evaluating accuracy by inadvertently using forecasts published after auction gate closure is invalid—it inflates apparent accuracy using future weather runs.
  >
  > In `forecast_selector.py`, for any delivery interval on day $D$, our decision deadline is calculated as:
  > Day $(D - 1)$ at 11:00 UTC.
  > Again, this cutoff is an analytical assumption modeled on wholesale auction conventions rather than an official Elexon rule.
  >
  > We query candidate forecast vintages for that target hour sorted by `publish_time DESC`, and filter strictly for `publish_time <= decision_deadline`.
  >
  > Let's look at the concrete demonstration on screen for delivery hour **January 15, 2026 at 12:00 UTC**:
  > - 24 distinct vintages were published forecasting this exact hour from 2.5 days ahead down to real-time.
  > - Vintage #12 was published on **January 14 at 09:30 UTC** with value **11,178 megawatts**. This is selected as our **★ Day-Ahead Baseline** because it is the latest run published prior to the 11:00 UTC cutoff.
  > - The next run was published at **11:30 UTC** with **11,351 megawatts**. Because 11:30 is *after* the 11:00 deadline, our engine automatically flags it as **Post-Cutoff** and excludes it from the day-ahead baseline.
  > - Furthermore, earlier D-2 publications—such as the 11,888 megawatt run published January 13 at 04:30 UTC—are preserved in history but superseded by the later D-1 run.
  >
  > This provides complete lookahead-free mathematical guarantees."
- **Key Facts to Emphasize:**
  - Strict inequality: $\text{publish\_time} \le \text{decision\_deadline}$.
  - Concrete ground truth for Jan 15 12:00 UTC: 11,178 MW baseline selected, 11:30 UTC run (11,351 MW) excluded as post-cutoff, 11,888 MW D-2 run superseded.

---

### Segment 2.4: Resolution Preservation & Methodology Disclosure (7:50 – 8:35)

- **On Screen:** Switch back to the live dashboard and click the **Methodology & Assumptions** button in the header to open the modal.
- **Spoken Script:**
  > "Notice how our engine handles temporal resolution:
  > - Elexon actuals are native 30-minute settlement periods, while WINDFOR forecasts are hourly.
  > - Rather than discarding half of our settlement data or applying artificial interpolation, our native mode maps both Settlement Period 25 (:00) and Settlement Period 26 (:30) to the prevailing hourly forecast, preserving all 1,488 actual intervals.
  > - Missing values are strictly excluded from denominators and are never zero-filled.
  >
  > In our live Methodology modal on screen, all assumptions are disclosed:
  > - Section 2 explicitly classifies the D-1 11:00 UTC cutoff as an **analytical assumption** modeled on GB power auction conventions, not a statutory Elexon rule.
  > - Section 5 establishes our commercial boundary, reiterating that physical forecast error does not prove financial losses, net energy shortfalls, or portfolio imbalance costs."
- **Key Facts to Emphasize:**
  - Native half-hour preserves 100% of settlement actuals (1,488 SPs).
  - Explicit documentation of the analytical cutoff and commercial boundary.

---

### Segment 2.5: Automated Testing, Docker & Conclusion (8:35 – 9:30)

- **On Screen:** Switch to terminal. Run `.venv/bin/python -m pytest backend/tests -v`. Show all 34 passing tests. Then run `git status`.
- **Spoken Script:**
  > "Finally, let's verify code quality, test coverage, and deployment reproducibility.
  >
  > Here in our terminal, I'm running our automated test suite:
  > 34 unit and integration tests execute across the REST API, client retries, deduplication, resolution preservation, null handling, and zero-lookahead invariants.
  > All **34 tests pass cleanly in under 0.5 seconds**.
  >
  > For deployment:
  > - The backend uses a multi-stage `Dockerfile` with Python 3.11-slim, binding dynamically to `${PORT:-8000}` for Render.
  > - The frontend is built into static assets served via Vercel edge CDN, with an Nginx container configuration provided for local Docker Compose runs.
  > - For local reproduction, `docker compose up --build` spins up the entire stack with zero configuration.
  > - The live system is running in production with Vercel and Render at the URLs provided in our README.
  >
  > Thank you for reviewing the Gridbricks Wind Intelligence platform. The project is fully documented, tested, containerized, and deployed."
- **Closing Screen:** End on the clean working tree in terminal and the live dashboard in browser.

---

## 3. Final Submission Checklist

Once your recording is finished, execute these final verification steps:

1. **Upload Video to YouTube:**
   - Visibility: **Unlisted** (do NOT set to Private or Public).
   - Title: `Gridbricks Wind Intelligence - Technical & Customer Walkthrough (UK Wholesale Power)`
   - Description: Include the live URLs:
     - Dashboard: `https://kjhwr-7m2q.vercel.app/`
     - GitHub: `https://github.com/anurag-jaiswal-aj/kjhwr-7m2q`
2. **Update `README.md`:**
   - In [`README.md:L14`](file:///Users/anurag/Developer/gridbricks-challenge/README.md#L14), replace:
     ```markdown
     - **Unlisted YouTube Video Demonstration:** `[PENDING: Insert unlisted YouTube video URL prior to form submission, e.g., https://youtu.be/xxxxxxxxxxx]`
     ```
     with:
     ```markdown
     - **Unlisted YouTube Video Demonstration:** [https://youtu.be/YOUR_VIDEO_ID](https://youtu.be/YOUR_VIDEO_ID)
     ```
3. **Commit and Push:**
   ```bash
   cd ~/Developer/gridbricks-challenge
   git add README.md docs/VIDEO_DEMO_SCRIPT.md
   git commit -m "docs: attach unlisted YouTube demonstration URL and video script"
   git push origin main
   ```
4. **Incognito Public Verification:**
   - Open an **Incognito / Private browser tab**.
   - Paste and verify each of the 4 submission links:
     - [ ] Web Dashboard: `https://kjhwr-7m2q.vercel.app/`
     - [ ] Backend Health: `https://kjhwr-7m2q.onrender.com/api/health`
     - [ ] Public GitHub Repo: `https://github.com/anurag-jaiswal-aj/kjhwr-7m2q`
     - [ ] YouTube Video: `https://youtu.be/YOUR_VIDEO_ID` (plays without login)
5. **Submit the Challenge Google Form:**
   - Fill in your details and paste the verified links.
