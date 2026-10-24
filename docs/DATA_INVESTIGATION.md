# Stage 1: Data Investigation & Technical Feasibility Report
## UK Wind Generation Outturn vs. Day-Ahead Forecasts (January 2026)

**Project:** Gridbricks Full Stack Engineer Challenge — UK Wholesale Electricity Market Analytics  
**Role:** Senior Data Engineer  
**Status:** Revised Post-Review (Rigorous Classification: Verified Facts, Assumptions, Proposals, Unresolved Questions)  
**Date of Investigation:** October 2026  
**Target Delivery Period:** January 1, 2026 00:00 UTC – January 31, 2026 23:59 UTC  

---

## 1. Executive Summary

An energy utility's power procurement desk in Great Britain (GB) purchases electricity in the day-ahead wholesale market to serve consumer demand. Because wind output is intermittent and weather-dependent, procurement teams must forecast renewable generation one day ahead to determine how much dispatchable power (e.g. from thermal generation or interconnectors) must be procured.

This investigation evaluates the official Elexon BMRS data feeds, examines live API access, establishes rigorous data hygiene and forecast-selection rules, and designs an evidence-based implementation plan for **January 2026**.

### 1.1 Findings & Design Classifications at a Glance

Each statement in this report is strictly classified under one of four categories:
* **[Verified Fact]**: Empirically proven via live API testing or official documentation.
* **[Assumption]**: A domain-informed premise or configurable operational default.
* **[Proposed Design Decision]**: An engineering or analytical design choice recommended for the application.
* **[Unresolved Question]**: A domain question or trade-off requiring client alignment.

| Dimension | Classification | Finding / Design Decision |
| :--- | :---: | :--- |
| **Actuals Endpoint** | **[Verified Fact]** | `GET /datasets/FUELHH/stream?fuelType=WIND` provides half-hourly generation outturn in average Megawatts (MW). |
| **Forecast Endpoint** | **[Verified Fact]** | `GET /datasets/WINDFOR/stream` provides **historical forecast publication vintages** (8 publication runs/day, ~73 hourly points per run) in MW. |
| **Historical Vintages** | **[Verified Fact]** | Verified that historical forecast revisions are fully accessible and not overwritten by subsequent updates. Additionally, `/forecast/generation/wind/evolution` was verified to return all 24 historical revisions for any target delivery interval. |
| **Temporal Resolution** | **[Verified Fact]** | **FUELHH is 30-minute resolution** (`:00` and `:30`). **WINDFOR is 60-minute resolution** (`:00` strictly). |
| **Resolution Preservation** | **[Proposed Design Decision]** | **Preserve all 1,488 half-hourly actual records.** Each 30-minute actual interval maps to the prevailing day-ahead forecast for that hour block. Zero half-hourly records are discarded. |
| **Decision Cutoff** | **[Assumption]** | **11:00 UTC on D-1** is an analytical assumption modeled on GB Day-Ahead power exchange auction conventions (EPEX SPOT / Nord Pool). Elexon itself publishes no procurement decision cutoff. The cutoff is strictly configurable in the analytical engine and UI. |
| **Forecast Selection** | **[Proposed Design Decision]** | Select the latest forecast where `publishTime <= decision_deadline` for each delivery interval. Strictly forbids future information (zero lookahead bias). |
| **Data Hygiene & Nulls** | **[Proposed Design Decision]** | Missing or unforecasted intervals remain `null` and are **never converted to zero**. Record accounting explicitly distinguishes retrieved, valid, unique, and matched records. |
| **January 2026 Accuracy** | **[Verified Fact]** | For January 2026 (preserving all 1,488 half-hour intervals at D-1 11:00 UTC cutoff): <br> • Mean Actual: 11,581.11 MW <br> • Mean Forecast: 13,421.41 MW <br> • MAE: **2,126.12 MW** (18.36%) <br> • RMSE: **2,620.80 MW** (22.63%) <br> • Mean Bias Error (MBE): **+1,840.30 MW** (systematic over-forecasting). |

---

## 2. Official Sources and Endpoint URLs

### 2.1 Official Portal & Specifications
* **[Verified Fact] Official Documentation Links:**
  * Actual Generation (`FUELHH`): [https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/FUELHH/stream](https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/FUELHH/stream)
  * Forecast Generation (`WINDFOR`): [https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/WINDFOR/stream](https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/WINDFOR/stream)
