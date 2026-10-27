-- One row per station, with clearer column names.
select
    station_id,
    station_code,
    name        as station_name,
    lat         as latitude,
    lon         as longitude,
    capacity    as official_capacity,   -- "official" because we know it's sometimes wrong
    updated_at
from {{ source('velib', 'stations') }}   -- dbt replaces this with public.stations