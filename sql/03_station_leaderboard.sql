-- Q03  Station leaderboard with rank and quartile
-- Question : Which stations are consistently the most polluted, and how far from the network average?
-- Techniques: GROUP BY + HAVING, RANK(), NTILE(), window aggregate over the whole result
WITH per_station AS (
    SELECT station, area, COUNT(*) AS station_hours, AVG(aqi) AS mean_aqi, MAX(aqi) AS peak_aqi
    FROM v_aqi
    WHERE aqi IS NOT NULL
    GROUP BY station_id, station, area
    HAVING COUNT(*) >= 500            -- ignore stations with too little history
)
SELECT
    RANK() OVER (ORDER BY mean_aqi DESC)                 AS rank_most_polluted,
    station,
    area,
    station_hours,
    ROUND(mean_aqi, 0)                                   AS mean_aqi,
    peak_aqi,
    ROUND(mean_aqi - AVG(mean_aqi) OVER (), 0)           AS vs_network_avg,
    'Q' || NTILE(4) OVER (ORDER BY mean_aqi DESC)        AS quartile      -- Q1 = most polluted 25%
FROM per_station
ORDER BY rank_most_polluted
LIMIT 15;
