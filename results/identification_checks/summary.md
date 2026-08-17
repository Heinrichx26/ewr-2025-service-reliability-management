# Identification checks

## Short-window DID

| window        | side   | metric                     | metric_label       | unit   |     coef |   ci_low |   ci_high |
|:--------------|:-------|:---------------------------|:-------------------|:-------|---------:|---------:|----------:|
| May 20--Jun 2 | arr    | scheduled_ops              | Scheduled ops/day  | ops    | -28.9841 | -51.3336 |    0.0000 |
| May 20--Jun 2 | arr    | cancel_rate                | Cancellation rate  | pp     |  -0.0279 |  -0.0657 |    0.0030 |
| May 20--Jun 2 | arr    | delay15_rate               | Delay-15-plus rate | pp     |  -0.0624 |  -0.1983 |    0.0963 |
| May 20--Jun 2 | arr    | nas_delay_per_scheduled_op | NAS delay          | min    | -16.1331 | -32.4921 |    0.3552 |
| May 20--Jun 2 | dep    | scheduled_ops              | Scheduled ops/day  | ops    | -28.8714 | -52.5469 |   -6.9160 |
| May 20--Jun 2 | dep    | cancel_rate                | Cancellation rate  | pp     |  -0.0430 |  -0.0767 |    0.0000 |
| May 20--Jun 2 | dep    | delay15_rate               | Delay-15-plus rate | pp     |  -0.1041 |  -0.2082 |   -0.0078 |
| May 20--Jun 2 | dep    | nas_delay_per_scheduled_op | NAS delay          | min    |  -2.5012 |  -7.2124 |    0.7715 |
| Jun 3--Jun 15 | arr    | scheduled_ops              | Scheduled ops/day  | ops    | -46.3993 | -57.8045 |    0.0000 |
| Jun 3--Jun 15 | arr    | cancel_rate                | Cancellation rate  | pp     |  -0.0302 |  -0.0639 |    0.0000 |
| Jun 3--Jun 15 | arr    | delay15_rate               | Delay-15-plus rate | pp     |  -0.2557 |  -0.3142 |    0.0000 |
| Jun 3--Jun 15 | arr    | nas_delay_per_scheduled_op | NAS delay          | min    | -30.8799 | -39.2552 |    0.0000 |
| Jun 3--Jun 15 | dep    | scheduled_ops              | Scheduled ops/day  | ops    | -47.1956 | -58.6700 |    0.0000 |
| Jun 3--Jun 15 | dep    | cancel_rate                | Cancellation rate  | pp     |  -0.0495 |  -0.0837 |    0.0000 |
| Jun 3--Jun 15 | dep    | delay15_rate               | Delay-15-plus rate | pp     |  -0.2129 |  -0.2839 |    0.0000 |
| Jun 3--Jun 15 | dep    | nas_delay_per_scheduled_op | NAS delay          | min    |  -4.8746 |  -7.7093 |    0.0000 |

## Multiple pre-stress placebo windows

| placebo        | side   | metric                     | metric_label       | unit   |     coef |
|:---------------|:-------|:---------------------------|:-------------------|:-------|---------:|
| Jan 15--Feb 10 | arr    | scheduled_ops              | Scheduled ops/day  | ops    |  -8.7078 |
| Jan 15--Feb 10 | arr    | cancel_rate                | Cancellation rate  | pp     |   0.0043 |
| Jan 15--Feb 10 | arr    | delay15_rate               | Delay-15-plus rate | pp     |  -0.0006 |
| Jan 15--Feb 10 | arr    | nas_delay_per_scheduled_op | NAS delay          | min    |   1.2905 |
| Jan 15--Feb 10 | dep    | scheduled_ops              | Scheduled ops/day  | ops    |  -8.7984 |
| Jan 15--Feb 10 | dep    | cancel_rate                | Cancellation rate  | pp     |  -0.0057 |
| Jan 15--Feb 10 | dep    | delay15_rate               | Delay-15-plus rate | pp     |  -0.0309 |
| Jan 15--Feb 10 | dep    | nas_delay_per_scheduled_op | NAS delay          | min    |  -0.9464 |
| Feb 12--Mar 18 | arr    | scheduled_ops              | Scheduled ops/day  | ops    | -28.5046 |
| Feb 12--Mar 18 | arr    | cancel_rate                | Cancellation rate  | pp     |   0.0027 |
| Feb 12--Mar 18 | arr    | delay15_rate               | Delay-15-plus rate | pp     |   0.0102 |
| Feb 12--Mar 18 | arr    | nas_delay_per_scheduled_op | NAS delay          | min    |  -0.2423 |
| Feb 12--Mar 18 | dep    | scheduled_ops              | Scheduled ops/day  | ops    | -28.2255 |
| Feb 12--Mar 18 | dep    | cancel_rate                | Cancellation rate  | pp     |   0.0020 |
| Feb 12--Mar 18 | dep    | delay15_rate               | Delay-15-plus rate | pp     |  -0.0052 |
| Feb 12--Mar 18 | dep    | nas_delay_per_scheduled_op | NAS delay          | min    |  -0.2495 |
| Mar 1--Mar 27  | arr    | scheduled_ops              | Scheduled ops/day  | ops    | -31.5062 |
| Mar 1--Mar 27  | arr    | cancel_rate                | Cancellation rate  | pp     |  -0.0057 |
| Mar 1--Mar 27  | arr    | delay15_rate               | Delay-15-plus rate | pp     |  -0.0390 |
| Mar 1--Mar 27  | arr    | nas_delay_per_scheduled_op | NAS delay          | min    |  -0.3582 |
| Mar 1--Mar 27  | dep    | scheduled_ops              | Scheduled ops/day  | ops    | -30.9218 |
| Mar 1--Mar 27  | dep    | cancel_rate                | Cancellation rate  | pp     |  -0.0020 |
| Mar 1--Mar 27  | dep    | delay15_rate               | Delay-15-plus rate | pp     |  -0.0263 |
| Mar 1--Mar 27  | dep    | nas_delay_per_scheduled_op | NAS delay          | min    |   0.0909 |

