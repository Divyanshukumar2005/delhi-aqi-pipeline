-- Q07  Five worst and five cleanest days
-- Question : Which days stand out at both extremes?
-- Techniques: CTE, ROW_NUMBER() ordered in both directions, UNION ALL
WITH daily AS (
    SELECT day, COUNT(DISTINCT station_id) AS stations, AVG(aqi) AS city_aqi,
           MAX(aqi) AS worst_station_hour
    FROM v_aqi
    WHERE aqi IS NOT NULL
    GROUP BY day
    HAVING COUNT(DISTINCT station_id) >= 15
),
ranked AS (
    SELECT *,
           ROW_NUMBER() OVER (ORDER BY city_aqi DESC) AS rn_worst,
           ROW_NUMBER() OVER (ORDER BY city_aqi ASC)  AS rn_best
    FROM daily
)
SELECT 'worst' AS kind, rn_worst AS rank_no, day, stations, ROUND(city_aqi, 0) AS city_aqi, worst_station_hour
FROM ranked WHERE rn_worst <= 5
UNION ALL
SELECT 'cleanest', rn_best, day, stations, ROUND(city_aqi, 0), worst_station_hour
FROM ranked WHERE rn_best <= 5
ORDER BY kind DESC, rank_no;
