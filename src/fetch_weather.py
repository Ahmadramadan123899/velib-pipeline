import gzip  # save the raw answer compressed
import json  # read/write JSON
import os  # read environment variables (.env values)
from datetime import datetime, timezone  # timestamps
from pathlib import Path  # file paths

import psycopg  # PostgreSQL driver
import requests  # HTTP calls
from dotenv import load_dotenv  # loads .env into environment variables

# Configuration
PROJECT_ROOT = Path(__file__).resolve().parent.parent  # works from any folder
RAW_DIR = PROJECT_ROOT / "data" / "raw" / "weather"  # raw answers, like the Velib' feeds
load_dotenv(PROJECT_ROOT / ".env")

# Open-Meteo: free, no API key. This is the URL from the website, split into pieces.
URL = "https://api.open-meteo.com/v1/forecast"
PARAMS = {
    "latitude": 48.8534,  # Paris
    "longitude": 2.3488,
    "hourly": "temperature_2m,wind_speed_10m,cloud_cover,precipitation",
    "timezone": "GMT",  # times in UTC, like the rest of the project
    "past_days": 14,  # covers the Velib' days, fills holes, fixes old forecasts
    "forecast_days": 1,  # plus the rest of today
}

# Insert the hour, or update it if we already have it (newer values are better)
UPSERT = """
    INSERT INTO weather_hourly (hour_utc, temperature_c, precipitation_mm, wind_speed_kmh, cloud_cover_pct, fetched_at)
    VALUES (%s, %s, %s, %s, %s, now())
    ON CONFLICT (hour_utc) DO UPDATE SET
        temperature_c    = EXCLUDED.temperature_c,
        precipitation_mm = EXCLUDED.precipitation_mm,
        wind_speed_kmh   = EXCLUDED.wind_speed_kmh,
        cloud_cover_pct  = EXCLUDED.cloud_cover_pct,
        fetched_at       = now()
"""
# DO UPDATE (not DO NOTHING like the Velib' loader): a weather hour can change, the newest value wins.


def fetch() -> dict:
    response = requests.get(URL, params=PARAMS, timeout=10)  # requests builds the full URL from PARAMS
    response.raise_for_status()  # stop here if the API answered with an error
    return response.json()


def save_raw(payload: dict, fetched_at: datetime) -> Path:
    """Keep the answer exactly as it came, same idea as the Velib' raw files."""
    folder = RAW_DIR / fetched_at.strftime("%Y-%m-%d")  # data/raw/weather/2026-11-02
    folder.mkdir(parents=True, exist_ok=True)
    file_path = folder / fetched_at.strftime("T%H%M%SZ.json.gz")
    with gzip.open(file_path, "wt", encoding="utf-8") as f:
        json.dump(payload, f)
    return file_path


def to_rows(payload: dict) -> list[tuple]:
    """Open-Meteo sends one list per variable. We turn them into one row per hour."""
    h = payload["hourly"]
    rows = []
    for i, time_text in enumerate(h["time"]):  # i = position in the lists, time_text = "2026-11-02T09:00"
        hour_utc = datetime.fromisoformat(time_text).replace(tzinfo=timezone.utc)  # text -> UTC time
        rows.append((
            hour_utc,
            h["temperature_2m"][i],  # same position i in every list = same hour
            h["precipitation"][i],
            h["wind_speed_10m"][i],
            h["cloud_cover"][i],
        ))
    return rows


def main() -> None:
    fetched_at = datetime.now(timezone.utc)
    payload = fetch()
    file_path = save_raw(payload, fetched_at)  # 1. save raw first (we can always replay it)
    rows = to_rows(payload)  # 2. lists -> rows
    with psycopg.connect(
        host="localhost",
        port=5433,
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
    ) as conn:
        with conn.cursor() as cur:
            cur.executemany(UPSERT, rows)  # 3. one upsert per hour
        # leaving the "with conn" block commits everything at once
    print(f"{fetched_at:%Y-%m-%d %H:%M} UTC: {len(rows)} hours saved "
          f"({rows[0][0]:%m-%d %H}h to {rows[-1][0]:%m-%d %H}h) -> {file_path.name}")


if __name__ == "__main__":
    main()