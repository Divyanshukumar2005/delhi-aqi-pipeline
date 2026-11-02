# SQL query results

Output of all 15 queries on `data/aqi.db` (data up to 1 Nov 2026, 22:00 IST), generated with `python sql/run.py --markdown`. Numbers change as new data arrives; Q15 (Diwali) needs data from 8 Nov onwards.


### Q01  Data coverage and quality per station

| station | area | rows_stored | first_day | last_day | hours_in_span | pct_hours_present | pct_pm25_filled | pct_pm10_filled | pct_valid_aqi |
|---|---|---|---|---|---|---|---|---|---|
| Lodhi Road, Delhi - IITM | Delhi | 176 | 2026-10-12 | 2026-10-30 | 441 | 39.9 | 100 | 0 | 79.5 |
| Vikas Sadan, Gurugram - HSPCB | Gurugram | 1691 | 2026-08-02 | 2026-11-01 | 2194 | 77.1 | 99 | 99.9 | 83.9 |
| Sector-1, Noida - UPPCB | Noida | 1741 | 2026-08-02 | 2026-11-01 | 2194 | 79.4 | 100 | 0 | 86.6 |
| Jahangirpuri, Delhi - DPCC | Delhi | 1739 | 2026-08-02 | 2026-11-01 | 2194 | 79.3 | 100 | 0 | 87.9 |
| Jawaharlal Nehru Stadium, Delhi - DPCC | Delhi | 1830 | 2026-08-02 | 2026-11-01 | 2194 | 83.4 | 100 | 0 | 88.3 |
| New Industrial Town, Faridabad - HSPCB | Faridabad | 1750 | 2026-08-02 | 2026-11-01 | 2194 | 79.8 | 100 | 99.5 | 89 |
| IGI Airport (T3), Delhi - IMD | Delhi | 1708 | 2026-08-02 | 2026-11-01 | 2194 | 77.8 | 99.2 | 99.4 | 89.3 |
| Patparganj, Delhi - DPCC | Delhi | 1847 | 2026-08-02 | 2026-11-01 | 2194 | 84.2 | 97.6 | 99.2 | 90 |
| Wazirpur, Delhi - DPCC | Delhi | 1874 | 2026-08-02 | 2026-11-01 | 2194 | 85.4 | 100 | 0 | 90 |
| ITO, New Delhi - CPCB | Delhi | 1614 | 2026-08-01 | 2026-10-30 | 2159 | 74.8 | 100 | 0 | 90.5 |
| Sector 30, Faridabad - HSPCB | Faridabad | 1823 | 2026-08-02 | 2026-11-01 | 2194 | 83.1 | 98.6 | 99.8 | 91.3 |
| IHBAS, Dilshad Garden,New Delhi - CPCB | Delhi | 1921 | 2026-08-02 | 2026-11-01 | 2194 | 87.6 | 99.6 | 98.8 | 92 |
| Mandir Marg, New Delhi - DPCC | Delhi | 1863 | 2026-08-01 | 2026-10-30 | 2159 | 86.3 | 91.7 | 99.5 | 92.1 |
| Sector-51, Gurugram - HSPCB | Gurugram | 1903 | 2026-08-02 | 2026-11-01 | 2193 | 86.8 | 100 | 0 | 92.1 |
| Pusa, Delhi - IMD | Delhi | 1913 | 2026-08-02 | 2026-11-01 | 2194 | 87.2 | 98.2 | 99.4 | 92.2 |

### Q02  Monthly pollution trend with month-over-month change

| month | days_covered | stations | station_hours | mean_aqi | change_vs_prev_month | pct_poor_or_worse |
|---|---|---|---|---|---|---|
| 2026-08 | 30 | 29 | 15865 | 78 |  | 0.6 |
| 2026-09 | 30 | 29 | 18705 | 91 | 14 | 3.3 |
| 2026-10 | 31 | 30 | 15007 | 162 | 71 | 26.9 |
| 2026-11 | 1 | 25 | 544 | 247 | 85 | 69.3 |

### Q03  Station leaderboard with rank and quartile

