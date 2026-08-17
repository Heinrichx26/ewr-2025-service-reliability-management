# Control-set sensitivity

Comparison: stress period to interim-order period.

| control_set                             | metric                     | side   |   airport_count |   ewr_delta |   control_mean_delta |   ewr_minus_control_delta |
|:----------------------------------------|:---------------------------|:-------|----------------:|------------:|---------------------:|--------------------------:|
| All controls                            | delay15_rate               | arr    |               9 |     -0.2125 |               0.0048 |                   -0.2172 |
| All controls                            | delay15_rate               | dep    |               9 |     -0.1388 |               0.0176 |                   -0.1564 |
| Exclude New York City airports          | delay15_rate               | arr    |               7 |     -0.2125 |               0.0157 |                   -0.2282 |
| Exclude New York City airports          | delay15_rate               | dep    |               7 |     -0.1388 |               0.0226 |                   -0.1614 |
| Regional controls outside New York City | delay15_rate               | arr    |               5 |     -0.2125 |               0.0073 |                   -0.2198 |
| Regional controls outside New York City | delay15_rate               | dep    |               5 |     -0.1388 |               0.0106 |                   -0.1494 |
| Large hubs only                         | delay15_rate               | arr    |               2 |     -0.2125 |               0.0368 |                   -0.2493 |
| Large hubs only                         | delay15_rate               | dep    |               2 |     -0.1388 |               0.0524 |                   -0.1912 |
| Exclude large hubs                      | delay15_rate               | arr    |               7 |     -0.2125 |              -0.0044 |                   -0.2081 |
| Exclude large hubs                      | delay15_rate               | dep    |               7 |     -0.1388 |               0.0077 |                   -0.1465 |
| All controls                            | nas_delay_per_scheduled_op | arr    |               9 |    -30.1114 |              -0.7061 |                  -29.4053 |
| All controls                            | nas_delay_per_scheduled_op | dep    |               9 |     -3.5592 |               0.2480 |                   -3.8072 |
| Exclude New York City airports          | nas_delay_per_scheduled_op | arr    |               7 |    -30.1114 |               0.2689 |                  -30.3802 |
| Exclude New York City airports          | nas_delay_per_scheduled_op | dep    |               7 |     -3.5592 |               0.2014 |                   -3.7606 |
| Regional controls outside New York City | nas_delay_per_scheduled_op | arr    |               5 |    -30.1114 |              -0.1084 |                  -30.0030 |
| Regional controls outside New York City | nas_delay_per_scheduled_op | dep    |               5 |     -3.5592 |               0.5169 |                   -4.0761 |
| Large hubs only                         | nas_delay_per_scheduled_op | arr    |               2 |    -30.1114 |               1.2120 |                  -31.3234 |
| Large hubs only                         | nas_delay_per_scheduled_op | dep    |               2 |     -3.5592 |              -0.5873 |                   -2.9719 |
| Exclude large hubs                      | nas_delay_per_scheduled_op | arr    |               7 |    -30.1114 |              -1.2541 |                  -28.8572 |
| Exclude large hubs                      | nas_delay_per_scheduled_op | dep    |               7 |     -3.5592 |               0.4866 |                   -4.0458 |
