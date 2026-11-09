# Synthetic data generation summary

> Synthetic data, fictional scenario. Assessment exercise only.

- Random seed: `42`.
- Noisy arrival-order pings: 6315.
- Clean true pings: 5958.
- Fault manifest entries: 655.
- Fault counts: noise_offroad=89, noise_speed=89, duplicate_exact=119, duplicate_conflict=60, late=298.
- Fictional roads: finite horizontal/vertical grid from 0 to 8,000 m in each axis, spaced 1,000 m apart.
- Fictional campaign zone: closed rectangle from x=2,000–6,000 m and y=2,000–6,000 m; boundary is inside.
- Local coordinate origin: 35.6000° latitude, 139.6000° longitude; serialized lat/lon rounded to seven decimals.
- Drivers: DRV-001 through DRV-005. Service dates: 2026-03-02 through 2026-03-04 (local UTC+9).
- Shifts (local): DRV-001 08:30–09:30; DRV-002 23:30–00:30; DRV-003 14:00–15:00; DRV-004 08:45–09:45; DRV-005 18:00–19:00 and 23:45–00:15.
- Clean routes travel along a horizontal grid road. DRV-001 to DRV-004 use roads inside the zone; DRV-005 uses an outside-zone road. Speeds are drawn from 20–60 km/h and redrawn every minute; vehicles remain parked at their final point between shifts.
- Fault injection rates (rounded to records): off-road 1.5%, speed 1.5%, exact duplicate 2%, conflicting duplicate 1%, late arrival 5%. Noise fixes are extra records at event time +5 seconds; off-road fixes are at grid-cell centers; speed spikes jump 900 m on-road; conflicting duplicates shift 5–30 m; copies arrive 1–30 seconds after their source; ordinary receipt delay is 1–5 seconds and late receipt delay is 60–1,800 seconds.
- Sampled ground truth uses 2,000 midpoint substeps per moving clean segment.
- Convergence check at 8,000 substeps: max driver-day difference `0.000091 km` (tolerance `0.002 km`).
- The truth code is independent of the future corrected calculator; it reads only the clean trajectory and geometry constants in this file.
- Calculations and distance assumptions are described in `PROJECT_SPEC.md`.
