-- Q01  Data coverage and quality per station
-- Question : Which stations can I trust? How complete is each station's history?
-- Techniques: GROUP BY, conditional aggregation, date arithmetic with julianday()
SELECT
    station,
    area,
    COUNT(*)                                                         AS rows_stored,
    MIN(day)                                                         AS first_day,
    MAX(day)                                                         AS last_day,
    CAST(ROUND((julianday(MAX(ts)) - julianday(MIN(ts))) * 24) AS INTEGER) + 1  AS hours_in_span,
    ROUND(100.0 * COUNT(*) /
          (CAST(ROUND((julianday(MAX(ts)) - julianday(MIN(ts))) * 24) AS INTEGER) + 1), 1) AS pct_hours_present,
    ROUND(100.0 * COUNT(pm25) / COUNT(*), 1)                         AS pct_pm25_filled,
    ROUND(100.0 * COUNT(pm10) / COUNT(*), 1)                         AS pct_pm10_filled,
    ROUND(100.0 * SUM(CASE WHEN aqi IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*), 1)  AS pct_valid_aqi
FROM v_aqi
GROUP BY station_id, station, area
ORDER BY pct_valid_aqi ASC, station
LIMIT 15;
