> Synthetic data, fictional scenario. Assessment exercise only.

# Final Directive: GPS Distance QA Quest

## Objective

Find and correct errors in a fictional vehicle-advertising distance calculation. The deliverable demonstrates how the QA checker surfaces data and calculation issues, how the corrected reference follows the stated billing rules, and how regression checks protect the correction. All records, drivers, geography, and results are synthetic.

## Scope

### In scope

- Reproducible synthetic GPS pings with off-road noise, speed spikes, exact and conflicting duplicates, and late arrivals.
- A deliberately flawed legacy reference calculation and a runnable checker.
- A corrected reference calculation, daily and driver comparisons, and an independent sampled truth calculation.
- Regression checks for filtering, deduplication, event-time ordering, UTC+9 day handling, and campaign-zone clipping.

### Out of scope

- Real maps, road matching, production services, live billing, streaming ingestion, real compensation rates, and non-synthetic user or driver data.

## Requirements and assumptions

The implementation follows these rules:

1. Reject a ping more than 100 m from the nearest modeled road; exactly 100 m is retained.
2. Reject a ping implying speed above 150 km/h; exactly 150 km/h is retained. Evaluate speed against the last accepted point; a rejected ping never becomes the reference point. The first point is checked for road distance only.
3. Deduplicate by `(driver_id, timestamp_utc)`, keeping the earliest received record; break receipt-time ties by ping ID.
4. Sort each driver by event timestamp, then receipt timestamp and ping ID.
5. Keep event timestamps in UTC. Report by fixed UTC+9 local date using half-open days `[00:00, next 00:00)`. Split segments at local midnight; the segment piece starting at midnight belongs to the new date.
6. Count only the segment portion inside the campaign zone. The zone boundary counts as inside.
7. Use haversine distance between accepted fixes for the reported path. This is straight-line distance, not map-matched road distance.

The fictional road model is an orthogonal grid from 0–8,000 m on each axis, with roads every 1,000 m. The one campaign zone is a closed rectangle from x=2,000–6,000 m and y=2,000–6,000 m. GPS-shaped coordinates use a local origin at 35.6000° N, 139.6000° E. Five fictional drivers work three local service dates. Four routes run inside the zone and one route remains outside as a control. UTC+9 is treated as a fixed offset without daylight-saving changes.

The synthetic late-arrival model uses a receipt delay of 60–1,800 seconds; ordinary pings arrive 1–5 seconds after event time. The checker’s 60-second late threshold is a simulation assumption, not a production cutoff. Data generation uses seed 42. The clean-truth reference samples each moving segment at 2,000 midpoint substeps and checks convergence against 8,000 substeps; maximum per-driver/day change is 0.000091033 km, below the 0.002 km tolerance.

## Completion criteria

| Criterion | Result | Status |
| --- | --- | --- |
| At least 2,000 labelled synthetic pings | 6,315 pings; 5,958 clean true pings | PASS |
| Required injected fault categories present | 89 off-road, 89 speed, 119 exact duplicate, 60 conflicting duplicate, 298 late | PASS |
| Checker makes at least three issues visible and runs independently of the manifest | Seven check categories reported; manifest used only by the separate evaluator | PASS |
| Checker evaluation against the injected-fault manifest | Precision 1.000 and recall 1.000 for each of the five injected categories | PASS |
| Clean trajectory has no injected-fault detections | Zero noise, duplicate, or late findings; only structural day and zone boundaries remain | PASS |
| Corrected calculation matches independent truth per driver/day | Maximum absolute difference 0.000090 km; tolerance 0.002 km | PASS |
| Regression behavior | Corrected implementation passes 15/15; legacy fails all 15 contract cases | PASS |
| Before/after output by driver and day | 19 labelled day rows and five driver totals generated from calculation outputs | PASS |
| Reviewer-accessible repository and Loom link | I have not added the public repository URL or Loom URL yet | I will add and check both links before submission |
| Actual total effort | My effort log records AI-session work but not my time outside those sessions | I will add my actual total before submission |

## Findings and root cause

The checker surfaced these representative records from the synthetic dataset:

