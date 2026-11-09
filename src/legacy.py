"""Intentionally incorrect distance reference for the fictional QA exercise.

Run from the project root with: python3 src/legacy.py
This is an evidence baseline, not a corrected or production-safe calculator.
"""

from __future__ import annotations

import csv
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from generate import haversine_m, in_zone, to_local_xy


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data" / "pings_SYNTHETIC.csv"
OUTPUT = ROOT / "results" / "legacy_km.csv"


def parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def compute_legacy(rows: list[dict]) -> list[dict]:
    totals: dict[tuple[str, str], float] = defaultdict(float)
    last_by_driver: dict[str, dict] = {}

    for row in rows:  # LEGACY-F3: preserve received/ingestion order instead of event-time order.
        driver = row["driver_id"]
        current_time = parse_utc(row["timestamp_utc"])
        current = {
            **row,
            "time": current_time,
            "lat": float(row["lat"]),
            "lon": float(row["lon"]),
        }
        previous = last_by_driver.get(driver)
        if previous is not None:
            # LEGACY-F1: every received point is accepted, including GPS noise.
            # LEGACY-F2: duplicate timestamps/copies are never removed.
            distance_km = haversine_m((previous["lat"], previous["lon"]),
                                      (current["lat"], current["lon"])) / 1_000.0
            x, y = to_local_xy(previous["lat"], previous["lon"])
            # LEGACY-F5: count the entire segment only when its start point is in-zone.
            billed_km = distance_km if in_zone(x, y) else 0.0
            # LEGACY-F4: assign the whole segment to its start timestamp's UTC date.
            day = previous["time"].date().isoformat()
            totals[(driver, day)] += billed_km
        last_by_driver[driver] = current

    return [
        {"driver_id": driver, "day": day, "day_basis": "utc", "km_in_zone": f"{km:.6f}"}
        for (driver, day), km in sorted(totals.items())
    ]


def main() -> None:
    with INPUT.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    result = compute_legacy(rows)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["driver_id", "day", "day_basis", "km_in_zone"],
                                lineterminator="\n")
        writer.writeheader()
        writer.writerows(result)
    total = sum(float(row["km_in_zone"]) for row in result)
    print(f"Wrote {len(result)} driver/UTC-day rows to {OUTPUT.relative_to(ROOT)}.")
    print(f"Legacy billed distance: {total:.6f} km (intentionally incorrect baseline).")


if __name__ == "__main__":
    main()
