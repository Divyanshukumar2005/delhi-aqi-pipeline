# SQL analytics

Fifteen analytical queries that run directly on the project's SQLite database (`data/aqi.db`). They answer the kind of questions a data analyst gets asked: trends, rankings, comparisons, outliers and data-quality checks. Every query is a single, commented `SELECT` with a business question at the top.

## Run them

```bash
python sql/run.py                         # run all 15 queries and print the results
python sql/run.py --only 3 6 8            # run selected queries
python sql/run.py --markdown --only 3     # print as Markdown tables
python sql/run.py --csv-dir results/      # also save every result as CSV
```

`run.py` uses only the Python standard library and opens the database **read-only**, so `data/aqi.db` can never be changed by it. You can also use the `sqlite3` shell:

```bash
sqlite3 -header -column data/aqi.db ".read sql/00_setup.sql" ".read sql/03_station_leaderboard.sql"
```

Requires SQLite 3.25 or newer (window functions). Developed and tested on SQLite 3.45.

## The shared views (`00_setup.sql`)

The queries build on four TEMP views (in memory only, never saved to the database file):

| View | What it adds |
|---|---|
| `v_bands` | The CPCB breakpoint table for PM2.5 and PM10 |
| `v_hourly` | One row per station-hour, with sub-region, IST day, month and hour of day |
| `v_roll` | Rolling 24-hour PM2.5 and PM10 means (a mean needs at least 16 valid hours, as CPCB requires) |
| `v_aqi` | CPCB sub-indices, the overall AQI (the larger sub-index, rounded half up, capped at 500) and its category |

**The AQI maths is re-implemented in SQL, and checked against the Python version.** `tests/test_sql.py` compares the two row by row, and on the real database 49,911 of 49,924 values are identical; the other 13 differ by 1 point because of floating-point rounding, and none changes a category. The rolling window uses `RANGE BETWEEN 23 PRECEDING AND CURRENT ROW` over an absolute hour number, so a missing hour shortens the window instead of silently pulling in older data.

## The queries

| # | File | Question it answers | SQL techniques |
|---|---|---|---|
| 01 | `01_data_coverage.sql` | Which stations can I trust? How complete is each history? | `GROUP BY`, conditional aggregation, `julianday()` |
| 02 | `02_monthly_trend.sql` | Is air quality getting worse as winter approaches? | CTE, `LAG()` |
| 03 | `03_station_leaderboard.sql` | Which stations are consistently the most polluted? | `RANK()`, `NTILE()`, window average, `HAVING` |
| 04 | `04_area_comparison.sql` | How do the five sub-regions compare? | CTEs, `UNION ALL` total row |
| 05 | `05_hourly_profile.sql` | At what hour is PM2.5 worst and cleanest? | `RANK()` twice, window `AVG()` index |
| 06 | `06_daily_city_trend.sql` | What is the daily trend and which days jumped? | `RANGE` moving average, `LAG()` |
| 07 | `07_worst_and_best_days.sql` | Which days stand out at both extremes? | `ROW_NUMBER()` both directions |
| 08 | `08_pollution_streaks.sql` | How long do severe episodes last? | Gaps and islands with `ROW_NUMBER()` |
| 09 | `09_reporting_gaps.sql` | When did monitors go silent, and did many stop at once? | `LAG()`, `COUNT() OVER` |
| 10 | `10_hotspots_vs_city.sql` | Which stations run hotter than the city at the same hour? | Join to an hourly city average, `RANK()` |
| 11 | `11_pm25_no2_relationship.sql` | Do fine particles and NO₂ move together? | Correlation from aggregates (no `CORR()`) |
| 12 | `12_pm25_standard_exceedance.sql` | How many days breach the 60 µg/m³ standard? | Two-level CTE, `RANK()` |
| 13 | `13_time_of_day_by_area.sql` | Does every sub-region peak at the same time? | Pivot with conditional aggregation |
| 14 | `14_weekday_vs_weekend.sql` | Is pollution different on weekends? | `strftime('%w')`, `GROUP BY` |
| 15 | `15_diwali_benchmark.sql` | How does air quality change around Diwali? | Parameter CTE, date arithmetic |

## Selected results

Run on the data up to 1 Nov 2026, 13:00 IST. The numbers change as new data arrives.

**Q02  Monthly pollution trend with month-over-month change**

| month | days_covered | stations | station_hours | mean_aqi | change_vs_prev_month | pct_poor_or_worse |
|---|---|---|---|---|---|---|
| 2026-08 | 30 | 29 | 15865 | 78 |  | 0.6 |
| 2026-09 | 30 | 29 | 18705 | 91 | 14 | 3.3 |
| 2026-10 | 31 | 30 | 15007 | 162 | 71 | 26.9 |
| 2026-11 | 1 | 25 | 347 | 230 | 68 | 62.5 |

