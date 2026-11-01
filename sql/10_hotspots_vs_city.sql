-- Q10  Hotspots: stations that run hotter or cleaner than the city at the same hour
-- Question : Which stations are polluted for local reasons rather than because the whole city is polluted?
-- Techniques: CTE, self-join of a station table to an hourly city average, RANK(), UNION ALL
-- Note      : comparing at the same hour removes the effect of weather and season.
WITH city_hour AS (
    SELECT ts, AVG(aqi) AS city_aqi, COUNT(*) AS stations
    FROM v_aqi
    WHERE aqi IS NOT NULL
    GROUP BY ts
    HAVING COUNT(*) >= 15
),
dev AS (
    SELECT a.station, a.area,
           COUNT(*)                      AS hours_compared,
           AVG(a.aqi - c.city_aqi)       AS avg_gap_to_city
    FROM v_aqi AS a
    JOIN city_hour AS c ON c.ts = a.ts
    WHERE a.aqi IS NOT NULL
    GROUP BY a.station_id, a.station, a.area
    HAVING COUNT(*) >= 500
),
ranked AS (
    SELECT *,
           RANK() OVER (ORDER BY avg_gap_to_city DESC) AS rk_hot,
           RANK() OVER (ORDER BY avg_gap_to_city ASC)  AS rk_clean
    FROM dev
)
SELECT 'hotter than city' AS kind, rk_hot AS rank_no, station, area, hours_compared, ROUND(avg_gap_to_city, 1) AS avg_gap_to_city
FROM ranked WHERE rk_hot <= 5
UNION ALL
SELECT 'cleaner than city', rk_clean, station, area, hours_compared, ROUND(avg_gap_to_city, 1)
FROM ranked WHERE rk_clean <= 5
ORDER BY kind DESC, rank_no;
