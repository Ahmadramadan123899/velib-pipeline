-- One row per station per hour (UTC). The main table for the dashboard and the ML model.
-- Ghost stations are left out.

with active_stations as (
    select station_id, real_capacity
    from {{ ref('dim_stations') }}
    where not is_ghost -- only stations we can trust
),

hourly as (
    select
        s.station_id,
        date_trunc('hour', s.snapshot_at)       as hour_utc,     -- e.g. 16:23 -> 16:00
        date_trunc('hour', s.snapshot_at_paris) as hour_paris,   -- same hour, in Paris time
        count(*)                                as n_snapshots,  -- normally 12 per hour (one every 5 min)
        round(avg(s.bikes_available), 1)        as avg_bikes,
        min(s.bikes_available)                  as min_bikes,
        max(s.bikes_available)                  as max_bikes,
        round(avg(s.ebike_available), 1)        as avg_ebikes,
        round(avg(s.docks_available), 1)        as avg_docks,
        round(100.0*avg(case when s.bikes_available=0 then 1 else 0 end) filter (where s.is_open), 1)      
                          as pct_time_empty,   -- empty, counting only open moments
        round(100.0 * avg(case when s.docks_available = 0 then 1 else 0 end) filter (where s.is_open), 1)  
                          as pct_time_full,    -- full, counting only open moments
        round(100.0 * avg(case when s.is_open then 0 else 1 end), 1)
                          as pct_time_closed   -- percentage of time the station was closed
    from {{ ref('stg_station_status') }} s
    join active_stations using (station_id)    -- inner join = ghost stations drop out here
    group by 1, 2, 3                            -- group by the first 3 columns
)

select
    h.*,
    extract(isodow from h.hour_paris)::int      as day_of_week, -- 1 = Monday ... 7 = Sunday
    extract(hour from h.hour_paris)::int        as hour_of_day, -- 0 to 23, Paris time
    extract(isodow from h.hour_paris) in (6, 7) as is_weekend,
    h.hour_paris::date                          as date_paris, -- the day, in Paris time, for filters
    round(100.0*h.avg_bikes/nullif(a.real_capacity, 0), 1) as pct_fill -- nullif(x, 0) avoids "division by zero" if a capacity is 0
from hourly h
join active_stations a using (station_id)