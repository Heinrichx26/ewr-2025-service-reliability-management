# EWR hourly schedule-pressure analysis

Months: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12.
Hours: 06:00 through 22:59 local scheduled time.
Benchmark targets: 28 operations per hour for stress/interim construction windows and 34 operations per hour for the operating-limit period.

| period          | side       |   hours |   avg_ops_per_hour |   p90_ops_per_hour |   p95_ops_per_hour |   max_ops_per_hour |   share_above_28 |   share_above_34 |   share_above_period_target |
|:----------------|:-----------|--------:|-------------------:|-------------------:|-------------------:|-------------------:|-----------------:|-----------------:|----------------------------:|
| Stress          | Arrivals   |     595 |              15.48 |              19.00 |              21.00 |                 25 |             0.00 |             0.00 |                        0.00 |
| Stress          | Departures |     595 |              17.24 |              25.00 |              28.00 |                 32 |             2.69 |             0.00 |                        2.69 |
| Interim order   | Arrivals   |     459 |              14.27 |              19.00 |              21.00 |                 25 |             0.00 |             0.00 |                        0.00 |
| Interim order   | Departures |     459 |              15.74 |              22.00 |              23.00 |                 26 |             0.00 |             0.00 |                        0.00 |
| Operating limit | Arrivals   |    2244 |              17.55 |              22.00 |              23.00 |                 27 |             0.00 |             0.00 |                        0.00 |
| Operating limit | Departures |    2244 |              19.35 |              26.00 |              31.00 |                 34 |             5.66 |             0.00 |                        0.00 |
