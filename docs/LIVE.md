# Rewind LIVE run (2026-11-15)

Objects first observed on or after 2026-11-01 (JPL SBDB query, 2026-11-15): 455 (0 new comets). Screened with IRSA MOST (catalog=spherex, 120 days before the first observation): 296 NEOs and main-belt objects with H <= 18.5. Newest public SPHEREx frame for any of them: 2026-10-04 (VERIFIED in MOST), so the public photos end at least 27 days before these objects were first seen. Brightest predicted V in those photos: 21.56 (MOST, reflected light only).

Engine run on the 12 most promising (8 NEOs, 4 bright non-NEOs), with exactly the same final rules (frame QA, nulls, time shift, days, injection, sign test, best-day test, orbit check). Nothing was loosened and nothing was submitted.

| Object | NEO | H | Arc today (days, MPC obs) | SPHEREx frames read | Days before first obs | Verdict | Null-scaled S/N | Injection limit (AB) | Predicted (AB) |
|-|-|-|-|-|-|-|-|-|-|
| 2026 VD4 | Y | 20.55 | 11 (51) | 50 | 28 | TOO_FAINT | 0.1 | 20.7 | 22.2 |
| 2026 VH6 | Y | 20.47 | 11 (24) | 114 | 37 | TOO_FAINT | -0.8 | 20.6 | 21.1 |
| 2026 VB16 | Y | 20.07 | 7 (30) | 120 | 31 | TOO_FAINT | -1.0 | 21.0 | 22.5 |
| 2026 VJ7 | Y | 20.85 | 7 (21) | 120 | 32 | TOO_FAINT | 1.1 | 20.4 | 21.9 |
| 2026 VW5 | Y | 23.15 | 5 (32) | 20 | 34 | TOO_FAINT | 0.4 | 21.6 | 23.1 |
| 2026 VW6 | Y | 22.43 | 7 (35) | 120 | 34 | TOO_FAINT | 0.8 | 20.0 | 21.5 |
| 2026 VZ1 | Y | 22.21 | 10 (32) | 120 | 29 | TOO_FAINT | -1.3 | 20.8 | 22.3 |
| 2026 VC13 | Y | 22.29 | 6 (41) | 120 | 35 | TOO_FAINT | -1.5 | 21.0 | 22.5 |
| 2026 VQ7 | N | 17.75 | 3 (6) | 80 | 90 | TOO_FAINT | -2.7 | 19.7 | 21.2 |
| 2026 VH7 | N | 18.2 | 3 (17) | 61 | 36 | TOO_FAINT | -1.2 | 19.8 | 21.3 |
| 2026 VB3 | N | 18.21 | 3 (15) | 120 | 28 | TOO_FAINT | -1.4 | 20.9 | 22.4 |
| 2026 VU17 | N | 18.23 | 5 (19) | 38 | 40 | TOO_FAINT | 0.6 | 20.6 | 22.1 |

Live stats: {'searched': 12, 'found': 0, 'hints': 0, 'too_faint': 12, 'no_photos_yet': 92, 'run_iso': '2026-11-15T17:21+00:00', 'since_first_obs': '2026-11-01', 'note': 'objects first observed 2026-11-01 or later, searched with the same final rules', 'candidates': 455, 'screened': 296, 'with_public_photos': 204, 'newest_public_frame': '2026-10-04', 'min_days_before_first_obs': 27}


## Honest notes

- Screen: 296 objects screened; 204 have public SPHEREx photos in the 120 days before their first observation, 92 have none yet (MEASURED, MOST).
- The newest public SPHEREx photo for any candidate is from 2026-10-04: the public archive (QR3, released in weekly batches) ends at least 27 days before these objects were first seen. In those older photos the objects were farther away and fainter.
- All 12 objects run were predicted 0.5-1.5 mag fainter than our injection-tested limit in those photos (COMPUTED from MEASURED limits), so TOO_FAINT is the correct, expected answer. No FOUND, so there is no live orbit refit to report; nothing was loosened to change that.
- Positions are uncertain for these young orbits (U 7-9), so stamps were large and the orbit-clone search (300 covariance clones) ran on 8 of the 12 (the other 4 had no usable clone positions). Its best clones reached S/N up to 42 (2026 VW5) and 18 (2026 VB16), but null trials on shifted and shuffled paths reach the same values (false-alarm rate x 300 clones = 0.2-1.6), which is what stars crossing un-subtracted clone paths look like. None is significant, so none is claimed (MEASURED).
- The run used the Mac in 3 parallel lanes (about 35 minutes for 12 objects) rather than a Kaggle kernel: packaging a new kernel did not fit the 90-minute box.

## Pitch lines

1. MEASURED: on 2026-11-15 Rewind searched, end to end in about 40 minutes, every asteroid first seen since 1 November that SPHEREx might have photographed (296 screened, the 12 most promising measured with all checks).
2. MEASURED: the limit today is data age, not software: the newest public SPHEREx photos end 27+ days before these discoveries, when the objects were 0.5-1.5 mag too faint; Rewind says 'too faint' honestly instead of guessing.
3. COMPUTED (from the archive run, docs/IMPACT.md): when the photos are recent enough, the same pipeline found 7 objects 4-20 days before anyone else and would have cut the one-year uncertainty of 2025 ST20 by about 6x and of the hazardous 2025 YH5 by about 3x right after discovery; faster public releases of SPHEREx data would turn that into a live service.
