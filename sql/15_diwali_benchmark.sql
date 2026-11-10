-- Q15  Diwali 2026 benchmark: festival night vs the same clock hours on the 7 nights before
-- Question : How much higher was PM2.5 on Diwali night (8 Nov 2026, 18:00 to 9 Nov 12:00 IST) than at the same hours earlier?
-- Techniques: parameter CTE, window labelling with CASE + date(), two-level aggregation, minimum-coverage HAVING filters
-- Note      : raw hourly PM2.5 (not the 24 h AQI, which smooths a short spike away). A city hour needs >= 5 stations and
--             a night window needs >= 12 valid city hours, otherwise that night is skipped (data gap).
--             Mirrors analysis.diwali_night_benchmark in src/analysis.py. Change `event_day` to reuse it for another event.
WITH params AS (
    SELECT '2026-11-08' AS event_day, 18 AS start_hour, 12 AS end_hour,
           7 AS baseline_days, 5 AS min_stations, 12 AS min_hours, 4 AS min_days
),
city_hour AS (
    SELECT CASE WHEN h.hour >= p.start_hour THEN h.day ELSE date(h.day, '-1 day') END AS win_day,
           h.ts,
           AVG(h.pm25) AS city_pm25,
           MAX(h.pm25) AS worst_station
    FROM v_hourly AS h CROSS JOIN params AS p
    WHERE h.pm25 IS NOT NULL AND (h.hour >= p.start_hour OR h.hour < p.end_hour)
    GROUP BY win_day, h.ts
    HAVING COUNT(*) >= (SELECT min_stations FROM params)
),
per_window AS (
    SELECT win_day, COUNT(*) AS hours, AVG(city_pm25) AS mean_pm25,
           MAX(city_pm25) AS peak_city_pm25, MAX(worst_station) AS peak_station_pm25
    FROM city_hour
    GROUP BY win_day
    HAVING COUNT(*) >= (SELECT min_hours FROM params)
),
summary AS (
    SELECT 'same hours, 7 nights before' AS period, 0 AS ord,
           COUNT(*) AS nights_used, AVG(w.mean_pm25) AS mean_pm25,
           MAX(w.peak_city_pm25) AS peak_city_pm25, MAX(w.peak_station_pm25) AS peak_station_pm25
    FROM per_window AS w CROSS JOIN params AS p
    WHERE w.win_day <  p.event_day
      AND w.win_day >= date(p.event_day, '-' || p.baseline_days || ' days')
    UNION ALL
    SELECT 'Diwali night', 1, COUNT(*), AVG(w.mean_pm25), MAX(w.peak_city_pm25), MAX(w.peak_station_pm25)
    FROM per_window AS w CROSS JOIN params AS p
    WHERE w.win_day = p.event_day
)
SELECT period,
       nights_used,
       CASE WHEN nights_used >= CASE ord WHEN 0 THEN (SELECT min_days FROM params) ELSE 1 END
            THEN CAST(ROUND(mean_pm25) AS TEXT) ELSE 'not enough data yet' END AS mean_city_pm25,
       CASE WHEN nights_used > 0 THEN ROUND(peak_city_pm25)    END AS peak_city_hour_pm25,
       CASE WHEN nights_used > 0 THEN ROUND(peak_station_pm25) END AS peak_station_pm25
FROM summary
ORDER BY ord;
