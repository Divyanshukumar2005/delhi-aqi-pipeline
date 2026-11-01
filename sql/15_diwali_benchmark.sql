-- Q15  Diwali 2026 benchmark: 7 days before vs 7 days from the festival
-- Question : How much does air quality change around Diwali (8 Nov 2026)?
-- Techniques: parameter CTE, date arithmetic with date(), CASE labelling, HAVING-style data check
-- Note      : returns "not enough data yet" until at least 4 days exist on each side.
--             Change the date in `params` to reuse the query for any other event.
WITH params AS (
    SELECT '2026-11-08' AS event_day, 7 AS window_days, 4 AS min_days
),
daily AS (
    SELECT day, AVG(aqi) AS city_aqi
    FROM v_aqi
    WHERE aqi IS NOT NULL
    GROUP BY day
    HAVING COUNT(DISTINCT station_id) >= 15
),
labelled AS (
    SELECT d.day, d.city_aqi,
           CASE WHEN d.day <  p.event_day AND d.day >= date(p.event_day, '-' || p.window_days || ' days') THEN 'before'
                WHEN d.day >= p.event_day AND d.day <  date(p.event_day, '+' || p.window_days || ' days') THEN 'after'
           END AS period
    FROM daily AS d CROSS JOIN params AS p
),
summary AS (
    SELECT period, COUNT(*) AS days_available, AVG(city_aqi) AS mean_aqi
    FROM labelled WHERE period IS NOT NULL GROUP BY period
)
SELECT
    p.period,
    COALESCE(s.days_available, 0) AS days_available,
    CASE WHEN COALESCE(s.days_available, 0) >= (SELECT min_days FROM params)
         THEN CAST(ROUND(s.mean_aqi) AS TEXT) ELSE 'not enough data yet' END AS mean_city_aqi
FROM (SELECT 'before' AS period UNION ALL SELECT 'after') AS p
LEFT JOIN summary AS s ON s.period = p.period
ORDER BY CASE p.period WHEN 'before' THEN 0 ELSE 1 END;
