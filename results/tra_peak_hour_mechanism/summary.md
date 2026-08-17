# TRA peak-hour mechanism check

Months used: 3, 4, 5, 6.
Airports: 50.
Facilitated hours are 06:00-22:59 local scheduled time.

## EWR facilitated-hour summary

| airport   | side   | period        | hour_group        |   hours |   avg_ops_per_hour |   p90_ops_per_hour |   p95_ops_per_hour |   max_ops_per_hour |   share_above_28 |   share_above_34 |   scheduled_ops |   operated_ops |   cancelled_ops |   delay15_ops |   nas_delay_minutes |   cancel_rate |   delay15_rate |   nas_delay_per_scheduled_op |
|:----------|:-------|:--------------|:------------------|--------:|-------------------:|-------------------:|-------------------:|-------------------:|-----------------:|-----------------:|----------------:|---------------:|----------------:|--------------:|--------------------:|--------------:|---------------:|-----------------------------:|
| EWR       | arr    | early_interim | Facilitated hours |     238 |            14.3739 |            19.0000 |            22.0000 |                 25 |           0.0000 |           0.0000 |            3421 |      3403.0000 |         18.0000 |     1111.0000 |          63091.0000 |        0.0053 |         0.3265 |                      18.4423 |
| EWR       | arr    | late_interim  | Facilitated hours |     221 |            14.1493 |            19.0000 |            20.0000 |                 23 |           0.0000 |           0.0000 |            3127 |      3116.0000 |         11.0000 |      507.0000 |           9618.0000 |        0.0035 |         0.1627 |                       3.0758 |
| EWR       | arr    | reference     | Facilitated hours |     476 |            17.3697 |            23.0000 |            25.0000 |                 27 |           0.0000 |           0.0000 |            8268 |      8201.0000 |         67.0000 |     1563.0000 |          43341.0000 |        0.0081 |         0.1906 |                       5.2420 |
| EWR       | arr    | stress        | Facilitated hours |     595 |            15.4756 |            19.0000 |            21.0000 |                 25 |           0.0000 |           0.0000 |            9208 |      8699.0000 |        509.0000 |     4016.0000 |         394639.0000 |        0.0553 |         0.4617 |                      42.8583 |
| EWR       | dep    | early_interim | Facilitated hours |     238 |            15.9286 |            22.3000 |            24.0000 |                 26 |           0.0000 |           0.0000 |            3791 |      3777.0000 |         14.0000 |      758.0000 |          20339.0000 |        0.0037 |         0.2007 |                       5.3651 |
| EWR       | dep    | late_interim  | Facilitated hours |     221 |            15.5294 |            22.0000 |            23.0000 |                 25 |           0.0000 |           0.0000 |            3432 |      3418.0000 |         14.0000 |      547.0000 |          19683.0000 |        0.0041 |         0.1600 |                       5.7351 |
| EWR       | dep    | reference     | Facilitated hours |     476 |            19.1954 |            26.5000 |            30.0000 |                 34 |           0.0840 |           0.0000 |            9137 |      9072.0000 |         65.0000 |     1638.0000 |          32354.0000 |        0.0071 |         0.1806 |                       3.5410 |
| EWR       | dep    | stress        | Facilitated hours |     595 |            17.2353 |            25.0000 |            28.0000 |                 32 |           0.0269 |           0.0000 |           10255 |      9695.0000 |        560.0000 |     3150.0000 |          94245.0000 |        0.0546 |         0.3249 |                       9.1902 |

## Calendar-date fixed-effect phase estimates