| rank_most_polluted | station | area | station_hours | mean_aqi | peak_aqi | vs_network_avg | quartile |
|---|---|---|---|---|---|---|---|
| 1 | Sector - 125, Noida, UP - UPPCB | Noida | 1762 | 142 | 446 | 32 | Q1 |
| 2 | Sonia Vihar, Delhi - DPCC | Delhi | 1803 | 136 | 345 | 26 | Q1 |
| 3 | Vikas Sadan, Gurugram - HSPCB | Gurugram | 1418 | 135 | 452 | 25 | Q1 |
| 4 | Sirifort, Delhi - CPCB | Delhi | 1868 | 133 | 338 | 23 | Q1 |
| 5 | Pusa, Delhi - DPCC | Delhi | 1817 | 130 | 328 | 20 | Q1 |
| 6 | Patparganj, Delhi - DPCC | Delhi | 1663 | 129 | 338 | 19 | Q1 |
| 7 | Jahangirpuri, Delhi - DPCC | Delhi | 1528 | 129 | 404 | 19 | Q1 |
| 8 | Sector - 62, Noida, UP - IMD | Noida | 1878 | 124 | 367 | 14 | Q1 |
| 9 | Sector-51, Gurugram - HSPCB | Gurugram | 1752 | 123 | 392 | 13 | Q2 |
| 10 | Pusa, Delhi - IMD | Delhi | 1764 | 121 | 364 | 11 | Q2 |
| 11 | North Campus, DU, Delhi - IMD | Delhi | 1809 | 120 | 327 | 10 | Q2 |
| 12 | Rohini, Delhi - DPCC | Delhi | 1874 | 119 | 377 | 9 | Q2 |
| 13 | Mandir Marg, New Delhi - DPCC | Delhi | 1715 | 118 | 340 | 8 | Q2 |
| 14 | New Industrial Town, Faridabad - HSPCB | Faridabad | 1558 | 116 | 239 | 6 | Q2 |
| 15 | IGI Airport (T3), Delhi - IMD | Delhi | 1525 | 116 | 263 | 6 | Q2 |

### Q04  Sub-region comparison including an all-NCR total row

| area | stations | station_hours | mean_aqi | peak_aqi | pct_poor_or_worse | pct_good_or_satisfactory |
|---|---|---|---|---|---|---|
| Gurugram | 2 | 3170 | 128 | 452 | 18.1 | 53.6 |
| Noida | 3 | 5147 | 119 | 446 | 12.8 | 50.8 |
| Delhi | 22 | 36737 | 108 | 404 | 10 | 58.2 |
| Faridabad | 2 | 3222 | 108 | 296 | 1.8 | 47.9 |
| Bahadurgarh | 1 | 1845 | 92 | 316 | 9.2 | 73.1 |
| All NCR | 30 | 50121 | 110 | 452 | 10.2 | 57.1 |

### Q05  Time-of-day profile of PM2.5 (raw hourly concentrations)

| hour_ist | readings | mean_pm25_ugm3 | index_vs_daily_mean | flag |
|---|---|---|---|---|
| 00:00 | 2159 | 60.3 | 116 | peak |
| 01:00 | 2215 | 59.1 | 114 |  |
| 02:00 | 2164 | 56.2 | 109 |  |
| 03:00 | 2222 | 54.5 | 105 |  |
| 04:00 | 2231 | 53.1 | 103 |  |
| 05:00 | 2261 | 52.4 | 101 |  |
| 06:00 | 2297 | 52.2 | 101 |  |
| 07:00 | 2277 | 54.9 | 106 |  |
| 08:00 | 2304 | 56.7 | 109 |  |
| 09:00 | 2330 | 54.3 | 105 |  |
| 10:00 | 2321 | 50.7 | 98 |  |
| 11:00 | 2293 | 47.7 | 92 |  |
| 12:00 | 2330 | 45.7 | 88 |  |
| 13:00 | 2341 | 44.7 | 86 |  |
| 14:00 | 2279 | 42.6 | 82 |  |
| 15:00 | 2249 | 41.9 | 81 | cleanest |
| 16:00 | 2236 | 41.6 | 80 | cleanest |
| 17:00 | 2267 | 41.8 | 81 | cleanest |
| 18:00 | 2233 | 44.3 | 86 |  |
| 19:00 | 2247 | 50.3 | 97 |  |
| 20:00 | 2139 | 56.8 | 110 |  |
| 21:00 | 2089 | 60.7 | 117 | peak |
| 22:00 | 2019 | 60 | 116 | peak |
| 23:00 | 2256 | 60 | 116 |  |

