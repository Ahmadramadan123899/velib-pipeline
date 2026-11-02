-- One row per hour (UTC): the weather in Paris.
select
    hour_utc,
    temperature_c,
    precipitation_mm,
    precipitation_mm > 0 as is_raining,  -- easier to read in charts
    wind_speed_kmh,
    cloud_cover_pct
from {{ source('velib', 'weather_hourly') }}
