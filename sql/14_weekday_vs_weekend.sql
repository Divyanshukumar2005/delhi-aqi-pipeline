-- Q14  Weekday vs weekend city AQI
-- Question : Is pollution different on weekends (less traffic and industry)?
-- Techniques: CTE, strftime('%w') day-of-week, GROUP BY, HAVING coverage filter
-- Note      : this only describes the averages. The dashboard's Insights tab adds a Welch's t-test;
--             with a few weekends of data the difference is usually not statistically significant.
WITH daily AS (
    SELECT day, AVG(aqi) AS city_aqi
    FROM v_aqi
    WHERE aqi IS NOT NULL
    GROUP BY day
    HAVING COUNT(DISTINCT station_id) >= 15
)
SELECT
    CASE WHEN CAST(strftime('%w', day) AS INTEGER) IN (0, 6) THEN 'Weekend' ELSE 'Weekday' END AS day_type,
    COUNT(*)                  AS days,
    ROUND(AVG(city_aqi), 0)   AS mean_city_aqi,
    ROUND(MIN(city_aqi), 0)   AS lowest_day,
    ROUND(MAX(city_aqi), 0)   AS highest_day
FROM daily
GROUP BY day_type
ORDER BY day_type DESC;