**Q04  Sub-region comparison including an all-NCR total row**

| area | stations | station_hours | mean_aqi | peak_aqi | pct_poor_or_worse | pct_good_or_satisfactory |
|---|---|---|---|---|---|---|
| Gurugram | 2 | 3154 | 128 | 452 | 18.1 | 53.8 |
| Noida | 3 | 5123 | 118 | 446 | 12.4 | 51.1 |
| Faridabad | 2 | 3206 | 108 | 296 | 1.8 | 47.9 |
| Delhi | 22 | 36600 | 107 | 379 | 9.7 | 58.4 |
| Bahadurgarh | 1 | 1841 | 92 | 316 | 9 | 73.3 |
| All NCR | 30 | 49924 | 109 | 452 | 10 | 57.3 |

**Q08  Longest runs of consecutive "Poor or worse" days (gaps and islands)**

| episode_start | episode_end | days_in_a_row | mean_city_aqi | peak_day_aqi |
|---|---|---|---|---|
| 2026-10-27 | 2026-10-29 | 3 | 234 | 243 |
| 2026-10-21 | 2026-10-23 | 3 | 256 | 262 |
| 2026-11-01 | 2026-11-01 | 1 | 230 | 230 |
| 2026-10-18 | 2026-10-18 | 1 | 211 | 211 |

**Q09  Longest reporting gaps (monitor outages)**

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

**Q10  Hotspots: stations that run hotter or cleaner than the city at the same hour**

| kind | rank_no | station | area | hours_compared | avg_gap_to_city |
|---|---|---|---|---|---|
| hotter than city | 1 | Sector - 125, Noida, UP - UPPCB | Noida | 1753 | 31.4 |
| hotter than city | 2 | Vikas Sadan, Gurugram - HSPCB | Gurugram | 1410 | 26.4 |
| hotter than city | 3 | Sonia Vihar, Delhi - DPCC | Delhi | 1793 | 25.1 |
| hotter than city | 4 | Sirifort, Delhi - CPCB | Delhi | 1846 | 24.7 |
| hotter than city | 5 | Pusa, Delhi - DPCC | Delhi | 1795 | 19 |
| cleaner than city | 1 | Shadipur, Delhi - CPCB | Delhi | 1764 | -42.5 |
| cleaner than city | 2 | Sector-1, Noida - UPPCB | Noida | 1499 | -30.4 |
| cleaner than city | 3 | Nehru Nagar, Delhi - DPCC | Delhi | 1855 | -25.8 |
| cleaner than city | 4 | ITO, New Delhi - CPCB | Delhi | 1446 | -22.1 |
| cleaner than city | 5 | IHBAS, Dilshad Garden,New Delhi - CPCB | Delhi | 1760 | -18.2 |

**Q14  Weekday vs weekend city AQI**

| day_type | days | mean_city_aqi | lowest_day | highest_day |
|---|---|---|---|---|
| Weekend | 23 | 102 | 44 | 230 |
| Weekday | 63 | 115 | 46 | 262 |

## What the queries found

- **A worsening season:** mean AQI went from 78 (August) to 91 (September) to 162 (October), and the share of Poor-or-worse station-hours went from 0.6% to 26.9% (Q02).
- **Sub-regions:** Gurugram had the highest average (128) and Bahadurgarh the lowest (92). Faridabad had the smallest share of Poor-or-worse hours (1.8%). Gurugram and Faridabad each have only two stations, so treat their rows as indicative (Q04).
- **A shared outage:** 28 stations stopped reporting at the same time, from 23 Oct 20:00 to 27 Oct 08:00 IST (83 hours). A gap this shared points to a problem in the data feed, not to 28 broken monitors (Q09).
- **Local hotspots:** at the same hour, Sector-125 (Noida) ran about 31 AQI points above the city average, while Shadipur ran about 43 below, so one "Delhi AQI" figure hides large local differences (Q10).
- **Weak link between PM2.5 and NO₂:** r² is only about 0.03 across the region, so the two pollutants do not track each other closely (Q11).
- **Weekday vs weekend:** weekends averaged 102 and weekdays 115, but only 23 weekend days are available, so this is descriptive, not a proven effect (Q14).

## Testing

`tests/test_sql.py` (24 tests, offline, synthetic data) checks that every query runs and returns rows, that the SQL AQI matches `src/analysis.py`, that CPCB's worked example (PM2.5 of 45 µg/m³ gives AQI 75) holds, that the 16-hour rule and the 500 cap hold, and that `run.py` cannot write to the database.
