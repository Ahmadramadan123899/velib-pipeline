# ---------- Imports ----------
import gzip                                   # read .json.gz files
import json                                   # parse JSON text into Python dicts
import os                                     # read environment variables (our .env values)
from datetime import datetime, timezone       # timestamps
from pathlib import Path                      # file paths

import psycopg                                # PostgreSQL driver (version 3)
from dotenv import load_dotenv                # loads .env into environment variables

# ---------- Configuration ----------
PROJECT_ROOT = Path(__file__).resolve().parent.parent   # same trick as the fetcher: works from any folder
RAW_DIR = PROJECT_ROOT / "data" / "raw"                 # where the raw files are

load_dotenv(PROJECT_ROOT / ".env")            # put POSTGRES_USER, POSTGRES_PASSWORD... into os.environ

# ---------- SQL statements ----------
# Upsert: insert the station, or if it already exists, update it with the latest values.
INSERT_STATION = """
    INSERT INTO stations (station_id, station_code, name, lat, lon, capacity, updated_at)
    VALUES (%s, %s, %s, %s, %s, %s, now())
    ON CONFLICT (station_id) DO UPDATE SET
        station_code = EXCLUDED.station_code,
        name         = EXCLUDED.name,
        lat          = EXCLUDED.lat,
        lon          = EXCLUDED.lon,
        capacity     = EXCLUDED.capacity,
        updated_at   = now()
"""
# %s = placeholders. psycopg fills them in safely (this protects against SQL injection).
# EXCLUDED = "the new row we tried to insert".

# Insert a status row; if this (station, snapshot) already exists, skip it silently.
INSERT_STATUS = """
    INSERT INTO station_status (
        snapshot_at, station_id, bikes_available, mechanical_available, ebike_available,
        docks_available, is_installed, is_renting, is_returning, last_reported
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (station_id, snapshot_at) DO NOTHING
"""

# Remember that a file is done.
INSERT_LOADED_FILE = "INSERT INTO loaded_files (file_path, row_count) VALUES (%s, %s)"


# ---------- Small helpers ----------
def get_connection() -> psycopg.Connection:
    return psycopg.connect(
        host="localhost",                         # Docker exposes Postgres on our own PC...
        port=5433,                                # ...on port 5433 (see docker-compose.yml)
        dbname=os.environ["POSTGRES_DB"],         # values come from .env
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        autocommit=True,                          # each "with conn.transaction()" below becomes its own real transaction
    )


def read_json(path: Path) -> dict:
    if path.suffix == ".gz":                                  # new compressed files
        with gzip.open(path, "rt", encoding="utf-8") as f:    # "rt" = read text, decompressing on the fly
            return json.load(f)
    with open(path, encoding="utf-8") as f:                   # your old uncompressed .json files
        return json.load(f)


def snapshot_time_from_path(path: Path) -> datetime:
    day = path.parent.name                    # folder name, e.g. "2026-10-25"
    time_part = path.name.split(".")[0]       # "T150958Z.json.gz" -> "T150958Z"
    return datetime.strptime(day + time_part, "%Y-%m-%dT%H%M%SZ").replace(tzinfo=timezone.utc)
    # strptime = "string parse time": turns text into a datetime using the pattern we gave


def to_timestamp(unix_seconds):
    if not unix_seconds:                      # missing or 0 -> store NULL instead of 1970-01-01
        return None
    return datetime.fromtimestamp(unix_seconds, tz=timezone.utc)


def to_bool(value):
    if value is None:                         # missing -> NULL (we don't pretend we know)
        return None
    return bool(value)                        # 1 -> True, 0 -> False


# ---------- Turning JSON into rows ----------
def parse_station_rows(payload: dict) -> list:
    rows = []
    for s in payload["data"]["stations"]:     # one dict per station
        rows.append((                         # a tuple, in the same order as the INSERT columns
            s["station_id"],                  # [] = required: crash if missing (it must exist)
            s.get("stationCode"),             # .get() = optional: None if missing
            s["name"],
            s.get("lat"),
            s.get("lon"),
            s.get("capacity"),
        ))
    return rows


def parse_status_rows(payload: dict, snapshot_at: datetime) -> list:
    rows = []
    for s in payload["data"]["stations"]:
        bike_types = {}                                       # turn [{"mechanical": 2}, {"ebike": 3}]...
        for item in s.get("num_bikes_available_types", []):
            bike_types.update(item)                           # ...into {"mechanical": 2, "ebike": 3}
        rows.append((
            snapshot_at,                                      # same time for every station in this file
            s["station_id"],
            s.get("num_bikes_available"),
            bike_types.get("mechanical"),
            bike_types.get("ebike"),
            s.get("num_docks_available"),
            to_bool(s.get("is_installed")),
            to_bool(s.get("is_renting")),
            to_bool(s.get("is_returning")),
            to_timestamp(s.get("last_reported")),
        ))
    return rows


# ---------- Loading one file ----------
def load_file(conn: psycopg.Connection, path: Path, file_key: str) -> int:
    payload = read_json(path)
    feed_name = file_key.split("/")[0]        # "station_status/2026-10-25/T...json.gz" -> "station_status"
    if feed_name == "station_information":
        rows = parse_station_rows(payload)
        sql = INSERT_STATION
    else:
        rows = parse_status_rows(payload, snapshot_time_from_path(path))
        sql = INSERT_STATUS
    with conn.transaction():                  # ALL or NOTHING: the rows AND the loaded_files entry together
        with conn.cursor() as cur:
            cur.executemany(sql, rows)        # run the INSERT once per row (psycopg batches it, so it's fast)
            cur.execute(INSERT_LOADED_FILE, (file_key, len(rows)))
    return len(rows)


# ---------- Main ----------
def main() -> None:
    with get_connection() as conn:            # connection closes automatically at the end
        already_loaded = {row[0] for row in conn.execute("SELECT file_path FROM loaded_files")}
        # a set = very fast "is this in there?" checks

        new_files = []
        for path in sorted(RAW_DIR.rglob("*.json*")):          # every .json and .json.gz, in all subfolders
            file_key = path.relative_to(RAW_DIR).as_posix()    # short name with "/" (same on Windows & Linux)
            if file_key not in already_loaded:
                new_files.append((path, file_key))
        # sorted() puts station_information before station_status, and dates in order

        print(f"{len(new_files)} new files to load")
        for path, file_key in new_files:
            n_rows = load_file(conn, path, file_key)
            print(f"  loaded {file_key} ({n_rows} rows)")


if __name__ == "__main__":
    main()