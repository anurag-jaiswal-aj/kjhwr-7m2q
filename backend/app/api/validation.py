from datetime import datetime
from fastapi import HTTPException


def validate_date_str(date_str: str, param_name: str) -> str:
    """
    Validates that a string is a valid calendar date in YYYY-MM-DD format.
    Raises HTTP 400 on failure.
    """
    if not date_str or not isinstance(date_str, str):
        raise HTTPException(
            status_code=400,
            detail=f"Missing or invalid {param_name}. Expected format YYYY-MM-DD.",
        )
    try:
        dt = datetime.strptime(date_str.strip(), "%Y-%m-%d")
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid {param_name} format: '{date_str}'. Expected YYYY-MM-DD.",
        )


def validate_date_range(start_date: str, end_date: str) -> None:
    """
    Validates that start_date <= end_date.
    Raises HTTP 400 on failure.
    """
    if start_date > end_date:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid date range: start_date '{start_date}' must be before or equal to end_date '{end_date}'. start_date must be before or equal to end_date.",
        )


def validate_resolution(resolution: str) -> str:
    """
    Normalizes and validates resolution query parameter.
    Maps:
      - 'native_half_hour', 'half_hour', '30m' -> 'native_half_hour'
      - 'hourly_aggregated', 'hourly', '1h' -> 'hourly_aggregated'
    Raises HTTP 400 on failure.
    """
    cleaned = resolution.strip().lower()
    if cleaned in ("native_half_hour", "half_hour", "30m", "native"):
        return "native_half_hour"
    if cleaned in ("hourly_aggregated", "hourly", "1h", "aggregated"):
        return "hourly_aggregated"
    raise HTTPException(
        status_code=400,
        detail=f"Unsupported resolution: '{resolution}'. Supported values are 'native_half_hour' (or 'half_hour') and 'hourly_aggregated' (or 'hourly').",
    )


def validate_cutoff_time(cutoff_time: str) -> str:
    """
    Validates that cutoff_time is a valid 24-hour time string (HH:MM or HH:MM:SS).
    Raises HTTP 400 on failure.
    """
    cleaned = cutoff_time.strip()
    parts = cleaned.split(":")
    if len(parts) not in (2, 3):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid cutoff_time format: '{cutoff_time}'. Expected HH:MM in 24-hour UTC format (e.g. '11:00').",
        )
    try:
        hour = int(parts[0])
        minute = int(parts[1])
        second = int(parts[2]) if len(parts) == 3 else 0
        if not (0 <= hour <= 23 and 0 <= minute <= 59 and 0 <= second <= 59):
            raise ValueError()
        return f"{hour:02d}:{minute:02d}"
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid cutoff_time values in '{cutoff_time}'. Hours must be 0-23 and minutes 0-59.",
        )


def validate_iso_timestamp(timestamp_str: str, param_name: str = "start_time") -> str:
    """
    Validates that a string is a valid ISO 8601 timestamp.
    Raises HTTP 400 on failure.
    """
    if not timestamp_str or not isinstance(timestamp_str, str):
        raise HTTPException(
            status_code=400,
            detail=f"Missing or invalid {param_name}. Expected ISO 8601 UTC timestamp.",
        )
    try:
        # Standardize UTC indicator
        cleaned = timestamp_str.strip().replace("Z", "+00:00")
        dt = datetime.fromisoformat(cleaned)
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid {param_name} format: '{timestamp_str}'. Expected valid ISO 8601 timestamp (e.g. '2026-01-15T12:00:00Z').",
        )
