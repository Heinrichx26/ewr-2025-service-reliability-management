# EWR 2025 temporary airport operating limits

This repository provides reproducible code and selected derived outputs for an open-data analysis of the 2025 temporary airport operating-limit episode at Newark Liberty International Airport (EWR).

The submitted article, article PDF, LaTeX source, Word submission files, cover letter, title page, declaration forms, reference library, and publisher templates are intentionally excluded.

## Repository contents

- `src/`: scripts for data processing, robustness checks, policy-exposure checks, transferability checks, synthetic-control analysis, and figure generation.
- `src/policy_method_benchmarks/`: one independent implementation file for each 2024--2026 decision-method benchmark, plus a shared data interface.
- `results/ewr_2025_full/`: airport-day-side panels and period summaries used for the main descriptive evidence.
- `results/did_robustness/`: daily difference-in-differences estimates and weather-control sensitivity.
- `results/control_set_sensitivity/`: control-airport sensitivity results.
- `results/hourly_schedule_pressure/`: hourly scheduled-operation summaries used for the schedule-pressure figure.
- `results/public_data_validation_checks/`: short-window checks, hourly upper-tail summaries, and OPSNET validation output.
- `results/access_carrier_checks/`: route retention, passenger-access, carrier-burden, and capacity-reliability trade-off outputs.
- `results/identification_checks/`: short-window DID, event-time DID, multiple placebo, and airport-label permutation results.
- `results/calendar_placebo_2024/`: same-calendar 2024 placebo results.
- `results/transferability_checks/`: 50-airport benchmark outputs.
- `results/tra_policy_experiments/`: synthetic-control recovery contrasts, donor-exclusion sensitivity, domestic T-100 passenger and seat exposure, and delay-exposure accounting.
- `results/tra_t100_international_exposure/`: international T-100 access and carrier-exposure summaries used for the access-preservation checks.
- `results/tra_identification_upgrade/`: calendar-date fixed-effect phase estimates and stress-start sensitivity.
- `results/tra_peak_hour_mechanism/`: peak-hour pressure models connecting reported schedule exposure with reliability.
- `results/tra_weather_controls/`: station-weather controls based on ASOS/AWOS/METAR records.
- `results/tra_atcscc_advisories/`: ATCSCC advisory diagnostics for flow-management pressure.
- `results/tra_deep_policy_checks/`: dynamic event-study contrasts, severe-delay checks, weighted market retention, ridge counterfactuals, passenger-time bootstrap intervals, and carrier-group heterogeneity.
- `results/operational_policy_mechanism/`: policy-mechanism bridge table linking capacity governance, peak-hour pressure, reliability, counterfactual checks, access, and carrier response.
- `results/seps_policy_frontier/`: the common four-regime reliability, service, access, and burden matrix.
- `results/policy_method_benchmarks/`: rankings, top-state audit, preference sensitivity, and implementation-fidelity records for six recent method families.
- `results/figure_previews/`: PNG previews of the figures generated from the public-data results.
- `data/raw_bts_2025/` and `data/raw_bts_2024/`: placeholder folders for public BTS ZIP files. Raw BTS files are not committed.
- `data/t100_domestic_segment/`: placeholder folder for public BTS T-100 Domestic Segment ZIP files. Raw T-100 files are not committed.
- `data/t100_international_segment/`: placeholder folder for public BTS T-100 International Segment ZIP files. Raw T-100 files are not committed.

## Public data sources

All empirical inputs are publicly available:

- Bureau of Transportation Statistics On-Time Performance records: <https://www.transtats.bts.gov/OT_Delay/>
- Bureau of Transportation Statistics T-100 Domestic and International Segment records: <https://www.transtats.bts.gov/>
- Federal Register notice of meeting: <https://www.federalregister.gov/documents/2025/05/14/2025-08559/operating-limitations-at-newark-liberty-international-airport-notice-of-meeting-and-request-for>
- Federal Register interim order: <https://www.federalregister.gov/documents/2025/05/23/2025-09376/operating-limitations-at-newark-liberty-international-airport-interim-order-establishing-targeted>
- Federal Register final order: <https://www.federalregister.gov/documents/2025/06/10/2025-10613/operating-limitations-at-newark-liberty-international-airport-order-establishing-targeted-scheduling>
- Federal Register extension: <https://www.federalregister.gov/documents/2025/09/29/2025-18871/operating-limitations-at-newark-liberty-international-airport>
- FAA ATADS/OPSNET Airport Operations Standard Report: <https://www.aspm.faa.gov/opsnet/sys/Airport.asp>
- Iowa Environmental Mesonet ASOS/AWOS/METAR archive: <https://mesonet.agron.iastate.edu/request/download.phtml>
- FAA ATCSCC operational information: <https://www.fly.faa.gov/>

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

