select cast(d as date) as date_day
from generate_series(date '2022-01-01', date '2027-12-31', interval 1 day) as t(d)