### Q06  Daily city AQI with 7-day moving average and day-over-day change

| day | stations | city_aqi | moving_avg_7d | change_vs_prev_day | flag |
|---|---|---|---|---|---|
| 2026-11-01 | 25 | 247 | 191 | 136 | big swing |
| 2026-10-31 | 25 | 111 | 179 | 30 |  |
| 2026-10-30 | 28 | 81 | 196 | -156 | big swing |
| 2026-10-29 | 28 | 238 | 238 | -6 |  |
| 2026-10-28 | 29 | 243 | 243 | 21 |  |
| 2026-10-27 | 28 | 222 | 247 |  |  |
| 2026-10-23 | 26 | 248 | 207 | -8 |  |
| 2026-10-22 | 27 | 256 | 184 | -6 |  |
| 2026-10-21 | 28 | 262 | 169 | 86 | big swing |
| 2026-10-20 | 28 | 176 | 159 | 42 |  |
| 2026-10-19 | 27 | 134 | 156 | -77 | big swing |
| 2026-10-18 | 28 | 211 | 147 | 52 |  |
| 2026-10-17 | 28 | 160 | 132 | 71 |  |
| 2026-10-16 | 29 | 89 | 126 | -62 |  |
| 2026-10-15 | 29 | 150 | 136 | -46 |  |
| 2026-10-14 | 29 | 197 | 135 | 47 |  |
| 2026-10-13 | 27 | 150 | 125 | 74 |  |
| 2026-10-12 | 26 | 75 | 124 | -29 |  |
| 2026-10-11 | 28 | 104 | 132 | -10 |  |
| 2026-10-10 | 28 | 114 | 141 | -49 |  |

### Q07  Five worst and five cleanest days

| kind | rank_no | day | stations | city_aqi | worst_station_hour |
|---|---|---|---|---|---|
| worst | 1 | 2026-10-21 | 28 | 262 | 367 |
| worst | 2 | 2026-10-22 | 27 | 256 | 365 |
| worst | 3 | 2026-10-23 | 26 | 248 | 331 |
| worst | 4 | 2026-11-01 | 25 | 247 | 404 |
| worst | 5 | 2026-10-28 | 29 | 243 | 349 |
| cleanest | 1 | 2026-09-27 | 25 | 44 | 262 |
| cleanest | 2 | 2026-09-06 | 27 | 45 | 111 |
| cleanest | 3 | 2026-08-07 | 29 | 46 | 100 |
| cleanest | 4 | 2026-09-28 | 26 | 46 | 302 |
| cleanest | 5 | 2026-09-05 | 27 | 48 | 244 |

### Q08  Longest runs of consecutive "Poor or worse" days (gaps and islands)

| episode_start | episode_end | days_in_a_row | mean_city_aqi | peak_day_aqi |
|---|---|---|---|---|
| 2026-10-27 | 2026-10-29 | 3 | 234 | 243 |
| 2026-10-21 | 2026-10-23 | 3 | 256 | 262 |
| 2026-11-01 | 2026-11-01 | 1 | 247 | 247 |
| 2026-10-18 | 2026-10-18 | 1 | 211 | 211 |

### Q09  Longest reporting gaps (monitor outages)

