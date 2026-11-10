# SQL query results

Output of all 15 queries on `data/aqi.db` (data up to 10 Nov 2026, 08:00 IST), generated with `python sql/run.py --markdown`. Numbers change as new data arrives. Q15 compares raw hourly PM2.5 on Diwali night with the same clock hours on the 7 nights before (6 nights had enough data; 2 Nov is skipped for a data gap).

### Q01  Data coverage and quality per station

| station | area | rows_stored | first_day | last_day | hours_in_span | pct_hours_present | pct_pm25_filled | pct_pm10_filled | pct_valid_aqi |
|---|---|---|---|---|---|---|---|---|---|
| Lodhi Road, Delhi - IITM | Delhi | 176 | 2026-10-12 | 2026-10-30 | 441 | 39.9 | 100 | 0 | 79.5 |
| Vikas Sadan, Gurugram - HSPCB | Gurugram | 1866 | 2026-08-02 | 2026-11-10 | 2396 | 77.9 | 99.1 | 99.9 | 84.6 |
| Sector-1, Noida - UPPCB | Noida | 1924 | 2026-08-02 | 2026-11-10 | 2396 | 80.3 | 100 | 0 | 87.1 |
| Jahangirpuri, Delhi - DPCC | Delhi | 1922 | 2026-08-02 | 2026-11-10 | 2396 | 80.2 | 100 | 0 | 88.2 |
| Jawaharlal Nehru Stadium, Delhi - DPCC | Delhi | 2005 | 2026-08-02 | 2026-11-10 | 2396 | 83.7 | 100 | 0 | 88.6 |
| New Industrial Town, Faridabad - HSPCB | Faridabad | 1917 | 2026-08-02 | 2026-11-10 | 2396 | 80 | 100 | 99 | 89.2 |
| IGI Airport (T3), Delhi - IMD | Delhi | 1886 | 2026-08-02 | 2026-11-10 | 2396 | 78.7 | 99.3 | 99.2 | 89.5 |
| Wazirpur, Delhi - DPCC | Delhi | 2052 | 2026-08-02 | 2026-11-10 | 2396 | 85.6 | 100 | 0 | 90.1 |
| Patparganj, Delhi - DPCC | Delhi | 2026 | 2026-08-02 | 2026-11-10 | 2396 | 84.6 | 97.8 | 99.2 | 90.2 |
| ITO, New Delhi - CPCB | Delhi | 1614 | 2026-08-01 | 2026-10-30 | 2159 | 74.8 | 100 | 0 | 90.5 |
| Sector 30, Faridabad - HSPCB | Faridabad | 1998 | 2026-08-02 | 2026-11-10 | 2396 | 83.4 | 98.6 | 99.5 | 91.3 |
| Pusa, Delhi - IMD | Delhi | 2082 | 2026-08-02 | 2026-11-10 | 2396 | 86.9 | 98.3 | 99.4 | 91.4 |
| IHBAS, Dilshad Garden,New Delhi - CPCB | Delhi | 2101 | 2026-08-02 | 2026-11-10 | 2396 | 87.7 | 99.7 | 98.7 | 92 |
| Sector-51, Gurugram - HSPCB | Gurugram | 2083 | 2026-08-02 | 2026-11-10 | 2395 | 87 | 100 | 0 | 92 |
| Mandir Marg, New Delhi - DPCC | Delhi | 1863 | 2026-08-01 | 2026-10-30 | 2159 | 86.3 | 91.7 | 99.5 | 92.1 |

### Q02  Monthly pollution trend with month-over-month change

| month | days_covered | stations | station_hours | mean_aqi | change_vs_prev_month | pct_poor_or_worse |
|---|---|---|---|---|---|---|
| 2026-08 | 30 | 29 | 15865 | 78 |  | 0.6 |
| 2026-09 | 30 | 29 | 18705 | 91 | 14 | 3.3 |
| 2026-10 | 31 | 30 | 15007 | 162 | 71 | 26.9 |
| 2026-11 | 10 | 25 | 4546 | 359 | 197 | 93.8 |

### Q03  Station leaderboard with rank and quartile

