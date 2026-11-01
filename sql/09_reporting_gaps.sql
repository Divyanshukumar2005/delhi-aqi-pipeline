-- Q09  Longest reporting gaps (monitor outages)
-- Question : When did monitors stop reporting, and for how long? Did many stop at once?
-- Techniques: LAG() per partition, hour arithmetic, a second window COUNT() OVER to spot shared outages
-- Reading it: stations_with_same_gap > 1 means several stations went silent over the same stretch,
--             which points to an upstream data-feed problem rather than a single broken monitor.
WITH spaced AS (
    SELECT
        station, area, ts,
        LAG(ts) OVER (PARTITION BY station_id, source ORDER BY hour_idx)                   AS prev_ts,
        hour_idx - LAG(hour_idx) OVER (PARTITION BY station_id, source ORDER BY hour_idx)  AS hours_since_prev
    FROM v_hourly
),
gaps AS (
    SELECT station, area,
           prev_ts AS last_reading_before_gap,
           ts      AS first_reading_after_gap,
           hours_since_prev - 1 AS hours_missing
    FROM spaced
    WHERE hours_since_prev > 6          -- ignore short blips
)
SELECT
    station,
    area,
    last_reading_before_gap,
    first_reading_after_gap,
    hours_missing,
    COUNT(*) OVER (PARTITION BY last_reading_before_gap, first_reading_after_gap) AS stations_with_same_gap
FROM gaps
ORDER BY hours_missing DESC, stations_with_same_gap DESC, station
LIMIT 15;
