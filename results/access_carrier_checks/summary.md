# Access and carrier-burden checks

Months: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12.
Scope: EWR domestic scheduled flights in BTS On-Time Performance records.

## Route service coverage
| side       | period          |   counterpart_airports |   weekly_service_markets |   daily_service_markets |   avg_daily_active_counterparts |   ops_per_day |
|:-----------|:----------------|-----------------------:|-------------------------:|------------------------:|--------------------------------:|--------------:|
| Arrivals   | Baseline        |                     76 |                       72 |                      57 |                           64.81 |        334.36 |
| Arrivals   | Stress          |                     70 |                       68 |                      59 |                           63.29 |        304.46 |
| Arrivals   | Interim order   |                     75 |                       75 |                      60 |                           68.15 |        276.26 |
| Arrivals   | Operating limit |                     80 |                       74 |                      61 |                           66.31 |        335.00 |
| Arrivals   | Extension       |                     76 |                       74 |                      60 |                           63.79 |        346.81 |
| Departures | Baseline        |                     75 |                       71 |                      58 |                           64.30 |        334.34 |
| Departures | Stress          |                     69 |                       67 |                      58 |                           62.20 |        304.66 |
| Departures | Interim order   |                     75 |                       74 |                      60 |                           67.56 |        276.19 |
| Departures | Operating limit |                     81 |                       74 |                      61 |                           66.54 |        335.04 |
| Departures | Extension       |                     76 |                       74 |                      59 |                           63.36 |        345.82 |

## Stress-to-interim market retention
| side       | threshold   |   stress_markets |   retained_markets | retention_rate_text   |   mean_ops_per_day_change |   median_ops_per_day_change |
|:-----------|:------------|-----------------:|-------------------:|:----------------------|--------------------------:|----------------------------:|
| Arrivals   | weekly      |               68 |                 67 | 98.5%                 |                     -0.47 |                       -0.08 |
| Arrivals   | daily       |               59 |                 55 | 93.2%                 |                     -0.60 |                       -0.23 |
| Departures | weekly      |               67 |                 66 | 98.5%                 |                     -0.49 |                       -0.08 |
| Departures | daily       |               58 |                 56 | 96.6%                 |                     -0.61 |                       -0.22 |

## United versus other carriers
| carrier_group   | side       |   delta_ops_per_day |   delta_cancel_rate |   delta_delay15_rate |   delta_nas_delay_per_scheduled_op |   delta_counterpart_airports |
|:----------------|:-----------|--------------------:|--------------------:|---------------------:|-----------------------------------:|-----------------------------:|
| Other carriers  | Arrivals   |              4.0381 |             -0.0783 |              -0.2282 |                           -30.5435 |                       5.0000 |
| Other carriers  | Departures |              4.1608 |             -0.0805 |              -0.1479 |                            -7.4445 |                       6.0000 |
| United          | Arrivals   |            -32.2360 |             -0.0249 |              -0.2061 |                           -29.9321 |                       2.0000 |
| United          | Departures |            -32.6328 |             -0.0272 |              -0.1371 |                            -0.8071 |                       3.0000 |

## Capacity-reliability trade-off
| side       |   ops_reduction_per_day |   cancelled_ops_reduction_per_day |   delay15_ops_reduction_per_day |   nas_minutes_reduction_per_day |   cancelled_ops_reduction_per_ops_day_reduced |   delay15_ops_reduction_per_ops_day_reduced |   nas_minutes_reduction_per_ops_day_reduced |
|:-----------|------------------------:|----------------------------------:|--------------------------------:|--------------------------------:|----------------------------------------------:|--------------------------------------------:|--------------------------------------------:|
| Arrivals   |                   28.20 |                             14.63 |                           64.80 |                         9463.34 |                                          0.52 |                                        2.30 |                                      335.60 |
| Departures |                   28.47 |                             15.20 |                           42.38 |                         1238.10 |                                          0.53 |                                        1.49 |                                       43.49 |

