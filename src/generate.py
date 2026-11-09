"""Generate reproducible, fictional GPS pings and independent truth outputs.

Run from the project root with: python3 src/generate.py
Uses only the Python standard library.
"""

from __future__ import annotations

import csv
import math
import random
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RESULTS = ROOT / "results"
SEED = 42
UTC_PLUS_9 = timezone(timedelta(hours=9))
EARTH_RADIUS_M = 6_371_008.8
ORIGIN_LAT = 35.6
ORIGIN_LON = 139.6
M_PER_DEG_LAT = 111_320.0
M_PER_DEG_LON = M_PER_DEG_LAT * math.cos(math.radians(ORIGIN_LAT))
GRID_MIN_M = 0.0
GRID_MAX_M = 8_000.0
ROAD_SPACING_M = 1_000.0
ZONE = (2_000.0, 2_000.0, 6_000.0, 6_000.0)  # xmin, ymin, xmax, ymax
SERVICE_DATES = (date(2026, 3, 2), date(2026, 3, 3), date(2026, 3, 4))
POLL_SECONDS = 10
TRUTH_SUBSTEPS = 2_000
CONVERGENCE_SUBSTEPS = 8_000
TRUTH_TOLERANCE_KM = 0.002

DRIVERS = {
    "DRV-001": {"y": 3_000.0, "start_x": 800.0, "shifts": (("08:30", "09:30"),)},
    "DRV-002": {"y": 4_000.0, "start_x": 2_200.0, "shifts": (("23:30", "00:30"),)},
    "DRV-003": {"y": 5_000.0, "start_x": 4_000.0, "shifts": (("14:00", "15:00"),)},
    "DRV-004": {"y": 3_000.0, "start_x": 6_500.0, "shifts": (("08:45", "09:45"),)},
    "DRV-005": {
        "y": 7_000.0,
        "start_x": 1_500.0,
        "shifts": (("18:00", "19:00"), ("23:45", "00:15")),
    },
}


def iso_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_clock(value: str) -> time:
    hour, minute = (int(part) for part in value.split(":"))
    return time(hour, minute)


def shift_datetimes(service_day: date, start_text: str, end_text: str) -> tuple[datetime, datetime]:
    start_local = datetime.combine(service_day, parse_clock(start_text), UTC_PLUS_9)
    end_day = service_day + timedelta(days=1) if parse_clock(end_text) <= parse_clock(start_text) else service_day
    end_local = datetime.combine(end_day, parse_clock(end_text), UTC_PLUS_9)
    return start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc)


def to_latlon(x: float, y: float) -> tuple[float, float]:
    lat = ORIGIN_LAT + y / M_PER_DEG_LAT
    lon = ORIGIN_LON + x / M_PER_DEG_LON
    return round(lat, 7), round(lon, 7)


def to_local_xy(lat: float, lon: float) -> tuple[float, float]:
    return (lon - ORIGIN_LON) * M_PER_DEG_LON, (lat - ORIGIN_LAT) * M_PER_DEG_LAT


def haversine_m(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lon1 = map(math.radians, a)
    lat2, lon2 = map(math.radians, b)
    dlat, dlon = lat2 - lat1, lon2 - lon1
    value = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(value))


def nearest_road_m(x: float, y: float) -> float:
    """Distance to the nearest finite segment in the fictional orthogonal grid."""
    xs = [GRID_MIN_M + i * ROAD_SPACING_M for i in range(9)]
    best = math.inf
    for road_y in xs:
        dx = max(GRID_MIN_M - x, 0.0, x - GRID_MAX_M)
        best = min(best, math.hypot(dx, y - road_y))
    for road_x in xs:
        dy = max(GRID_MIN_M - y, 0.0, y - GRID_MAX_M)
        best = min(best, math.hypot(x - road_x, dy))
    return best


def in_zone(x: float, y: float) -> bool:
    xmin, ymin, xmax, ymax = ZONE
    return xmin <= x <= xmax and ymin <= y <= ymax


