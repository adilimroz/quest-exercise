# Synthetic before/after distance comparison

> Synthetic data, fictional scenario. Assessment exercise only.

- Legacy total (UTC day basis): **809.448557 km**.
- Corrected total (local UTC+9 day basis): **273.691685 km**.
- Independent clean reference total: **273.691796 km**.
- Maximum absolute corrected per-driver/day error: **0.000090 km**; tolerance **0.002 km**; result **PASS**.
- Legacy values are keyed by their UTC report date; corrected and reference values use the same-named local UTC+9 date. This intentionally exposes the old day-cut mismatch.

## Driver totals

| Driver | Legacy UTC km | Corrected local km | Reference local km | Legacy − reference km | Corrected − reference km |
| --- | ---: | ---: | ---: | ---: | ---: |
| DRV-001 | 200.457309 | 67.900813 | 67.900801 | 132.556508 | 0.000012 |
| DRV-002 | 199.797355 | 71.687217 | 71.687262 | 128.110093 | -0.000045 |
| DRV-003 | 187.484777 | 66.202842 | 66.202971 | 121.281806 | -0.000129 |
| DRV-004 | 221.709116 | 67.900813 | 67.900762 | 153.808354 | 0.000051 |
| DRV-005 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |

## Driver/day rows

| Driver | Day label | Legacy UTC km | Corrected local km | Reference local km | Legacy error km | Corrected error km |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| DRV-001 | 2026-03-01 | 33.710597 | 0.000000 | 0.000000 | 33.710597 | 0.000000 |
| DRV-001 | 2026-03-02 | 58.171924 | 21.780066 | 21.780077 | 36.391847 | -0.000011 |
| DRV-001 | 2026-03-03 | 66.355139 | 22.517402 | 22.517457 | 43.837682 | -0.000055 |
| DRV-001 | 2026-03-04 | 42.219649 | 23.603345 | 23.603267 | 18.616382 | 0.000078 |
| DRV-002 | 2026-03-02 | 65.128315 | 11.781467 | 11.781428 | 53.346887 | 0.000039 |
| DRV-002 | 2026-03-03 | 84.263006 | 23.962300 | 23.962390 | 60.300616 | -0.000090 |
| DRV-002 | 2026-03-04 | 50.406034 | 23.962300 | 23.962314 | 26.443720 | -0.000014 |
| DRV-002 | 2026-03-05 | 0.000000 | 11.981150 | 11.981130 | -11.981130 | 0.000020 |
| DRV-003 | 2026-03-02 | 69.159418 | 21.962970 | 21.963024 | 47.196394 | -0.000054 |
| DRV-003 | 2026-03-03 | 69.151989 | 23.959606 | 23.959602 | 45.192387 | 0.000004 |
| DRV-003 | 2026-03-04 | 49.173370 | 20.280266 | 20.280345 | 28.893025 | -0.000079 |
| DRV-004 | 2026-03-01 | 5.796516 | 0.000000 | 0.000000 | 5.796516 | 0.000000 |
| DRV-004 | 2026-03-02 | 82.344998 | 23.964993 | 23.964965 | 58.380033 | 0.000028 |
| DRV-004 | 2026-03-03 | 89.824751 | 20.252130 | 20.252103 | 69.572648 | 0.000027 |
| DRV-004 | 2026-03-04 | 43.742851 | 23.683690 | 23.683694 | 20.059157 | -0.000004 |
| DRV-005 | 2026-03-02 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| DRV-005 | 2026-03-03 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| DRV-005 | 2026-03-04 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| DRV-005 | 2026-03-05 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |

Full precision rows are in `results/before_after.csv`; the separate driver total file is `results/driver_totals.csv`.
