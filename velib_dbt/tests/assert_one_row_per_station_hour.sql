-- The grain of fct_station_hourly is (station, hour). Any duplicate = bug.
select station_id, hour_utc, count(*) as n
from {{ ref('fct_station_hourly') }}
group by station_id, hour_utc
having count(*) > 1