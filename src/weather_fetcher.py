"""
weather_fetcher.py
------------------
Fetches current weather from the Open-Meteo API for a list of European cities
and inserts the results into the weather_readings table in PostgreSQL.

Can be run standalone for testing:
    python src/weather_fetcher.py
"""

# Makes all type annotations lazy (treated as strings), so modern union syntax
# like `dict | None` works even on Python 3.8/3.9.
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

import psycopg2
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

# ── City definitions ───────────────────────────────────────────────────────────
# Each entry is (city_name, latitude, longitude)
CITIES = [
    ("London",    51.5085,   -0.1257),
    ("Paris",     48.8534,    2.3488),
    ("Berlin",    52.5244,   13.4105),
    ("Amsterdam", 52.3740,    4.8897),
    ("Madrid",    40.4165,   -3.7026),
    ("Rome",      41.8955,   12.4823),
    ("Warsaw",    52.2298,   21.0118),
    ("Stockholm", 59.3326,   18.0649),
    ("Vienna",    48.2085,   16.3721),
    ("Zurich",    47.3769,    8.5417),
]

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

# ── Database connection ────────────────────────────────────────────────────────
# Reads from environment variables so the same code works locally and inside Docker.
# Defaults match what docker-compose.yml defines.
def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", 5432)),
        dbname=os.getenv("DB_NAME", "weather_data"),
        user=os.getenv("DB_USER", "airflow"),
        password=os.getenv("DB_PASSWORD", "airflow"),
    )


# ── API fetch ─────────────────────────────────────────────────────────────────
def fetch_weather(city: str, lat: float, lon: float) -> dict | None:
    """Call Open-Meteo and return a flat dict ready for DB insertion."""
    params = {
        "latitude": lat,
        "longitude": lon,
        "current_weather": True,
        "timezone": "UTC",
    }
    try:
        response = requests.get(OPEN_METEO_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        cw = data["current_weather"]
        return {
            "city": city,
            "latitude": lat,
            "longitude": lon,
            # The API returns a string like "2024-06-25T14:00" — we parse it to datetime
            "recorded_at": datetime.strptime(cw["time"], "%Y-%m-%dT%H:%M").replace(
                tzinfo=timezone.utc
            ),
            "temperature_c": cw["temperature"],
            "wind_speed_kmh": cw["windspeed"],
        }
    except requests.RequestException as exc:
        log.error("Failed to fetch weather for %s: %s", city, exc)
        return None


# ── DB insert ─────────────────────────────────────────────────────────────────
INSERT_SQL = """
    INSERT INTO weather_readings
        (city, latitude, longitude, recorded_at, temperature_c, wind_speed_kmh)
    VALUES
        (%(city)s, %(latitude)s, %(longitude)s, %(recorded_at)s,
         %(temperature_c)s, %(wind_speed_kmh)s)
    ON CONFLICT (city, recorded_at) DO NOTHING;
"""

def save_readings(readings: list[dict]) -> int:
    """Insert a list of reading dicts. Returns the number of rows inserted."""
    if not readings:
        return 0

    conn = get_db_connection()
    try:
        with conn:                    # auto-commits on success, rolls back on error
            with conn.cursor() as cur:
                cur.executemany(INSERT_SQL, readings)
                return cur.rowcount
    finally:
        conn.close()


# ── Orchestration entry-point ─────────────────────────────────────────────────
def run_pipeline() -> None:
    """Fetch weather for all cities and persist to PostgreSQL."""
    log.info("Starting weather fetch for %d cities", len(CITIES))

    readings = []
    for city, lat, lon in CITIES:
        reading = fetch_weather(city, lat, lon)
        if reading:
            readings.append(reading)
            log.info("  ✓ %s — %.1f°C, wind %.1f km/h", city, reading["temperature_c"], reading["wind_speed_kmh"])
        else:
            log.warning("  ✗ %s — skipped", city)

    inserted = save_readings(readings)
    log.info("Pipeline complete. %d/%d readings saved.", inserted, len(CITIES))


if __name__ == "__main__":
    run_pipeline()
