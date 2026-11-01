-- =====================================================================
-- 00_setup.sql  -  shared TEMP views used by every query in this folder
-- =====================================================================
-- Run this first in the same session. TEMP views live only in memory, so the
-- committed database file (data/aqi.db) is never modified.
--
--   sqlite3 -header -column data/aqi.db ".read sql/00_setup.sql" ".read sql/03_station_leaderboard.sql"
--
-- Requires SQLite 3.25+ (window functions). Tested on 3.37 to 3.45.
--
-- Views (each builds on the previous one):
--   v_bands   CPCB breakpoint table (PM2.5 and PM10)
--   v_hourly  one row per station-hour with area, IST day and hour of day
--   v_roll    + rolling 24-hour PM2.5 / PM10 means (CPCB rule: >= 16 valid hours)
--   v_aqi     + CPCB sub-indices, overall AQI and category
-- The AQI maths mirrors src/analysis.py and is checked against it in tests/test_sql.py.

DROP VIEW IF EXISTS temp.v_aqi;
DROP VIEW IF EXISTS temp.v_roll;
DROP VIEW IF EXISTS temp.v_hourly;
DROP VIEW IF EXISTS temp.v_bands;

-- Continuous CPCB bands: (lower conc, upper conc, lower index, upper index).
CREATE TEMP VIEW v_bands AS
SELECT column1 AS pollutant, column2 AS c_lo, column3 AS c_hi, column4 AS i_lo, column5 AS i_hi
FROM (VALUES
    ('pm25',   0.0,  30.0,   0,  50),
    ('pm25',  30.0,  60.0,  50, 100),
    ('pm25',  60.0,  90.0, 100, 200),
    ('pm25',  90.0, 120.0, 200, 300),
    ('pm25', 120.0, 250.0, 300, 400),
    ('pm25', 250.0, 380.0, 400, 500),
    ('pm10',   0.0,  50.0,   0,  50),
    ('pm10',  50.0, 100.0,  50, 100),
    ('pm10', 100.0, 250.0, 100, 200),
    ('pm10', 250.0, 350.0, 200, 300),
    ('pm10', 350.0, 430.0, 300, 400),
    ('pm10', 430.0, 510.0, 400, 500)
);

-- One row per station per hour. ts is ISO 8601 in IST (for example 2026-10-30T13:00:00+05:30).
CREATE TEMP VIEW v_hourly AS
SELECT
    station_id,
    station,
    CASE
        WHEN lower(station) LIKE '%gurugram%' OR lower(station) LIKE '%gurgaon%' THEN 'Gurugram'
        WHEN lower(station) LIKE '%noida%'        THEN 'Noida'
        WHEN lower(station) LIKE '%faridabad%'    THEN 'Faridabad'
        WHEN lower(station) LIKE '%bahadurgarh%'  THEN 'Bahadurgarh'
        ELSE 'Delhi'
    END                                            AS area,
    ts,
    substr(ts, 1, 10)                              AS day,
    substr(ts, 1, 7)                               AS month,
    CAST(substr(ts, 12, 2) AS INTEGER)             AS hour,       -- hour of day (IST label)
    CAST(strftime('%s', ts) AS INTEGER) / 3600     AS hour_idx,   -- absolute hour number, used for rolling windows
    pm25, pm10, no2, o3,
    source
FROM readings;

-- Rolling 24-hour means per station. RANGE over the absolute hour number means a missing
-- hour shortens the window instead of silently pulling in older rows. CPCB needs >= 16 valid hours.
CREATE TEMP VIEW v_roll AS
SELECT
    h.*,
    CASE WHEN COUNT(pm25) OVER w >= 16 THEN AVG(pm25) OVER w END AS pm25_24h,
    CASE WHEN COUNT(pm10) OVER w >= 16 THEN AVG(pm10) OVER w END AS pm10_24h
FROM v_hourly AS h
WINDOW w AS (PARTITION BY station_id, source ORDER BY hour_idx RANGE BETWEEN 23 PRECEDING AND CURRENT ROW);

-- CPCB AQI = the larger of the PM2.5 and PM10 sub-indices, rounded half up, capped at 500.
CREATE TEMP VIEW v_aqi AS
WITH sub AS (
    SELECT
        r.*,
        CASE WHEN r.pm25_24h IS NULL THEN NULL
             ELSE COALESCE(b25.i_lo + (b25.i_hi - b25.i_lo) * (r.pm25_24h - b25.c_lo) / (b25.c_hi - b25.c_lo), 500.0)
        END AS si_pm25,
        CASE WHEN r.pm10_24h IS NULL THEN NULL
             ELSE COALESCE(b10.i_lo + (b10.i_hi - b10.i_lo) * (r.pm10_24h - b10.c_lo) / (b10.c_hi - b10.c_lo), 500.0)
        END AS si_pm10
    FROM v_roll AS r
    LEFT JOIN v_bands AS b25 ON b25.pollutant = 'pm25' AND r.pm25_24h >= b25.c_lo AND r.pm25_24h < b25.c_hi
    LEFT JOIN v_bands AS b10 ON b10.pollutant = 'pm10' AND r.pm10_24h >= b10.c_lo AND r.pm10_24h < b10.c_hi
),
worst AS (
    SELECT
        sub.*,
        CASE WHEN si_pm25 IS NULL THEN si_pm10
             WHEN si_pm10 IS NULL THEN si_pm25
             WHEN si_pm25 >= si_pm10 THEN si_pm25
             ELSE si_pm10 END AS worst_si
    FROM sub
)
SELECT
    worst.*,
    CASE WHEN worst_si IS NULL THEN NULL
         WHEN worst_si + 0.5 >= 500 THEN 500
         ELSE CAST(worst_si + 0.5 AS INTEGER) END AS aqi,
    CASE
        WHEN worst_si IS NULL THEN NULL
        WHEN CAST(worst_si + 0.5 AS INTEGER) <= 50  THEN 'Good'
        WHEN CAST(worst_si + 0.5 AS INTEGER) <= 100 THEN 'Satisfactory'
        WHEN CAST(worst_si + 0.5 AS INTEGER) <= 200 THEN 'Moderate'
        WHEN CAST(worst_si + 0.5 AS INTEGER) <= 300 THEN 'Poor'
        WHEN CAST(worst_si + 0.5 AS INTEGER) <= 400 THEN 'Very Poor'
        ELSE 'Severe'
    END AS category
FROM worst;
