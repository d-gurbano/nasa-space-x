# Rewind impact: precovery FOUNDs vs the first known observation (2026-11-15)

First/last known observation: JPL SBDB, queried 2026-11-15 (VERIFIED). Our days and positions: MEASURED from SPHEREx pixels. Arcs and uncertainties: COMPUTED with kete least-squares fits of the real MPC observations, without and with our SPHEREx positions (each given an uncertainty of at least 2.0 arcsec, a third of a SPHEREx pixel, because they come from stacks searched within +-1.25 px of the prediction). 3-sigma = largest axis of 300 covariance clones (linear, gravity only).

## 1. Today (all known observations + ours)

| Object | First known obs | Our earliest positive day | Days earlier | SPHEREx positions used (earlier than first obs) | Arc days before -> after | 3-sigma 1 yr after last obs (km) before -> after | Factor |
|-|-|-|-|-|-|-|-|
| 2025 YH5 | 2025-12-20 | 2025-12-02 | 18 | 7 (7) | 85.0 -> 99.3 | 32,462 -> 30,404 | 1.07 |
| C/2026 S1 | 2026-09-16 | 2026-09-12 | 4 | 2 (2) | 45.0 -> 48.4 | 4,142,121 -> 4,082,458 | 1.01 |
| 2025 ST20 | 2025-09-27 | 2025-09-13 | 14 | 1 (1) | 76.0 -> 85.2 | 19,329 -> 19,115 | 1.01 |
| 2025 YJ6 | 2025-12-26 | 2025-12-09 | 17 | 2 (2) | 41.0 -> 55.3 | 57,219 -> 56,128 | 1.02 |
| P/2025 Y2 | 2025-12-27 | 2025-12-21 | 6 | 1 (1) | 217.0 -> 221.9 | 12,335 -> 12,342 | 1.0 |
| C/2025 L2 | 2025-06-02 | 2025-05-13 | 20 | 1 (1) | 365.0 -> 374.9 | 4,732 -> 4,727 | 1.0 |
| P/2026 V1 | 2026-09-15 | 2026-09-02 | 13 | 1 (1) | 55.0 -> 57.7 | 255,856 -> 255,804 | 1.0 |
| C/2025 W2 | 2025-10-26 | 2025-10-27 | not earlier | 4 (0) | 71.0 -> 71.0 | 197,697 -> 196,489 | 1.01 |

2025 YH5 (PHA, U=5) next Earth close approach in the SBDB list: 2134-02-13 at 36.3 LD; 3-sigma there 8,281,459 -> 7,732,726 km (factor 1.07). That is 108 years ahead, where a linear covariance is not reliable; treat it as indicative only.

## 2. Scenario: as if Rewind had run right after discovery (COMPUTED)

Only the MPC observations of the first 7 days after the first known observation, without and with our SPHEREx positions that are earlier than it; 3-sigma one year after the first observation.

| Object | MPC obs in first 7 days | SPHEREx positions | 3-sigma (km) without -> with | Factor | Note |
|-|-|-|-|-|-|
| 2025 YH5 | 22 | 7 | 3,534,715 -> 1,121,914 | 3.2 |  |
| C/2026 S1 | 14 | 2 | 27,631,448 -> 31,811,539 | 0.9 |  |
| 2025 ST20 | 18 | 1 | 15,967,617 -> 2,719,821 | 5.9 |  |
| 2025 YJ6 | 107 | 2 | 1,116,627 -> 1,060,971 | 1.1 |  |
| P/2025 Y2 | 39 | 1 | 176,580,398 -> 132,967,093 | 1.3 | fit did not fully converge: unreliable |
| C/2025 L2 | 61 | 1 | 11,196,919 -> 7,310,388 | 1.5 |  |
| P/2026 V1 | - | - | - | - | short-arc covariance not finite (fit too weak to sample) |
| C/2025 W2 | - | - | - | - | no SPHEREx position earlier than the first known observation |

## 3. Headlines for the pitch

1. MEASURED: 7 of our 8 SPHEREx finds were caught before anyone else saw them: 4 to 20 days before the first known observation anywhere (JPL SBDB), including the potentially hazardous asteroid 2025 YH5 (18 days earlier, 7 positions).
2. COMPUTED: had Rewind run on the day of discovery, our old SPHEREx positions would have shrunk the one-year position uncertainty of 2025 ST20 by about 6x (16 million km to 2.7 million km) and of 2025 YH5 by about 3x (3.5 million km to 1.1 million km).
3. COMPUTED (honest limit): today these objects already have weeks to a year of telescope data, so our few stacked positions improve their orbits by only 0 to 7 percent; Rewind's value is speed, right after discovery, not after the follow-up is done.

Notes: C/2025 W2 was first observed on 2025-10-26, one day before our first SPHEREx day, so it is a SPHEREx detection with extra positions, not a precovery. P/2026 V1's first known observation is 2026-09-15 (precovered back from its 2026-11-03 designation), so our lead is 3-13 days, not 52-62. Nothing was submitted to the MPC.
