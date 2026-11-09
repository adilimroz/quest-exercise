# Synthetic checker evaluation

> Synthetic data, fictional scenario. Assessment exercise only.

The manifest is used only by this evaluation script. `qa.py` does not load it.

| Fault | TP | FP | FN | Precision | Recall |
| --- | ---: | ---: | ---: | ---: | ---: |
| noise_offroad | 89 | 0 | 0 | 1.000 | 1.000 |
| noise_speed | 89 | 0 | 0 | 1.000 | 1.000 |
| duplicate_exact | 119 | 0 | 0 | 1.000 | 1.000 |
| duplicate_conflict | 60 | 0 | 0 | 1.000 | 1.000 |
| late | 298 | 0 | 0 | 1.000 | 1.000 |

Overall check: **PASS** (all five fault classes have precision and recall 1.0).
