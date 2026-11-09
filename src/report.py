"""Compare legacy, corrected, and independent synthetic truth outputs.

Run after `src/legacy.py`, `src/corrected.py`, and `src/generate.py`:
  python3 src/report.py
"""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LEGACY = ROOT / "results" / "legacy_km.csv"
FIXED = ROOT / "results" / "fixed_km.csv"
TRUTH = ROOT / "data" / "ground_truth_SYNTHETIC.csv"
COMPARISON = ROOT / "results" / "before_after.csv"
TOTALS = ROOT / "results" / "driver_totals.csv"
SUMMARY = ROOT / "results" / "before_after.md"
TOLERANCE_KM = 0.002


def read_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def keyed(rows: list[dict], date_field: str, value_field: str) -> dict[tuple[str, str], float]:
    return {(row["driver_id"], row[date_field]): float(row[value_field]) for row in rows}


def write_csv(path: Path, fields: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    legacy = keyed(read_csv(LEGACY), "day", "km_in_zone")
    fixed = keyed(read_csv(FIXED), "day", "km_in_zone")
    truth = keyed(read_csv(TRUTH), "local_date", "true_km_in_zone")
    keys = sorted(set(legacy) | set(fixed) | set(truth))
    rows = []
    by_driver: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    max_fixed_error = 0.0
    for driver, day in keys:
        old = legacy.get((driver, day), 0.0)
        new = fixed.get((driver, day), 0.0)
        expected = truth.get((driver, day), 0.0)
        fixed_error = new - expected
        legacy_error = old - expected
        max_fixed_error = max(max_fixed_error, abs(fixed_error))
        rows.append({
            "driver_id": driver, "day": day,
            "legacy_utc_km": f"{old:.6f}", "corrected_local_km": f"{new:.6f}",
            "reference_local_km": f"{expected:.6f}",
            "legacy_minus_reference_km": f"{legacy_error:.6f}",
            "corrected_minus_reference_km": f"{fixed_error:.6f}",
            "legacy_day_basis": "UTC", "corrected_day_basis": "local UTC+9",
        })
        by_driver[driver]["legacy"] += old
        by_driver[driver]["corrected"] += new
        by_driver[driver]["reference"] += expected
    write_csv(COMPARISON, [
        "driver_id", "day", "legacy_utc_km", "corrected_local_km", "reference_local_km",
        "legacy_minus_reference_km", "corrected_minus_reference_km", "legacy_day_basis", "corrected_day_basis",
    ], rows)

    total_rows = []
    for driver in sorted(by_driver):
        v = by_driver[driver]
        total_rows.append({
            "driver_id": driver, "legacy_utc_km": f"{v['legacy']:.6f}",
            "corrected_local_km": f"{v['corrected']:.6f}",
            "reference_local_km": f"{v['reference']:.6f}",
            "legacy_minus_reference_km": f"{v['legacy'] - v['reference']:.6f}",
            "corrected_minus_reference_km": f"{v['corrected'] - v['reference']:.6f}",
        })
    write_csv(TOTALS, [
        "driver_id", "legacy_utc_km", "corrected_local_km", "reference_local_km",
        "legacy_minus_reference_km", "corrected_minus_reference_km",
    ], total_rows)

    old_total = sum(v["legacy"] for v in by_driver.values())
    new_total = sum(v["corrected"] for v in by_driver.values())
    truth_total = sum(v["reference"] for v in by_driver.values())
    all_fixed_pass = max_fixed_error <= TOLERANCE_KM
    lines = [
        "# Synthetic before/after distance comparison",
        "",
        "> Synthetic data, fictional scenario. Assessment exercise only.",
        "",
        f"- Legacy total (UTC day basis): **{old_total:.6f} km**.",
        f"- Corrected total (local UTC+9 day basis): **{new_total:.6f} km**.",
        f"- Independent clean reference total: **{truth_total:.6f} km**.",
        f"- Maximum absolute corrected per-driver/day error: **{max_fixed_error:.6f} km**; tolerance **{TOLERANCE_KM:.3f} km**; result **{'PASS' if all_fixed_pass else 'FAIL'}**.",
        "- Legacy values are keyed by their UTC report date; corrected and reference values use the same-named local UTC+9 date. This intentionally exposes the old day-cut mismatch.",
        "",
        "## Driver totals",
        "",
        "| Driver | Legacy UTC km | Corrected local km | Reference local km | Legacy − reference km | Corrected − reference km |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in total_rows:
        lines.append(
            f"| {row['driver_id']} | {row['legacy_utc_km']} | {row['corrected_local_km']} | {row['reference_local_km']} | {row['legacy_minus_reference_km']} | {row['corrected_minus_reference_km']} |"
        )
    lines += [
        "",
        "## Driver/day rows",
        "",
        "| Driver | Day label | Legacy UTC km | Corrected local km | Reference local km | Legacy error km | Corrected error km |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            f"| {row['driver_id']} | {row['day']} | {row['legacy_utc_km']} | {row['corrected_local_km']} | {row['reference_local_km']} | {row['legacy_minus_reference_km']} | {row['corrected_minus_reference_km']} |"
        )
    lines += [
        "",
        "Full precision rows are in `results/before_after.csv`; the separate driver total file is `results/driver_totals.csv`.",
        "",
    ]
    SUMMARY.write_text("\n".join(lines), encoding="utf-8")
    print(f"Legacy total: {old_total:.6f} km (UTC day basis).")
    print(f"Corrected total: {new_total:.6f} km (local UTC+9).")
    print(f"Independent truth: {truth_total:.6f} km.")
    print(f"Maximum corrected driver/day error: {max_fixed_error:.6f} km; tolerance {TOLERANCE_KM:.3f} km; {'PASS' if all_fixed_pass else 'FAIL'}.")
    print(f"Wrote {len(rows)} driver/day rows to {COMPARISON.relative_to(ROOT)} and {len(total_rows)} driver totals.")
    if not all_fixed_pass:
        raise SystemExit("FAIL: corrected output is outside truth tolerance")


if __name__ == "__main__":
    main()