* **[Verified Fact] OpenAPI / Swagger Spec:**
  * `https://data.elexon.co.uk/swagger/v1/swagger.json` (Insights API v1.0, OpenAPI 3.0).

### 2.2 Endpoint Evaluation & Comparison

We inspected all relevant endpoints in the official OpenAPI specification:

| Endpoint | Method | Supported Query Parameters | Payload Structure | Recommended Use |
| :--- | :---: | :--- | :--- | :--- |
| `/datasets/FUELHH/stream` | GET | `settlementDateFrom`, `settlementDateTo`, `settlementPeriod`, `fuelType`, `publishDateTimeFrom`, `publishDateTimeTo` | Chunked JSON array `[...]` | **Primary Actuals Feed** (Efficient, unnested, direct stream). |
| `/datasets/FUELHH` | GET | Same as stream + `format=json\|xml` | Paginated wrapper `{"data": [...]}` | Alternative (extra wrapper overhead). |
| `/datasets/WINDFOR/stream` | GET | `publishDateTimeFrom`, `publishDateTimeTo` | Chunked JSON array `[...]` | **Primary Forecast Feed** (Retrieves all historical publication batches). |
| `/datasets/WINDFOR` | GET | `publishDateTimeFrom`, `publishDateTimeTo`, `format` | Paginated wrapper `{"data": [...]}` | Alternative (extra wrapper overhead). |
| `/forecast/generation/wind/latest` | GET | `from`, `to`, `format` | Wrapper `{"data": [...]}` | **Not suitable for day-ahead reconstruction** (returns only the latest single forecast snapshot). |
| `/forecast/generation/wind/evolution` | GET | `startTime`, `format` | Wrapper `{"data": [...]}` | **Verified Secondary Tool** (Retrieves all historical forecast revisions for a specific delivery hour). |
| `/forecast/generation/wind/history` | GET | `publishTime`, `format` | Wrapper `{"data": [...]}` | Retrieves the complete forecast batch released at a specific publication timestamp. |

* **[Proposed Design Decision]:** Use `GET /datasets/FUELHH/stream` and `GET /datasets/WINDFOR/stream` for bulk analytical ingestion. Use `GET /forecast/generation/wind/evolution` on-demand in the UI for interactive inspection of specific delivery hours.

---

## 3. Actual API Requests Attempted and Observed Results

All API requests documented below were executed directly against `https://data.elexon.co.uk/bmrs/api/v1` in October 2026. No synthetic data, mock servers, or fabricated responses were used.

### 3.1 Test 1: Actual Wind Generation (`FUELHH/stream`)
**Reproducible Command:**
```bash
curl -s -D - "https://data.elexon.co.uk/bmrs/api/v1/datasets/FUELHH/stream?settlementDateFrom=2026-01-01&settlementDateTo=2026-01-31&fuelType=WIND" -o fuelhh_jan2026.json
```
**Observed Response:**
* **HTTP Status:** `200 OK`
* **Content-Type:** `application/json; charset=utf-8`
* **Transfer-Encoding:** `chunked`
* **Authentication:** None required (public open-access API).
* **Rate Limits:** No `X-RateLimit-*` headers returned.
* **Record Accounting:**
  * **Retrieved Records:** 1,488
  * **Valid Records:** 1,488 (All records have valid ISO timestamps, `fuelType == "WIND"`, and non-negative numeric `generation`).
  * **Unique Records:** 1,488 (Evaluated by primary key `(startTime, fuelType)`; 0 duplicates found).
* **Sample Record (JSON):**
```json
{
  "dataset": "FUELHH",
  "publishTime": "2026-01-01T00:30:00Z",
  "startTime": "2026-01-01T00:00:00Z",
  "settlementDate": "2026-01-01",
  "settlementPeriod": 1,
  "fuelType": "WIND",
  "generation": 13756
}
```

### 3.2 Test 2: Forecast Generation (`WINDFOR/stream`) for January 2026 Publications
**Reproducible Command:**
```bash
curl -s -D - "https://data.elexon.co.uk/bmrs/api/v1/datasets/WINDFOR/stream?publishDateTimeFrom=2026-01-01T00:00:00Z&publishDateTimeTo=2026-01-31T23:59:59Z" -o windfor_jan2026.json
```
**Observed Response:**
* **HTTP Status:** `200 OK`
* **Record Accounting:**
  * **Retrieved Records:** 18,104
  * **Valid Records:** 18,104
  * **Unique Records:** 18,104 (Evaluated by composite key `(publishTime, startTime)`; 0 duplicates found).
