# Same-calendar 2024 placebo DID check

The check compares April 15-May 19 with May 20-June 15 in 2024 using the same airport set, fixed effects, and outcome definitions as the main 2025 DID.

| window             | side   | metric                     | metric_label       | unit   |     coef |   ci_low |   ci_high |
|:-------------------|:-------|:---------------------------|:-------------------|:-------|---------:|---------:|----------:|
| 2024_same_calendar | arr    | scheduled_ops              | Scheduled ops/day  | ops    | -12.0299 | -18.5966 |   -5.3972 |
| 2024_same_calendar | arr    | cancel_rate                | Cancellation rate  | pp     |   0.0064 |  -0.0035 |    0.0143 |
| 2024_same_calendar | arr    | delay15_rate               | Delay-15-plus rate | pp     |   0.0205 |  -0.0025 |    0.0449 |
| 2024_same_calendar | arr    | nas_delay_per_scheduled_op | NAS delay          | min    |   2.5443 |  -0.1770 |    4.0376 |
| 2024_same_calendar | dep    | scheduled_ops              | Scheduled ops/day  | ops    | -12.4978 | -19.6791 |   -5.8619 |
| 2024_same_calendar | dep    | cancel_rate                | Cancellation rate  | pp     |   0.0067 |  -0.0008 |    0.0130 |
| 2024_same_calendar | dep    | delay15_rate               | Delay-15-plus rate | pp     |   0.0034 |  -0.0326 |    0.0335 |
| 2024_same_calendar | dep    | nas_delay_per_scheduled_op | NAS delay          | min    |  -0.6231 |  -1.3741 |   -0.0415 |
