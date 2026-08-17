# TRA identification upgrade

## Calendar-date fixed-effect phase model

| side   | metric                     | metric_label       | unit   | phase         |     coef |     se |   ci_low |   ci_high | weather_control   |
|:-------|:---------------------------|:-------------------|:-------|:--------------|---------:|-------:|---------:|----------:|:------------------|
| arr    | scheduled_ops              | Scheduled ops/day  | ops    | Stress        | -31.0300 | 3.8457 | -38.5675 |  -23.4925 | False             |
| arr    | scheduled_ops              | Scheduled ops/day  | ops    | May 20--Jun 2 | -58.1122 | 4.0664 | -66.0823 |  -50.1421 | False             |
| arr    | scheduled_ops              | Scheduled ops/day  | ops    | Jun 3--Jun 15 | -69.4682 | 3.7575 | -76.8329 |  -62.1034 | False             |
| arr    | cancel_rate                | Cancellation rate  | pp     | Stress        |   0.0434 | 0.0103 |   0.0232 |    0.0636 | False             |
| arr    | cancel_rate                | Cancellation rate  | pp     | May 20--Jun 2 |   0.0011 | 0.0024 |  -0.0037 |    0.0059 | False             |
| arr    | cancel_rate                | Cancellation rate  | pp     | Jun 3--Jun 15 |  -0.0047 | 0.0028 |  -0.0102 |    0.0009 | False             |
| arr    | delay15_rate               | Delay-15-plus rate | pp     | Stress        |   0.2620 | 0.0339 |   0.1956 |    0.3284 | False             |
| arr    | delay15_rate               | Delay-15-plus rate | pp     | May 20--Jun 2 |   0.1175 | 0.0566 |   0.0065 |    0.2285 | False             |
| arr    | delay15_rate               | Delay-15-plus rate | pp     | Jun 3--Jun 15 |  -0.0972 | 0.0239 |  -0.1440 |   -0.0503 | False             |
| arr    | nas_delay_per_scheduled_op | NAS delay          | min/op | Stress        |  34.3919 | 4.8037 |  24.9766 |   43.8071 | False             |
| arr    | nas_delay_per_scheduled_op | NAS delay          | min/op | May 20--Jun 2 |  12.1071 | 5.8755 |   0.5911 |   23.6230 | False             |
| arr    | nas_delay_per_scheduled_op | NAS delay          | min/op | Jun 3--Jun 15 |  -3.6548 | 1.5208 |  -6.6355 |   -0.6740 | False             |
| dep    | scheduled_ops              | Scheduled ops/day  | ops    | Stress        | -30.7363 | 3.8094 | -38.2027 |  -23.2699 | False             |
| dep    | scheduled_ops              | Scheduled ops/day  | ops    | May 20--Jun 2 | -57.7442 | 4.0195 | -65.6223 |  -49.8660 | False             |
| dep    | scheduled_ops              | Scheduled ops/day  | ops    | Jun 3--Jun 15 | -69.8903 | 4.0395 | -77.8076 |  -61.9729 | False             |
| dep    | cancel_rate                | Cancellation rate  | pp     | Stress        |   0.0455 | 0.0107 |   0.0246 |    0.0665 | False             |
| dep    | cancel_rate                | Cancellation rate  | pp     | May 20--Jun 2 |   0.0008 | 0.0029 |  -0.0049 |    0.0064 | False             |
| dep    | cancel_rate                | Cancellation rate  | pp     | Jun 3--Jun 15 |  -0.0038 | 0.0033 |  -0.0102 |    0.0026 | False             |
| dep    | delay15_rate               | Delay-15-plus rate | pp     | Stress        |   0.1343 | 0.0234 |   0.0884 |    0.1803 | False             |
| dep    | delay15_rate               | Delay-15-plus rate | pp     | May 20--Jun 2 |   0.0039 | 0.0343 |  -0.0633 |    0.0711 | False             |
| dep    | delay15_rate               | Delay-15-plus rate | pp     | Jun 3--Jun 15 |  -0.0874 | 0.0205 |  -0.1275 |   -0.0473 | False             |
| dep    | nas_delay_per_scheduled_op | NAS delay          | min/op | Stress        |   4.4142 | 1.0355 |   2.3847 |    6.4437 | False             |
| dep    | nas_delay_per_scheduled_op | NAS delay          | min/op | May 20--Jun 2 |   1.1496 | 1.2463 |  -1.2931 |    3.5924 | False             |
| dep    | nas_delay_per_scheduled_op | NAS delay          | min/op | Jun 3--Jun 15 |   0.6117 | 1.8762 |  -3.0657 |    4.2891 | False             |

