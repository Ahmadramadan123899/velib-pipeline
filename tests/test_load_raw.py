from datetime import datetime, timezone
from pathlib import Path

from load_raw import parse_station_rows, parse_status_rows, snapshot_time_from_path

SNAPSHOT = datetime(2026, 10, 25, 15, 9, 58, tzinfo=timezone.utc)


def test_snapshot_time_comes_from_folder_and_file_name():
    path = Path("data/raw/station_status/2026-10-25/T150958Z.json.gz")
    assert snapshot_time_from_path(path) == SNAPSHOT  # folder = day, file = time, in UTC


def test_bike_types_list_is_flattened():
    # the API sends bike types as a list of one-key dicts
    payload = {"data": {"stations": [{
        "station_id": 1,
        "num_bikes_available": 5,
        "num_bikes_available_types": [{"mechanical": 2}, {"ebike": 3}],
    }]}}
    row = parse_status_rows(payload, SNAPSHOT)[0]
    assert row[2] == 5  # bikes
    assert row[3] == 2  # mechanical
    assert row[4] == 3  # ebike


def test_missing_values_become_none_not_zero():
    # a station that sends almost nothing: we store NULL, we don't invent values
    payload = {"data": {"stations": [{"station_id": 1, "last_reported": 0}]}}
    row = parse_status_rows(payload, SNAPSHOT)[0]
    assert row[2] is None  # bikes unknown, not 0
    assert row[6] is None  # is_installed unknown, not False
    assert row[9] is None  # last_reported = 0 -> NULL, not 1970-01-01


def test_flags_become_booleans():
    payload = {"data": {"stations": [{
        "station_id": 1, "is_installed": 1, "is_renting": 0, "is_returning": 1,
    }]}}
    row = parse_status_rows(payload, SNAPSHOT)[0]
    assert row[6:9] == (True, False, True)


def test_station_rows_keep_the_column_order():
    payload = {"data": {"stations": [{
        "station_id": 42, "stationCode": "16107", "name": "Benjamin Godard",
        "lat": 48.86, "lon": 2.27, "capacity": 35,
    }]}}
    assert parse_station_rows(payload) == [(42, "16107", "Benjamin Godard", 48.86, 2.27, 35)]