| Issue | Example evidence | Legacy behavior | Correction |
| --- | --- | --- | --- |
| Late/out-of-order arrival | `P0000038` is 89 s after event time and 80 s behind the preceding received event timestamp | `legacy.py` line 30 processes received order | Sort by event timestamp before forming segments |
| Off-road noise | `P0000068` is 500.0 m from the nearest modeled road | `legacy.py` line 41 accepts every fix | Reject points over 100 m from the road |
| Speed noise | `P0000032` implies 647.1 km/h from the previous accepted point | `legacy.py` line 41 accepts every fix | Reject speeds over 150 km/h |
| Duplicate records | `P0000055` is an exact duplicate; `P0000081` has conflicting coordinates at the same driver/time | `legacy.py` line 42 counts every copy | Keep the earliest-received record for each driver/timestamp |
| Local-day boundary | `P0000665→P0002116` crosses local midnight from 2026-03-02 to 2026-03-03 | `legacy.py` line 48 assigns the whole segment to its start ping’s UTC day | Split at local midnight and assign each piece to its local start date |
| Campaign-zone boundary | `P0000014→P0000015` has both in-zone and out-of-zone portions | `legacy.py` line 46 counts the entire segment based on its start point | Clip the segment to the zone before summing distance |

The combined legacy result is 809.448557 km, while the corrected result is 273.691685 km and independent clean truth is 273.691796 km. This aggregate difference is not attributed to individual faults. The selected first priority is late/out-of-order handling because the checker found 298 late records and 405 event-time regressions, and arrival-order path construction can connect points out of sequence. The first-fix choice is based on frequency and mechanism, not a claimed fault-specific kilometre contribution.

## Results and handoff

### Reproduce

From the repository root, run:

```bash
python3 run.py all
```

The full run regenerates the synthetic data and truth, runs the legacy and corrected calculations, runs the checker and separate evaluator, checks clean data, creates the comparison report, and confirms fixed-pass/legacy-fail regression behavior. Python standard library only; no external package installation is required.

### Artifact links

Paths are relative to the project root and will resolve when this project is published in an accessible repository.

| Artifact | Link |
| --- | --- |
| Runnable full pipeline | [`run.py`](run.py) |
| QA checker | [`src/qa.py`](src/qa.py) |
| Checker evaluation (separate from detection) | [`src/evaluate.py`](src/evaluate.py) |
| Synthetic arrival-order dataset | [`data/pings_SYNTHETIC.csv`](data/pings_SYNTHETIC.csv) |
| Clean synthetic trajectory | [`data/true_pings_SYNTHETIC.csv`](data/true_pings_SYNTHETIC.csv) |
| Synthetic fault manifest (evaluation only) | [`data/fault_manifest_SYNTHETIC.csv`](data/fault_manifest_SYNTHETIC.csv) |
| Synthetic independent truth | [`data/ground_truth_SYNTHETIC.csv`](data/ground_truth_SYNTHETIC.csv) |
| Data assumptions and counts | [`data/README.md`](data/README.md) |
| Intentionally flawed legacy calculation | [`src/legacy.py`](src/legacy.py) |
| Corrected calculation | [`src/corrected.py`](src/corrected.py) |
| Checker findings and examples | [`results/qa_summary.md`](results/qa_summary.md), [`results/findings.csv`](results/findings.csv) |
| Manifest precision/recall | [`results/checker_evaluation.md`](results/checker_evaluation.md), [`results/checker_evaluation.csv`](results/checker_evaluation.csv) |
| Clean-data checker results | [`results/clean_qa_summary.md`](results/clean_qa_summary.md), [`results/clean_findings.csv`](results/clean_findings.csv) |
| Legacy totals | [`results/legacy_km.csv`](results/legacy_km.csv) |
| Corrected totals and rejected pings | [`results/fixed_km.csv`](results/fixed_km.csv), [`results/fixed_rejections.csv`](results/fixed_rejections.csv) |
| Before/after by driver/day and driver totals | [`results/before_after.csv`](results/before_after.csv), [`results/driver_totals.csv`](results/driver_totals.csv), [`results/before_after.md`](results/before_after.md) |
| Regression tests and output | [`tests/test_regression.py`](tests/test_regression.py), [`results/regression_fixed.txt`](results/regression_fixed.txt), [`results/regression_legacy.txt`](results/regression_legacy.txt) |
| Full dataset truth convergence | [`results/truth_convergence.txt`](results/truth_convergence.txt) |
| Public repository URL | **I have not published this repository yet. I will add the reviewer-accessible URL after publishing and checking access.** |
| Loom video URL | **I have not recorded or shared the Loom yet. I will add its URL after recording and checking reviewer access.** |

