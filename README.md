# GPS Distance QA Quest

This project investigates distance errors in a fictional vehicle-advertising system. I used AI to build the generator, QA checker, intentionally flawed baseline, corrected reference calculation, reports, and regression checks. I reviewed the assumptions, chose the issue ranking, and checked the boundary regression cases. All drivers, GPS records, roads, campaign geography, and results are synthetic; no real driver or employer data is used.

The assessment handoff is in [`intent.md`](intent.md) and [`directive.md`](directive.md). The directive links the runnable tool, dataset, calculations, results, tests, and Loom video.

## Start here

You need Python 3.10 or later. The project uses only the Python standard library; no package installation is required.

From the repository root, run the complete reproducible workflow:

```bash
python3 run.py all
```

The command regenerates the synthetic data and independent reference, runs the flawed calculation, runs the checker and its separate evaluation, checks the clean trajectory, runs the corrected calculation, writes comparisons, and verifies regression behavior. It exits successfully only when the corrected implementation passes all 15 regression cases and the legacy implementation fails all 15.

Expected headline results:

- Dataset: 6,315 pings, including 5,958 clean trajectory pings.
- Checker: 1,209 findings across seven categories. Its detections do not use the fault manifest.
- Checker evaluation: precision and recall are 1.000 for each of the five injected fault classes.
- Legacy billed distance: **809.448557 km**.
- Corrected billed distance: **273.691685 km**.
- Independent clean reference: **273.691796 km**.
- Largest corrected per-driver/day difference from reference: **0.000090 km**, within the **0.002 km** tolerance.
- Regression check: corrected calculation passes **15/15** cases; legacy fails **15/15**.

The generated data and reports are included in the project, so a reviewer can inspect the results without running Python. Running the full workflow regenerates them.

## What the project checks

The fictional billing rules implemented by the corrected reference are:

1. Reject a ping more than 100 metres from the nearest modeled road; retain a ping exactly 100 metres away.
2. Reject a ping implying speed above 150 km/h; retain exactly 150 km/h. Compare with the last accepted point, and do not use a rejected ping as the next reference.
3. Keep one ping per driver and event timestamp: the earliest received record, with ping ID as a tie-breaker.
4. Sort each driver's pings by event timestamp before connecting points.
5. Keep timestamps in UTC and report by fixed UTC+9 local date. Split segments at local midnight.
6. Count only the segment portion inside the campaign zone; the zone boundary counts as inside.
7. Measure straight-line distance between accepted GPS fixes. This project does not perform map matching.

The fictional road network is a grid spanning 0–8,000 metres on each axis, with roads every 1,000 metres. The campaign zone is the closed rectangle from x=2,000–6,000 metres and y=2,000–6,000 metres. The data README documents the generation seed, drivers, shifts, fault counts, and sampled reference method.

## Follow the evidence