* **Unique Publication Vintages:** 248 distinct `publishTime` timestamps (exactly 8 publications per day for 31 days).
* **Batch Consistency:** Every publication vintage contains exactly 73 records.
* **Sample Record (JSON):**
```json
{
  "dataset": "WINDFOR",
  "publishTime": "2026-01-01T02:30:00Z",
  "startTime": "2026-01-01T00:00:00Z",
  "generation": 19960
}
```

### 3.3 Test 3: Historical Publications Required for Early January Delivery
To evaluate day-ahead decisions for January 1 and 2, 2026, purchasing decisions were made on December 30 and 31, 2025.
**Reproducible Command:**
```bash
curl -s "https://data.elexon.co.uk/bmrs/api/v1/datasets/WINDFOR/stream?publishDateTimeFrom=2025-12-30T00:00:00Z&publishDateTimeTo=2025-12-31T23:59:59Z" -o windfor_dec2025.json
```
**Observed Response:**
* **Retrieved Records:** 1,168 records across 16 publication batches.
* **Relevant Records for January 2026:** 368 forecast records explicitly target delivery intervals starting on or after `2026-01-01T00:00:00Z`.
* **Total Combined WINDFOR Pool (Dec 30, 2025 – Jan 31, 2026):**
  * **Retrieved Records:** 19,272
  * **Valid Records:** 19,272
  * **Unique Records:** 19,272

### 3.4 Test 4: Forecast Evolution Verification
**Reproducible Command:**
```bash
curl -s "https://data.elexon.co.uk/bmrs/api/v1/forecast/generation/wind/evolution?startTime=2026-01-15T12:00:00Z&format=json"
```
**Observed Response:**
* **HTTP Status:** `200 OK`
* **Revisions Returned:** Exactly 24 chronological revisions forecasting delivery at `2026-01-15T12:00:00Z`.
* **Chronological Span:** First forecast released at `2026-01-13T02:30:00Z` (11,938 MW) evolving down to `2026-01-15T22:30:00Z` (10,229 MW).
* **[Verified Fact]:** Confirms that Elexon maintains a complete, granular audit trail of forecast evolution.

---

## 4. Dataset Fields, Units, Timestamps, and Timezones

### 4.1 Field Semantics and Units
* **[Verified Fact] Generation Units:** Integer Megawatts (MW).
  * `FUELHH`: Average MW generation over the 30-minute settlement period for fuel type `WIND`.
  * `WINDFOR`: Expected MW generation at the specified target `startTime`.
* **[Verified Fact] Timestamp Formatting:** ISO 8601 strings ending in `Z` (e.g., `2026-01-01T00:00:00Z`), indicating UTC.

### 4.2 Timezones: UK Local Time vs. UTC
* **[Verified Fact] January Local Time:** In January, Great Britain observes Greenwich Mean Time (GMT = UTC+0). Local clock time and UTC are identical during the target delivery period.
* **[Verified Fact] Publication Schedule Behavior:** In January, publications occur at `02:30`, `04:30`, `07:30`, `09:30`, `11:30`, `15:30`, `18:30`, and `22:30` UTC. During British Summer Time (BST = UTC+1, tested in July), UTC publish times shift to `03:30`, `05:30`, etc.
* **[Proposed Design Decision]:** The application backend will store, query, and calculate all timestamps strictly in UTC. Conversions to `Europe/London` will occur exclusively at the presentation layer.

### 4.3 Native Temporal Resolution
* **[Verified Fact] FUELHH Actuals:** Half-hourly cadence (30 minutes). Exactly 48 settlement periods per complete day (`:00` and `:30`).
* **[Verified Fact] WINDFOR Forecasts:** Hourly cadence (60 minutes). Stamped exclusively at `:00` minutes.
* **[Proposed Design Decision]:** Section 6 defines how native 30-minute actuals are preserved in full without discarding data or unjustified aggregation.

---

## 5. Decision-Deadline Methodology

