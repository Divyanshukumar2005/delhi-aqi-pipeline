-- Q06  Daily city AQI with 7-day moving average and day-over-day change
-- Question : What is the trend, and which days jumped or dropped the most?
-- Techniques: CTE, HAVING for a coverage filter, AVG() OVER (RANGE ...), LAG()
-- Notes     : days where fewer than 15 stations reported are excluded so partial days do not distort the city mean.
--             The moving average uses a calendar window (the 7 days up to and including the row), and the
--             day-over-day change is only shown when the previous qualifying day is exactly one day earlier.
WITH daily AS (
    SELECT day, CAST(julianday(day) AS INTEGER) AS day_no,
           COUNT(DISTINCT station_id) AS stations, AVG(aqi) AS city_aqi
    FROM v_aqi
    WHERE aqi IS NOT NULL
    GROUP BY day
    HAVING COUNT(DISTINCT station_id) >= 15
),
with_prev AS (
    SELECT *,
           LAG(city_aqi) OVER (ORDER BY day_no) AS prev_aqi,
           LAG(day_no)   OVER (ORDER BY day_no) AS prev_day_no
    FROM daily
)
SELECT
    day,
    stations,
    ROUND(city_aqi, 0)                                                                   AS city_aqi,
    ROUND(AVG(city_aqi) OVER (ORDER BY day_no RANGE BETWEEN 6 PRECEDING AND CURRENT ROW), 0) AS moving_avg_7d,
    CASE WHEN day_no - prev_day_no = 1 THEN ROUND(city_aqi - prev_aqi, 0) END            AS change_vs_prev_day,
    CASE WHEN day_no - prev_day_no = 1 AND ABS(city_aqi - prev_aqi) >= 75 THEN 'big swing' ELSE '' END AS flag
FROM with_prev
ORDER BY day DESC
LIMIT 20;