| rank_most_polluted | station | area | station_hours | mean_aqi | peak_aqi | vs_network_avg | quartile |
|---|---|---|---|---|---|---|---|
| 1 | Jahangirpuri, Delhi - DPCC | Delhi | 1696 | 162 | 500 | 33 | Q1 |
| 2 | Sonia Vihar, Delhi - DPCC | Delhi | 1954 | 159 | 500 | 29 | Q1 |
| 3 | Sector - 125, Noida, UP - UPPCB | Noida | 1918 | 157 | 446 | 27 | Q1 |
| 4 | Patparganj, Delhi - DPCC | Delhi | 1827 | 155 | 496 | 26 | Q1 |
| 5 | Sirifort, Delhi - CPCB | Delhi | 2033 | 155 | 458 | 26 | Q1 |
| 6 | Pusa, Delhi - DPCC | Delhi | 1985 | 152 | 448 | 23 | Q1 |
| 7 | Vikas Sadan, Gurugram - HSPCB | Gurugram | 1578 | 150 | 452 | 21 | Q1 |
| 8 | Sector - 62, Noida, UP - IMD | Noida | 2043 | 148 | 500 | 19 | Q1 |
| 9 | Rohini, Delhi - DPCC | Delhi | 2038 | 145 | 500 | 16 | Q2 |
| 10 | Pusa, Delhi - IMD | Delhi | 1903 | 142 | 451 | 13 | Q2 |
| 11 | Sector-51, Gurugram - HSPCB | Gurugram | 1917 | 141 | 412 | 12 | Q2 |
| 12 | IGI Airport (T3), Delhi - IMD | Delhi | 1688 | 140 | 452 | 10 | Q2 |
| 13 | New Industrial Town, Faridabad - HSPCB | Faridabad | 1710 | 131 | 434 | 2 | Q2 |
| 14 | DTU, New Delhi - CPCB | Delhi | 2040 | 131 | 492 | 2 | Q2 |
| 15 | Ashok Vihar, Delhi - DPCC | Delhi | 2017 | 130 | 484 | 1 | Q2 |

### Q04  Sub-region comparison including an all-NCR total row

| area | stations | station_hours | mean_aqi | peak_aqi | pct_poor_or_worse | pct_good_or_satisfactory |
|---|---|---|---|---|---|---|
| Gurugram | 2 | 3495 | 145 | 452 | 25.2 | 48.6 |
| Noida | 3 | 5636 | 140 | 500 | 20.3 | 46.4 |
| Delhi | 22 | 39472 | 128 | 500 | 16.2 | 54.2 |
| Faridabad | 2 | 3534 | 123 | 483 | 8 | 44.7 |
| Bahadurgarh | 1 | 1986 | 111 | 459 | 15.7 | 67.9 |
| All NCR | 30 | 54123 | 130 | 500 | 16.7 | 52.9 |

### Q05  Time-of-day profile of PM2.5 (raw hourly concentrations)

| hour_ist | readings | mean_pm25_ugm3 | index_vs_daily_mean | flag |
|---|---|---|---|---|
| 00:00 | 2339 | 75.6 | 117 |  |
| 01:00 | 2394 | 73.2 | 113 |  |
| 02:00 | 2350 | 72.3 | 112 |  |
| 03:00 | 2412 | 70 | 109 |  |
| 04:00 | 2422 | 68.1 | 106 |  |
| 05:00 | 2449 | 66 | 102 |  |
| 06:00 | 2489 | 66.5 | 103 |  |
| 07:00 | 2470 | 69.3 | 108 |  |
| 08:00 | 2500 | 72.5 | 112 |  |
| 09:00 | 2527 | 70.4 | 109 |  |
| 10:00 | 2519 | 66 | 102 |  |
| 11:00 | 2488 | 60.4 | 94 |  |
| 12:00 | 2522 | 55.7 | 86 |  |
| 13:00 | 2509 | 51.7 | 80 |  |
| 14:00 | 2450 | 49.3 | 77 | cleanest |
| 15:00 | 2422 | 48.7 | 76 | cleanest |
| 16:00 | 2410 | 48.8 | 76 | cleanest |
| 17:00 | 2441 | 49.4 | 77 |  |
| 18:00 | 2406 | 52.9 | 82 |  |
| 19:00 | 2422 | 60.4 | 94 |  |
| 20:00 | 2313 | 69.8 | 108 |  |
| 21:00 | 2264 | 76.1 | 118 | peak |
| 22:00 | 2208 | 78.3 | 121 | peak |
| 23:00 | 2441 | 76.1 | 118 | peak |

