# AI Work Log

I used AI to help build and verify this synthetic GPS QA exercise. This log records the work AI produced, the checks I reviewed, and the decisions I made. It is a factual record of this project, not a claim that I wrote the generated code unaided.

| Pass | Work AI produced | What I reviewed or decided |
| --- | --- | --- |
| 1 | Assignment interpretation, project structure, and deterministic calculation assumptions. | I kept the proposed assumptions for threshold edges, duplicate handling, event-time sorting, fixed UTC+9 days, and zone clipping. |
| 2 | A synthetic finite grid, rectangular campaign zone, generator, labelled dataset, and independent clean reference. | I chose a simple fictional road grid and campaign zone. The data and geography are synthetic and do not describe a real platform. |
| 3 | The intentionally flawed legacy baseline and a checker that reports data issues, plus separate manifest-based evaluation. | I reviewed the summarized findings and selected the impact ranking recorded in `intent.md`. The checker does not use the fault manifest to detect problems. |
| 4 | The corrected calculation and per-driver/day comparison against the legacy output and clean reference. | I chose late and out-of-order pings as the first issue to fix. I treated the overall distance change as combined impact, not a per-fault attribution. |
| 5 | Focused regression cases and fixed-versus-legacy runs. | I inspected `test_zone_entry_is_clipped` and `test_segment_is_split_at_local_midnight`. The first expects only the 100 m inside the zone; the second assigns half the segment to each local day. The fixed run matched both expectations. |
| 6 | The one-command pipeline, handoff documents, and Loom script. | I reviewed the reported totals, test results, and document consistency. I have not supplied a public repository URL, Loom URL, or my total effort yet. |

## Corrections made during verification

The first generated route fixture placed drivers on the campaign-zone edge. GPS rounding could put a point just outside, so AI moved the main routes inside the zone and retained an outside control route. An early regression draft also used a tolerance that was too tight, and its late-ping fixture accidentally passed against the legacy implementation. AI adjusted the fixtures and tolerance; the final run passes all 15 cases against the corrected calculation and fails all 15 against legacy. I inspected the two boundary-related regression cases named above and confirmed their expected and actual outputs agree.

AI generated the application code and initial document wording. I reviewed the assumptions, selected the ranking, and checked the named regression outputs. My actual effort and reviewer-accessible public links are still to be added.
