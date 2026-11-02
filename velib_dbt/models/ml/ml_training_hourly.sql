-- One row per station per target hour T.
-- Features = what we know before T. Target = average bikes during T.

with hourly as (
    select
        station_id,
        hour_utc,
        hour_of_day,        -- Paris time
        day_of_week,        -- 1 = Monday ... 7 = Sunday
        is_weekend,
        avg_bikes,
        avg_ebikes,
        pct_time_empty,
        pct_time_full,
        pct_time_closed
    from {{ ref('fct_station_hourly') }}
),

weather as (
    select hour_utc, temperature_c, precipitation_mm, wind_speed_kmh
    from {{ ref('stg_weather') }}
),


stations as (
    select station_id, real_capacity
    from {{ ref('dim_stations') }}
    where not is_ghost
)

select
    -- who and when
    t.station_id,
    t.hour_utc                as target_hour_utc,
    t.hour_of_day,                                 -- hour of T (we know the clock in advance)
    t.day_of_week,
    t.is_weekend,
    s.real_capacity,

    -- features: only hours BEFORE T
    h1.avg_bikes              as bikes_last_hour,           -- T-1
    h1.avg_ebikes             as ebikes_last_hour,
    h1.pct_time_empty         as pct_empty_last_hour,
    h1.pct_time_full          as pct_full_last_hour,
    h2.avg_bikes              as bikes_2h_ago,              -- T-2
    d1.avg_bikes              as bikes_same_hour_yesterday, -- T-24h
    
    -- weather: T-1 is measured; T stands in for the forecast (1h-ahead forecasts are very close)
    w1.precipitation_mm       as rain_last_hour_mm,
    w.precipitation_mm        as rain_mm,
    w.temperature_c,
    w.wind_speed_kmh,

    -- target: what we want to predict
    t.avg_bikes               as target_bikes

from hourly t
-- T-1 must exist: no "last hour", no prediction (inner join)
join hourly h1
    on  h1.station_id = t.station_id
    and h1.hour_utc   = t.hour_utc - interval '1 hour'
-- T-2 and yesterday can be missing (left join -> null)
left join hourly h2
    on  h2.station_id = t.station_id
    and h2.hour_utc   = t.hour_utc - interval '2 hours'
left join hourly d1
    on  d1.station_id = t.station_id
    and d1.hour_utc   = t.hour_utc - interval '24 hours'
-- weather can be missing for an hour: left join, LightGBM handles the nulls
left join weather w
    on  w.hour_utc  = t.hour_utc
left join weather w1
    on  w1.hour_utc = t.hour_utc - interval '1 hour'
join stations s
    on  s.station_id = t.station_id
-- skip hours where the station was mostly closed: nothing to predict there
where t.pct_time_closed  < 50
  and h1.pct_time_closed < 50