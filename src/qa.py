"""Small, manifest-blind QA checker for synthetic GPS pings.

Run from the project root:
  python3 src/qa.py
  python3 src/qa.py --clean

The checker detects from ping fields only. Manifest comparison is in evaluate.py.
"""

from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

from generate import haversine_m, in_zone, nearest_road_m, to_local_xy


ROOT = Path(__file__).resolve().parents[1]
UTC_PLUS_9 = timezone(timedelta(hours=9))
THRESHOLD_OFFROAD_M = 100.0
THRESHOLD_SPEED_KMH = 150.0
LATE_AFTER_SECONDS = 60
FIELDS = [
    "check_id", "fault_type", "ping_id", "driver_id", "timestamp_utc",
    "related_ping_id", "measured_value", "threshold", "detail",
]


def parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def iso_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_rows(path: Path, clean: bool) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    for index, row in enumerate(rows, 1):
        if clean:
            row["ping_id"] = f"T{index:07d}"
            row["received_at_utc"] = row["timestamp_utc"]
            row["dataset"] = "SYNTHETIC"
        row["time"] = parse_utc(row["timestamp_utc"])
        row["received"] = parse_utc(row["received_at_utc"])
        row["lat_value"] = float(row["lat"])
        row["lon_value"] = float(row["lon"])
        row["x"], row["y"] = to_local_xy(row["lat_value"], row["lon_value"])
    return rows


def finding(check_id: str, fault_type: str, row: dict, detail: str,
            related: str = "", measured: str = "", threshold: str = "") -> dict:
    return {
        "check_id": check_id,
        "fault_type": fault_type,
        "ping_id": row["ping_id"],
        "driver_id": row["driver_id"],
        "timestamp_utc": row["timestamp_utc"],
        "related_ping_id": related,
        "measured_value": measured,
        "threshold": threshold,
        "detail": detail,
    }


def deduplicate(rows: list[dict]) -> tuple[list[dict], list[dict]]:
    groups: dict[tuple[str, datetime], list[dict]] = defaultdict(list)
    for row in rows:
        groups[(row["driver_id"], row["time"])].append(row)
    keepers, duplicate_findings = [], []
    for key, group in groups.items():
        group.sort(key=lambda row: (row["received"], row["ping_id"]))
        keeper = group[0]
        keepers.append(keeper)
        for duplicate in group[1:]:
            exact = (duplicate["lat"], duplicate["lon"]) == (keeper["lat"], keeper["lon"])
            fault_type = "duplicate_exact" if exact else "duplicate_conflict"
            duplicate_findings.append(finding(
                "DUPLICATE", fault_type, duplicate,
                "same driver and event timestamp; earliest-received copy retained for analysis",
                related=keeper["ping_id"],
                measured="same coordinates" if exact else "coordinates differ",
                threshold="one record per driver/timestamp",
            ))
    keepers.sort(key=lambda row: (row["driver_id"], row["time"], row["received"], row["ping_id"]))
    return keepers, duplicate_findings


def segment_touches_zone_boundary(a: dict, b: dict) -> bool:
    """Return true when a segment has both in-zone and out-of-zone portions."""
    xmin, ymin, xmax, ymax = 2_000.0, 2_000.0, 6_000.0, 6_000.0
    dx, dy = b["x"] - a["x"], b["y"] - a["y"]
    lower, upper = 0.0, 1.0
    for p, q in ((-dx, a["x"] - xmin), (dx, xmax - a["x"]),
                 (-dy, a["y"] - ymin), (dy, ymax - a["y"])):
        if p == 0:
            if q < 0:
                return False
            continue
        ratio = q / p
        if p < 0:
            lower = max(lower, ratio)
        else:
            upper = min(upper, ratio)
        if lower > upper:
            return False
    return upper > lower and (lower > 0.0 or upper < 1.0)


