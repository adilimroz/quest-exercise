"""Run the full synthetic GPS QA exercise from the repository root.

Usage: python3 run.py all
Uses only the Python standard library.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PYTHON = sys.executable


def run(label: str, args: list[str]) -> None:
    print(f"\n== {label} ==", flush=True)
    subprocess.run([PYTHON, *args], cwd=ROOT, check=True)


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] != "all":
        print("Usage: python3 run.py all")
        return 2

    steps = [
        ("Generate synthetic data and independent truth", ["src/generate.py"]),
        ("Run intentionally incorrect legacy baseline", ["src/legacy.py"]),
        ("Run manifest-blind QA checker", ["src/qa.py"]),
        ("Evaluate checker against the separate fault manifest", ["src/evaluate.py"]),
        ("Check clean synthetic trajectory", ["src/qa.py", "--clean"]),
        ("Run corrected calculation", ["src/corrected.py"]),
        ("Compare legacy, corrected, and truth totals", ["src/report.py"]),
        ("Regression suite against corrected calculation", ["tests/test_regression.py", "--impl", "fixed"]),
    ]
    for label, command in steps:
        run(label, command)

    print("\n== Confirm legacy behavior fails the regression contract ==", flush=True)
    legacy_result = subprocess.run(
        [PYTHON, "tests/test_regression.py", "--impl", "legacy"],
        cwd=ROOT, capture_output=True, text=True,
    )
    if legacy_result.returncode == 0:
        print("FAIL: legacy unexpectedly passed the regression contract.")
        return 1
    if "FAILED (failures=15)" not in legacy_result.stdout:
        print("FAIL: legacy failed, but not with the expected 15 regression failures.")
        print(legacy_result.stdout)
        print(legacy_result.stderr)
        return 1
    print("PASS: legacy fails all 15 regression cases as expected; see results/regression_legacy.txt.")
    print("\nAll synthetic QA, calculation, comparison, and regression steps completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
