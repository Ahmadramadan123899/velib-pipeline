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
Vélib' API  -->  fetch_snapshot.py  -->  data/raw/ (compressed files)
                                              |
                                         load_raw.py  -->  PostgreSQL (Docker)
                                                                |
                                                         check_quality.py
```

Fetching and loading both run every 5 minutes with Windows Task Scheduler.
The quality checks I run by hand for now.

### 1. Getting the data

`fetch_snapshot.py` calls two feeds:

- `station_information`: the list of stations (name, location, capacity). It almost never changes.
- `station_status`: what's at each station right now (bikes, free docks, electric or mechanical).

Each run saves both answers exactly as they come, compressed, in one folder per day:

```
data/raw/station_status/2026-10-25/T150958Z.json.gz
```

### 2. Loading into PostgreSQL

`load_raw.py` reads the raw files and puts them into 3 tables:

- `stations`: one row per station (name, location, capacity)
- `station_status`: one row per station per snapshot (bikes, docks, e-bikes...)
- `loaded_files`: the list of files already loaded

The loader only loads files that are not in `loaded_files` yet. So I can run it as many
times as I want without getting duplicates. And if the database is down for a while, the raw
files just pile up and the loader catches up the next time it runs.

Each file is loaded in one transaction: either all of it goes in, or nothing does.
That way a crash can't leave a file half loaded.

PostgreSQL runs in Docker, so anyone can start the same database with one command.

### Some choices I made

- **I keep the raw files as they are.** The API only shows what's happening now.
  If I make a mistake later when cleaning the data, I can redo everything from these files.
- **All times are in UTC.** Paris time moves by one hour twice a year
  (it actually happened while I was building this). UTC never does.
- **Files are compressed with gzip.** One run is about 750 KB of JSON, so around 200 MB a day.
  Compressed, it's about 10 times smaller.
- **Fetching and loading are two separate steps.** Getting the data only needs the internet,
  loading only needs the database. One failing doesn't stop the other.
- **No foreign key between `station_status` and `stations`.** When Vélib' opens a new station,
  it can show up in the status feed first. I didn't want that to block the whole load,
  so I check it in the quality checks instead.

## Things I found in the data

- The API doesn't use the standard name for its update time. It sends `lastUpdatedOther`
  instead of `last_updated`.
- Some fields are sent twice under two names, like `num_bikes_available` and `numBikesAvailable`.
- The `ttl` field says the data stays fresh for one hour, but stations update every
  few minutes, so I don't rely on it.

## Data quality

`check_quality.py` runs a few checks on the database. Each check counts "bad" rows.
Some are errors (the pipeline is broken), some are warnings (strange, but it can happen
in real life).

What I found:

- **Capacity is not always right.** `capacity` is the number of docks at a station, so
  bikes + free docks should never be more than that. In 0.7% of the rows it was.
  It's always the same 11 stations, in almost every snapshot, so it's not a glitch: their
  capacity in the API is probably out of date. One station (BNF) is over by 27.
  I'll use the highest value seen at each station as its real capacity.
- **Almost half the time, some docks are missing.** In 45% of the rows, bikes + free docks
  are below capacity. That's normal: broken docks and bikes waiting for repair are not
  counted.
- **Some stations stopped reporting.** 19 stations hadn't sent any update in more than
  24 hours, and some not since 2017. I'll leave them out of the dashboard and the model.

## Project structure

```
velib-pipeline/
├── src/
│   ├── fetch_snapshot.py   # downloads and saves one snapshot
│   ├── load_raw.py         # loads new raw files into PostgreSQL
│   └── check_quality.py    # data quality checks
├── sql/
│   └── 001_create_tables.sql
├── docker-compose.yml      # PostgreSQL in Docker
├── .env.example            # database settings to copy into .env
├── run_fetch.bat           # what Task Scheduler runs every 5 minutes
├── requirements.txt
├── data/                   # raw files (not on GitHub)
└── logs/                   # run logs (not on GitHub)
```

## Run it yourself

You need Python 3.10 or newer and Docker. The scheduler part is for Windows.

```
git clone https://github.com/Ahmadramadan123899/velib-pipeline.git
cd velib-pipeline
python -m venv .venv
.venv\Scripts\activate.bat
pip install -r requirements.txt
```

Start the database (set your own password in `.env` first):

```
copy .env.example .env
docker compose up -d
docker exec -i velib-postgres psql -U velib -d velib < sql\001_create_tables.sql
```

Get one snapshot, load it and check it:

```
python src\fetch_snapshot.py
python src\load_raw.py
python src\check_quality.py
```

To run it every 5 minutes (change the path to where you cloned it):

```
schtasks /create /tn "VelibFetch" /tr "C:\path\to\velib-pipeline\run_fetch.bat" /sc minute /mo 5
```

## Plan

- [x] Get the data every 5 minutes and keep the raw files
- [x] Load it into PostgreSQL (running in Docker) and add data quality checks
- [ ] Build clean tables with dbt
- [ ] Make a dashboard: empty and full stations, rush hours, weather
- [ ] Predict the number of bikes per station one hour ahead
- [ ] Later: Airflow, tests, CI
0202.
## Data source

Vélib' Métropole open data (GBFS feeds).