## Ten-airport phase model with BTS weather-delay control

| side   | metric                     | metric_label       | unit   | phase         |     coef |     se |    ci_low |   ci_high | weather_control   |
|:-------|:---------------------------|:-------------------|:-------|:--------------|---------:|-------:|----------:|----------:|:------------------|
| arr    | scheduled_ops              | Scheduled ops/day  | ops    | Stress        | -45.1429 | 5.8551 |  -56.6188 |  -33.6669 | True              |
| arr    | scheduled_ops              | Scheduled ops/day  | ops    | May 20--Jun 2 | -74.1270 | 7.6106 |  -89.0438 |  -59.2102 | True              |
| arr    | scheduled_ops              | Scheduled ops/day  | ops    | Jun 3--Jun 15 | -91.5421 | 7.1887 | -105.6320 |  -77.4523 | True              |
| arr    | cancel_rate                | Cancellation rate  | pp     | Stress        |   0.0378 | 0.0101 |    0.0179 |    0.0576 | True              |
| arr    | cancel_rate                | Cancellation rate  | pp     | May 20--Jun 2 |   0.0058 | 0.0033 |   -0.0007 |    0.0123 | True              |
| arr    | cancel_rate                | Cancellation rate  | pp     | Jun 3--Jun 15 |   0.0015 | 0.0042 |   -0.0068 |    0.0098 | True              |
| arr    | delay15_rate               | Delay-15-plus rate | pp     | Stress        |   0.2195 | 0.0310 |    0.1588 |    0.2802 | True              |
| arr    | delay15_rate               | Delay-15-plus rate | pp     | May 20--Jun 2 |   0.1379 | 0.0561 |    0.0279 |    0.2480 | True              |
| arr    | delay15_rate               | Delay-15-plus rate | pp     | Jun 3--Jun 15 |  -0.0647 | 0.0246 |   -0.1130 |   -0.0165 | True              |
| arr    | nas_delay_per_scheduled_op | NAS delay          | min/op | Stress        |  30.4624 | 4.2653 |   22.1025 |   38.8223 | True              |
| arr    | nas_delay_per_scheduled_op | NAS delay          | min/op | May 20--Jun 2 |  13.0776 | 5.8967 |    1.5201 |   24.6351 | True              |
| arr    | nas_delay_per_scheduled_op | NAS delay          | min/op | Jun 3--Jun 15 |  -2.0624 | 1.4273 |   -4.8599 |    0.7351 | True              |
| dep    | scheduled_ops              | Scheduled ops/day  | ops    | Stress        | -44.9659 | 5.8765 |  -56.4839 |  -33.4479 | True              |
| dep    | scheduled_ops              | Scheduled ops/day  | ops    | May 20--Jun 2 | -73.8373 | 7.7448 |  -89.0170 |  -58.6576 | True              |
| dep    | scheduled_ops              | Scheduled ops/day  | ops    | Jun 3--Jun 15 | -92.1615 | 7.6968 | -107.2473 |  -77.0757 | True              |
| dep    | cancel_rate                | Cancellation rate  | pp     | Stress        |   0.0475 | 0.0110 |    0.0259 |    0.0690 | True              |
| dep    | cancel_rate                | Cancellation rate  | pp     | May 20--Jun 2 |   0.0044 | 0.0020 |    0.0005 |    0.0084 | True              |
| dep    | cancel_rate                | Cancellation rate  | pp     | Jun 3--Jun 15 |  -0.0023 | 0.0030 |   -0.0082 |    0.0036 | True              |
| dep    | delay15_rate               | Delay-15-plus rate | pp     | Stress        |   0.1352 | 0.0239 |    0.0883 |    0.1821 | True              |
| dep    | delay15_rate               | Delay-15-plus rate | pp     | May 20--Jun 2 |   0.0307 | 0.0331 |   -0.0342 |    0.0957 | True              |
| dep    | delay15_rate               | Delay-15-plus rate | pp     | Jun 3--Jun 15 |  -0.0787 | 0.0220 |   -0.1218 |   -0.0356 | True              |
| dep    | nas_delay_per_scheduled_op | NAS delay          | min/op | Stress        |   4.5173 | 1.0269 |    2.5044 |    6.5301 | True              |
| dep    | nas_delay_per_scheduled_op | NAS delay          | min/op | May 20--Jun 2 |   1.9842 | 1.1556 |   -0.2808 |    4.2492 | True              |
| dep    | nas_delay_per_scheduled_op | NAS delay          | min/op | Jun 3--Jun 15 |  -0.4434 | 1.5170 |   -3.4166 |    2.5299 | True              |

