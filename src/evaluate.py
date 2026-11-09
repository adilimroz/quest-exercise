"""Evaluate detected injected faults against the separate synthetic manifest.

The manifest is read here only, after `qa.py` has written its findings.
Run from the project root with: python3 src/evaluate.py
"""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data" / "fault_manifest_SYNTHETIC.csv"
FINDINGS = ROOT / "results" / "findings.csv"
OUTPUT = ROOT / "results" / "checker_evaluation.csv"
SUMMARY = ROOT / "results" / "checker_evaluation.md"
FAULT_TYPES = ("noise_offroad", "noise_speed", "duplicate_exact", "duplicate_conflict", "late")


def read_rows(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    manifest = read_rows(MANIFEST)
    findings = read_rows(FINDINGS)
    expected: dict[str, set[str]] = defaultdict(set)
    predicted: dict[str, set[str]] = defaultdict(set)
    for row in manifest:
        expected[row["fault_type"]].add(row["ping_id"])
    for row in findings:
        if row["fault_type"] in FAULT_TYPES:
            predicted[row["fault_type"]].add(row["ping_id"])

    result = []
    for fault_type in FAULT_TYPES:
        exp, pred = expected[fault_type], predicted[fault_type]
        tp = len(exp & pred)
        fp = len(pred - exp)
        fn = len(exp - pred)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        result.append({
            "fault_type": fault_type, "true_positive": tp, "false_positive": fp,
            "false_negative": fn, "precision": f"{precision:.6f}", "recall": f"{recall:.6f}",
        })

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(result[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(result)
    passed = all(float(row["precision"]) == 1.0 and float(row["recall"]) == 1.0 for row in result)
    lines = [
        "# Synthetic checker evaluation",
        "",
        "> Synthetic data, fictional scenario. Assessment exercise only.",
        "",
        "The manifest is used only by this evaluation script. `qa.py` does not load it.",
        "",
        "| Fault | TP | FP | FN | Precision | Recall |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in result:
        lines.append(
            f"| {row['fault_type']} | {row['true_positive']} | {row['false_positive']} | {row['false_negative']} | {float(row['precision']):.3f} | {float(row['recall']):.3f} |"
        )
    explanation = "all five fault classes have precision and recall 1.0" if passed else "at least one fault class needs review"
    lines += ["", f"Overall check: **{'PASS' if passed else 'REVIEW'}** ({explanation}).", ""]
    SUMMARY.write_text("\n".join(lines), encoding="utf-8")
    print(f"Manifest comparison: {'PASS' if passed else 'REVIEW'}.")
    for row in result:
        print(f"{row['fault_type']}: TP={row['true_positive']} FP={row['false_positive']} FN={row['false_negative']} precision={row['precision']} recall={row['recall']}")


if __name__ == "__main__":
    main()
