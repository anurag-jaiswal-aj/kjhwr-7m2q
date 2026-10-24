import httpx
import pytest

from backend.app.services.elexon_client import (
    ElexonClient,
    ElexonAPIError,
    ElexonTimeoutError,
    ElexonRateLimitError,
)


def test_client_fetch_actuals_success():
    def handler(request: httpx.Request) -> httpx.Response:
        assert "datasets/FUELHH/stream" in str(request.url)
        assert request.url.params["fuelType"] == "WIND"
        data = [
            {
                "dataset": "FUELHH",
                "publishTime": "2026-01-01T00:30:00Z",
                "startTime": "2026-01-01T00:00:00Z",
                "settlementDate": "2026-01-01",
                "settlementPeriod": 1,
                "fuelType": "WIND",
                "generation": 12000,
            }
        ]
        return httpx.Response(200, json=data)

    transport = httpx.MockTransport(handler)
    http_client = httpx.Client(transport=transport)
    client = ElexonClient(client=http_client)

    result = client.fetch_actuals_stream("2026-01-01", "2026-01-01", "WIND")
    assert len(result) == 1
    assert result[0]["generation"] == 12000


def test_client_client_error_400():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, text="Bad query parameters")

    transport = httpx.MockTransport(handler)
    http_client = httpx.Client(transport=transport)
    client = ElexonClient(client=http_client, max_retries=2, backoff_factor=0.01)

    with pytest.raises(ElexonAPIError) as exc_info:
        client.fetch_actuals_stream("invalid-date", "invalid-date")
    assert exc_info.value.status_code == 400


def test_client_rate_limit_429():
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(429, text="Too Many Requests")

    transport = httpx.MockTransport(handler)
    http_client = httpx.Client(transport=transport)
    client = ElexonClient(client=http_client, max_retries=2, backoff_factor=0.001)

    with pytest.raises(ElexonRateLimitError):
        client.fetch_forecasts_stream("2026-01-01T00:00:00Z", "2026-01-01T23:59:59Z")
    assert attempts == 3  # initial + 2 retries


def test_client_timeout_retry():
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        raise httpx.ReadTimeout("Socket timeout")

    transport = httpx.MockTransport(handler)
    http_client = httpx.Client(transport=transport)
    client = ElexonClient(client=http_client, max_retries=2, backoff_factor=0.001)

    with pytest.raises(ElexonTimeoutError):
        client.fetch_actuals_stream("2026-01-01", "2026-01-01")
    assert attempts == 3


def test_client_server_error_500_retry_then_success():
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts < 2:
            return httpx.Response(500, text="Internal Server Error")
        return httpx.Response(200, json=[{"startTime": "2026-01-01T00:00:00Z", "publishTime": "2025-12-31T11:30:00Z", "generation": 15000}])

    transport = httpx.MockTransport(handler)
    http_client = httpx.Client(transport=transport)
    client = ElexonClient(client=http_client, max_retries=2, backoff_factor=0.001)

    result = client.fetch_forecasts_stream("2025-12-31T00:00:00Z", "2025-12-31T23:59:59Z")
    assert attempts == 2
    assert len(result) == 1
    assert result[0]["generation"] == 15000
