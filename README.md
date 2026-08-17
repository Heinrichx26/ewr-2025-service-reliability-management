# EWR 2025 service reliability management

This repository provides the reproducible code and selected derived outputs for an open-data analysis of service reliability management at Newark Liberty International Airport (EWR) during the 2025 capacity-impairment episode.

The submitted article, article PDF, LaTeX source, Word submission files, cover letter, title page, declaration forms, reference library, and publisher templates are intentionally excluded.

## Repository contents

- `src/`: scripts for data processing, robustness checks, service-management checks, transferability checks, and figure generation.
- `results/ewr_2025_full/`: airport-day-side panels and period summaries used for the main descriptive evidence.
- `results/did_robustness/`: daily difference-in-differences estimates and weather-control sensitivity.
- `results/control_set_sensitivity/`: control-airport sensitivity results.
- `results/hourly_schedule_pressure/`: hourly scheduled-operation summaries used for the schedule-pressure figure.
- `results/public_data_validation_checks/`: short-window checks, hourly upper-tail summaries, and OPSNET validation output.
- `results/service_management_checks/`: service coverage, route retention, dominant-carrier response, and capacity-reliability trade-off outputs.
- `results/identification_checks/`: short-window DID, event-time DID, multiple placebo, and airport-label permutation results.
- `results/calendar_placebo_2024/`: same-calendar 2024 placebo results.
- `results/transferability_checks/`: 50-airport benchmark outputs.
- `results/figure_previews/`: PNG previews of the figures generated from the public-data results.
- `data/raw_bts_2025/` and `data/raw_bts_2024/`: placeholder folders for public BTS ZIP files. Raw BTS files are not committed.

## Public data sources

All empirical inputs are publicly available:

- Bureau of Transportation Statistics On-Time Performance records: <https://www.transtats.bts.gov/OT_Delay/>
- Federal Register notice of meeting: <https://www.federalregister.gov/documents/2025/05/14/2025-08559/operating-limitations-at-newark-liberty-international-airport-notice-of-meeting-and-request-for>
- Federal Register interim order: <https://www.federalregister.gov/documents/2025/05/23/2025-09376/operating-limitations-at-newark-liberty-international-airport-interim-order-establishing-targeted>
- Federal Register final order: <https://www.federalregister.gov/documents/2025/06/10/2025-10613/operating-limitations-at-newark-liberty-international-airport-order-establishing-targeted-scheduling>
- Federal Register extension: <https://www.federalregister.gov/documents/2025/09/29/2025-18871/operating-limitations-at-newark-liberty-international-airport>
- FAA ATADS/OPSNET Airport Operations Standard Report: <https://www.aspm.faa.gov/opsnet/sys/Airport.asp>

## Raw BTS files

Place the 2025 BTS monthly ZIP files in `data/raw_bts_2025/` using the BTS file names:

```text
On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2025_1.zip
On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2025_2.zip
...
On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2025_12.zip
```

The same-calendar placebo check expects April-June 2024 files in `data/raw_bts_2024/`:

```text
bts_on_time_2024_04.zip
bts_on_time_2024_05.zip
bts_on_time_2024_06.zip
```

The repository includes selected derived result files, so the reported values can be inspected without downloading the raw ZIP files.

## Environment

Python 3.10 or later is recommended.

```bash
pip install -r requirements.txt
```

## Reproduce the full workflow

From the repository root:

```bash
python src/analyze_ewr_2025_full.py --months 1 2 3 4 5 6 7 8 9 10 11 12
python src/analyze_hourly_schedule_pressure.py --months 1 2 3 4 5 6 7 8 9 10 11 12
python src/add_public_data_validation_checks.py --months 1 2 3 4 5 6 7 8 9 10 11 12 --fetch-opsnet
python src/add_service_management_checks.py --months 1 2 3 4 5 6 7 8 9 10 11 12
python src/add_transferability_checks.py --months 1 2 3 4 5 6 7 8 9 10 11 12
python src/add_identification_checks.py --months 1 2 3 4 5 6 7 8 9 10 11 12
python src/run_did_robustness.py --boot 499 --seed 20260510
python src/add_control_set_sensitivity.py
python src/add_calendar_placebo_2024.py --boot 499 --seed 20260520
python src/make_figures.py
```

## Quick smoke checks

```bash
python src/analyze_ewr_2025_full.py --months 4 5 6 --out results/ewr_2025_smoke
python src/analyze_hourly_schedule_pressure.py --months 4 5 6 --out results/hourly_schedule_pressure_smoke
python src/add_calendar_placebo_2024.py --smoke
```

## Scope

This repository is limited to public-data processing, derived outputs, and figure previews. It does not redistribute the submitted article or any publisher-formatted material.