### 5.1 Regulatory Status of Decision Cutoffs
* **[Verified Fact]:** Elexon BMRS does **NOT** document, mandate, or publish an official "day-ahead procurement decision cutoff." Elexon operates the Balancing and Settlement Code (BSC), under which Gate Closure is 1 hour before each half-hour settlement period (an intraday operational deadline, not a day-ahead procurement deadline).
* **[Assumption]:** Day-ahead wholesale procurement occurs on commercial power exchanges (such as EPEX SPOT and Nord Pool). In Great Britain, order books for the primary day-ahead auction close at **11:00 UK local time (GMT)** on Day $D-1$. Other desks participate in the 15:30 half-hourly auction or finalize positions at end-of-day (17:00 / 23:00).
* **[Proposed Design Decision]:** The decision cutoff is **strictly an analytical assumption** and must be fully configurable. We establish **11:00 UTC on D-1** as the baseline analytical default, accompanied by quick presets (11:00, 15:30, 23:00) and a custom cutoff selector in the application UI.

### 5.2 Deterministic Forecast-Selection Algorithm

For any delivery interval starting at $T$ on delivery day $D$:
1. **Decision Deadline Calculation:**
   $$D_{\text{deadline}} = (D - 1\text{ day}) \text{ at } \text{decision\_cutoff\_time (UTC)}$$
   *(Example: For delivery on 2026-01-15, $D_{\text{deadline}} = \text{2026-01-14T11:00:00Z}$).*
2. **Target Hour Resolution:**
   Because WINDFOR forecasts are hourly, identify the parent hour $H = \text{floor\_to\_hour}(T)$ (e.g., for both 12:00:00Z and 12:30:00Z, $H = \text{12:00:00Z}$).
3. **Eligible Forecast Pool:**
   $$\mathcal{F}(H) = \{ f \in \text{WINDFOR} \mid f.\text{startTime} = H \text{ and } f.\text{publishTime} \le D_{\text{deadline}} \}$$
4. **Deterministic Selection:**
   $$F_T = \arg\max_{f \in \mathcal{F}(H)} (f.\text{publishTime})$$
   Select the forecast with the latest `publishTime` on or before the deadline.
5. **No Lookahead Guarantee:** Because every candidate satisfies $f.\text{publishTime} \le D_{\text{deadline}}$, no information published after the decision deadline can influence the selected forecast.
6. **Missing Forecast Policy:** If $\mathcal{F}(H) = \emptyset$, $F_T = \text{null}$. The interval is flagged as unforecasted and excluded from paired error metrics. **It is never set to zero.**

---

## 6. Half-Hourly Resolution Preservation & Alignment

### 6.1 Assignment Requirement
The assignment brief explicitly defines:
* Actual generation `startTime`: "the target time (resolution of 30 minutes)"
* The user guidance instructs:
  > *"Preserve the datasets' verified native temporal resolution. The assignment specifies 30-minute actual generation intervals. Do not discard half-hourly records by matching only hourly timestamps. Do not aggregate to hourly values unless the API investigation demonstrates that this is necessary and the aggregation is mathematically justified."*

### 6.2 Primary Alignment: Preserving All 30-Minute Actuals
* **[Proposed Design Decision]:** Retain all **1,488 half-hourly actual records** for January 2026.
* **Mechanism:** An hourly wind generation forecast represents expected average generation capacity across that 60-minute clock hour. That 60-minute delivery block comprises two consecutive half-hour settlement periods (e.g. 12:00–12:30 [SP 25] and 12:30–13:00 [SP 26]).
* Therefore, each half-hour settlement interval $T$ is evaluated against the day-ahead forecast established for its parent hour $H = \text{floor\_to\_hour}(T)$.
* **Record Count Impact:** Exactly **1,488 matched intervals** (100.0% coverage of all half-hour actual intervals in January 2026). Zero actuals are discarded.

### 6.3 Comparison of Alignment Methodologies on January 2026 Data

To evaluate the mathematical impact of different alignment choices, we executed reproducible calculations across the January 2026 dataset (using the D-1 11:00 UTC cutoff):

| Alignment Strategy | Description | Matched Intervals | Actuals Preserved | MAE (MW) | RMSE (MW) | MBE (MW) | Classification |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Primary: Native 30-Min Resolution** | Evaluates all 48 SPs/day against prevailing hourly forecast | **1,488 / 1,488** | **100.0% (1,488/1,488)** | **2,126.12** | **2,620.80** | **+1,840.30** | **[Proposed Design Decision]** (Preserves native granularity) |
| **Secondary: Hourly Aggregated Actuals** | Averages two 30-min actuals ($\frac{A_{:00} + A_{:30}}{2}$) vs hourly forecast | 744 / 744 | Aggregated to 744 blocks | 2,122.81 | 2,616.69 | +1,840.30 | **[Proposed Design Decision]** (Optional UI comparison mode) |
| **Discarding `:30` Actuals (Subsampling)** | Matches only exact `:00` timestamps; drops all `:30` actuals | 744 / 744 | 50.0% (744/1,488 discarded) | 2,107.18 | 2,611.24 | +1,839.92 | **Rejected as Primary** (Violates requirement to preserve 30-min data) |

