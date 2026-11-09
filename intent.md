> Synthetic data, fictional scenario. Assessment exercise only.

# Intent and Investigation Notes

## Initial investigation plan

I will test how event ordering, duplicates, GPS noise, local-day boundaries, and campaign-zone clipping affect reported distance. These are investigation questions, not confirmed findings. I will rank only issues demonstrated by the generated data, checker output, and before/after comparison.

## Problems found and ranking

I chose the priority order below after reviewing the summarized checker findings and before/after results. Findings are based on checker output and its separate comparison with the synthetic fault manifest. This is a reasoned priority order, not a per-fault distance attribution: the measured before/after total combines several defects.

| Rank | Demonstrated problem | Evidence / how found | Advertiser impact | Driver impact |
| --- | --- | --- | ---: | ---: |
| 1 | Delayed/out-of-order pings are processed in arrival order | Checker found 298 pings delayed by at least 60 s and 405 event-time regressions. Late points can create long false connections when processed in arrival order. See `results/findings.csv` and `results/checker_evaluation.md`. | Highest priority: can add or remove billable path distance; exact per-fault km is not isolated. | Can corrupt reported distance and assign it to the wrong day; any pay effect depends on a rate not specified in the brief. |
| 2 | GPS noise is retained | Checker flagged 89 off-road points and 89 on-road speed spikes; all matched their injected fault classes. These extra fixes can create false segments or break a valid path. | Direct risk of overstating or understating campaign distance; exact per-fault km is not isolated. | Can distort driver/day distance; any pay effect depends on a rate not specified in the brief. |
| 3 | Duplicate driver/timestamp records are counted | Checker flagged 119 exact and 60 conflicting extra copies; all matched their manifest class. Conflicting coordinates can add artificial movement, while exact copies can disrupt ordering-based calculations. | Can inflate distance, especially for conflicting copies; exact per-fault km is not isolated. | Can distort daily distance; any pay effect depends on a rate not specified in the brief. |
| 4 | Segments crossing the campaign-zone edge are not clipped | Checker identified 137 accepted-trace segments with both in-zone and out-of-zone portions. Counting a whole segment misstates the campaign's billable distance. | Direct billing risk at the zone boundary; exact per-fault km is not isolated. | Changes the credited in-zone distance; any pay effect depends on a rate not specified in the brief. |
| 5 | Local UTC+9 midnight is not used for daily reporting | Checker identified 12 accepted-trace segments crossing a local-day boundary. A UTC day cut can put distance on the wrong daily row even when the campaign total is unchanged. | Daily invoice/report allocation can be wrong; campaign-total effect is zero from reassignment alone. | Driver/day report can be wrong; any pay effect depends on a rate not specified in the brief. |

### Aggregate calculation evidence (not fault-by-fault attribution)

The legacy calculation reports **809.448557 km** on a UTC-day basis. The corrected calculation reports **273.691685 km** on a local UTC+9 basis, compared with **273.691796 km** from the independent clean reference. The legacy total is **535.756761 km above the reference**; the largest corrected driver/day difference is **0.000090 km**, within the 0.002 km tolerance. These totals show the combined effect of the legacy behaviors and do not attribute the error to any one fault.

The brief does not specify advertiser or driver payment rates, so these observations are in kilometres rather than invented currency. Use the per-driver/day details in `results/before_after.md` when deciding how the errors affect each party.

## Chosen first fix

I chose delayed/out-of-order handling as the first problem to prioritize because the checker found 298 late records and 405 event-time regressions, and arrival-order path construction can connect distant fixes out of sequence. That can materially distort both campaign billing distance and driver-day reporting. The available before/after totals show the combined impact of all legacy defects, so this choice is based on frequency and direct mechanism rather than a claimed isolated kilometre contribution.

## Scope left out

- Map matching to real road geometry; this exercise uses a fictional grid and straight segments between pings.
- Signal gaps, offline periods, and faults that replace rather than add to a real fix.
- Daylight-saving changes and time zones other than fixed UTC+9.
- Multiple campaign zones, campaigns, and streaming late-arrival cutoffs.
- Production billing integration, invoice rounding, real advertiser/driver rates, and financial impact.
- Performance and operational behavior at production scale.

These limits keep the work focused on the stated calculation rules; they are not claims that those cases are solved.

## How I used AI and checked its work

AI created the generator, legacy baseline, checker, corrected calculation, reports, tests, and initial versions of the documents. I chose a simple fictional grid and zone, selected the ranking, and inspected the zone-entry and local-midnight test cases; their expected and actual values matched.

During verification, AI identified that the initial route fixture put drivers exactly on the campaign-zone edge, where seven-decimal GPS rounding could place them just outside. AI moved the main routes inside the zone and kept a control route outside. An early regression version used a tolerance that was too tight and rounded boundary fixtures; its late-ping scenario also accidentally let the legacy implementation pass. AI changed the focused fixtures to use precise local coordinates, applied the documented truth tolerance to dataset checks, and moved the late-ping scenario inside the zone. The regression logs show the final fixed pass and legacy failure.

I keep a more detailed working record in `ai-log.md`. The summary here and in `directive.md` describes AI's role and my review accurately.

## Effort and prior work

I have not yet calculated my total effort. The AI-session entries in `effort-log.md` do not include time I spent outside those sessions. `BUILD.md` existed in the workspace before this work. I did not carry over GPS implementation, data, or tests from it; the code, dataset, and tests in this submission were created for this exercise.
