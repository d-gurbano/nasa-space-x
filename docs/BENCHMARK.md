# Benchmark v2 (2026-11-15): harder 'pretend it is new' test

Method: v2: 10 NEOs, 8 comets, 12 main-belt; orbit from the MPC observations in the first 20-45 days after a hidden date; up to 40 SPHEREx frames in the 20 days before it; blind engine with the final rules (orbit-refit check skipped); truth = same photometry at the true JPL Horizons positions (S/N >= 5); decoy = same frames, path shifted 8 px sideways. missed excludes hints. Frames listed with MOST (full orbit).

**Rewind found 10 of 18 known objects that were visible in SPHEREx before the pretend discovery date (7 more were hints, 1 missed), with 0 false alarms in 23 real cases and 22 empty-sky decoys (1 more decoy failed to run).** (MEASURED)

- Usable cases: 23 of 30: 7 of 30 cases had no usable 'pretend it is new' test: 5 periodic comets (P/2016 G1, P/2005 L1, 383P, 59P, 176P; 198P and 244P were replaced by C/2025 Y1 and P/2025 Y2) had no ground observations after any date with SPHEREx frames, and 2 NEOs gave a short-arc orbit whose covariance cannot be sampled. Comet cases are therefore only 3 usable (217P, C/2025 Y1, P/2025 Y2).
- By type (usable / seen by the truth run / FOUND / HINT): NEO 8/5/2/3, comet 3/2/1/2, main belt 12/11/7/4.
- Positional error of the blind measurement vs the truth: median 0.5 arcsec, 90th percentile 2.85 arcsec (19 FOUND/HINT cases).
- False alarms: 0 on the real cases (FOUND where the truth run sees nothing, or position > 12 arcsec off) and 0 on 22 empty-sky decoys (1 decoy failed to run).
- Missed (`missed` now excludes hints): only cases the truth run sees and the blind run calls TOO_FAINT.

## Completeness vs brightness (V from JPL Horizons at the frames)

| V | cases | FOUND | FOUND or HINT | seen by the truth run | fraction FOUND |
|-|-|-|-|-|-|
| 0-17 | 4 | 3 | 4 | 4 | 0.75 |
| 17-18 | 5 | 4 | 4 | 4 | 0.8 |
| 18-19 | 8 | 2 | 8 | 8 | 0.25 |
| 19-20 | 4 | 1 | 3 | 2 | 0.25 |
| 20-21 | 2 | 0 | 0 | 0 | 0.0 |

Reading: the strict rules buy zero false alarms at the price of completeness: below V 18 Rewind finds 3 of 4 objects (bright fast NEOs can fail the time-shift or sign test and stay HINT); at V 18-20 most visible objects are only HINTs (2 of 8 and 1 of 4 FOUND); beyond V 20 nothing is seen even with the true positions.

## Precovery hit rate of the archive search (253 objects, MEASURED)

| Type | searched | with photos | FOUND | HINT | FOUND rate | median predicted AB (all / FOUND) |
|-|-|-|-|-|-|-|
| comet | 32 | 31 | 5 | 13 | 0.161 | 20.73 / 20.37 |
| famous | 5 | 3 | 2 | 0 | 0.667 | 15.92 / 13.02 |
| lost | 11 | 11 | 0 | 2 | 0.0 | 22.74 / None |
| neo | 205 | 201 | 3 | 33 | 0.015 | 21.45 / 19.78 |

No main-belt objects were in the archive search; NEOs dominate it and are mostly fainter than the limit (median AB 21.5), hence 1.5% (3 of 201). Comets: 5 of 31 (16%), one of which (C/2025 W2) is not earlier than its first known observation.
