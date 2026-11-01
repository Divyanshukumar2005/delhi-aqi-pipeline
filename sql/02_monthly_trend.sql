-- Q02  Monthly pollution trend with month-over-month change
-- Question : Is air quality getting better or worse as winter approaches?
-- Techniques: CTE, GROUP BY, LAG() window function, conditional aggregation
-- Note      : the latest month is usually partial, so check days_covered before comparing.
WITH monthly AS (
    SELECT
        month,
        COUNT(DISTINCT day)                              AS days_covered,
        COUNT(DISTINCT station_id)                       AS stations,
        COUNT(*)                                         AS station_hours,
        AVG(aqi)                                         AS mean_aqi,
        100.0 * AVG(CASE WHEN aqi > 200 THEN 1.0 ELSE 0.0 END) AS pct_poor_or_worse
    FROM v_aqi
    WHERE aqi IS NOT NULL
    GROUP BY month
)
SELECT
    month,
    days_covered,
    stations,
    station_hours,
    ROUND(mean_aqi, 0)                                              AS mean_aqi,
    ROUND(mean_aqi - LAG(mean_aqi) OVER (ORDER BY month), 0)        AS change_vs_prev_month,
    ROUND(pct_poor_or_worse, 1)                                     AS pct_poor_or_worse
FROM monthly
ORDER BY month;
