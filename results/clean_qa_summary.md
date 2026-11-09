# Synthetic QA checker summary

> Synthetic data, fictional scenario. Assessment exercise only.

- Input: `data/true_pings_SYNTHETIC.csv`.
- Pings inspected: 5958.
- Findings: 149.
- Checker reads ping fields and geometry only; it does not read the fault manifest.
- Checks: arrival-order regression, delayed receipt, duplicate keys, off-road distance, implied speed, local-day crossings, zone crossings.

| Check | Findings |
| --- | ---: |
| LOCAL_DAY_CROSSING | 12 |
| ZONE_CROSSING | 137 |

## Example findings

| Check | Ping | Related ping | Measurement | Why it was flagged |
| --- | --- | --- | --- | --- |
| LOCAL_DAY_CROSSING | T0000362 | T0000361 | 2026-03-02 → 2026-03-03 | segment T0000361→T0000362 crosses local midnight; split before daily reporting |
| ZONE_CROSSING | T0000015 | T0000014 | segment intersects zone edge | segment T0000014→T0000015 has both in-zone and out-of-zone distance |

Detailed rows: `results/clean_findings.csv`.