## Airport-label permutation ranks for EWR

| treated_airport   | side   | metric                     | metric_label       | unit   |     coef |   rank_lowest |   airports |   permutation_p_lower_or_equal |
|:------------------|:-------|:---------------------------|:-------------------|:-------|---------:|--------------:|-----------:|-------------------------------:|
| EWR               | arr    | scheduled_ops              | Scheduled ops/day  | ops    | -37.3692 |        1.0000 |         10 |                         0.1000 |
| EWR               | arr    | cancel_rate                | Cancellation rate  | pp     |  -0.0310 |        1.0000 |         10 |                         0.1000 |
| EWR               | arr    | delay15_rate               | Delay-15-plus rate | pp     |  -0.1602 |        1.0000 |         10 |                         0.1000 |
| EWR               | arr    | nas_delay_per_scheduled_op | NAS delay          | min    | -23.8775 |        1.0000 |         10 |                         0.1000 |
| EWR               | dep    | scheduled_ops              | Scheduled ops/day  | ops    | -37.6942 |        1.0000 |         10 |                         0.1000 |
| EWR               | dep    | cancel_rate                | Cancellation rate  | pp     |  -0.0462 |        1.0000 |         10 |                         0.1000 |
| EWR               | dep    | delay15_rate               | Delay-15-plus rate | pp     |  -0.1565 |        1.0000 |         10 |                         0.1000 |
| EWR               | dep    | nas_delay_per_scheduled_op | NAS delay          | min    |  -3.6534 |        1.0000 |         10 |                         0.1000 |

## Event-time DID

| event_period   | side   | metric                     | metric_label       | unit   |     coef |
|:---------------|:-------|:---------------------------|:-------------------|:-------|---------:|
| Stress start   | arr    | scheduled_ops              | Scheduled ops/day  | ops    | -40.4286 |
| Stress start   | arr    | cancel_rate                | Cancellation rate  | pp     |   0.0203 |
| Stress start   | arr    | delay15_rate               | Delay-15-plus rate | pp     |   0.1892 |
| Stress start   | arr    | nas_delay_per_scheduled_op | NAS delay          | min    |  24.8992 |
| Pre-order late | arr    | scheduled_ops              | Scheduled ops/day  | ops    | -48.2857 |
| Pre-order late | arr    | cancel_rate                | Cancellation rate  | pp     |   0.0442 |
| Pre-order late | arr    | delay15_rate               | Delay-15-plus rate | pp     |   0.2174 |
| Pre-order late | arr    | nas_delay_per_scheduled_op | NAS delay          | min    |  33.4623 |
| May 20--Jun 2  | arr    | scheduled_ops              | Scheduled ops/day  | ops    | -74.1270 |
| May 20--Jun 2  | arr    | cancel_rate                | Cancellation rate  | pp     |   0.0058 |
| May 20--Jun 2  | arr    | delay15_rate               | Delay-15-plus rate | pp     |   0.1395 |
| May 20--Jun 2  | arr    | nas_delay_per_scheduled_op | NAS delay          | min    |  12.9978 |
| Jun 3--Jun 15  | arr    | scheduled_ops              | Scheduled ops/day  | ops    | -91.5421 |
| Jun 3--Jun 15  | arr    | cancel_rate                | Cancellation rate  | pp     |   0.0021 |
| Jun 3--Jun 15  | arr    | delay15_rate               | Delay-15-plus rate | pp     |  -0.0598 |
| Jun 3--Jun 15  | arr    | nas_delay_per_scheduled_op | NAS delay          | min    |  -2.4158 |
| Stress start   | dep    | scheduled_ops              | Scheduled ops/day  | ops    | -40.5198 |
| Stress start   | dep    | cancel_rate                | Cancellation rate  | pp     |   0.0262 |
| Stress start   | dep    | delay15_rate               | Delay-15-plus rate | pp     |   0.1390 |
| Stress start   | dep    | nas_delay_per_scheduled_op | NAS delay          | min    |   4.8338 |
| Pre-order late | dep    | scheduled_ops              | Scheduled ops/day  | ops    | -47.9299 |
| Pre-order late | dep    | cancel_rate                | Cancellation rate  | pp     |   0.0630 |
| Pre-order late | dep    | delay15_rate               | Delay-15-plus rate | pp     |   0.1347 |
| Pre-order late | dep    | nas_delay_per_scheduled_op | NAS delay          | min    |   4.4930 |
| May 20--Jun 2  | dep    | scheduled_ops              | Scheduled ops/day  | ops    | -73.8373 |
| May 20--Jun 2  | dep    | cancel_rate                | Cancellation rate  | pp     |   0.0053 |
| May 20--Jun 2  | dep    | delay15_rate               | Delay-15-plus rate | pp     |   0.0326 |
| May 20--Jun 2  | dep    | nas_delay_per_scheduled_op | NAS delay          | min    |   2.0867 |
| Jun 3--Jun 15  | dep    | scheduled_ops              | Scheduled ops/day  | ops    | -92.1615 |
| Jun 3--Jun 15  | dep    | cancel_rate                | Cancellation rate  | pp     |  -0.0010 |
| Jun 3--Jun 15  | dep    | delay15_rate               | Delay-15-plus rate | pp     |  -0.0765 |
| Jun 3--Jun 15  | dep    | nas_delay_per_scheduled_op | NAS delay          | min    |  -0.2531 |

