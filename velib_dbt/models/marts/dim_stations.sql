-- One row per station, with the fixes we decided on in week 2:
--   * real capacity (the feed's capacity is wrong for ~11 stations)
--   * ghost flag (stations that stopped reporting)

with status_stats as (
    -- What we have actually seen at each station, across all snapshots
    select
        station_id,
        max(bikes_available + docks_available) as max_observed_total,  -- most bikes + free docks ever seen
        max(last_reported)                     as last_reported,       -- most recent report from the station
        max(snapshot_at)                       as last_seen_at         -- most recent snapshot we have
    from {{ ref('stg_station_status') }}      -- ref() = "use another dbt model" (source() was for raw tables)
    group by station_id
)

select
    s.station_id,
    s.station_code,
    s.station_name,
    s.latitude,
    s.longitude,
    s.official_capacity,
    greatest(s.official_capacity, st.max_observed_total) as real_capacity,      -- the bigger of the two
    coalesce(st.max_observed_total > s.official_capacity, false) as capacity_was_wrong,
    st.last_reported,
    coalesce(st.last_reported < st.last_seen_at - interval '24 hours', true) as is_ghost
    -- ghost = no report in the 24h before our latest snapshot (or never reported at all)
from {{ ref('stg_stations') }} s
left join status_stats st using (station_id)   -- left join: keep every station, even with no status rows