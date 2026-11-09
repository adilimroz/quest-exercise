# Synthetic QA checker summary

> Synthetic data, fictional scenario. Assessment exercise only.

- Input: `data/pings_SYNTHETIC.csv`.
- Pings inspected: 6315.
- Findings: 1209.
- Checker reads ping fields and geometry only; it does not read the fault manifest.
- Checks: arrival-order regression, delayed receipt, duplicate keys, off-road distance, implied speed, local-day crossings, zone crossings.

| Check | Findings |
| --- | ---: |
| ARRIVAL_ORDER | 405 |
| DUPLICATE | 179 |
| LATE_ARRIVAL | 298 |
| LOCAL_DAY_CROSSING | 12 |
| OFFROAD_NOISE | 89 |
| SPEED_NOISE | 89 |
| ZONE_CROSSING | 137 |

## Example findings

| Check | Ping | Related ping | Measurement | Why it was flagged |
| --- | --- | --- | --- | --- |
| ARRIVAL_ORDER | P0000038 | P0000037 | 80 s behind | event timestamp is older than a previously received ping |
| DUPLICATE | P0000055 | P0000050 | same coordinates | same driver and event timestamp; earliest-received copy retained for analysis |
| LATE_ARRIVAL | P0000038 | — | 89 s | received substantially after its event timestamp |
| LOCAL_DAY_CROSSING | P0002116 | P0000665 | 2026-03-02 → 2026-03-03 | segment P0000665→P0002116 crosses local midnight; split before daily reporting |
| OFFROAD_NOISE | P0000068 | — | 500.0 m | point lies farther than the limit from every modeled road segment |
| SPEED_NOISE | P0000032 | P0000031 | 647.1 km/h | implied speed from the last accepted point exceeds the limit |
| ZONE_CROSSING | P0000015 | P0000014 | segment intersects zone edge | segment P0000014→P0000015 has both in-zone and out-of-zone distance |

Detailed rows: `results/findings.csv`.
