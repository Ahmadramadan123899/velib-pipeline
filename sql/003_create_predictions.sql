-- The model's predictions on the test period, next to the real values.
-- Replaced at every training run (we only keep the latest model's results).

CREATE TABLE IF NOT EXISTS predictions_hourly (
    station_id       BIGINT      NOT NULL,
    target_hour_utc  TIMESTAMPTZ NOT NULL,  -- the hour we predicted
    predicted_bikes  REAL,                  -- what the model said
    baseline_bikes   REAL,                  -- what "last hour" said
    actual_bikes     REAL,                  -- what really happened
    model_run_at     TIMESTAMPTZ NOT NULL,  -- when the model was trained
    PRIMARY KEY (station_id, target_hour_utc)
);