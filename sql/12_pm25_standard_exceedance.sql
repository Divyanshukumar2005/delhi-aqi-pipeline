-- Q12  Days above the CPCB 24-hour PM2.5 standard (60 ug/m3) per station
-- Question : On how many days does each station breach the national standard?
-- Techniques: two-level CTE (hour -> day -> station), HAVING for valid days, RANK()
-- Rule      : a day counts only when the station has at least 16 PM2.5 hours that day.
WITH daily AS (
    SELECT station_id, station, area, day, AVG(pm25) AS mean_pm25
    FROM v_hourly
    WHERE pm25 IS NOT NULL
    GROUP BY station_id, station, area, day
    HAVING COUNT(pm25) >= 16
),
per_station AS (
    SELECT station, area,
           COUNT(*)                                              AS valid_days,
           SUM(CASE WHEN mean_pm25 > 60 THEN 1 ELSE 0 END)        AS days_above_60,
           ROUND(AVG(mean_pm25), 1)                              AS mean_daily_pm25,
           ROUND(MAX(mean_pm25), 1)                              AS worst_day_pm25
    FROM daily
    GROUP BY station_id, station, area
    HAVING COUNT(*) >= 20
)
SELECT
    RANK() OVER (ORDER BY 1.0 * days_above_60 / valid_days DESC) AS rank_no,
    station, area, valid_days, days_above_60,
    ROUND(100.0 * days_above_60 / valid_days, 0)                  AS pct_days_above_60,
    mean_daily_pm25, worst_day_pm25
FROM per_station
ORDER BY rank_no, station
LIMIT 15;
