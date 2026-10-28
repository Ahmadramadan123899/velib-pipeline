-- One row per station per snapshot, plus a few simple helper columns.
select
    snapshot_at,
    snapshot_at at time zone 'Europe/Paris'  as snapshot_at_paris, -- local time, for rush-hour analysis
    station_id,
    bikes_available,
    mechanical_available,
    ebike_available,
    docks_available,
    is_installed,
    is_renting,
    is_returning,
    last_reported,
    snapshot_at - last_reported as report_age,-- how old the station's info is
    coalesce( last_reported < snapshot_at - interval '24 hours',true) as is_stale,-- no report for 24h(or never)=can't trust it
    (is_installed and is_renting and is_returning) as is_open -- true only if fully working
from {{ source('velib', 'station_status') }}