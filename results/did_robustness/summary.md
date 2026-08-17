# Daily DID robustness

Models use airport and day-of-week fixed effects. Reliability outcomes include weather-delay minutes per scheduled operation as a covariate.

| window             | side   | metric                     | metric_label       | unit   | weather_adjusted   |     coef |   ci_low |   ci_high |
|:-------------------|:-------|:---------------------------|:-------------------|:-------|:-------------------|---------:|---------:|----------:|
| main               | arr    | scheduled_ops              | Scheduled ops/day  | ops    | False              | -37.3692 | -53.0164 |  -20.3615 |
| main               | arr    | cancel_rate                | Cancellation rate  | pp     | True               |  -0.0310 |  -0.0659 |    0.0004 |
| main               | arr    | delay15_rate               | Delay-15-plus rate | pp     | True               |  -0.1602 |  -0.2945 |    0.0205 |
| main               | arr    | nas_delay_per_scheduled_op | NAS delay          | min    | True               | -23.8775 | -36.4540 |   -5.5287 |
| main               | dep    | scheduled_ops              | Scheduled ops/day  | ops    | False              | -37.6942 | -54.5640 |  -19.8338 |
| main               | dep    | cancel_rate                | Cancellation rate  | pp     | True               |  -0.0462 |  -0.0800 |   -0.0136 |
| main               | dep    | delay15_rate               | Delay-15-plus rate | pp     | True               |  -0.1565 |  -0.2557 |   -0.0390 |
| main               | dep    | nas_delay_per_scheduled_op | NAS delay          | min    | True               |  -3.6534 |  -6.5502 |   -0.3112 |
| pre_stress_placebo | arr    | scheduled_ops              | Scheduled ops/day  | ops    | False              | -28.5046 | -46.7756 |  -13.5846 |
| pre_stress_placebo | arr    | cancel_rate                | Cancellation rate  | pp     | True               |   0.0027 |  -0.0053 |    0.0122 |
| pre_stress_placebo | arr    | delay15_rate               | Delay-15-plus rate | pp     | True               |   0.0102 |  -0.0415 |    0.0625 |
| pre_stress_placebo | arr    | nas_delay_per_scheduled_op | NAS delay          | min    | True               |  -0.2423 |  -3.1829 |    2.1975 |
| pre_stress_placebo | dep    | scheduled_ops              | Scheduled ops/day  | ops    | False              | -28.2255 | -45.7803 |  -10.5099 |
| pre_stress_placebo | dep    | cancel_rate                | Cancellation rate  | pp     | True               |   0.0020 |  -0.0026 |    0.0081 |
| pre_stress_placebo | dep    | delay15_rate               | Delay-15-plus rate | pp     | True               |  -0.0052 |  -0.0418 |    0.0310 |
| pre_stress_placebo | dep    | nas_delay_per_scheduled_op | NAS delay          | min    | True               |  -0.2495 |  -1.6033 |    1.0783 |

## Reliability DID without weather-delay control

These models use airport and day-of-week fixed effects only.

| window   | side   | metric                     | metric_label       | unit   | weather_adjusted   |     coef |   ci_low |   ci_high |
|:---------|:-------|:---------------------------|:-------------------|:-------|:-------------------|---------:|---------:|----------:|
| main     | arr    | cancel_rate                | Cancellation rate  | pp     | False              |  -0.0450 |  -0.0776 |   -0.0134 |
| main     | arr    | delay15_rate               | Delay-15-plus rate | pp     | False              |  -0.2210 |  -0.3647 |    0.0047 |
| main     | arr    | nas_delay_per_scheduled_op | NAS delay          | min    | False              | -28.9108 | -41.1564 |   -5.5729 |
| main     | dep    | cancel_rate                | Cancellation rate  | pp     | False              |  -0.0466 |  -0.0814 |   -0.0140 |
| main     | dep    | delay15_rate               | Delay-15-plus rate | pp     | False              |  -0.1588 |  -0.2631 |   -0.0341 |
| main     | dep    | nas_delay_per_scheduled_op | NAS delay          | min    | False              |  -3.7624 |  -7.2447 |    0.0000 |
