"""Regression contract for the synthetic GPS distance exercise.

Run from the project root:
  python3 tests/test_regression.py --impl fixed
  python3 tests/test_regression.py --impl legacy  # expected to fail

Expected values use stated points and the standalone haversine primitive; no
expected distance is obtained by calling either calculator under test.
"""

from __future__ import annotations

import argparse
import csv
import io
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

import corrected  # noqa: E402
import generate  # noqa: E402
import legacy  # noqa: E402


UTC = timezone.utc
SCENARIO_TOLERANCE_KM = 0.000002
TRUTH_TOLERANCE_KM = 0.002
DRIVER = "DRV-001"
IMPL = "fixed"


def utc(text: str) -> datetime:
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def stamp(value: datetime) -> str:
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def make_ping(driver: str, x: float, y: float, event: datetime, *,
              receive_delay_s: int = 1, received_at: datetime | None = None,
              ping_id: str = "") -> dict:
    lat = generate.ORIGIN_LAT + y / generate.M_PER_DEG_LAT
    lon = generate.ORIGIN_LON + x / generate.M_PER_DEG_LON
    received = received_at or event + timedelta(seconds=receive_delay_s)
    return {
        "dataset": "SYNTHETIC",
        "ping_id": ping_id,
        "driver_id": driver,
        "timestamp_utc": stamp(event),
        "received_at_utc": stamp(received),
        "lat": f"{lat:.12f}",
        "lon": f"{lon:.12f}",
        "time": event,
        "received": received,
        "lat_value": lat,
        "lon_value": lon,
    }


def ordered_arrival(rows: list[dict]) -> list[dict]:
    return sorted(rows, key=lambda row: (row["received"], row["timestamp_utc"], row["driver_id"], row["ping_id"]))