| Assignment question | Where to look | What the evidence shows |
| --- | --- | --- |
| What problems were found and how were they ranked? | [`intent.md`](intent.md) | Five ranked findings, evidence from the checker, advertiser and driver impact, first-fix rationale, and scope left out. |
| Can someone else run the QA tool? | [`src/qa.py`](src/qa.py), [`run.py`](run.py) | A manifest-blind checker and one-command workflow. |
| What did the checker find? | [`results/qa_summary.md`](results/qa_summary.md), [`results/findings.csv`](results/findings.csv) | Counts and row-level examples for ordering, delayed arrival, duplicates, noise, local-day crossings, and zone crossings. |
| How was checker accuracy assessed? | [`src/evaluate.py`](src/evaluate.py), [`results/checker_evaluation.md`](results/checker_evaluation.md) | A separate comparison between detections and the synthetic fault manifest. Detection itself does not read the manifest. |
| Does the checker behave sensibly on clean input? | [`results/clean_qa_summary.md`](results/clean_qa_summary.md), [`results/clean_findings.csv`](results/clean_findings.csv) | No injected noise, duplicate, or late-arrival findings; structural day and zone crossings remain visible. |
| What was wrong in the old calculation? | [`src/legacy.py`](src/legacy.py) | The baseline uses received order, accepts every point, counts whole segments based on the start point, and assigns the segment to a UTC date. |
| What changed in the fix? | [`src/corrected.py`](src/corrected.py), [`results/fixed_rejections.csv`](results/fixed_rejections.csv) | Event-time ordering, deduplication, noise rejection, local-midnight splitting, and zone clipping. Rejected pings are listed with reasons. |
| What are the before/after distances? | [`results/before_after.md`](results/before_after.md), [`results/before_after.csv`](results/before_after.csv), [`results/driver_totals.csv`](results/driver_totals.csv) | Distance by driver and day, driver totals, reference values, and errors. |
| Does the regression check fail on the old behavior and pass on the fix? | [`tests/test_regression.py`](tests/test_regression.py), [`results/regression_fixed.txt`](results/regression_fixed.txt), [`results/regression_legacy.txt`](results/regression_legacy.txt) | Fifteen contract cases pass for corrected and fail for legacy, covering noise, duplicates, late pings, UTC+9 day handling, zone entry/exit, and boundaries. |
| What is still not solved, and how was AI used? | [`intent.md`](intent.md), [`directive.md`](directive.md) | Limitations, AI contribution and verification, prior-work statement, and the submission handoff. |

## Run individual steps

These commands run from the repository root. The full workflow above is the recommended first run.

| Command | What it does and writes |
| --- | --- |
| `python3 src/generate.py` | Regenerates the noisy arrival-order pings, clean trajectory, fault manifest, and sampled independent reference. |
| `python3 src/legacy.py` | Runs the intentionally flawed baseline; writes `results/legacy_km.csv`. |
| `python3 src/qa.py` | Checks noisy input without reading the manifest; writes `results/findings.csv` and `results/qa_summary.md`. |
| `python3 src/evaluate.py` | Compares checker findings with the manifest; writes `results/checker_evaluation.csv` and `.md`. Run after the checker. |
| `python3 src/qa.py --clean` | Checks the clean trajectory; writes `results/clean_findings.csv` and `results/clean_qa_summary.md`. |
| `python3 src/corrected.py` | Runs the corrected calculation; writes `results/fixed_km.csv` and `results/fixed_rejections.csv`. |
| `python3 src/report.py` | Compares legacy, corrected, and reference output; writes the driver/day and driver-total reports. Run after generation and both calculations. |
| `python3 tests/test_regression.py --impl fixed` | Runs the 15 regression cases against the corrected calculation. |
| `python3 tests/test_regression.py --impl legacy` | Runs the same contract against legacy; it should fail all 15 cases, save the output to `results/regression_legacy.txt`, and exit with a failure status as expected. The full `run.py all` command checks this expected failure and completes successfully only when all 15 legacy failures are present. |

## How to read the comparison

In [`results/before_after.md`](results/before_after.md), legacy amounts use the UTC date of the segment's start ping. Corrected and reference amounts use UTC+9 local dates. The report places them on the same date-labelled row for comparison, but a legacy amount on a row does not mean it belongs to that local day. Use the day-basis columns and the report's explanation when interpreting daily differences.

The aggregate change is the combined effect of several corrected behaviors. The project does not claim a fault-by-fault kilometre attribution, and the assignment does not specify payment rates, so impacts are reported in distance rather than currency.

## Limits

This is a compact reference exercise, not a production billing system. It uses a fictional grid and rectangular zone, straight-line segments between fixes, one campaign, and a fixed UTC+9 offset. It does not model real map matching, daylight-saving changes, long signal gaps, faults replacing true fixes, streaming late-arrival policies, production integration, payment rates, or invoice rounding.

## Assessment handoff

The required submission consists of exactly three items: a Loom video (maximum five minutes), [`intent.md`](intent.md), and [`directive.md`](directive.md). The directive is the reviewer handoff for the links and measured results. Before submission, I will make sure the repository and Loom URLs in the directive are accessible and that my actual effort is recorded. The Loom walks through the problem, tool, root cause, fix, before/after numbers, regression evidence, and how I used and checked AI assistance.
