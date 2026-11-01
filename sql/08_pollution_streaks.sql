-- Q08  Longest runs of consecutive "Poor or worse" days (gaps and islands)
-- Question : How long do severe pollution episodes last?
-- Techniques: CTE chain, ROW_NUMBER() minus date number to label islands, GROUP BY island
-- Note      : days with fewer than 15 reporting stations are skipped, so they also end a run.
-- How it works: for qualifying days, (day number - row number) stays constant while days are
--               consecutive and changes at every break, so it identifies each run.
WITH daily AS (
    SELECT day, AVG(aqi) AS city_aqi
    FROM v_aqi
    WHERE aqi IS NOT NULL
    GROUP BY day
    HAVING COUNT(DISTINCT station_id) >= 15
),
bad_days AS (
    SELECT day, city_aqi FROM daily WHERE city_aqi > 200      -- CPCB "Poor" starts above 200
),
labelled AS (
    SELECT day, city_aqi,
           CAST(julianday(day) AS INTEGER) - ROW_NUMBER() OVER (ORDER BY day) AS island
    FROM bad_days
)
SELECT
    MIN(day)                 AS episode_start,
    MAX(day)                 AS episode_end,
    COUNT(*)                 AS days_in_a_row,
    ROUND(AVG(city_aqi), 0)  AS mean_city_aqi,
    ROUND(MAX(city_aqi), 0)  AS peak_day_aqi
FROM labelled
GROUP BY island
ORDER BY days_in_a_row DESC, episode_start DESC
LIMIT 10;
