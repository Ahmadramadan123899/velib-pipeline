-- 001_create_tables.sql
-- Creates the 3 tables of the pipeline. Safe to run more than once (IF NOT EXISTS).

-- One row per station (from station_information). Updated on each load.
CREATE TABLE IF NOT EXISTS stations (
    station_id    BIGINT PRIMARY KEY,                 -- Vélib's unique id for the station
    station_code  TEXT,                               -- the short code shown to users, e.g. '16107'
    name          TEXT NOT NULL,                      -- every station must have a name
    lat           DOUBLE PRECISION,                   -- latitude (GPS)
    lon           DOUBLE PRECISION,                   -- longitude (GPS)
    capacity      INT,                                -- total number of docks
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()  -- when our loader last refreshed this row
);

-- One row per station per snapshot (from station_status). The big table.
CREATE TABLE IF NOT EXISTS station_status (
    snapshot_at           TIMESTAMPTZ NOT NULL,   -- when our script fetched the data (from the file name)
    station_id            BIGINT NOT NULL,        -- which station
    bikes_available       INT,                    -- all bikes (mechanical + ebike)
    mechanical_available  INT,                    -- normal bikes only
    ebike_available       INT,                    -- electric bikes only
    docks_available       INT,                    -- free spots to return a bike
    is_installed          BOOLEAN,                -- is the station physically there and set up
    is_renting            BOOLEAN,                -- can you take a bike right now
    is_returning          BOOLEAN,                -- can you return a bike right now
    last_reported         TIMESTAMPTZ,            -- when the station itself last sent its status
    PRIMARY KEY (station_id, snapshot_at)         -- one station can't appear twice in the same snapshot
);

-- Speeds up queries filtered by time, e.g. "everything from last week".
-- The primary key already covers queries by station_id first.
CREATE INDEX IF NOT EXISTS idx_station_status_snapshot_at
    ON station_status (snapshot_at);

-- One row per raw file already loaded. Lets the loader skip files it has already done.
CREATE TABLE IF NOT EXISTS loaded_files (
    file_path   TEXT PRIMARY KEY,                    -- e.g. 'station_status/2026-10-25/T150958Z.json.gz'
    loaded_at   TIMESTAMPTZ NOT NULL DEFAULT now(),  -- when it was loaded
    row_count   INT                                  -- how many rows it gave (handy for checks)
);