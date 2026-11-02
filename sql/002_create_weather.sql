-- Hourly weather in Paris, from Open-Meteo.
-- One row per hour (UTC). Values can be updated: a forecast becomes a measurement later.
CREATE TABLE IF NOT EXISTS weather_hourly (
    hour_utc         TIMESTAMPTZ PRIMARY KEY,           -- start of the hour, UTC
    temperature_c    REAL,                              -- air temperature at 2 m
    precipitation_mm REAL,                              -- rain (or snow) during the hour
    wind_speed_kmh   REAL,                              -- wind at 10 m
    cloud_cover_pct  REAL,                              -- 0 = clear sky, 100 = fully cloudy
    fetched_at       TIMESTAMPTZ NOT NULL DEFAULT now() -- when we last got this hour
);