* **[Verified Fact]:** Discarding `:30` records artificially reduced the sample size by 50% and produced an MAE of 2,107.18 MW. Preserving all native 30-minute intervals produces an MAE of 2,126.12 MW on the full 1,488-record dataset.

---

## 7. Data Quality and Hygiene Rules

### 7.1 Record Accounting Framework
To ensure complete transparency in data processing, the pipeline tracks four distinct record states:
1. **Retrieved Records:** Raw count received in API response payloads.
2. **Valid Records:** Records passing schema validation (valid ISO timestamps, correct fuel type, numeric generation $\ge 0$).
3. **Unique Records:** Records remaining after deterministic deduplication.
4. **Matched Records:** Paired actual-forecast records available for metric computation.

### 7.2 Deterministic Deduplication Rules
* **[Proposed Design Decision] FUELHH Deduplication:** Primary Key = `(startTime, fuelType)`. If duplicate records are encountered, retain the record with the latest `publishTime`. If `publishTime` is identical, retain the record with the largest `generation` value.
* **[Proposed Design Decision] WINDFOR Deduplication:** Primary Key = `(publishTime, startTime)`. If duplicate rows occur within a publication batch, retain the first received record.

### 7.3 Invalid and Missing Data Handling
* **[Proposed Design Decision] Missing Values:** If an interval lacks an actual observation or has no eligible forecast published before the cutoff:
  * Field value is set to `null`.
  * **Strict Prohibition:** Missing values must **NEVER be converted to zero**. Converting missing observations to zero introduces artificial errors of 10,000+ MW and completely corrupts MAE/RMSE.
  * The interval is excluded from paired error metrics and tallied in `unmatched_intervals`.
* **[Proposed Design Decision] Invalid Values:** If `generation < 0` or non-numeric, flag as `INVALID_NUMERIC` and treat as missing.

---

## 8. Metric Definitions

Let $\mathcal{T}$ be the set of $N$ valid matched delivery intervals in the evaluation period. For interval $i \in \mathcal{T}$, let $A_i$ be actual generation (MW) and $F_i$ be the day-ahead forecast (MW).

### 8.1 Error Direction Convention
* **[Proposed Design Decision]:**
  $$\text{Error } e_i = F_i - A_i$$
  * **$e_i > 0$ (Positive Error / Over-forecast):** Forecasted national wind generation exceeded actual outturn (optimistic forecast).
  * **$e_i < 0$ (Negative Error / Under-forecast):** Forecasted national wind generation was below actual outturn (conservative forecast).
  * **Interpretation Boundary [Important Limitation]:** This application evaluates the accuracy and bias of the national wind generation forecast against actual outturn. Because our dataset is restricted to national wind generation alone and does not include consumer demand forecasts, other fuel generation, wholesale market prices, or the utility's commercial hedging portfolio, an observed forecast error does not prove that the utility would have been under-procured or experienced a financial loss. It quantifies meteorological forecast bias to help the team account for forecast uncertainty when planning day-ahead power purchases.

### 8.2 Formulation of Statistical Metrics
1. **Mean Absolute Error (MAE) [MW]:**
   $$\text{MAE} = \frac{1}{N} \sum_{i=1}^{N} |F_i - A_i|$$
2. **Root Mean Squared Error (RMSE) [MW]:**
   $$\text{RMSE} = \sqrt{\frac{1}{N} \sum_{i=1}^{N} (F_i - A_i)^2}$$
3. **Mean Bias Error (MBE) [MW]:**
   $$\text{MBE} = \frac{1}{N} \sum_{i=1}^{N} (F_i - A_i)$$
4. **Normalized MAE (nMAE) [%]:**
   $$\text{nMAE} = \frac{\text{MAE}}{\bar{A}} \times 100\%, \quad \text{where } \bar{A} = \frac{1}{N} \sum_{i=1}^N A_i$$
5. **Coverage Rate [%]:**
   $$\text{Coverage Rate} = \frac{N_{\text{matched}}}{N_{\text{expected}}} \times 100\%$$

---

## 9. Comprehensive Classification Matrix