The passenger and seat exposure checks expect 2025 T-100 Domestic Segment ZIP files in `data/t100_domestic_segment/` using names such as:

```text
t100_domestic_segment_all_carriers_2025_01.zip
t100_domestic_segment_all_carriers_2025_02.zip
...
t100_domestic_segment_all_carriers_2025_12.zip
```

International access checks expect 2024 and 2025 T-100 International Segment ZIP files in `data/t100_international_segment/`. The workflow uses monthly records for April--June 2025 in the main access-preservation summary and the same months in 2024 for context checks.

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
python src/add_access_carrier_checks.py --months 1 2 3 4 5 6 7 8 9 10 11 12
python src/add_transferability_checks.py --months 1 2 3 4 5 6 7 8 9 10 11 12
python src/add_identification_checks.py --months 1 2 3 4 5 6 7 8 9 10 11 12
python src/run_did_robustness.py --boot 499 --seed 20260510
python src/add_control_set_sensitivity.py
python src/add_calendar_placebo_2024.py --boot 499 --seed 20260520
python src/add_tra_policy_experiments.py --top-n 50
python src/add_tra_policy_exclusion_checks.py
python src/add_operational_policy_mechanism_checks.py
python src/add_tra_identification_upgrade.py
python src/add_tra_peak_hour_mechanism.py
python src/add_tra_asos_weather_controls.py
python src/add_tra_atcscc_advisory_check.py
python src/add_tra_t100_international_exposure.py
python src/add_tra_deep_policy_checks.py --bootstrap-reps 2000
python src/run_policy_method_benchmarks.py
python src/make_figures.py
```

## Quick smoke checks

```bash
python src/analyze_ewr_2025_full.py --months 4 5 6 --out results/ewr_2025_smoke
python src/analyze_hourly_schedule_pressure.py --months 4 5 6 --out results/hourly_schedule_pressure_smoke
python src/add_calendar_placebo_2024.py --smoke
python src/add_tra_policy_experiments.py --smoke
python src/add_tra_policy_exclusion_checks.py --smoke
python src/add_operational_policy_mechanism_checks.py --smoke
python src/add_tra_identification_upgrade.py --smoke
python src/add_tra_peak_hour_mechanism.py --smoke
python src/add_tra_asos_weather_controls.py --smoke
python src/add_tra_atcscc_advisory_check.py --smoke
python src/add_tra_t100_international_exposure.py --smoke
python src/add_tra_deep_policy_checks.py --smoke --bootstrap-reps 300
python src/run_policy_method_benchmarks.py --smoke
```

## Recent method-family benchmark

The benchmark compares six decision mechanisms on the same four observed policy states:

- fair risk-averse allocation based on Sun, Deng, Wei, and Xie (2024), `10.1002/nav.22217`;
- Z-number network data envelopment analysis based on Yang, Omrani, and Imanirad (2024), `10.1016/j.seps.2024.102080`;
- series-network slacks-based measurement based on Taleb (2025), `10.1016/j.seps.2025.102211`;
- combined compromise for ideal solution based on Rasoanaivo et al. (2024), `10.1016/j.eswa.2024.124079`;
- effectiveness-equity preference analysis based on Eisenhandler, Meyer, and Tzur (2026), `10.1016/j.seps.2026.102483`;
- feasibility-constrained sequencing based on Do, Xia, and Pham (2026), `10.1016/j.seps.2026.102568`.

Each implementation records the mathematical components retained, the airport-specific adaptation, and its decision output. Scores remain on their native method scales. The common audit compares the top state, uniqueness, compliance with the balanced policy bounds, and preference sensitivity. Run the smoke command before the full benchmark.

## Scope

This repository is limited to public-data processing, derived outputs, and figure previews. It does not redistribute the submitted article or any publisher-formatted material.