### Before/after by driver and day

Legacy values use the UTC date of the segment’s start ping. Corrected and reference values use local UTC+9 dates. The same date label is shown in each column so the day-cut difference is visible; a legacy amount on a row does not imply that it belongs to that local date.

| Driver | Day label | Legacy UTC km | Corrected local km | Reference local km | Legacy error km | Corrected error km |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| DRV-001 | 2026-03-01 | 33.710597 | 0.000000 | 0.000000 | 33.710597 | 0.000000 |
| DRV-001 | 2026-03-02 | 58.171924 | 21.780066 | 21.780077 | 36.391847 | -0.000011 |
| DRV-001 | 2026-03-03 | 66.355139 | 22.517402 | 22.517457 | 43.837682 | -0.000055 |
| DRV-001 | 2026-03-04 | 42.219649 | 23.603345 | 23.603267 | 18.616382 | 0.000078 |
| DRV-002 | 2026-03-02 | 65.128315 | 11.781467 | 11.781428 | 53.346887 | 0.000039 |
| DRV-002 | 2026-03-03 | 84.263006 | 23.962300 | 23.962390 | 60.300616 | -0.000090 |
| DRV-002 | 2026-03-04 | 50.406034 | 23.962300 | 23.962314 | 26.443720 | -0.000014 |
| DRV-002 | 2026-03-05 | 0.000000 | 11.981150 | 11.981130 | -11.981130 | 0.000020 |
| DRV-003 | 2026-03-02 | 69.159418 | 21.962970 | 21.963024 | 47.196394 | -0.000054 |
| DRV-003 | 2026-03-03 | 69.151989 | 23.959606 | 23.959602 | 45.192387 | 0.000004 |
| DRV-003 | 2026-03-04 | 49.173370 | 20.280266 | 20.280345 | 28.893025 | -0.000079 |
| DRV-004 | 2026-03-01 | 5.796516 | 0.000000 | 0.000000 | 5.796516 | 0.000000 |
| DRV-004 | 2026-03-02 | 82.344998 | 23.964993 | 23.964965 | 58.380033 | 0.000028 |
| DRV-004 | 2026-03-03 | 89.824751 | 20.252130 | 20.252103 | 69.572648 | 0.000027 |
| DRV-004 | 2026-03-04 | 43.742851 | 23.683690 | 23.683694 | 20.059157 | -0.000004 |
| DRV-005 | 2026-03-02 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| DRV-005 | 2026-03-03 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| DRV-005 | 2026-03-04 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| DRV-005 | 2026-03-05 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |

### AI use, prior work, and effort

AI produced the code, synthetic records, checker, corrected calculation, test suite, and first drafts of the analysis documents. During verification, AI identified that the initial route fixture sat on the zone edge, where GPS rounding could move a point outside, and moved the main routes inside while keeping an outside control route. An early regression draft used an overly tight tolerance, and its late-ping test fixture accidentally passed against legacy; AI corrected the fixtures, and the final run now fails all 15 cases against legacy and passes all 15 against the corrected implementation. I chose the assumptions and ranking, and I reviewed the zone-entry and midnight split tests. Their expected values matched the fixed run. I keep the detailed working AI-use record privately; this section summarizes the relevant facts for reviewers.

`BUILD.md` was present in the workspace before this exercise. No GPS code, data, or tests were reused from it; the implementation and synthetic dataset linked above were created for this assessment.

**My actual total effort:** I have not calculated it yet. The AI-session entries in `effort-log.md` exclude my time outside those sessions; I will add my actual total before submission.

## Known limitations / still not solved

- The road grid and campaign rectangle are fictional; results do not represent a real map or actual platform.
- Straight-line distance between accepted fixes is used; no road map matching is performed.
- The independent truth is sampled, not a production billing oracle. Its measured convergence is within the documented tolerance.
- UTC+9 is a fixed offset. Daylight-saving time and other local time zones are not modeled.
- The generator injects faults as extra records. It does not model noise replacing true fixes, long signal gaps, or offline periods.
- Only one zone and campaign are modeled. There is no streaming arrival cutoff or late-data policy.
- Real driver/advertiser rates and invoice rounding rules are unspecified, so impact is reported in distance, not currency.
- The corrected reference has been validated against this synthetic contract and data; production-scale performance and integration are not evaluated.
