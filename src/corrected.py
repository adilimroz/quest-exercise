"""Corrected GPS distance calculation for the fictional QA exercise.

Run from the project root with: python3 src/corrected.py
The calculation reads pings and documented geometry only, never the fault manifest.
"""

from __future__ import annotations

import csv
import math
from collections import defaultdict
from datetime import datetime, time, timedelta, timezone
from pathlib import Path

from generate import haversine_m, nearest_road_m, to_local_xy


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data" / "pings_SYNTHETIC.csv"
OUTPUT = ROOT / "results" / "fixed_km.csv"
REJECTIONS = ROOT / "results" / "fixed_rejections.csv"
UTC_PLUS_9 = timezone(timedelta(hours=9))
OFFROAD_LIMIT_M = 100.0
SPEED_LIMIT_KMH = 150.0
ZONE = (2_000.0, 2_000.0, 6_000.0, 6_000.0)  # xmin, ymin, xmax, ymax


def parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def read_pings() -> list[dict]:
    with INPUT.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        row["time"] = parse_utc(row["timestamp_utc"])
        row["received"] = parse_utc(row["received_at_utc"])
        row["lat_value"] = float(row["lat"])
        row["lon_value"] = float(row["lon"])
    return rows


def remove_duplicates(rows: list[dict]) -> tuple[list[dict], int]:
    groups: dict[tuple[str, datetime], list[dict]] = defaultdict(list)
    for row in rows:
        groups[(row["driver_id"], row["time"])].append(row)
    chosen = []
    duplicate_count = 0
    for group in groups.values():
        group.sort(key=lambda row: (row["received"], row["ping_id"]))
        chosen.append(group[0])
        duplicate_count += len(group) - 1
    chosen.sort(key=lambda row: (row["driver_id"], row["time"], row["received"], row["ping_id"]))
    return chosen, duplicate_count


def clip_to_zone(a: tuple[float, float], b: tuple[float, float]) -> tuple[float, float]:
    """Return Liang–Barsky segment parameters for the rectangle intersection."""
    xmin, ymin, xmax, ymax = ZONE
    dx, dy = b[0] - a[0], b[1] - a[1]
    lower, upper = 0.0, 1.0
    for p, q in ((-dx, a[0] - xmin), (dx, xmax - a[0]),
                 (-dy, a[1] - ymin), (dy, ymax - a[1])):
        if p == 0:
            if q < 0:
                return 0.0, 0.0
            continue
        ratio = q / p
        if p < 0:
            lower = max(lower, ratio)
        else:
            upper = min(upper, ratio)
        if lower > upper:
            return 0.0, 0.0
    return max(0.0, lower), min(1.0, upper)


def interpolate(a: dict, b: dict, fraction: float) -> tuple[float, float]:
    return (
        a["lat_value"] + (b["lat_value"] - a["lat_value"]) * fraction,
        a["lon_value"] + (b["lon_value"] - a["lon_value"]) * fraction,
    )


def local_midnight_cuts(start: datetime, end: datetime) -> list[datetime]:
    cuts = [start]
    local_date = start.astimezone(UTC_PLUS_9).date()
    while True:
        midnight_utc = datetime.combine(local_date + timedelta(days=1), time(0), UTC_PLUS_9).astimezone(timezone.utc)
        if midnight_utc >= end:
            break
        if midnight_utc > start:
            cuts.append(midnight_utc)
        local_date += timedelta(days=1)
    cuts.append(end)
    return cuts


def segment_zone_km(a: dict, b: dict, start: datetime, end: datetime) -> float:
    dt_s = (end - start).total_seconds()
    if dt_s <= 0:
        return 0.0
    frac_start = (start - a["time"]).total_seconds() / (b["time"] - a["time"]).total_seconds()
    frac_end = (end - a["time"]).total_seconds() / (b["time"] - a["time"]).total_seconds()
    ll_a = interpolate(a, b, frac_start)
    ll_b = interpolate(a, b, frac_end)
    piece_km = haversine_m(ll_a, ll_b) / 1_000.0
    xy_a = to_local_xy(*ll_a)
    xy_b = to_local_xy(*ll_b)
    projected_length = math.hypot(xy_b[0] - xy_a[0], xy_b[1] - xy_a[1])
    if projected_length == 0.0:
        return 0.0
    enter, leave = clip_to_zone(xy_a, xy_b)
    if leave <= enter:
        return 0.0
    intersection_length = (leave - enter) * projected_length
    return piece_km * (intersection_length / projected_length)