## Stress-window start-date sensitivity

| stress_start   | side   | metric                     | metric_label       | unit   |   stress_coef |   stress_se |   stress_ci_low |   stress_ci_high |   late_coef |   late_se |   late_ci_low |   late_ci_high |   late_minus_stress |   late_minus_stress_se |   late_minus_stress_ci_low |   late_minus_stress_ci_high |
|:---------------|:-------|:---------------------------|:-------------------|:-------|--------------:|------------:|----------------:|-----------------:|------------:|----------:|--------------:|---------------:|--------------------:|-----------------------:|---------------------------:|----------------------------:|
| 2025-04-15     | arr    | delay15_rate               | Delay-15-plus rate | pp     |        0.2620 |      0.0339 |          0.1956 |           0.3284 |     -0.0972 |    0.0239 |       -0.1440 |        -0.0503 |             -0.3592 |                 0.0348 |                    -0.4273 |                     -0.2910 |
| 2025-04-15     | arr    | nas_delay_per_scheduled_op | NAS delay          | min/op |       34.3919 |      4.8037 |         24.9766 |          43.8071 |     -3.6548 |    1.5208 |       -6.6355 |        -0.6740 |            -38.0466 |                 4.8036 |                   -47.4617 |                    -28.6316 |
| 2025-04-15     | dep    | delay15_rate               | Delay-15-plus rate | pp     |        0.1343 |      0.0234 |          0.0884 |           0.1803 |     -0.0874 |    0.0205 |       -0.1275 |        -0.0473 |             -0.2217 |                 0.0283 |                    -0.2772 |                     -0.1662 |
| 2025-04-15     | dep    | nas_delay_per_scheduled_op | NAS delay          | min/op |        4.4142 |      1.0355 |          2.3847 |           6.4437 |      0.6117 |    1.8762 |       -3.0657 |         4.2891 |             -3.8025 |                 2.0848 |                    -7.8886 |                      0.2837 |
| 2025-04-22     | arr    | delay15_rate               | Delay-15-plus rate | pp     |        0.2735 |      0.0369 |          0.2011 |           0.3459 |     -0.0972 |    0.0239 |       -0.1441 |        -0.0502 |             -0.3707 |                 0.0378 |                    -0.4447 |                     -0.2967 |
| 2025-04-22     | arr    | nas_delay_per_scheduled_op | NAS delay          | min/op |       36.8300 |      5.4393 |         26.1691 |          47.4910 |     -3.6548 |    1.5223 |       -6.6384 |        -0.6711 |            -40.4848 |                 5.4392 |                   -51.1455 |                    -29.8240 |
| 2025-04-22     | dep    | delay15_rate               | Delay-15-plus rate | pp     |        0.1372 |      0.0268 |          0.0846 |           0.1898 |     -0.0874 |    0.0205 |       -0.1276 |        -0.0472 |             -0.2246 |                 0.0312 |                    -0.2858 |                     -0.1635 |
| 2025-04-22     | dep    | nas_delay_per_scheduled_op | NAS delay          | min/op |        4.8438 |      1.2014 |          2.4891 |           7.1985 |      0.6117 |    1.8780 |       -3.0692 |         4.2927 |             -4.2321 |                 2.1734 |                    -8.4919 |                      0.0278 |
| 2025-05-01     | arr    | delay15_rate               | Delay-15-plus rate | pp     |        0.2986 |      0.0463 |          0.2078 |           0.3895 |     -0.0972 |    0.0240 |       -0.1442 |        -0.0502 |             -0.3958 |                 0.0470 |                    -0.4879 |                     -0.3037 |
| 2025-05-01     | arr    | nas_delay_per_scheduled_op | NAS delay          | min/op |       40.2838 |      6.8506 |         26.8565 |          53.7110 |     -3.6548 |    1.5246 |       -6.6429 |        -0.6666 |            -43.9385 |                 6.8506 |                   -57.3657 |                    -30.5114 |
| 2025-05-01     | dep    | delay15_rate               | Delay-15-plus rate | pp     |        0.1431 |      0.0336 |          0.0774 |           0.2089 |     -0.0874 |    0.0205 |       -0.1276 |        -0.0472 |             -0.2305 |                 0.0371 |                    -0.3034 |                     -0.1577 |
| 2025-05-01     | dep    | nas_delay_per_scheduled_op | NAS delay          | min/op |        4.1629 |      1.3503 |          1.5163 |           6.8094 |      0.6117 |    1.8809 |       -3.0748 |         4.2983 |             -3.5511 |                 2.2613 |                    -7.9833 |                      0.8811 |
| 2025-05-07     | arr    | delay15_rate               | Delay-15-plus rate | pp     |        0.2455 |      0.0562 |          0.1354 |           0.3557 |     -0.0972 |    0.0240 |       -0.1442 |        -0.0501 |             -0.3427 |                 0.0568 |                    -0.4540 |                     -0.2315 |
| 2025-05-07     | arr    | nas_delay_per_scheduled_op | NAS delay          | min/op |       31.2999 |      8.1705 |         15.2858 |          47.3140 |     -3.6548 |    1.5265 |       -6.6466 |        -0.6629 |            -34.9547 |                 8.1704 |                   -50.9687 |                    -18.9407 |
| 2025-05-07     | dep    | delay15_rate               | Delay-15-plus rate | pp     |        0.1022 |      0.0376 |          0.0285 |           0.1759 |     -0.0874 |    0.0205 |       -0.1277 |        -0.0471 |             -0.1896 |                 0.0408 |                    -0.2696 |                     -0.1095 |
| 2025-05-07     | dep    | nas_delay_per_scheduled_op | NAS delay          | min/op |        3.5373 |      1.6674 |          0.2692 |           6.8053 |      0.6117 |    1.8832 |       -3.0794 |         4.3028 |             -2.9255 |                 2.4655 |                    -7.7579 |                      1.9068 |
| 2025-05-14     | arr    | delay15_rate               | Delay-15-plus rate | pp     |        0.2555 |      0.0940 |          0.0713 |           0.4398 |     -0.0972 |    0.0240 |       -0.1443 |        -0.0500 |             -0.3527 |                 0.0943 |                    -0.5376 |                     -0.1678 |
| 2025-05-14     | arr    | nas_delay_per_scheduled_op | NAS delay          | min/op |       36.5597 |     12.9761 |         11.1266 |          61.9929 |     -3.6548 |    1.5291 |       -6.6519 |        -0.6577 |            -40.2145 |                12.9761 |                   -65.6476 |                    -14.7814 |
| 2025-05-14     | dep    | delay15_rate               | Delay-15-plus rate | pp     |        0.1223 |      0.0623 |          0.0001 |           0.2444 |     -0.0874 |    0.0206 |       -0.1277 |        -0.0471 |             -0.2097 |                 0.0643 |                    -0.3357 |                     -0.0836 |
| 2025-05-14     | dep    | nas_delay_per_scheduled_op | NAS delay          | min/op |        4.0115 |      2.5488 |         -0.9840 |           9.0071 |      0.6117 |    1.8865 |       -3.0859 |         4.3093 |             -3.3998 |                 3.1315 |                    -9.5375 |                      2.7379 |
