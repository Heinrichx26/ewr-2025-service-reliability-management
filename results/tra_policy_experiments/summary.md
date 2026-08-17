# TRA policy experiments

## Synthetic-control post gaps

| treated_airport   | side   | metric                     | metric_label         | unit    |   pre_rmse |   post_mean_gap |   post_abs_mean_gap |   post_days |   observed_stress_mean |   observed_interim_mean |   synthetic_stress_mean |   synthetic_interim_mean |   observed_change |   synthetic_change |   recovery_gap |
|:------------------|:-------|:---------------------------|:---------------------|:--------|-----------:|----------------:|--------------------:|------------:|-----------------------:|------------------------:|------------------------:|-------------------------:|------------------:|-------------------:|---------------:|
| EWR               | arr    | scheduled_ops              | Scheduled operations | ops/day | 34.6064    |    -25.3059     |         25.3059     |          27 |            304.457     |            276.259      |             315.822     |             301.565      |       -28.1979    |       -14.2563     |    -13.9415    |
| EWR               | arr    | cancel_rate                | Cancellation rate    | pp      |  0.035132  |      9.2868e-06 |          0.0049995  |          27 |              0.0507189 |              0.00455918 |               0.0145448 |               0.00454989 |        -0.0461597 |        -0.00999488 |     -0.0361648 |
| EWR               | arr    | delay15_rate               | Delay-15-plus rate   | pp      |  0.138753  |      0.0116398  |          0.13262    |          27 |              0.472901  |              0.25584    |               0.255486  |               0.2442     |        -0.217061  |        -0.0112851  |     -0.205775  |
| EWR               | arr    | nas_delay_per_scheduled_op | NAS delay            | min/op  | 17.2829    |      6.28303    |          9.47149    |          27 |             40.0311    |             10.4535     |               8.46061   |               4.17045    |       -29.5776    |        -4.29016    |    -25.2874    |
| EWR               | dep    | scheduled_ops              | Scheduled operations | ops/day | 34.1895    |    -25.922      |         25.922      |          27 |            304.657     |            276.185      |             315.762     |             302.107      |       -28.472     |       -13.6545     |    -14.8174    |
| EWR               | dep    | cancel_rate                | Cancellation rate    | pp      |  0.0352069 |     -0.00133481 |          0.00507211 |          27 |              0.0520561 |              0.00400966 |               0.0118732 |               0.00534448 |        -0.0480464 |        -0.00652873 |     -0.0415177 |
| EWR               | dep    | delay15_rate               | Delay-15-plus rate   | pp      |  0.0887633 |     -0.0757345  |          0.116558   |          27 |              0.320159  |              0.177368   |               0.227762  |               0.253102   |        -0.142791  |         0.0253407  |     -0.168132  |
| EWR               | dep    | nas_delay_per_scheduled_op | NAS delay            | min/op  |  3.96634   |     -0.091801   |          4.25931    |          27 |              8.86693   |              5.38667    |               5.43135   |               5.47847    |        -3.48026   |         0.0471229  |     -3.52738   |

## T-100 exposure summary

| side   |   apr_seats_per_day |   jun_seats_per_day |   apr_passengers_per_day |   jun_passengers_per_day |   apr_routes |   jun_routes |   seat_retention_apr_to_jun |   passenger_retention_apr_to_jun |   route_retention_apr_to_jun |   jun_passengers_per_departure |
|:-------|--------------------:|--------------------:|-------------------------:|-------------------------:|-------------:|-------------:|----------------------------:|---------------------------------:|-----------------------------:|-------------------------------:|
| arr    |             51584.8 |             48750.2 |                  43065.1 |                  41894.3 |           91 |          101 |                    0.945049 |                         0.972814 |                      1.10989 |                        124.723 |
| dep    |             51508.2 |             48634.6 |                  43500.7 |                  41643.5 |           86 |           94 |                    0.944211 |                         0.957306 |                      1.09302 |                        123.145 |

## Delay-exposure accounting

| side   |   stress_nas_minutes_per_day |   interim_nas_minutes_per_day |   observed_nas_minutes_per_day_reduction |   apr_jun_passengers_per_departure |   passenger_minutes_per_day_reduction |   synthetic_post_gap_nas_min_per_op |
|:-------|-----------------------------:|------------------------------:|-----------------------------------------:|-----------------------------------:|--------------------------------------:|------------------------------------:|
| arr    |                     12360.5  |                       2897.15 |                                  9463.34 |                            122.775 |                           1.16186e+06 |                            6.28303  |
| dep    |                      2729.77 |                       1491.67 |                                  1238.1  |                            120.463 |                      149146           |                           -0.091801 |