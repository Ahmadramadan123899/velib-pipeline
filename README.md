# Vélib' pipeline

I'm building a small data pipeline around Vélib', the bike sharing system in Paris.
Every 5 minutes it saves the state of all ~1,500 stations: how many bikes are there,
how many docks are free, and how many of the bikes are electric.

The goal is to take this raw data all the way to something useful: clean tables,
a dashboard, and in the end a model that guesses how many bikes a station will have
in one hour.

I'm building it step by step, so some parts are not there yet (see the plan at the bottom).

## Why Vélib'

The data is real, public and changes all the time. There's a lot to look at:
morning and evening rush hours, stations that are always empty or always full,
and the weather changing how people ride. It's a good project to practice data
engineering, analysis and a bit of machine learning on the same data.

## How it works right now

```
Vélib' API  -->  fetch_snapshot.py  -->  data/raw/  (one compressed file per run)
                 runs every 5 min with Windows Task Scheduler
```

The script calls two feeds:

- `station_information`: the list of stations (name, location, capacity). It almost never changes.
- `station_status`: what's at each station right now (bikes, free docks, electric or mechanical).

Each run saves both answers exactly as they come, compressed, in one folder per day:

```
data/raw/station_status/2026-10-25/T150958Z.json.gz
```

Some choices I made:

- **I keep the raw files as they are.** The API only shows what's happening now.
  If I make a mistake later when cleaning the data, I can redo everything from these files.
- **All times are in UTC.** Paris time moves by one hour twice a year
  (it actually happened while I was building this). UTC never does.
- **Files are compressed with gzip.** One run is about 750 KB of JSON, so around 200 MB a day.
  Compressed, it's about 10 times smaller.

Things I found in the data:

- The API doesn't use the standard name for its update time. It sends `lastUpdatedOther`
  instead of `last_updated`.
- Some fields are sent twice under two names, like `num_bikes_available` and `numBikesAvailable`.
- The `ttl` field says the data stays fresh for one hour, but stations update every
  few minutes, so I don't rely on it.

## Project structure

```
velib-pipeline/
├── src/
│   └── fetch_snapshot.py   # downloads and saves one snapshot
├── run_fetch.bat           # what Task Scheduler runs every 5 minutes
├── requirements.txt
├── data/                   # raw files (not on GitHub)
└── logs/                   # run logs (not on GitHub)
```

## Run it yourself

You need Python 3.10 or newer. The scheduler part is for Windows.

```
git clone https://github.com/Ahmadramadan123899/velib-pipeline.git
cd velib-pipeline
python -m venv .venv
.venv\Scripts\activate.bat
pip install -r requirements.txt
python src\fetch_snapshot.py
```

To run it every 5 minutes (change the path to where you cloned it):

```
schtasks /create /tn "VelibFetch" /tr "C:\path\to\velib-pipeline\run_fetch.bat" /sc minute /mo 5
```

## Plan

- [x] Get the data every 5 minutes and keep the raw files
- [ ] Load it into PostgreSQL (running in Docker) and add data quality checks
- [ ] Build clean tables with dbt
- [ ] Make a dashboard: empty and full stations, rush hours, weather
- [ ] Predict the number of bikes per station one hour ahead
- [ ] Later: Airflow, tests, CI

## Data source

Vélib' Métropole open data (GBFS feeds).