def route_shifts(rng: random.Random) -> list[dict]:
    clean: list[dict] = []
    for driver, setup in DRIVERS.items():
        x = setup["start_x"]
        direction = 1.0
        y = setup["y"]
        for service_day in SERVICE_DATES:
            for start_text, end_text in setup["shifts"]:
                start_utc, end_utc = shift_datetimes(service_day, start_text, end_text)
                total_steps = int((end_utc - start_utc).total_seconds() // POLL_SECONDS)
                speed_mps = rng.uniform(20.0, 60.0) / 3.6
                for step in range(total_steps + 1):
                    if step and step % 6 == 0:
                        speed_mps = rng.uniform(20.0, 60.0) / 3.6
                    ts = start_utc + timedelta(seconds=step * POLL_SECONDS)
                    clean.append({"driver_id": driver, "timestamp": ts, "x": x, "y": y})
                    if step < total_steps:
                        # Reflect at x=500/7500; the entire trajectory remains on one horizontal road.
                        proposed = x + direction * speed_mps * POLL_SECONDS
                        if proposed > 7_500.0:
                            x = 7_500.0 - (proposed - 7_500.0)
                            direction = -1.0
                        elif proposed < 500.0:
                            x = 500.0 + (500.0 - proposed)
                            direction = 1.0
                        else:
                            x = proposed
                # Keep a deterministic low-variance path while preserving parked location.
    return clean


def choose_offroad_point(x: float, y: float) -> tuple[float, float]:
    """Move a spurious fix to a nearby grid-cell center, safely >100 m from roads."""
    centers = [500.0 + i * ROAD_SPACING_M for i in range(8)]
    cx = min(centers, key=lambda value: abs(value - x))
    cy = min(centers, key=lambda value: abs(value - y))
    candidate = (cx, cy)
    if nearest_road_m(*candidate) <= 100.0:
        raise RuntimeError(f"off-road generator selected a point too close to roads: {candidate}")
    return candidate


def make_inputs(clean: list[dict]) -> list[dict]:
    rng = random.Random(SEED)
    records: list[dict] = []
    source_records: list[dict] = []
    for serial, row in enumerate(clean):
        lat, lon = to_latlon(row["x"], row["y"])
        source = {
            "serial": serial,
            "driver_id": row["driver_id"],
            "timestamp": row["timestamp"],
            "received": row["timestamp"] + timedelta(seconds=rng.randint(1, 5)),
            "lat": lat,
            "lon": lon,
            "x": row["x"],
            "y": row["y"],
            "kind": "true",
            "source_serial": serial,
        }
        source_records.append(source)

    count = len(source_records)
    indexes = list(range(count))
    rng.shuffle(indexes)
    offroad_n = max(1, round(count * 0.015))
    speed_n = max(1, round(count * 0.015))
    exact_dup_n = max(1, round(count * 0.020))
    conflict_dup_n = max(1, round(count * 0.010))
    late_n = max(1, round(count * 0.050))
    offroad_ids = set(indexes[:offroad_n])
    speed_ids = set(indexes[offroad_n : offroad_n + speed_n])
    exact_ids = set(indexes[offroad_n + speed_n : offroad_n + speed_n + exact_dup_n])
    conflict_ids = set(indexes[offroad_n + speed_n + exact_dup_n : offroad_n + speed_n + exact_dup_n + conflict_dup_n])
    late_ids = set(indexes[-late_n:])

    for i, source in enumerate(source_records):
        if i in late_ids:
            source["received"] = source["timestamp"] + timedelta(seconds=rng.randint(60, 1_800))
            source["faults"] = [("late", "received 60–1800 seconds after event time")]
        else:
            source["faults"] = []
        records.append(source)

        if i in offroad_ids:
            ox, oy = choose_offroad_point(source["x"], source["y"])
            olat, olon = to_latlon(ox, oy)
            event_time = source["timestamp"] + timedelta(seconds=5)
            records.append({
                "serial": count + len(records), "driver_id": source["driver_id"],
                "timestamp": event_time,
                "received": event_time + timedelta(seconds=rng.randint(1, 5)),
                "lat": olat, "lon": olon, "x": ox, "y": oy,
                "kind": "noise_offroad", "source_serial": i,
                "faults": [("noise_offroad", f"{nearest_road_m(ox, oy):.1f} m from nearest road")],
            })
        elif i in speed_ids:
            sign = 1.0 if source["x"] < 7_000.0 else -1.0
            sx = source["x"] + sign * 900.0
            if sx > GRID_MAX_M:
                sx = source["x"] - 900.0
            slat, slon = to_latlon(sx, source["y"])
            event_time = source["timestamp"] + timedelta(seconds=5)
            records.append({
                "serial": count + len(records), "driver_id": source["driver_id"],
                "timestamp": event_time,
                "received": event_time + timedelta(seconds=rng.randint(1, 5)),
                "lat": slat, "lon": slon, "x": sx, "y": source["y"],
                "kind": "noise_speed", "source_serial": i,
                "faults": [("noise_speed", "on-road 900 m jump in five seconds")],
            })

        if i in exact_ids:
            delay = rng.randint(1, 30)
            records.append({
                "serial": count + len(records), "driver_id": source["driver_id"],
                "timestamp": source["timestamp"], "received": source["received"] + timedelta(seconds=delay),
                "lat": source["lat"], "lon": source["lon"], "x": source["x"], "y": source["y"],
                "kind": "duplicate_exact", "source_serial": i,
                "faults": [("duplicate_exact", f"exact copy; received {delay} seconds after original")],
            })
        if i in conflict_ids:
            delay = rng.randint(1, 30)
            jitter = rng.choice((-1.0, 1.0)) * rng.uniform(5.0, 30.0)
            cx = source["x"] + jitter
            clat, clon = to_latlon(cx, source["y"])
            records.append({
                "serial": count + len(records), "driver_id": source["driver_id"],
                "timestamp": source["timestamp"], "received": source["received"] + timedelta(seconds=delay),
                "lat": clat, "lon": clon, "x": cx, "y": source["y"],
                "kind": "duplicate_conflict", "source_serial": i,
                "faults": [("duplicate_conflict", f"coordinate jitter {abs(jitter):.1f} m")],
            })

    # Arrival order is intentionally different from event-time order for delayed fixes.
    records.sort(key=lambda row: (row["received"], row["timestamp"], row["driver_id"], row["serial"]))
    return records


def independent_truth(clean: list[dict], substeps: int) -> dict[tuple[str, str], tuple[float, float]]:
    """Numerically integrate clean segments without importing the calculation under test."""
    totals: dict[tuple[str, str], list[float]] = defaultdict(lambda: [0.0, 0.0])
    by_driver: dict[str, list[dict]] = defaultdict(list)
    for row in clean:
        by_driver[row["driver_id"]].append(row)
    for driver, rows in by_driver.items():
        rows.sort(key=lambda row: row["timestamp"])
        for row in rows:
            local_day = row["timestamp"].astimezone(UTC_PLUS_9).date().isoformat()
            totals[(driver, local_day)]  # retain zero-distance driver-days
        for a, b in zip(rows, rows[1:]):
            point_a = (a["lat"], a["lon"])
            point_b = (b["lat"], b["lon"])
            segment_m = haversine_m(point_a, point_b)
            if segment_m == 0:
                continue
            dt_s = (b["timestamp"] - a["timestamp"]).total_seconds()
            ax, ay = to_local_xy(*point_a)
            bx, by = to_local_xy(*point_b)
            # Split at each local midnight first. Sampling then needs only a date
            # lookup per piece instead of a datetime conversion for every substep.
            cuts = [a["timestamp"]]
            cursor_day = a["timestamp"].astimezone(UTC_PLUS_9).date()
            while True:
                next_midnight = datetime.combine(cursor_day + timedelta(days=1), time(0), UTC_PLUS_9).astimezone(timezone.utc)
                if next_midnight >= b["timestamp"]:
                    break
                if next_midnight > cuts[-1]:
                    cuts.append(next_midnight)
                cursor_day += timedelta(days=1)
            cuts.append(b["timestamp"])
            for piece_start, piece_end in zip(cuts, cuts[1:]):
                f0 = (piece_start - a["timestamp"]).total_seconds() / dt_s
                f1 = (piece_end - a["timestamp"]).total_seconds() / dt_s
                local_date = piece_start.astimezone(UTC_PLUS_9).date().isoformat()
                piece_m = segment_m * (f1 - f0)
                tick_m = piece_m / substeps
                for step in range(substeps):
                    fraction = f0 + (step + 0.5) / substeps * (f1 - f0)
                    mx = ax + (bx - ax) * fraction
                    my = ay + (by - ay) * fraction
                    totals[(driver, local_date)][1] += tick_m / 1_000.0
                    if in_zone(mx, my):
                        totals[(driver, local_date)][0] += tick_m / 1_000.0
    return {key: (values[0], values[1]) for key, values in totals.items()}


def write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    RESULTS.mkdir(parents=True, exist_ok=True)
    clean_raw = route_shifts(random.Random(SEED))
    clean: list[dict] = []
    for row in clean_raw:
        lat, lon = to_latlon(row["x"], row["y"])
        clean.append({**row, "lat": lat, "lon": lon})

    records = make_inputs(clean)
    ping_rows = []
    manifest_rows = []
    for ping_index, row in enumerate(records, 1):
        ping_id = f"P{ping_index:07d}"
        ping_rows.append({
            "dataset": "SYNTHETIC", "ping_id": ping_id, "driver_id": row["driver_id"],
            "timestamp_utc": iso_utc(row["timestamp"]), "received_at_utc": iso_utc(row["received"]),
            "lat": f"{row['lat']:.7f}", "lon": f"{row['lon']:.7f}",
        })
        for fault_type, detail in row.get("faults", []):
            manifest_rows.append({
                "ping_id": ping_id, "driver_id": row["driver_id"], "fault_type": fault_type, "detail": detail,
            })

    true_rows = [
        {"driver_id": row["driver_id"], "timestamp_utc": iso_utc(row["timestamp"]),
         "lat": f"{row['lat']:.7f}", "lon": f"{row['lon']:.7f}"}
        for row in sorted(clean, key=lambda item: (item["driver_id"], item["timestamp"]))
    ]
    write_csv(DATA / "pings_SYNTHETIC.csv",
              ["dataset", "ping_id", "driver_id", "timestamp_utc", "received_at_utc", "lat", "lon"], ping_rows)
    write_csv(DATA / "true_pings_SYNTHETIC.csv",
              ["driver_id", "timestamp_utc", "lat", "lon"], true_rows)
    manifest_rows.sort(key=lambda row: row["ping_id"])
    write_csv(DATA / "fault_manifest_SYNTHETIC.csv",
              ["ping_id", "driver_id", "fault_type", "detail"], manifest_rows)

    truth_rows_internal = [
        {"driver_id": row["driver_id"], "timestamp": row["timestamp"],
         "lat": row["lat"], "lon": row["lon"]}
        for row in clean
    ]
    truth = independent_truth(truth_rows_internal, TRUTH_SUBSTEPS)
    convergence = independent_truth(truth_rows_internal, CONVERGENCE_SUBSTEPS)
    all_keys = sorted(set(truth) | set(convergence))
    diffs = [(key, abs(truth.get(key, (0.0, 0.0))[0] - convergence.get(key, (0.0, 0.0))[0])) for key in all_keys]
    max_diff_km = max((diff for _, diff in diffs), default=0.0)
    truth_output = [
        {"driver_id": driver, "local_date": day,
         "true_km_in_zone": f"{truth.get((driver, day), (0.0, 0.0))[0]:.6f}",
         "true_km_total": f"{truth.get((driver, day), (0.0, 0.0))[1]:.6f}"}
        for driver, day in all_keys
    ]
    write_csv(DATA / "ground_truth_SYNTHETIC.csv",
              ["driver_id", "local_date", "true_km_in_zone", "true_km_total"], truth_output)

    fault_counts: dict[str, int] = defaultdict(int)
    for row in manifest_rows:
        fault_counts[row["fault_type"]] += 1
    summary = [
        "# Synthetic data generation summary",
        "",
        "> Synthetic data, fictional scenario. Assessment exercise only.",
        "",
        f"- Random seed: `{SEED}`.",
        f"- Noisy arrival-order pings: {len(ping_rows)}.",
        f"- Clean true pings: {len(true_rows)}.",
        f"- Fault manifest entries: {len(manifest_rows)}.",
        f"- Fault counts: {', '.join(f'{name}={fault_counts.get(name, 0)}' for name in ('noise_offroad', 'noise_speed', 'duplicate_exact', 'duplicate_conflict', 'late'))}.",
        "- Fictional roads: finite horizontal/vertical grid from 0 to 8,000 m in each axis, spaced 1,000 m apart.",
        "- Fictional campaign zone: closed rectangle from x=2,000–6,000 m and y=2,000–6,000 m; boundary is inside.",
        f"- Local coordinate origin: {ORIGIN_LAT:.4f}° latitude, {ORIGIN_LON:.4f}° longitude; serialized lat/lon rounded to seven decimals.",
        "- Drivers: DRV-001 through DRV-005. Service dates: 2026-03-02 through 2026-03-04 (local UTC+9).",
        "- Shifts (local): DRV-001 08:30–09:30; DRV-002 23:30–00:30; DRV-003 14:00–15:00; DRV-004 08:45–09:45; DRV-005 18:00–19:00 and 23:45–00:15.",
        "- Clean routes travel along a horizontal grid road. DRV-001 to DRV-004 use roads inside the zone; DRV-005 uses an outside-zone road. Speeds are drawn from 20–60 km/h and redrawn every minute; vehicles remain parked at their final point between shifts.",
        "- Fault injection rates (rounded to records): off-road 1.5%, speed 1.5%, exact duplicate 2%, conflicting duplicate 1%, late arrival 5%. Noise fixes are extra records at event time +5 seconds; off-road fixes are at grid-cell centers; speed spikes jump 900 m on-road; conflicting duplicates shift 5–30 m; copies arrive 1–30 seconds after their source; ordinary receipt delay is 1–5 seconds and late receipt delay is 60–1,800 seconds.",
        f"- Sampled ground truth uses {TRUTH_SUBSTEPS:,} midpoint substeps per moving clean segment.",
        f"- Convergence check at {CONVERGENCE_SUBSTEPS:,} substeps: max driver-day difference `{max_diff_km:.6f} km` (tolerance `{TRUTH_TOLERANCE_KM:.3f} km`).",
        "- The truth code is independent of the future corrected calculator; it reads only the clean trajectory and geometry constants in this file.",
        "- Calculations and distance assumptions are described in `PROJECT_SPEC.md`.",
        "",
    ]
    (DATA / "README.md").write_text("\n".join(summary), encoding="utf-8")
    (RESULTS / "truth_convergence.txt").write_text(
        f"Synthetic truth convergence: {'PASS' if max_diff_km <= TRUTH_TOLERANCE_KM else 'FAIL'}\n"
        f"Base substeps: {TRUTH_SUBSTEPS}\nComparison substeps: {CONVERGENCE_SUBSTEPS}\n"
        f"Maximum driver-day difference: {max_diff_km:.9f} km\nTolerance: {TRUTH_TOLERANCE_KM:.9f} km\n",
        encoding="utf-8",
    )
    print(f"Generated {len(ping_rows)} synthetic pings ({len(true_rows)} clean true pings).")
    print("Fault counts: " + ", ".join(f"{name}={fault_counts.get(name, 0)}" for name in (
        "noise_offroad", "noise_speed", "duplicate_exact", "duplicate_conflict", "late")))
    print(f"Truth convergence max difference: {max_diff_km:.6f} km; tolerance {TRUTH_TOLERANCE_KM:.3f} km.")
    if len(ping_rows) < 2_000:
        raise SystemExit("FAIL: synthetic dataset has fewer than 2,000 pings")
    expected_faults = {"noise_offroad", "noise_speed", "duplicate_exact", "duplicate_conflict", "late"}
    if not expected_faults.issubset(fault_counts):
        raise SystemExit(f"FAIL: missing fault types: {sorted(expected_faults - set(fault_counts))}")
    if max_diff_km > TRUTH_TOLERANCE_KM:
        raise SystemExit("FAIL: independent truth did not converge within tolerance")


if __name__ == "__main__":
    main()
