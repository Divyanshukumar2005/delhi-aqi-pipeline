-- Q04  Sub-region comparison including an all-NCR total row
-- Question : How do Delhi, Gurugram, Noida, Faridabad and Bahadurgarh compare?
-- Techniques: CTE, GROUP BY, UNION ALL for a total row, conditional aggregation
WITH base AS (
    SELECT area, station_id, aqi, category
    FROM v_aqi
    WHERE aqi IS NOT NULL
),
by_area AS (
    SELECT area, COUNT(DISTINCT station_id) AS stations, COUNT(*) AS station_hours,
           AVG(aqi) AS mean_aqi, MAX(aqi) AS peak_aqi,
           100.0 * AVG(CASE WHEN aqi > 200 THEN 1.0 ELSE 0.0 END) AS pct_poor_or_worse,
           100.0 * AVG(CASE WHEN aqi <= 100 THEN 1.0 ELSE 0.0 END) AS pct_good_or_satisfactory
    FROM base GROUP BY area
),
total AS (
    SELECT 'All NCR' AS area, COUNT(DISTINCT station_id), COUNT(*),
           AVG(aqi), MAX(aqi),
           100.0 * AVG(CASE WHEN aqi > 200 THEN 1.0 ELSE 0.0 END),
           100.0 * AVG(CASE WHEN aqi <= 100 THEN 1.0 ELSE 0.0 END)
    FROM base
)
SELECT area, stations, station_hours,
       ROUND(mean_aqi, 0) AS mean_aqi, peak_aqi,
       ROUND(pct_poor_or_worse, 1) AS pct_poor_or_worse,
       ROUND(pct_good_or_satisfactory, 1) AS pct_good_or_satisfactory
FROM (SELECT * FROM by_area UNION ALL SELECT * FROM total)
ORDER BY CASE WHEN area = 'All NCR' THEN 1 ELSE 0 END, mean_aqi DESC;
