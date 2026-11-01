-- Q05  Time-of-day profile of PM2.5 (raw hourly concentrations)
-- Question : At what hour is fine-particle pollution worst and cleanest?
-- Techniques: GROUP BY hour, RANK() twice, window AVG for an index versus the daily mean
-- Note      : uses the raw hourly PM2.5, not the 24-hour rolling AQI, because a rolling mean hides the daily cycle.
WITH hourly AS (
    SELECT hour, AVG(pm25) AS mean_pm25, COUNT(pm25) AS readings
    FROM v_hourly
    WHERE pm25 IS NOT NULL
    GROUP BY hour
)
SELECT
    printf('%02d:00', hour)                                  AS hour_ist,
    readings,
    ROUND(mean_pm25, 1)                                      AS mean_pm25_ugm3,
    ROUND(100.0 * mean_pm25 / AVG(mean_pm25) OVER (), 0)     AS index_vs_daily_mean,   -- 100 = average hour
    CASE WHEN RANK() OVER (ORDER BY mean_pm25 DESC) <= 3 THEN 'peak'
         WHEN RANK() OVER (ORDER BY mean_pm25 ASC)  <= 3 THEN 'cleanest'
         ELSE '' END                                         AS flag
FROM hourly
ORDER BY hour;