### Q06  Daily city AQI with 7-day moving average and day-over-day change

| day | stations | city_aqi | moving_avg_7d | change_vs_prev_day | flag |
|---|---|---|---|---|---|
| 2026-11-10 | 25 | 352 | 386 | -61 |  |
| 2026-11-09 | 24 | 413 | 384 | 16 |  |
| 2026-11-08 | 25 | 397 | 371 | 16 |  |
| 2026-11-07 | 25 | 381 | 350 | -18 |  |
| 2026-11-06 | 25 | 398 | 311 | 23 |  |
| 2026-11-05 | 25 | 376 | 266 | -13 |  |
| 2026-11-04 | 24 | 388 | 246 | 55 |  |
| 2026-11-03 | 24 | 333 | 226 | 12 |  |
| 2026-11-02 | 24 | 321 | 210 | 70 |  |
| 2026-11-01 | 25 | 251 | 191 | 140 | big swing |
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

### Q07  Five worst and five cleanest days

| kind | rank_no | day | stations | city_aqi | worst_station_hour |
|---|---|---|---|---|---|
| worst | 1 | 2026-11-09 | 24 | 413 | 500 |
| worst | 2 | 2026-11-06 | 25 | 398 | 500 |
| worst | 3 | 2026-11-08 | 25 | 397 | 500 |
| worst | 4 | 2026-11-04 | 24 | 388 | 485 |
| worst | 5 | 2026-11-07 | 25 | 381 | 483 |
| cleanest | 1 | 2026-09-27 | 25 | 44 | 262 |
| cleanest | 2 | 2026-09-06 | 27 | 45 | 111 |
| cleanest | 3 | 2026-08-07 | 29 | 46 | 100 |
| cleanest | 4 | 2026-09-28 | 26 | 46 | 302 |
| cleanest | 5 | 2026-09-05 | 27 | 48 | 244 |

### Q08  Longest runs of consecutive "Poor or worse" days (gaps and islands)

| episode_start | episode_end | days_in_a_row | mean_city_aqi | peak_day_aqi |
|---|---|---|---|---|
| 2026-11-01 | 2026-11-10 | 10 | 361 | 413 |
| 2026-10-27 | 2026-10-29 | 3 | 234 | 243 |
| 2026-10-21 | 2026-10-23 | 3 | 256 | 262 |
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
| hotter than city | 1 | Sonia Vihar, Delhi - DPCC | Delhi | 1951 | 26.9 |
| hotter than city | 2 | Sirifort, Delhi - CPCB | Delhi | 2019 | 25.3 |
| hotter than city | 3 | Sector - 125, Noida, UP - UPPCB | Noida | 1915 | 24.5 |
| hotter than city | 4 | Jahangirpuri, Delhi - DPCC | Delhi | 1694 | 22.8 |
| hotter than city | 5 | Pusa, Delhi - DPCC | Delhi | 1969 | 18.2 |
| cleaner than city | 1 | Shadipur, Delhi - CPCB | Delhi | 1764 | -42.5 |
| cleaner than city | 2 | Sector-1, Noida - UPPCB | Noida | 1673 | -33.6 |
| cleaner than city | 3 | Nehru Nagar, Delhi - DPCC | Delhi | 2023 | -24.5 |
| cleaner than city | 4 | ITO, New Delhi - CPCB | Delhi | 1446 | -22.1 |
| cleaner than city | 5 | IHBAS, Dilshad Garden,New Delhi - CPCB | Delhi | 1933 | -21.6 |

### Q11  How strongly do PM2.5 and NO2 move together?