| Item / Finding | Classification | Evidence / Basis |
| :--- | :---: | :--- |
| FUELHH stream provides actual generation in MW | **[Verified Fact]** | Verified via live API request; schema confirms integer MW average. |
| WINDFOR stream provides historical forecast vintages | **[Verified Fact]** | Verified via live API request; 248 vintages retrieved for Jan 2026. |
| `/forecast/generation/wind/evolution` returns 24 revisions/hour | **[Verified Fact]** | Verified via live API request for `2026-01-15T12:00:00Z`. |
| FUELHH is 30-min; WINDFOR is 60-min | **[Verified Fact]** | Verified across all 1,488 FUELHH and 18,104 WINDFOR records. |
| Timestamps are UTC (`Z`) | **[Verified Fact]** | Verified across all API response payloads. |
| Elexon documents no day-ahead procurement cutoff | **[Verified Fact]** | Verified in Elexon BSC rules; BSC Gate Closure is 1 hour before SP. |
| GB Day-Ahead auction closes at 11:00 UK local time | **[Assumption]** | Standard commercial market practice on EPEX SPOT and Nord Pool. |
| 11:00 UTC on D-1 as baseline analytical cutoff | **[Assumption]** | Configurable analytical default; allows early-morning procurement evaluation. |
| Error direction defined as $F - A$ | **[Proposed Design Decision]** | Standard analytical forecasting convention; positive = over-forecast. |
| Preserving all 1,488 half-hour actual intervals | **[Proposed Design Decision]** | Directly fulfills assignment requirement to preserve 30-min data. |
| Missing data must never be zero-filled | **[Proposed Design Decision]** | Prevents massive metric distortion; preserves statistical integrity. |
| SQLite local caching in FastAPI backend | **[Proposed Design Decision]** | Eliminates redundant external network calls; ensures fast local UI. |
| What specific trading desk cutoff does client use? | **[Unresolved Question]** | Solved by making cutoff fully interactive (11:00, 15:30, 23:00, custom). |

---

## 10. Reproducible Verification Script

To allow any engineer or reviewer to independently verify all numbers in this report without external dependencies, run:

```bash
python3 -c '
import urllib.request, json
from datetime import datetime, timedelta
import math

# 1. Fetch FUELHH Actuals (30-min resolution)
url_fuel = "https://data.elexon.co.uk/bmrs/api/v1/datasets/FUELHH/stream?settlementDateFrom=2026-01-01&settlementDateTo=2026-01-31&fuelType=WIND"
actuals_raw = json.loads(urllib.request.urlopen(url_fuel).read().decode())
print(f"Retrieved FUELHH records: {len(actuals_raw)}")

# 2. Fetch WINDFOR Forecasts (Dec 30 2025 to Jan 31 2026)
url_wind = "https://data.elexon.co.uk/bmrs/api/v1/datasets/WINDFOR/stream?publishDateTimeFrom=2025-12-30T00:00:00Z&publishDateTimeTo=2026-01-31T23:59:59Z"
wind_raw = json.loads(urllib.request.urlopen(url_wind).read().decode())
print(f"Retrieved WINDFOR records: {len(wind_raw)}")

# 3. Evaluate Preserving All 30-min Actuals at D-1 11:00 UTC Cutoff
matched = []
for r in actuals_raw:
    t_dt = datetime.fromisoformat(r["startTime"].replace("Z", "+00:00"))
    deliv_date = t_dt.strftime("%Y-%m-%d")
    deliv_dt = datetime.strptime(deliv_date, "%Y-%m-%d")
    deadline = (deliv_dt - timedelta(days=1)).strftime("%Y-%m-%dT11:00:00Z")
    hour_start = t_dt.strftime("%Y-%m-%dT%H:00:00Z")
    cands = [w for w in wind_raw if w["startTime"] == hour_start and w["publishTime"] <= deadline]
    if not cands: continue
    sel = max(cands, key=lambda x: x["publishTime"])
    matched.append(sel["generation"] - r["generation"])

print(f"Matched half-hourly intervals: {len(matched)} / {len(actuals_raw)}")
mae = sum(abs(e) for e in matched) / len(matched)
rmse = math.sqrt(sum(e**2 for e in matched) / len(matched))
mbe = sum(matched) / len(matched)
print(f"Native 30-Minute Results (D-1 11:00 Cutoff):")
print(f"  MAE:  {mae:.2f} MW")
print(f"  RMSE: {rmse:.2f} MW")
print(f"  MBE:  {mbe:.2f} MW")
'
```