| station | area | last_reading_before_gap | first_reading_after_gap | hours_missing | stations_with_same_gap |
|---|---|---|---|---|---|
| New Delhi | Delhi | 2026-09-24T15:00:00+05:30 | 2026-10-09T12:00:00+05:30 | 356 | 1 |
| ITO, New Delhi - CPCB | Delhi | 2026-10-18T13:00:00+05:30 | 2026-10-27T16:00:00+05:30 | 218 | 1 |
| Lodhi Road, Delhi - IITM | Delhi | 2026-10-12T14:00:00+05:30 | 2026-10-19T12:00:00+05:30 | 165 | 1 |
| IGI Airport (T3), Delhi - IMD | Delhi | 2026-09-11T12:00:00+05:30 | 2026-09-18T09:00:00+05:30 | 164 | 1 |
| ITO, New Delhi - CPCB | Delhi | 2026-08-27T14:00:00+05:30 | 2026-09-01T14:00:00+05:30 | 119 | 1 |
| New Industrial Town, Faridabad - HSPCB | Faridabad | 2026-09-28T15:00:00+05:30 | 2026-10-02T10:00:00+05:30 | 90 | 1 |
| Arya Nagar, Bahadurgarh - HSPCB | Bahadurgarh | 2026-10-23T20:00:00+05:30 | 2026-10-27T08:00:00+05:30 | 83 | 28 |
| Ashok Vihar, Delhi - DPCC | Delhi | 2026-10-23T20:00:00+05:30 | 2026-10-27T08:00:00+05:30 | 83 | 28 |
| DTU, New Delhi - CPCB | Delhi | 2026-10-23T20:00:00+05:30 | 2026-10-27T08:00:00+05:30 | 83 | 28 |
| IGI Airport (T3), Delhi - IMD | Delhi | 2026-10-23T20:00:00+05:30 | 2026-10-27T08:00:00+05:30 | 83 | 28 |
| IHBAS, Dilshad Garden,New Delhi - CPCB | Delhi | 2026-10-23T20:00:00+05:30 | 2026-10-27T08:00:00+05:30 | 83 | 28 |
| Jahangirpuri, Delhi - DPCC | Delhi | 2026-10-23T20:00:00+05:30 | 2026-10-27T08:00:00+05:30 | 83 | 28 |
| Jawaharlal Nehru Stadium, Delhi - DPCC | Delhi | 2026-10-23T20:00:00+05:30 | 2026-10-27T08:00:00+05:30 | 83 | 28 |
| Lodhi Road, Delhi - IITM | Delhi | 2026-10-23T20:00:00+05:30 | 2026-10-27T08:00:00+05:30 | 83 | 28 |
| Mandir Marg, New Delhi - DPCC | Delhi | 2026-10-23T20:00:00+05:30 | 2026-10-27T08:00:00+05:30 | 83 | 28 |

### Q10  Hotspots: stations that run hotter or cleaner than the city at the same hour

| kind | rank_no | station | area | hours_compared | avg_gap_to_city |
|---|---|---|---|---|---|
| hotter than city | 1 | Sector - 125, Noida, UP - UPPCB | Noida | 1761 | 31.1 |
| hotter than city | 2 | Vikas Sadan, Gurugram - HSPCB | Gurugram | 1418 | 25.3 |
| hotter than city | 3 | Sonia Vihar, Delhi - DPCC | Delhi | 1801 | 25.3 |
| hotter than city | 4 | Sirifort, Delhi - CPCB | Delhi | 1854 | 24.8 |
| hotter than city | 5 | Pusa, Delhi - DPCC | Delhi | 1803 | 19.1 |
| cleaner than city | 1 | Shadipur, Delhi - CPCB | Delhi | 1764 | -42.5 |
| cleaner than city | 2 | Sector-1, Noida - UPPCB | Noida | 1507 | -30.5 |
| cleaner than city | 3 | Nehru Nagar, Delhi - DPCC | Delhi | 1863 | -25.8 |
| cleaner than city | 4 | ITO, New Delhi - CPCB | Delhi | 1446 | -22.1 |
| cleaner than city | 5 | IHBAS, Dilshad Garden,New Delhi - CPCB | Delhi | 1768 | -18.6 |

### Q11  How strongly do PM2.5 and NO2 move together?

