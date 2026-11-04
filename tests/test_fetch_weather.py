from datetime import datetime, timezone

from fetch_weather import to_rows


def test_lists_become_one_row_per_hour():
    # Open-Meteo sends one list per variable; position i = same hour everywhere
    payload = {"hourly": {
        "time": ["2026-11-02T08:00", "2026-11-02T09:00"],
        "temperature_2m": [7.5, 8.1],
        "precipitation": [0.0, 1.2],
        "wind_speed_10m": [10.0, 12.5],
        "cloud_cover": [90, 100],
    }}
    rows = to_rows(payload)
    assert len(rows) == 2
    assert rows[1] == (datetime(2026, 11, 2, 9, tzinfo=timezone.utc), 8.1, 1.2, 12.5, 100)


def test_times_are_utc():
    payload = {"hourly": {
        "time": ["2026-11-02T08:00"], "temperature_2m": [7.5],
        "precipitation": [0.0], "wind_speed_10m": [10.0], "cloud_cover": [90],
    }}
    assert to_rows(payload)[0][0].tzinfo == timezone.utc  # never a "naive" time without zone