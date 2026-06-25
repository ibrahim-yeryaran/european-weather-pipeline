"""
Unit tests for weather_fetcher.

These tests mock the network and database so they run instantly with no
internet connection and no running PostgreSQL — exactly what you want in CI.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

# Make src/ importable without installing the package
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import weather_fetcher  # noqa: E402


# A canned Open-Meteo response (only the fields we use)
FAKE_API_RESPONSE = {
    "current_weather": {
        "time": "2024-06-25T14:00",
        "temperature": 21.5,
        "windspeed": 12.3,
    }
}


@patch("weather_fetcher.requests.get")
def test_fetch_weather_parses_api_response(mock_get):
    """fetch_weather should turn the API JSON into a flat, DB-ready dict."""
    mock_response = MagicMock()
    mock_response.json.return_value = FAKE_API_RESPONSE
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    result = weather_fetcher.fetch_weather("Paris", 48.85, 2.35)

    assert result == {
        "city": "Paris",
        "latitude": 48.85,
        "longitude": 2.35,
        "recorded_at": datetime(2024, 6, 25, 14, 0, tzinfo=timezone.utc),
        "temperature_c": 21.5,
        "wind_speed_kmh": 12.3,
    }


@patch("weather_fetcher.requests.get")
def test_fetch_weather_returns_none_on_http_error(mock_get):
    """A network/HTTP error should be handled gracefully, returning None."""
    mock_get.side_effect = weather_fetcher.requests.RequestException("boom")

    result = weather_fetcher.fetch_weather("London", 51.5, -0.12)

    assert result is None


def test_save_readings_empty_list_skips_db():
    """An empty list should short-circuit and never touch the database."""
    with patch("weather_fetcher.get_db_connection") as mock_conn:
        inserted = weather_fetcher.save_readings([])

    assert inserted == 0
    mock_conn.assert_not_called()
