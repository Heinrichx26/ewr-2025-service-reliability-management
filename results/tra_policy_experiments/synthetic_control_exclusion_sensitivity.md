# Synthetic-control exclusion sensitivity

The table reports EWR recovery gaps after excluding selected donor airports from the synthetic-control donor pool.

| scenario                           | side   | metric                     | excluded_airports                                                                                       |   recovery_gap |   pre_rmse |   rank |   p_value |
|:-----------------------------------|:-------|:---------------------------|:--------------------------------------------------------------------------------------------------------|---------------:|-----------:|-------:|----------:|
| Baseline donor pool                | arr    | delay15_rate               | --                                                                                                      |        -0.2058 |     0.1388 |      1 |    0.0200 |
| Baseline donor pool                | arr    | nas_delay_per_scheduled_op | --                                                                                                      |       -25.2874 |    17.2829 |      1 |    0.0200 |
| Baseline donor pool                | dep    | delay15_rate               | --                                                                                                      |        -0.1681 |     0.0888 |      1 |    0.0200 |
| Baseline donor pool                | dep    | nas_delay_per_scheduled_op | --                                                                                                      |        -3.5274 |     3.9663 |      1 |    0.0200 |
| Exclude NYC airports (JFK, LGA)    | arr    | delay15_rate               | JFK, LGA                                                                                                |        -0.2378 |     0.1429 |      1 |    0.0208 |
| Exclude NYC airports (JFK, LGA)    | arr    | nas_delay_per_scheduled_op | JFK, LGA                                                                                                |       -30.9724 |    19.5683 |      1 |    0.0208 |
| Exclude NYC airports (JFK, LGA)    | dep    | delay15_rate               | JFK, LGA                                                                                                |        -0.1712 |     0.0913 |      1 |    0.0208 |
| Exclude NYC airports (JFK, LGA)    | dep    | nas_delay_per_scheduled_op | JFK, LGA                                                                                                |        -3.3300 |     4.3349 |      1 |    0.0208 |
| Exclude nearby Northeast airports  | arr    | delay15_rate               | JFK, LGA, BOS, PHL, BWI, DCA, IAD                                                                       |        -0.2537 |     0.1505 |      1 |    0.0233 |
| Exclude nearby Northeast airports  | arr    | nas_delay_per_scheduled_op | JFK, LGA, BOS, PHL, BWI, DCA, IAD                                                                       |       -31.9858 |    20.0372 |      1 |    0.0233 |
| Exclude nearby Northeast airports  | dep    | delay15_rate               | JFK, LGA, BOS, PHL, BWI, DCA, IAD                                                                       |        -0.1809 |     0.0943 |      1 |    0.0233 |
| Exclude nearby Northeast airports  | dep    | nas_delay_per_scheduled_op | JFK, LGA, BOS, PHL, BWI, DCA, IAD                                                                       |        -3.3322 |     4.6940 |      1 |    0.0233 |
| Exclude high-weight donor airports | arr    | delay15_rate               | BOS, BWI, CMH, DAL, DEN, DFW, FLL, HNL, HOU, IAD, IAH, JFK, LGA, MCO, MIA, MSY, OAK, PHL, PIT, RSW, SFO |        -0.2310 |     0.1486 |      1 |    0.0345 |
| Exclude high-weight donor airports | arr    | nas_delay_per_scheduled_op | BOS, BWI, CMH, DAL, DEN, DFW, FLL, HNL, HOU, IAD, IAH, JFK, LGA, MCO, MIA, MSY, OAK, PHL, PIT, RSW, SFO |       -29.6684 |    19.6800 |      1 |    0.0345 |
| Exclude high-weight donor airports | dep    | delay15_rate               | BOS, BWI, CMH, DAL, DEN, DFW, FLL, HNL, HOU, IAD, IAH, JFK, LGA, MCO, MIA, MSY, OAK, PHL, PIT, RSW, SFO |        -0.1673 |     0.0964 |      1 |    0.0345 |
| Exclude high-weight donor airports | dep    | nas_delay_per_scheduled_op | BOS, BWI, CMH, DAL, DEN, DFW, FLL, HNL, HOU, IAD, IAH, JFK, LGA, MCO, MIA, MSY, OAK, PHL, PIT, RSW, SFO |        -2.9757 |     4.8622 |      1 |    0.0345 |