def compute(rows: list[dict]) -> tuple[list[dict], list[dict], dict[str, int]]:
    unique, duplicates_removed = remove_duplicates(rows)
    totals: dict[tuple[str, str], float] = defaultdict(float)
    rejection_rows = []
    accepted_by_driver: dict[str, list[dict]] = defaultdict(list)
    stats = {"input_pings": len(rows), "duplicates_removed": duplicates_removed,
             "rejected_offroad": 0, "rejected_speed": 0, "accepted": 0}

    # R3: evaluate in event-time order; a rejected point never replaces last_accepted.
    for row in unique:
        x, y = to_local_xy(row["lat_value"], row["lon_value"])
        road_distance = nearest_road_m(x, y)
        if road_distance > OFFROAD_LIMIT_M:
            stats["rejected_offroad"] += 1
            rejection_rows.append({
                "ping_id": row["ping_id"], "driver_id": row["driver_id"],
                "timestamp_utc": row["timestamp_utc"], "reason": "offroad",
                "measured": f"{road_distance:.3f} m from nearest road",
            })
            continue
        trace = accepted_by_driver[row["driver_id"]]
        if trace:
            previous = trace[-1]
            dt_s = (row["time"] - previous["time"]).total_seconds()
            speed = haversine_m((previous["lat_value"], previous["lon_value"]),
                                (row["lat_value"], row["lon_value"])) / dt_s * 3.6
            if speed > SPEED_LIMIT_KMH:
                stats["rejected_speed"] += 1
                rejection_rows.append({
                    "ping_id": row["ping_id"], "driver_id": row["driver_id"],
                    "timestamp_utc": row["timestamp_utc"], "reason": "speed",
                    "measured": f"{speed:.3f} km/h from {previous['ping_id']}",
                })
                continue
        trace.append(row)
        stats["accepted"] += 1

    # R4–R6: connect accepted fixes, split at local midnight, clip each piece.
    driver_days: set[tuple[str, str]] = set()
    for driver, trace in accepted_by_driver.items():
        for row in trace:
            local_day = row["time"].astimezone(UTC_PLUS_9).date().isoformat()
            driver_days.add((driver, local_day))
            totals[(driver, local_day)] += 0.0
        for a, b in zip(trace, trace[1:]):
            cuts = local_midnight_cuts(a["time"], b["time"])
            for piece_start, piece_end in zip(cuts, cuts[1:]):
                day = piece_start.astimezone(UTC_PLUS_9).date().isoformat()
                driver_days.add((driver, day))
                totals[(driver, day)] += segment_zone_km(a, b, piece_start, piece_end)

    output = [
        {"driver_id": driver, "day": day, "day_basis": "local_utc+9",
         "km_in_zone": f"{totals.get((driver, day), 0.0):.6f}"}
        for driver, day in sorted(driver_days)
    ]
    return output, rejection_rows, stats


def main() -> None:
    rows = read_pings()
    output, rejected, stats = compute(rows)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["driver_id", "day", "day_basis", "km_in_zone"],
                                lineterminator="\n")
        writer.writeheader()
        writer.writerows(output)
    with REJECTIONS.open("w", newline="", encoding="utf-8") as handle:
        fields = ["ping_id", "driver_id", "timestamp_utc", "reason", "measured"]
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(sorted(rejected, key=lambda row: (row["driver_id"], row["timestamp_utc"], row["ping_id"])))
    total = sum(float(row["km_in_zone"]) for row in output)
    print(f"Fixed calculation: {stats['accepted']} accepted, {stats['duplicates_removed']} duplicates removed, "
          f"{stats['rejected_offroad']} off-road and {stats['rejected_speed']} speed rejects.")
    print(f"Wrote {len(output)} local driver/day rows; corrected billed distance: {total:.6f} km.")
    print(f"Rejected-ping evidence: {REJECTIONS.relative_to(ROOT)}.")


if __name__ == "__main__":
    main()
