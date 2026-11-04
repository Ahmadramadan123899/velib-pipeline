from decimal import Decimal

import pandas as pd

from train_model import TEST_HOURS, prepare, split_by_time


def make_hours(n_hours: int) -> pd.DataFrame:
    """A fake training table: one station, one row per hour."""
    return pd.DataFrame({
        "target_hour_utc": pd.date_range("2026-11-01", periods=n_hours, freq="h", tz="UTC"),
    })


def test_split_never_mixes_past_and_future():
    train, valid, test = split_by_time(make_hours(120))  # 5 days
    # every train hour is before every valid hour, and every valid hour before every test hour
    assert train["target_hour_utc"].max() < valid["target_hour_utc"].min()
    assert valid["target_hour_utc"].max() < test["target_hour_utc"].min()


def test_split_sizes_and_no_row_lost():
    df = make_hours(120)
    train, valid, test = split_by_time(df)
    assert len(test) == TEST_HOURS  # the last 48 hours
    assert len(valid) == 24  # the 24 hours before
    assert len(train) + len(valid) + len(test) == len(df)  # nothing lost, nothing counted twice


def test_prepare_fixes_types_and_adds_trend():
    df = pd.DataFrame({
        "station_id": [1, 2],
        "target_hour_utc": pd.to_datetime(["2026-11-02 08:00", "2026-11-02 08:00"], utc=True),
        "is_weekend": [False, True],
        "bikes_last_hour": [Decimal("10.0"), Decimal("4.0")],  # PostgreSQL sends Decimals
        "bikes_2h_ago": [Decimal("7.0"), None],  # one hour missing
    })
    out = prepare(df)
    assert out["bikes_last_hour"].dtype == float
    assert out["is_weekend"].tolist() == [0, 1]
    assert out.loc[0, "trend_last_hour"] == 3.0  # 10 - 7: bikes arriving
    assert pd.isna(out.loc[1, "trend_last_hour"])  # missing stays missing (LightGBM handles it)