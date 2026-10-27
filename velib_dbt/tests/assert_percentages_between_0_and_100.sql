-- A percentage outside 0-100 means the calculation is wrong.
select *
from {{ ref('fct_station_hourly') }}
where pct_time_empty not between 0 and 100
   or pct_time_full  not between 0 and 100