def expected_segment_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Independent expected distance between stated local-metre points."""
    lat_a = generate.ORIGIN_LAT + a[1] / generate.M_PER_DEG_LAT
    lon_a = generate.ORIGIN_LON + a[0] / generate.M_PER_DEG_LON
    lat_b = generate.ORIGIN_LAT + b[1] / generate.M_PER_DEG_LAT
    lon_b = generate.ORIGIN_LON + b[0] / generate.M_PER_DEG_LON
    return generate.haversine_m((lat_a, lon_a), (lat_b, lon_b)) / 1_000.0


def points(driver: str, start: datetime, values: list[tuple[float, float, int, int | None]]) -> list[dict]:
    """(x, y, event seconds from start, optional receipt seconds from start)."""
    output = []
    for index, (x, y, event_s, receive_s) in enumerate(values, 1):
        event = start + timedelta(seconds=event_s)
        received = start + timedelta(seconds=receive_s) if receive_s is not None else event + timedelta(seconds=1)
        output.append(make_ping(driver, x, y, event, received_at=received, ping_id=f"{driver}-P{index:02d}"))
    return ordered_arrival(output)


def calculate(rows: list[dict]) -> dict[tuple[str, str], float]:
    if IMPL == "fixed":
        result, _, _ = corrected.compute(rows)
    else:
        result = legacy.compute_legacy(ordered_arrival(rows))
    return {(row["driver_id"], row["day"]): float(row["km_in_zone"]) for row in result}


def read_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def attach_runtime_fields(row: dict) -> dict:
    result = dict(row)
    result["time"] = utc(row["timestamp_utc"])
    result["received"] = utc(row["received_at_utc"])
    result["lat_value"] = float(row["lat"])
    result["lon_value"] = float(row["lon"])
    return result


class GPSRegressionTests(unittest.TestCase):
    def assert_scenario(self, rows: list[dict], expected: dict[tuple[str, str], float],
                        tolerance: float = SCENARIO_TOLERANCE_KM) -> None:
        actual = calculate(rows)
        keys = set(expected) | {key for key, value in actual.items() if value != 0.0}
        for key in sorted(keys):
            self.assertAlmostEqual(actual.get(key, 0.0), expected.get(key, 0.0), delta=tolerance,
                                   msg=f"{key}: expected {expected.get(key, 0.0):.6f} km, got {actual.get(key, 0.0):.6f} km")

    def test_offroad_noise_is_ignored(self) -> None:
        start = utc("2026-03-02T03:00:00Z")
        rows = points(DRIVER, start, [(2400, 3000, 0, None), (2500, 3000, 10, None),
                                      (2500, 3500, 5, None), (2600, 3000, 20, None)])
        expected = expected_segment_km((2400, 3000), (2500, 3000)) + expected_segment_km((2500, 3000), (2600, 3000))
        self.assert_scenario(rows, {(DRIVER, "2026-03-02"): expected})

    def test_speed_noise_is_ignored(self) -> None:
        start = utc("2026-03-02T03:00:00Z")
        rows = points(DRIVER, start, [(2400, 3000, 0, None), (2500, 3000, 10, None),
                                      (3400, 3000, 15, None), (2600, 3000, 20, None)])
        expected = expected_segment_km((2400, 3000), (2500, 3000)) + expected_segment_km((2500, 3000), (2600, 3000))
        self.assert_scenario(rows, {(DRIVER, "2026-03-02"): expected})

    def test_offroad_threshold_is_strict(self) -> None:
        start = utc("2026-03-02T03:00:00Z")
        rows = points("DRV-001", start, [(2500, 3000, 0, None), (2500, 3099, 5, None), (2500, 3000, 10, None)])
        rows += points("DRV-002", start, [(2500, 3000, 0, None), (2500, 3101, 5, None), (2500, 3000, 10, None)])
        expected = expected_segment_km((2500, 3000), (2500, 3099)) * 2
        self.assert_scenario(ordered_arrival(rows), {("DRV-001", "2026-03-02"): expected,
                                                      ("DRV-002", "2026-03-02"): 0.0})

    def test_speeds_below_and_above_threshold(self) -> None:
        start = utc("2026-03-02T03:00:00Z")
        dx_149 = 149.0 * 1_000 / 3_600 * 10
        dx_151 = 151.0 * 1_000 / 3_600 * 10
        rows = points("DRV-001", start, [(2500, 3000, 0, None), (2500 + dx_149, 3000, 10, None)])
        rows += points("DRV-002", start, [(2500, 3000, 0, None), (2500 + dx_151, 3000, 10, None)])
        expected = expected_segment_km((2500, 3000), (2500 + dx_149, 3000))
        self.assert_scenario(ordered_arrival(rows), {("DRV-001", "2026-03-02"): expected,
                                                      ("DRV-002", "2026-03-02"): 0.0})

    def test_exact_duplicate_counts_once(self) -> None:
        start = utc("2026-03-02T03:00:00Z")
        rows = points(DRIVER, start, [(2400, 3000, 0, 1), (2500, 3000, 10, 11),
                                      (2600, 3000, 20, 21), (2400, 3000, 0, 25)])
        expected = expected_segment_km((2400, 3000), (2500, 3000)) + expected_segment_km((2500, 3000), (2600, 3000))
        self.assert_scenario(rows, {(DRIVER, "2026-03-02"): expected})

    def test_conflicting_duplicate_keeps_earliest_received(self) -> None:
        start = utc("2026-03-02T03:00:00Z")
        rows = points(DRIVER, start, [(2900, 3000, 0, 1), (3000, 3000, 10, 11),
                                      (3020, 3000, 10, 12), (3000, 3100, 20, 21)])
        expected = expected_segment_km((2900, 3000), (3000, 3000)) + expected_segment_km((3000, 3000), (3000, 3100))
        self.assert_scenario(rows, {(DRIVER, "2026-03-02"): expected})

    def test_late_ping_uses_event_timestamp(self) -> None:
        start = utc("2026-03-02T03:00:00Z")
        rows = points(DRIVER, start, [(2300, 3000, 0, 1), (2400, 3000, 10, 45),
                                      (2500, 3000, 20, 21), (2600, 3000, 30, 31)])
        expected = sum(expected_segment_km((x, 3000), (x + 100, 3000)) for x in (2300, 2400, 2500))
        self.assert_scenario(rows, {(DRIVER, "2026-03-02"): expected})

    def test_utc_midnight_still_uses_local_date(self) -> None:
        start = utc("2026-03-02T23:59:50Z")
        rows = points(DRIVER, start, [(2900, 3000, 0, None), (3000, 3000, 10, None), (3100, 3000, 20, None)])
        expected = expected_segment_km((2900, 3000), (3000, 3000)) + expected_segment_km((3000, 3000), (3100, 3000))
        self.assert_scenario(rows, {(DRIVER, "2026-03-03"): expected})

    def test_ping_exactly_at_local_midnight_starts_new_day(self) -> None:
        start = utc("2026-03-02T14:59:50Z")
        rows = points(DRIVER, start, [(2900, 3000, 0, None), (3000, 3000, 10, None), (3100, 3000, 20, None)])
        one = expected_segment_km((2900, 3000), (3000, 3000))
        self.assert_scenario(rows, {(DRIVER, "2026-03-02"): one, (DRIVER, "2026-03-03"): one})

    def test_segment_is_split_at_local_midnight(self) -> None:
        start = utc("2026-03-02T14:59:55Z")
        rows = points(DRIVER, start, [(2900, 3000, 0, None), (3000, 3000, 10, None)])
        first = expected_segment_km((2900, 3000), (2950, 3000))
        second = expected_segment_km((2950, 3000), (3000, 3000))
        self.assert_scenario(rows, {(DRIVER, "2026-03-02"): first, (DRIVER, "2026-03-03"): second})

    def test_zone_entry_is_clipped(self) -> None:
        start = utc("2026-03-02T03:00:00Z")
        rows = points(DRIVER, start, [(1900, 3000, 0, None), (2100, 3000, 10, None)])
        expected = expected_segment_km((2000, 3000), (2100, 3000))
        self.assert_scenario(rows, {(DRIVER, "2026-03-02"): expected})

    def test_zone_exit_is_clipped(self) -> None:
        start = utc("2026-03-02T03:00:00Z")
        rows = points(DRIVER, start, [(5900, 3000, 0, None), (6100, 3000, 10, None)])
        expected = expected_segment_km((5900, 3000), (6000, 3000))
        self.assert_scenario(rows, {(DRIVER, "2026-03-02"): expected})

    def test_zone_boundary_counts_as_inside(self) -> None:
        start = utc("2026-03-02T03:00:00Z")
        outside_to_edge = points("DRV-001", start, [(1900, 3000, 0, None), (2000, 3000, 10, None)])
        edge_to_inside = points("DRV-002", start, [(2000, 3000, 0, None), (2100, 3000, 10, None)])
        expected_inside = expected_segment_km((2000, 3000), (2100, 3000))
        self.assert_scenario(ordered_arrival(outside_to_edge + edge_to_inside), {
            ("DRV-001", "2026-03-02"): 0.0,
            ("DRV-002", "2026-03-02"): expected_inside,
        })

    def test_full_dataset_matches_truth_per_driver_day(self) -> None:
        source = [attach_runtime_fields(row) for row in read_csv(ROOT / "data" / "pings_SYNTHETIC.csv")]
        actual = calculate(source)
        reference_rows = read_csv(ROOT / "data" / "ground_truth_SYNTHETIC.csv")
        expected = {(row["driver_id"], row["local_date"]): float(row["true_km_in_zone"])
                    for row in reference_rows}
        self.assert_scenario(source, expected, tolerance=TRUTH_TOLERANCE_KM)
        for key, expected_km in expected.items():
            self.assertAlmostEqual(actual.get(key, 0.0), expected_km, delta=TRUTH_TOLERANCE_KM,
                                   msg=f"{key}: differs from independent truth")
        self.assertEqual(set(actual), set(expected))

    def test_driver_totals_match_truth(self) -> None:
        source = [attach_runtime_fields(row) for row in read_csv(ROOT / "data" / "pings_SYNTHETIC.csv")]
        actual_rows = calculate(source)
        expected_rows = read_csv(ROOT / "data" / "ground_truth_SYNTHETIC.csv")
        actual_totals: dict[str, float] = {}
        expected_totals: dict[str, float] = {}
        for (driver, _), km in actual_rows.items():
            actual_totals[driver] = actual_totals.get(driver, 0.0) + km
        for row in expected_rows:
            driver = row["driver_id"]
            expected_totals[driver] = expected_totals.get(driver, 0.0) + float(row["true_km_in_zone"])
        self.assertEqual(set(actual_totals), set(expected_totals))
        for driver in expected_totals:
            self.assertAlmostEqual(actual_totals[driver], expected_totals[driver], delta=TRUTH_TOLERANCE_KM,
                                   msg=f"{driver}: driver total differs from independent truth")


def main() -> int:
    global IMPL
    parser = argparse.ArgumentParser()
    parser.add_argument("--impl", choices=("legacy", "fixed"), default="fixed")
    args = parser.parse_args()
    IMPL = args.impl
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(GPSRegressionTests)
    output = io.StringIO()
    result = unittest.TextTestRunner(stream=output, verbosity=2).run(suite)
    details = output.getvalue().replace(f"{ROOT}/", "")
    rendered = f"> Synthetic data, fictional scenario. Assessment exercise only.\nImplementation: {IMPL}\n\n{details}"
    output_path = ROOT / "results" / f"regression_{IMPL}.txt"
    output_path.write_text(rendered, encoding="utf-8")
    sys.stdout.write(rendered)
    print(f"Saved run output to {output_path.relative_to(ROOT)}.")
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