def inspect(rows: list[dict]) -> list[dict]:
    findings: list[dict] = []

    # Arrival-order checks use the input order, which is sorted by received time.
    max_event_by_driver: dict[str, tuple[datetime, dict]] = {}
    for row in rows:
        previous_max = max_event_by_driver.get(row["driver_id"])
        if previous_max and row["time"] < previous_max[0]:
            findings.append(finding(
                "ARRIVAL_ORDER", "out_of_order", row,
                "event timestamp is older than a previously received ping",
                related=previous_max[1]["ping_id"],
                measured=f"{(previous_max[0] - row['time']).total_seconds():.0f} s behind",
                threshold="timestamps should not regress in arrival order",
            ))
        if row["received"] > row["time"]:
            delay = (row["received"] - row["time"]).total_seconds()
            if delay >= LATE_AFTER_SECONDS:
                findings.append(finding(
                    "LATE_ARRIVAL", "late", row,
                    "received substantially after its event timestamp",
                    measured=f"{delay:.0f} s", threshold=f">={LATE_AFTER_SECONDS} s",
                ))
        if previous_max is None or row["time"] > previous_max[0]:
            max_event_by_driver[row["driver_id"]] = (row["time"], row)

    unique_rows, duplicate_findings = deduplicate(rows)
    findings.extend(duplicate_findings)

    # Apply observational noise checks in event-time order. Off-road takes precedence,
    # so one off-road spike is not also mislabeled as a speed-spike detection.
    accepted_by_driver: dict[str, list[dict]] = defaultdict(list)
    for row in unique_rows:
        road_distance = nearest_road_m(row["x"], row["y"])
        if road_distance > THRESHOLD_OFFROAD_M:
            findings.append(finding(
                "OFFROAD_NOISE", "noise_offroad", row,
                "point lies farther than the limit from every modeled road segment",
                measured=f"{road_distance:.1f} m", threshold=f"<={THRESHOLD_OFFROAD_M:.0f} m",
            ))
            continue
        prior = accepted_by_driver[row["driver_id"]]
        if prior:
            previous = prior[-1]
            dt = (row["time"] - previous["time"]).total_seconds()
            if dt > 0:
                speed = haversine_m((previous["lat_value"], previous["lon_value"]),
                                    (row["lat_value"], row["lon_value"])) / dt * 3.6
                if speed > THRESHOLD_SPEED_KMH:
                    findings.append(finding(
                        "SPEED_NOISE", "noise_speed", row,
                        "implied speed from the last accepted point exceeds the limit",
                        related=previous["ping_id"], measured=f"{speed:.1f} km/h",
                        threshold=f"<={THRESHOLD_SPEED_KMH:.0f} km/h",
                    ))
                    continue
        prior.append(row)

    # Boundary scans are structural risk indicators, not injected-fault classifications.
    for driver, accepted in accepted_by_driver.items():
        for a, b in zip(accepted, accepted[1:]):
            local_a = a["time"].astimezone(UTC_PLUS_9).date()
            local_b = b["time"].astimezone(UTC_PLUS_9).date()
            if local_a != local_b:
                findings.append(finding(
                    "LOCAL_DAY_CROSSING", "day_boundary", b,
                    f"segment {a['ping_id']}→{b['ping_id']} crosses local midnight; split before daily reporting",
                    related=a["ping_id"], measured=f"{local_a.isoformat()} → {local_b.isoformat()}",
                    threshold="half-open local UTC+9 day",
                ))
            if segment_touches_zone_boundary(a, b):
                findings.append(finding(
                    "ZONE_CROSSING", "zone_boundary", b,
                    f"segment {a['ping_id']}→{b['ping_id']} has both in-zone and out-of-zone distance",
                    related=a["ping_id"], measured="segment intersects zone edge",
                    threshold="count only the in-zone portion",
                ))

    findings.sort(key=lambda row: (row["check_id"], row["driver_id"], row["timestamp_utc"], row["ping_id"]))
    return findings


def write_findings(path: Path, findings: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(findings)


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect synthetic GPS pings without reading the fault manifest.")
    parser.add_argument("--clean", action="store_true", help="check the clean true-ping sequence")
    args = parser.parse_args()
    input_path = ROOT / "data" / ("true_pings_SYNTHETIC.csv" if args.clean else "pings_SYNTHETIC.csv")
    output_path = ROOT / "results" / ("clean_findings.csv" if args.clean else "findings.csv")
    summary_path = ROOT / "results" / ("clean_qa_summary.md" if args.clean else "qa_summary.md")
    rows = read_rows(input_path, args.clean)
    findings = inspect(rows)
    write_findings(output_path, findings)
    counts = Counter(row["check_id"] for row in findings)
    lines = [
        "# Synthetic QA checker summary",
        "",
        "> Synthetic data, fictional scenario. Assessment exercise only.",
        "",
        f"- Input: `{input_path.relative_to(ROOT)}`.",
        f"- Pings inspected: {len(rows)}.",
        f"- Findings: {len(findings)}.",
        "- Checker reads ping fields and geometry only; it does not read the fault manifest.",
        "- Checks: arrival-order regression, delayed receipt, duplicate keys, off-road distance, implied speed, local-day crossings, zone crossings.",
        "",
        "| Check | Findings |",
        "| --- | ---: |",
    ]
    for check in sorted({row["check_id"] for row in findings}):
        lines.append(f"| {check} | {counts[check]} |")
    if not findings:
        lines.append("| none | 0 |")
    lines += [
        "",
        "## Example findings",
        "",
        "| Check | Ping | Related ping | Measurement | Why it was flagged |",
        "| --- | --- | --- | --- | --- |",
    ]
    for check in sorted({row["check_id"] for row in findings}):
        example = next(row for row in findings if row["check_id"] == check)
        lines.append(
            f"| {check} | {example['ping_id']} | {example['related_ping_id'] or '—'} | "
            f"{example['measured_value'] or '—'} | {example['detail']} |"
        )
    if not findings:
        lines.append("| none | — | — | — | No findings. |")
    lines += ["", f"Detailed rows: `{output_path.relative_to(ROOT)}`.", ""]
    summary_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Inspected {len(rows)} pings; wrote {len(findings)} findings to {output_path.relative_to(ROOT)}.")
    for check in sorted(counts):
        print(f"{check}: {counts[check]}")


if __name__ == "__main__":
    main()