| area | paired_hours | mean_pm25 | mean_no2 | r_squared | direction |
|---|---|---|---|---|---|
| Bahadurgarh | 2115 | 60.7 | 36.8 | 0.034 | negative |
| Noida | 3804 | 68.5 | 40.8 | 0.031 | positive |
| Delhi | 21573 | 63.2 | 74.7 | 0.029 | positive |
| Faridabad | 3876 | 45.9 | 47 | 0.002 | negative |
| Gurugram | 2069 | 73.4 | 54.8 | 0 | positive |
| All NCR | 33437 | 62.3 | 64 | 0.021 | positive |

### Q12  Days above the CPCB 24-hour PM2.5 standard (60 ug/m3) per station

| rank_no | station | area | valid_days | days_above_60 | pct_days_above_60 | mean_daily_pm25 | worst_day_pm25 |
|---|---|---|---|---|---|---|---|
| 1 | Jahangirpuri, Delhi - DPCC | Delhi | 80 | 43 | 54 | 91.2 | 393.8 |
| 2 | Sonia Vihar, Delhi - DPCC | Delhi | 85 | 45 | 53 | 80.2 | 441.6 |
| 3 | Vikas Sadan, Gurugram - HSPCB | Gurugram | 75 | 36 | 48 | 75.9 | 279.2 |
| 4 | Sector-51, Gurugram - HSPCB | Gurugram | 85 | 38 | 45 | 72.6 | 225.3 |
| 5 | Sector - 62, Noida, UP - IMD | Noida | 90 | 39 | 43 | 77.9 | 393.5 |
| 6 | Pusa, Delhi - IMD | Delhi | 86 | 37 | 43 | 73.2 | 315.5 |
| 7 | Rohini, Delhi - DPCC | Delhi | 89 | 38 | 43 | 82.9 | 353.6 |
| 8 | Sector - 125, Noida, UP - UPPCB | Noida | 83 | 35 | 42 | 61.5 | 236.1 |
| 9 | Sirifort, Delhi - CPCB | Delhi | 88 | 37 | 42 | 76.6 | 317.8 |
| 10 | DTU, New Delhi - CPCB | Delhi | 90 | 37 | 41 | 74.6 | 360.1 |
| 11 | Wazirpur, Delhi - DPCC | Delhi | 82 | 33 | 40 | 69.6 | 334.1 |
| 12 | Jawaharlal Nehru Stadium, Delhi - DPCC | Delhi | 81 | 30 | 37 | 70.1 | 319.9 |
| 13 | Sector-1, Noida - UPPCB | Noida | 76 | 26 | 34 | 57.1 | 272.8 |
| 14 | Mundka, Delhi - DPCC | Delhi | 88 | 30 | 34 | 68.9 | 312.4 |
| 15 | Ashok Vihar, Delhi - DPCC | Delhi | 86 | 29 | 34 | 59.5 | 188 |

### Q13  PM2.5 by time of day and area (pivot table)

| area | night_00_05 | morning_06_11 | afternoon_12_17 | evening_18_23 | all_day | readings |
|---|---|---|---|---|---|---|
| Gurugram | 71.7 | 74.6 | 66.5 | 81.7 | 73.5 | 3932 |
| Noida | 73.6 | 65.4 | 48.9 | 74 | 65.3 | 6116 |
| Delhi | 72.5 | 69.7 | 50.2 | 68.7 | 65.2 | 42113 |
| Bahadurgarh | 66.7 | 63.6 | 50.3 | 62.6 | 60.7 | 2118 |
| Faridabad | 48.9 | 42.5 | 42.6 | 50.7 | 46.1 | 3888 |

### Q14  Weekday vs weekend city AQI

| day_type | days | mean_city_aqi | lowest_day | highest_day |
|---|---|---|---|---|
| Weekend | 25 | 126 | 44 | 397 |
| Weekday | 70 | 140 | 46 | 413 |

### Q15  Diwali 2026 benchmark: festival night vs the same clock hours on the 7 nights before

| period | nights_used | mean_city_pm25 | peak_city_hour_pm25 | peak_station_pm25 |
|---|---|---|---|---|
| same hours, 7 nights before | 6 | 232.0 | 340 | 718 |
| Diwali night | 1 | 356.0 | 578 | 993 |
