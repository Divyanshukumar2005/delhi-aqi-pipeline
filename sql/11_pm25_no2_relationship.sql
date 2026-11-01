-- Q11  How strongly do PM2.5 and NO2 move together?
-- Question : Are fine particles and traffic-linked NO2 rising and falling together?
-- Techniques: CTE, aggregate algebra for correlation (no CORR() in SQLite), UNION ALL
-- Maths     : r^2 = (n*Sxy - Sx*Sy)^2 / ((n*Sxx - Sx^2) * (n*Syy - Sy^2)); the sign of the
--             numerator gives the direction. Avoids sqrt() so it runs on every SQLite build.
WITH pairs AS (
    SELECT area, pm25 AS x, no2 AS y
    FROM v_hourly
    WHERE pm25 IS NOT NULL AND no2 IS NOT NULL
),
sums AS (
    SELECT area, COUNT(*) AS n, SUM(x) AS sx, SUM(y) AS sy, SUM(x*y) AS sxy, SUM(x*x) AS sxx, SUM(y*y) AS syy
    FROM pairs GROUP BY area
    UNION ALL
    SELECT 'All NCR', COUNT(*), SUM(x), SUM(y), SUM(x*y), SUM(x*x), SUM(y*y) FROM pairs
)
SELECT
    area,
    n AS paired_hours,
    ROUND(sx / n, 1) AS mean_pm25,
    ROUND(sy / n, 1) AS mean_no2,
    ROUND(((n*sxy - sx*sy) * (n*sxy - sx*sy)) / ((n*sxx - sx*sx) * (n*syy - sy*sy)), 3) AS r_squared,
    CASE WHEN (n*sxy - sx*sy) >= 0 THEN 'positive' ELSE 'negative' END AS direction
FROM sums
WHERE n >= 100
ORDER BY CASE WHEN area = 'All NCR' THEN 1 ELSE 0 END, r_squared DESC;
