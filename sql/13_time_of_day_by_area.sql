-- Q13  PM2.5 by time of day and area (pivot table)
-- Question : Does each sub-region peak at the same time of day?
-- Techniques: conditional aggregation to pivot rows into columns, CASE for day-parts
SELECT
    area,
    ROUND(AVG(CASE WHEN hour BETWEEN 0  AND 5  THEN pm25 END), 1) AS night_00_05,
    ROUND(AVG(CASE WHEN hour BETWEEN 6  AND 11 THEN pm25 END), 1) AS morning_06_11,
    ROUND(AVG(CASE WHEN hour BETWEEN 12 AND 17 THEN pm25 END), 1) AS afternoon_12_17,
    ROUND(AVG(CASE WHEN hour BETWEEN 18 AND 23 THEN pm25 END), 1) AS evening_18_23,
    ROUND(AVG(pm25), 1)                                           AS all_day,
    COUNT(pm25)                                                   AS readings
FROM v_hourly
WHERE pm25 IS NOT NULL
GROUP BY area
ORDER BY all_day DESC;