| area | paired_hours | mean_pm25 | mean_no2 | r_squared | direction |
|---|---|---|---|---|---|
| Noida | 3544 | 55.2 | 41.2 | 0.133 | positive |
| Delhi | 20156 | 51.3 | 73.3 | 0.041 | positive |
| Bahadurgarh | 1945 | 49.5 | 37.5 | 0.022 | negative |
| Faridabad | 3538 | 38.2 | 47.1 | 0.002 | positive |
| Gurugram | 1891 | 64.9 | 54.3 | 0.001 | negative |
| All NCR | 31074 | 51 | 63.3 | 0.032 | positive |

### Q12  Days above the CPCB 24-hour PM2.5 standard (60 ug/m3) per station

| rank_no | station | area | valid_days | days_above_60 | pct_days_above_60 | mean_daily_pm25 | worst_day_pm25 |
|---|---|---|---|---|---|---|---|
| 1 | Jahangirpuri, Delhi - DPCC | Delhi | 73 | 36 | 49 | 67.3 | 249.9 |
| 2 | Sonia Vihar, Delhi - DPCC | Delhi | 78 | 38 | 49 | 61.1 | 180.4 |
| 3 | Vikas Sadan, Gurugram - HSPCB | Gurugram | 68 | 29 | 43 | 70.5 | 279.2 |
| 4 | Sector-51, Gurugram - HSPCB | Gurugram | 79 | 32 | 41 | 65.1 | 212.3 |
| 5 | Sector - 62, Noida, UP - IMD | Noida | 83 | 32 | 39 | 59.8 | 206.9 |
| 6 | Pusa, Delhi - IMD | Delhi | 79 | 30 | 38 | 55.5 | 173 |
| 7 | Rohini, Delhi - DPCC | Delhi | 82 | 31 | 38 | 63.5 | 214 |
| 8 | Sirifort, Delhi - CPCB | Delhi | 81 | 30 | 37 | 60.7 | 170 |
| 9 | Sector - 125, Noida, UP - UPPCB | Noida | 76 | 28 | 37 | 52.7 | 146.9 |
| 10 | DTU, New Delhi - CPCB | Delhi | 83 | 30 | 36 | 54.6 | 139.7 |
| 11 | Wazirpur, Delhi - DPCC | Delhi | 75 | 26 | 35 | 55.7 | 134.5 |
| 12 | Mandir Marg, New Delhi - DPCC | Delhi | 68 | 22 | 32 | 50 | 160.5 |
| 13 | Jawaharlal Nehru Stadium, Delhi - DPCC | Delhi | 74 | 23 | 31 | 53.8 | 160 |
| 14 | North Campus, DU, Delhi - IMD | Delhi | 80 | 23 | 29 | 50.9 | 145.3 |
| 15 | Mundka, Delhi - DPCC | Delhi | 81 | 23 | 28 | 49.8 | 195 |

### Q13  PM2.5 by time of day and area (pivot table)

| area | night_00_05 | morning_06_11 | afternoon_12_17 | evening_18_23 | all_day | readings |
|---|---|---|---|---|---|---|
| Gurugram | 64.5 | 68.4 | 60.6 | 72.7 | 66.5 | 3577 |
| Noida | 57.2 | 52.2 | 42.4 | 59.6 | 52.7 | 5582 |
| Delhi | 56.4 | 53 | 42.2 | 54.7 | 51.5 | 39106 |
| Bahadurgarh | 55.4 | 51.7 | 42.3 | 48.6 | 49.5 | 1947 |
| Faridabad | 39.2 | 36.4 | 37.5 | 40.1 | 38.3 | 3547 |

### Q14  Weekday vs weekend city AQI

| day_type | days | mean_city_aqi | lowest_day | highest_day |
|---|---|---|---|---|
| Weekend | 23 | 103 | 44 | 247 |
| Weekday | 63 | 115 | 46 | 262 |

### Q15  Diwali 2026 benchmark: 7 days before vs 7 days from the festival

| period | days_available | mean_city_aqi |
|---|---|---|
| before | 1 | not enough data yet |
| after | 0 | not enough data yet |