| side   | hour_group        | metric                     | metric_label           | unit   | phase         |    coef |   ci_low |   ci_high |
|:-------|:------------------|:---------------------------|:-----------------------|:-------|:--------------|--------:|---------:|----------:|
| arr    | Facilitated hours | avg_ops_per_hour           | Scheduled ops/hour     | ops    | Stress        | -1.9961 |  -2.4077 |   -1.5845 |
| arr    | Facilitated hours | avg_ops_per_hour           | Scheduled ops/hour     | ops    | May 20--Jun 2 | -3.1785 |  -3.5773 |   -2.7798 |
| arr    | Facilitated hours | avg_ops_per_hour           | Scheduled ops/hour     | ops    | Jun 3--Jun 15 | -3.6006 |  -3.9668 |   -3.2344 |
| arr    | Facilitated hours | p95_ops_per_hour           | P95 scheduled ops/hour | ops    | Stress        | -3.6810 |  -4.6732 |   -2.6888 |
| arr    | Facilitated hours | p95_ops_per_hour           | P95 scheduled ops/hour | ops    | May 20--Jun 2 | -3.2599 |  -4.3025 |   -2.2173 |
| arr    | Facilitated hours | p95_ops_per_hour           | P95 scheduled ops/hour | ops    | Jun 3--Jun 15 | -3.9794 |  -4.9324 |   -3.0264 |
| arr    | Facilitated hours | share_above_28             | Share above 28/hour    | pp     | Stress        | -0.0018 |  -0.0100 |    0.0063 |
| arr    | Facilitated hours | share_above_28             | Share above 28/hour    | pp     | May 20--Jun 2 | -0.0030 |  -0.0138 |    0.0079 |
| arr    | Facilitated hours | share_above_28             | Share above 28/hour    | pp     | Jun 3--Jun 15 | -0.0019 |  -0.0123 |    0.0085 |
| arr    | Facilitated hours | share_above_34             | Share above 34/hour    | pp     | Stress        | -0.0017 |  -0.0061 |    0.0026 |
| arr    | Facilitated hours | share_above_34             | Share above 34/hour    | pp     | May 20--Jun 2 | -0.0028 |  -0.0081 |    0.0024 |
| arr    | Facilitated hours | share_above_34             | Share above 34/hour    | pp     | Jun 3--Jun 15 | -0.0036 |  -0.0093 |    0.0020 |
| arr    | Facilitated hours | delay15_rate               | Delay-15-plus rate     | pp     | Stress        |  0.2658 |   0.1948 |    0.3367 |
| arr    | Facilitated hours | delay15_rate               | Delay-15-plus rate     | pp     | May 20--Jun 2 |  0.1281 |   0.0100 |    0.2461 |
| arr    | Facilitated hours | delay15_rate               | Delay-15-plus rate     | pp     | Jun 3--Jun 15 | -0.0957 |  -0.1465 |   -0.0449 |
| arr    | Facilitated hours | nas_delay_per_scheduled_op | NAS delay              | min/op | Stress        | 36.5229 |  26.3300 |   46.7158 |
| arr    | Facilitated hours | nas_delay_per_scheduled_op | NAS delay              | min/op | May 20--Jun 2 | 13.3183 |   0.9347 |   25.7020 |
| arr    | Facilitated hours | nas_delay_per_scheduled_op | NAS delay              | min/op | Jun 3--Jun 15 | -3.5557 |  -6.8005 |   -0.3109 |
| arr    | Other hours       | avg_ops_per_hour           | Scheduled ops/hour     | ops    | Stress        |  0.4148 |   0.1436 |    0.6860 |
| arr    | Other hours       | avg_ops_per_hour           | Scheduled ops/hour     | ops    | May 20--Jun 2 | -0.5825 |  -0.8831 |   -0.2819 |
| arr    | Other hours       | avg_ops_per_hour           | Scheduled ops/hour     | ops    | Jun 3--Jun 15 | -1.1798 |  -1.4890 |   -0.8706 |
| arr    | Other hours       | p95_ops_per_hour           | P95 scheduled ops/hour | ops    | Stress        |  1.5876 |  -0.0266 |    3.2017 |
| arr    | Other hours       | p95_ops_per_hour           | P95 scheduled ops/hour | ops    | May 20--Jun 2 | -2.9388 |  -4.1051 |   -1.7726 |
| arr    | Other hours       | p95_ops_per_hour           | P95 scheduled ops/hour | ops    | Jun 3--Jun 15 | -4.6868 |  -5.9018 |   -3.4719 |
| arr    | Other hours       | share_above_28             | Share above 28/hour    | pp     | Stress        |  0.0340 |   0.0136 |    0.0544 |
| arr    | Other hours       | share_above_28             | Share above 28/hour    | pp     | May 20--Jun 2 |  0.0023 |   0.0002 |    0.0044 |
| arr    | Other hours       | share_above_28             | Share above 28/hour    | pp     | Jun 3--Jun 15 | -0.0003 |  -0.0036 |    0.0030 |
| arr    | Other hours       | share_above_34             | Share above 34/hour    | pp     | Stress        |  0.0006 |  -0.0009 |    0.0021 |
| arr    | Other hours       | share_above_34             | Share above 34/hour    | pp     | May 20--Jun 2 |  0.0010 |  -0.0008 |    0.0029 |
| arr    | Other hours       | share_above_34             | Share above 34/hour    | pp     | Jun 3--Jun 15 |  0.0017 |   0.0002 |    0.0033 |
| arr    | Other hours       | delay15_rate               | Delay-15-plus rate     | pp     | Stress        |  0.2167 |   0.1452 |    0.2881 |
| arr    | Other hours       | delay15_rate               | Delay-15-plus rate     | pp     | May 20--Jun 2 |  0.0245 |  -0.0722 |    0.1212 |
| arr    | Other hours       | delay15_rate               | Delay-15-plus rate     | pp     | Jun 3--Jun 15 | -0.1216 |  -0.1769 |   -0.0663 |
| arr    | Other hours       | nas_delay_per_scheduled_op | NAS delay              | min/op | Stress        | 19.9384 |  12.6004 |   27.2763 |
| arr    | Other hours       | nas_delay_per_scheduled_op | NAS delay              | min/op | May 20--Jun 2 |  3.5367 |  -3.1845 |   10.2578 |
| arr    | Other hours       | nas_delay_per_scheduled_op | NAS delay              | min/op | Jun 3--Jun 15 | -4.1206 |  -7.0258 |   -1.2154 |
| dep    | Facilitated hours | avg_ops_per_hour           | Scheduled ops/hour     | ops    | Stress        | -1.9696 |  -2.4131 |   -1.5262 |
| dep    | Facilitated hours | avg_ops_per_hour           | Scheduled ops/hour     | ops    | May 20--Jun 2 | -3.3604 |  -3.8129 |   -2.9078 |
| dep    | Facilitated hours | avg_ops_per_hour           | Scheduled ops/hour     | ops    | Jun 3--Jun 15 | -4.0329 |  -4.4971 |   -3.5688 |
| dep    | Facilitated hours | p95_ops_per_hour           | P95 scheduled ops/hour | ops    | Stress        | -2.0505 |  -2.8587 |   -1.2423 |
| dep    | Facilitated hours | p95_ops_per_hour           | P95 scheduled ops/hour | ops    | May 20--Jun 2 | -4.8449 |  -5.7091 |   -3.9807 |
| dep    | Facilitated hours | p95_ops_per_hour           | P95 scheduled ops/hour | ops    | Jun 3--Jun 15 | -5.5167 |  -6.2026 |   -4.8308 |
| dep    | Facilitated hours | share_above_28             | Share above 28/hour    | pp     | Stress        | -0.0558 |  -0.0748 |   -0.0368 |
| dep    | Facilitated hours | share_above_28             | Share above 28/hour    | pp     | May 20--Jun 2 | -0.0793 |  -0.0987 |   -0.0599 |
| dep    | Facilitated hours | share_above_28             | Share above 28/hour    | pp     | Jun 3--Jun 15 | -0.0836 |  -0.1029 |   -0.0643 |
| dep    | Facilitated hours | share_above_34             | Share above 34/hour    | pp     | Stress        |  0.0000 |  -0.0054 |    0.0055 |
| dep    | Facilitated hours | share_above_34             | Share above 34/hour    | pp     | May 20--Jun 2 |  0.0054 |  -0.0004 |    0.0111 |
| dep    | Facilitated hours | share_above_34             | Share above 34/hour    | pp     | Jun 3--Jun 15 | -0.0012 |  -0.0080 |    0.0056 |
| dep    | Facilitated hours | delay15_rate               | Delay-15-plus rate     | pp     | Stress        |  0.1386 |   0.0909 |    0.1862 |
| dep    | Facilitated hours | delay15_rate               | Delay-15-plus rate     | pp     | May 20--Jun 2 |  0.0043 |  -0.0644 |    0.0729 |
| dep    | Facilitated hours | delay15_rate               | Delay-15-plus rate     | pp     | Jun 3--Jun 15 | -0.0899 |  -0.1306 |   -0.0493 |
| dep    | Facilitated hours | nas_delay_per_scheduled_op | NAS delay              | min/op | Stress        |  4.5400 |   2.4283 |    6.6517 |
| dep    | Facilitated hours | nas_delay_per_scheduled_op | NAS delay              | min/op | May 20--Jun 2 |  1.2119 |  -1.2874 |    3.7112 |
| dep    | Facilitated hours | nas_delay_per_scheduled_op | NAS delay              | min/op | Jun 3--Jun 15 |  0.6386 |  -3.1469 |    4.4240 |
| dep    | Other hours       | avg_ops_per_hour           | Scheduled ops/hour     | ops    | Stress        |  0.3925 |   0.2011 |    0.5839 |
| dep    | Other hours       | avg_ops_per_hour           | Scheduled ops/hour     | ops    | May 20--Jun 2 | -0.0883 |  -0.3115 |    0.1349 |
| dep    | Other hours       | avg_ops_per_hour           | Scheduled ops/hour     | ops    | Jun 3--Jun 15 | -0.1900 |  -0.3757 |   -0.0044 |
| dep    | Other hours       | p95_ops_per_hour           | P95 scheduled ops/hour | ops    | Stress        |  1.6810 |   0.7877 |    2.5743 |
| dep    | Other hours       | p95_ops_per_hour           | P95 scheduled ops/hour | ops    | May 20--Jun 2 | -0.7453 |  -1.6878 |    0.1972 |
| dep    | Other hours       | p95_ops_per_hour           | P95 scheduled ops/hour | ops    | Jun 3--Jun 15 | -1.0525 |  -1.8703 |   -0.2348 |
| dep    | Other hours       | share_above_28             | Share above 28/hour    | pp     | Stress        | -0.0000 | nan      |  nan      |
| dep    | Other hours       | share_above_28             | Share above 28/hour    | pp     | May 20--Jun 2 | -0.0000 | nan      |  nan      |
| dep    | Other hours       | share_above_28             | Share above 28/hour    | pp     | Jun 3--Jun 15 | -0.0011 |  -0.0019 |   -0.0003 |
| dep    | Other hours       | share_above_34             | Share above 34/hour    | pp     | Stress        |  0.0000 |   0.0000 |    0.0000 |
| dep    | Other hours       | share_above_34             | Share above 34/hour    | pp     | May 20--Jun 2 |  0.0000 |   0.0000 |    0.0000 |
| dep    | Other hours       | share_above_34             | Share above 34/hour    | pp     | Jun 3--Jun 15 |  0.0000 |   0.0000 |    0.0000 |
| dep    | Other hours       | delay15_rate               | Delay-15-plus rate     | pp     | Stress        |  0.0618 |   0.0165 |    0.1071 |
| dep    | Other hours       | delay15_rate               | Delay-15-plus rate     | pp     | May 20--Jun 2 |  0.0117 |  -0.0505 |    0.0739 |
| dep    | Other hours       | delay15_rate               | Delay-15-plus rate     | pp     | Jun 3--Jun 15 | -0.0157 |  -0.0721 |    0.0407 |
| dep    | Other hours       | nas_delay_per_scheduled_op | NAS delay              | min/op | Stress        |  1.4705 |  -0.9953 |    3.9364 |
| dep    | Other hours       | nas_delay_per_scheduled_op | NAS delay              | min/op | May 20--Jun 2 | -1.3256 |  -2.7021 |    0.0509 |
| dep    | Other hours       | nas_delay_per_scheduled_op | NAS delay              | min/op | Jun 3--Jun 15 | -0.4645 |  -1.9216 |    0.9926 |
