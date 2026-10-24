from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_DB_PATH = os.environ.get("DATABASE_PATH", str(DATA_DIR / "analytics.db"))

ELEXON_BASE_URL = os.environ.get("ELEXON_BASE_URL", "https://data.elexon.co.uk/bmrs/api/v1")
ELEXON_TIMEOUT_SECONDS = float(os.environ.get("ELEXON_TIMEOUT_SECONDS", "30.0"))
ELEXON_MAX_RETRIES = int(os.environ.get("ELEXON_MAX_RETRIES", "3"))
ELEXON_BACKOFF_FACTOR = float(os.environ.get("ELEXON_BACKOFF_FACTOR", "1.0"))

DEFAULT_DECISION_CUTOFF_TIME = "11:00"
DELIVERY_MONTH_START = "2026-01-01"
DELIVERY_MONTH_END = "2026-01-31"

# We fetch WINDFOR starting from Dec 30 2025 to reconstruct day-ahead decisions for Jan 1 2026
FORECAST_FETCH_START = "2025-12-30T00:00:00Z"
FORECAST_FETCH_END = "2026-01-31T23:59:59Z"

# CORS configuration for frontend integration
CORS_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        "CORS_ORIGINS",
        "http://localhost:3000,http://localhost:3001,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:3001,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]

