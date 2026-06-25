-- This script runs once when the PostgreSQL container is first created.
-- It sets up a dedicated database and table for our weather data,
-- separate from the 'airflow' metadata database.

CREATE DATABASE weather_data;

\connect weather_data;

CREATE TABLE IF NOT EXISTS weather_readings (
    id              SERIAL PRIMARY KEY,
    city            VARCHAR(100)    NOT NULL,
    latitude        NUMERIC(7, 4)   NOT NULL,
    longitude       NUMERIC(7, 4)   NOT NULL,
    recorded_at     TIMESTAMP       NOT NULL,   -- UTC timestamp from the API
    temperature_c   NUMERIC(5, 2),              -- degrees Celsius
    wind_speed_kmh  NUMERIC(6, 2),              -- km/h
    created_at      TIMESTAMP       NOT NULL DEFAULT NOW()
);

-- Index on (city, recorded_at) makes time-range queries per city fast
CREATE INDEX IF NOT EXISTS idx_weather_city_time
    ON weather_readings (city, recorded_at DESC);
