import time
import logging
from typing import Any, Dict, List, Optional
import httpx

from backend.app.config import (
    ELEXON_BASE_URL,
    ELEXON_TIMEOUT_SECONDS,
    ELEXON_MAX_RETRIES,
    ELEXON_BACKOFF_FACTOR,
)

logger = logging.getLogger(__name__)


class ElexonClientError(Exception):
    """Base exception for Elexon client errors."""
    pass


class ElexonTimeoutError(ElexonClientError):
    """Raised when an API request times out."""
    pass


class ElexonRateLimitError(ElexonClientError):
    """Raised when receiving HTTP 429 Too Many Requests."""
    pass


class ElexonAPIError(ElexonClientError):
    """Raised when receiving HTTP 4xx or 5xx error responses."""
    def __init__(self, status_code: int, message: str, url: str):
        self.status_code = status_code
        self.message = message
        self.url = url
        super().__init__(f"Elexon API error {status_code} at {url}: {message}")


class ElexonClient:
    """
    Robust HTTP client for Elexon BMRS API endpoints with configurable timeouts,
    bounded exponential backoff retries, and comprehensive error handling.
    """

    def __init__(
        self,
        base_url: str = ELEXON_BASE_URL,
        timeout: float = ELEXON_TIMEOUT_SECONDS,
        max_retries: int = ELEXON_MAX_RETRIES,
        backoff_factor: float = ELEXON_BACKOFF_FACTOR,
        client: Optional[httpx.Client] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self._client = client or httpx.Client(timeout=httpx.Timeout(timeout))

    def close(self) -> None:
        if self._client:
            self._client.close()

    def __enter__(self) -> "ElexonClient":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def _request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Any:
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        retries = 0
        last_exception = None

        while retries <= self.max_retries:
            try:
                logger.debug("Requesting %s with params %s (attempt %d/%d)", url, params, retries + 1, self.max_retries + 1)
                response = self._client.get(url, params=params)
                
                # Check HTTP 429
                if response.status_code == 429:
                    if retries < self.max_retries:
                        sleep_time = self.backoff_factor * (2 ** retries)
                        logger.warning("HTTP 429 rate limit at %s. Retrying in %.1fs...", url, sleep_time)
                        time.sleep(sleep_time)
                        retries += 1
                        continue
                    raise ElexonRateLimitError(f"HTTP 429 Too Many Requests at {url} after {retries} retries")

                # Check 5xx server errors
                if 500 <= response.status_code < 600:
                    if retries < self.max_retries:
                        sleep_time = self.backoff_factor * (2 ** retries)
                        logger.warning("Server error %d at %s. Retrying in %.1fs...", response.status_code, url, sleep_time)
                        time.sleep(sleep_time)
                        retries += 1
                        continue
                    raise ElexonAPIError(response.status_code, response.text, url)

                # Check 4xx client errors (non-retryable)
                if 400 <= response.status_code < 500:
                    raise ElexonAPIError(response.status_code, response.text, url)

                response.raise_for_status()
                return response.json()

            except httpx.TimeoutException as e:
                last_exception = e
                if retries < self.max_retries:
                    sleep_time = self.backoff_factor * (2 ** retries)
                    logger.warning("Timeout requesting %s: %s. Retrying in %.1fs...", url, e, sleep_time)
                    time.sleep(sleep_time)
                    retries += 1
                    continue
                raise ElexonTimeoutError(f"Request to {url} timed out after {self.max_retries} retries: {e}") from e

            except httpx.NetworkError as e:
                last_exception = e
                if retries < self.max_retries:
                    sleep_time = self.backoff_factor * (2 ** retries)
                    logger.warning("Network error requesting %s: %s. Retrying in %.1fs...", url, e, sleep_time)
                    time.sleep(sleep_time)
                    retries += 1
                    continue
                raise ElexonClientError(f"Network error requesting {url}: {e}") from e

        raise ElexonClientError(f"Failed to fetch {url} after {self.max_retries} retries: {last_exception}")

    def fetch_actuals_stream(
        self,
        settlement_date_from: str,
        settlement_date_to: str,
        fuel_type: str = "WIND",
    ) -> List[Dict[str, Any]]:
        """
        Retrieves half-hourly generation outturn from FUELHH/stream.
        """
        params = {
            "settlementDateFrom": settlement_date_from,
            "settlementDateTo": settlement_date_to,
            "fuelType": fuel_type,
        }
        data = self._request("datasets/FUELHH/stream", params=params)
        if not isinstance(data, list):
            raise ElexonAPIError(500, f"Expected JSON list from FUELHH stream, got {type(data)}", "datasets/FUELHH/stream")
        return data

    def fetch_forecasts_stream(
        self,
        publish_date_time_from: str,
        publish_date_time_to: str,
    ) -> List[Dict[str, Any]]:
        """
        Retrieves historical wind forecast publications from WINDFOR/stream.
        """
        params = {
            "publishDateTimeFrom": publish_date_time_from,
            "publishDateTimeTo": publish_date_time_to,
        }
        data = self._request("datasets/WINDFOR/stream", params=params)
        if not isinstance(data, list):
            raise ElexonAPIError(500, f"Expected JSON list from WINDFOR stream, got {type(data)}", "datasets/WINDFOR/stream")
        return data

    def fetch_forecast_evolution(self, start_time: str) -> List[Dict[str, Any]]:
        """
        Retrieves all historical revisions forecasting a specific delivery hour.
        """
        params = {"startTime": start_time, "format": "json"}
        data = self._request("forecast/generation/wind/evolution", params=params)
        if isinstance(data, dict) and "data" in data:
            return data["data"]
        return []
