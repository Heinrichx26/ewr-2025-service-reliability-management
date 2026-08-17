# TRA external station-weather control check

## Weather coverage

| airport   |   days |   obs |
|:----------|-------:|------:|
| ATL       |     89 | 28080 |
| BOS       |     89 | 25916 |
| BWI       |     89 | 27938 |
| DCA       |     89 | 27941 |
| EWR       |     89 | 27890 |
| IAD       |     89 | 27942 |
| JFK       |     89 | 27751 |
| LGA       |     89 | 27574 |
| ORD       |     89 | 28026 |
| PHL       |     89 | 28336 |

Merged airport-day-side rows: 1780.

## Phase estimates

| side   | metric                     | metric_label       | unit   | phase         | weather_controls   |    coef |   ci_low |   ci_high |
|:-------|:---------------------------|:-------------------|:-------|:--------------|:-------------------|--------:|---------:|----------:|
| arr    | cancel_rate                | Cancellation rate  | pp     | Stress        | False              |  0.0452 |   0.0243 |    0.0662 |
| arr    | cancel_rate                | Cancellation rate  | pp     | May 20--Jun 2 | False              |  0.0043 |  -0.0006 |    0.0092 |
| arr    | cancel_rate                | Cancellation rate  | pp     | Jun 3--Jun 15 | False              | -0.0029 |  -0.0103 |    0.0044 |
| arr    | cancel_rate                | Cancellation rate  | pp     | Stress        | True               |  0.0450 |   0.0242 |    0.0658 |
| arr    | cancel_rate                | Cancellation rate  | pp     | May 20--Jun 2 | True               |  0.0054 |   0.0006 |    0.0102 |
| arr    | cancel_rate                | Cancellation rate  | pp     | Jun 3--Jun 15 | True               | -0.0026 |  -0.0109 |    0.0056 |
| arr    | delay15_rate               | Delay-15-plus rate | pp     | Stress        | False              |  0.2481 |   0.1830 |    0.3131 |
| arr    | delay15_rate               | Delay-15-plus rate | pp     | May 20--Jun 2 | False              |  0.1321 |   0.0215 |    0.2427 |
| arr    | delay15_rate               | Delay-15-plus rate | pp     | Jun 3--Jun 15 | False              | -0.0805 |  -0.1331 |   -0.0279 |
| arr    | delay15_rate               | Delay-15-plus rate | pp     | Stress        | True               |  0.2546 |   0.1907 |    0.3185 |
| arr    | delay15_rate               | Delay-15-plus rate | pp     | May 20--Jun 2 | True               |  0.1451 |   0.0470 |    0.2433 |
| arr    | delay15_rate               | Delay-15-plus rate | pp     | Jun 3--Jun 15 | True               | -0.0707 |  -0.1248 |   -0.0165 |
| arr    | nas_delay_per_scheduled_op | NAS delay          | min/op | Stress        | False              | 33.3527 |  23.9969 |   42.7086 |
| arr    | nas_delay_per_scheduled_op | NAS delay          | min/op | May 20--Jun 2 | False              | 12.4878 |   0.7426 |   24.2329 |
| arr    | nas_delay_per_scheduled_op | NAS delay          | min/op | Jun 3--Jun 15 | False              | -4.0392 |  -7.3531 |   -0.7253 |
| arr    | nas_delay_per_scheduled_op | NAS delay          | min/op | Stress        | True               | 33.8299 |  24.8086 |   42.8513 |
| arr    | nas_delay_per_scheduled_op | NAS delay          | min/op | May 20--Jun 2 | True               | 13.4143 |   2.6246 |   24.2040 |
| arr    | nas_delay_per_scheduled_op | NAS delay          | min/op | Jun 3--Jun 15 | True               | -3.6776 |  -7.1883 |   -0.1668 |
| dep    | cancel_rate                | Cancellation rate  | pp     | Stress        | False              |  0.0468 |   0.0256 |    0.0681 |
| dep    | cancel_rate                | Cancellation rate  | pp     | May 20--Jun 2 | False              |  0.0036 |  -0.0010 |    0.0081 |
| dep    | cancel_rate                | Cancellation rate  | pp     | Jun 3--Jun 15 | False              | -0.0029 |  -0.0098 |    0.0041 |
| dep    | cancel_rate                | Cancellation rate  | pp     | Stress        | True               |  0.0464 |   0.0253 |    0.0675 |
| dep    | cancel_rate                | Cancellation rate  | pp     | May 20--Jun 2 | True               |  0.0049 |   0.0006 |    0.0092 |
| dep    | cancel_rate                | Cancellation rate  | pp     | Jun 3--Jun 15 | True               | -0.0021 |  -0.0105 |    0.0063 |
| dep    | delay15_rate               | Delay-15-plus rate | pp     | Stress        | False              |  0.1323 |   0.0851 |    0.1794 |
| dep    | delay15_rate               | Delay-15-plus rate | pp     | May 20--Jun 2 | False              |  0.0268 |  -0.0413 |    0.0949 |
| dep    | delay15_rate               | Delay-15-plus rate | pp     | Jun 3--Jun 15 | False              | -0.0772 |  -0.1217 |   -0.0327 |
| dep    | delay15_rate               | Delay-15-plus rate | pp     | Stress        | True               |  0.1348 |   0.0892 |    0.1803 |
| dep    | delay15_rate               | Delay-15-plus rate | pp     | May 20--Jun 2 | True               |  0.0350 |  -0.0228 |    0.0928 |
| dep    | delay15_rate               | Delay-15-plus rate | pp     | Jun 3--Jun 15 | True               | -0.0706 |  -0.1153 |   -0.0259 |
| dep    | nas_delay_per_scheduled_op | NAS delay          | min/op | Stress        | False              |  4.4089 |   2.3554 |    6.4624 |
| dep    | nas_delay_per_scheduled_op | NAS delay          | min/op | May 20--Jun 2 | False              |  1.8384 |  -0.5010 |    4.1777 |
| dep    | nas_delay_per_scheduled_op | NAS delay          | min/op | Jun 3--Jun 15 | False              | -0.4307 |  -3.9092 |    3.0477 |
| dep    | nas_delay_per_scheduled_op | NAS delay          | min/op | Stress        | True               |  4.6287 |   2.5593 |    6.6982 |
| dep    | nas_delay_per_scheduled_op | NAS delay          | min/op | May 20--Jun 2 | True               |  2.2012 |   0.1366 |    4.2657 |
| dep    | nas_delay_per_scheduled_op | NAS delay          | min/op | Jun 3--Jun 15 | True               | -0.1102 |  -3.5118 |    3.2915 |
