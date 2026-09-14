# Delay-waste fuel and CO2 smoke test

Accounting boundary: NAS-attributed delay minutes and extra taxi minutes
(operated flights, extra taxi = observed taxi minus airport-side 10th percentile
of on-time taxi). Not a full-flight LCA. Fuel flow 12.5 kg/min (idle/taxi fleet
mix; bounds 8--16 kg/min). CO2 = 3.16 kg/kg fuel (ICAO/IPCC jet A).

**Usable for the paper: True.** Stress-to-28/28 delay-waste CO2 cut exceeds 50 t/day, DID-implied cut exceeds 50 t/day, and 28/28 is the lowest-waste observed target.

## EWR regime delay-waste (NAS delay, primary factor)

| Regime | Ops/day | NAS min/day | Fuel t/day | CO2 t/day | CO2 kg/op | Fuel t/day (8--16 kg/min) |
|---|---:|---:|---:|---:|---:|---:|
| stress (no formal target) | 609.1 | 15090 | 188.6 | 596.1 | 978.6 | 120.7--241.4 |
| 28/28 construction | 552.4 | 4389 | 54.9 | 173.4 | 313.8 | 35.1--70.2 |
| 34/34 operating | 670.0 | 6393 | 79.9 | 252.5 | 376.9 | 51.1--102.3 |
| 36/36 extension | 692.6 | 6338 | 79.2 | 250.4 | 361.5 | 50.7--101.4 |

## Contrasts (primary factor)

- Stress to 28/28: 422.7 t CO2/day avoided (observed EWR).
- DID-implied (EWR minus controls, stress ops): -399.4 t CO2/day (-126.4 t fuel/day; -10113 delay-min/day).
- 28/28 to 34/34: 79.2 t CO2/day added as service is restored.
- 34/34 to 36/36: -2.2 t CO2/day.

## Extra taxi (engine-on ground waste)

| Regime | Extra taxi min/day | Fuel t/day | CO2 t/day |
|---|---:|---:|---:|
| stress (no formal target) | 6088 | 76.1 | 240.5 |
| 28/28 construction | 4397 | 55.0 | 173.7 |
| 34/34 operating | 5559 | 69.5 | 219.6 |
| 36/36 extension | 6019 | 75.2 | 237.7 |

## Judgment notes

NAS delay includes airborne holding and some assigned ground delay; gate holds
with engines off are not separated. Extra taxi is the more conservative
engine-on ground layer. Headline paper numbers should use DID-implied NAS
waste for the stress-to-interim cut, and observed-regime NAS (and extra taxi
if stable) for 28/28 vs 34/34 vs 36/36.
