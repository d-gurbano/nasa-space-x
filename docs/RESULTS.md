# Rewind final results (2026-11-15 04:56 Arizona)

Engine: rewind_engine (branch c2-engine). All numbers MEASURED from SPHEREx pixels unless marked; verdict rules in rewind_engine/README.md. Nothing was submitted to the MPC or anywhere else.

Totals: 38 objects; FOUND 7, HINT 10, TOO_FAINT 18, NO_PHOTOS 3.

> Correction (2026-11-15, see docs/IMPACT.md): "days before discovery" here used the designation date. Against the first known observation anywhere (JPL SBDB): P/2026 V1 is 3-13 days earlier (first obs 2026-09-15), not 52-62; C/2025 W2 (Kaggle run) is NOT earlier (first obs 2025-10-26), so it is a SPHEREx detection with extra positions, not a precovery.

Checks: snr = null-scaled S/N >= 5 in the sky-cleaned stack; cleaned = static-sky references for >= 10 frames; nulls = no null path reaches it; time_shift = peak at shift 0; days = >= 2 days with S/N >= 2; detectable = injection recovers >= 50% at the predicted brightness; sign_test = more frames positive than on every null path (>= 3 sigma); not_one_day = S/N >= 3 without the best day; orbit = refit with the new positions stays good (not required for known objects).

| Object | Role | Verdict | Null-scaled S/N | Days before discovery | Frames (cleaned / read) | Checks passed | Second method (aperture on median) |
|-|-|-|-|-|-|-|-|
| 2025 ST20 | precovery | FOUND | 9.1 | 1-14 | 77 / 120 | 9/9 | S/N 5.2, 44 uJy, 79 frames |
| 3I/ATLAS | known | FOUND | 14.9 | - | 99 / 120 | 8/8 | S/N 153.9, 7410 uJy, 103 frames |
| C/2025 L2 | precovery | FOUND | 5.7 | 7-20 | 85 / 120 | 9/9 | S/N 4.7, 30 uJy, 87 frames |
| C/2026 S1 | precovery | FOUND | 6.6 | 1-4 | 110 / 300 | 9/9 | S/N 4.5, 18 uJy, 110 frames |
| 433 Eros | known | FOUND | 110.9 | - | 17 / 300 | 8/8 | S/N 5362.4, 168844 uJy, 17 frames |
| P/2025 Y2 | precovery | FOUND | 5.6 | 2-6 | 42 / 61 | 9/9 | S/N 5.1, 34 uJy, 42 frames |
| P/2026 V1 | precovery | FOUND | 5.9 | 52-62 | 100 / 300 | 9/9 | S/N 3.1, 15 uJy, 108 frames |
| 2025 WC14 | precovery | HINT | 2.2 | - | 58 / 120 | 3/9; failed: snr, days, detectable, sign_test, not_one_day, orbit | - |
| 2025 XK3 | precovery | HINT | 2.1 | - | 22 / 34 | 1/9; failed: snr, cleaned, time_shift, days, detectable, sign_test, not_one_day, orbit | - |
| 2026 AQ1 | precovery | HINT | 2.2 | 83-90 | 43 / 120 | 4/9; failed: snr, detectable, sign_test, not_one_day, orbit | S/N 3.2, 39 uJy, 14 frames (best days only, post hoc) |
| 2026 PW6 | precovery | HINT | 4.8 | 25-28 | 27 / 44 | 6/9; failed: snr, detectable, orbit | S/N 6.4, 47 uJy, 27 frames (best days only, post hoc) |
| C/2026 C1 | precovery | HINT | 2.4 | - | 46 / 120 | 4/9; failed: snr, days, sign_test, not_one_day, orbit | - |
| C/2026 H2 | precovery | HINT | 2.9 | 37-236 | 106 / 300 | 5/9; failed: snr, sign_test, not_one_day, orbit | S/N 1.9, 19 uJy, 32 frames (best days only, post hoc) |
| C/2026 J1 | precovery | HINT | 3.2 | 5 | 67 / 120 | 4/9; failed: snr, days, sign_test, not_one_day, orbit | S/N 1.4, 29 uJy, 7 frames (best days only, post hoc) |
| C/2026 M3 | precovery | HINT | 3.8 | 37-79 | 71 / 120 | 6/9; failed: snr, detectable, orbit | S/N 0.9, 13 uJy, 37 frames (best days only, post hoc) |
| C/2026 Q1 | precovery | HINT | 6.1 | 41-42 | 44 / 120 | 7/9; failed: sign_test, not_one_day | S/N 6.0, 124 uJy, 8 frames (best days only, post hoc) |
| C/2026 S2 | precovery | HINT | 2.4 | 188 | 95 / 120 | 3/9; failed: snr, days, detectable, sign_test, not_one_day, orbit | - |
| 2024 YR4 | known | TOO_FAINT | 0.3 | - | 17 / 20 | 1/8; failed: snr, nulls, time_shift, days, detectable, sign_test, not_one_day | - |
| 2025 OZ | lost | TOO_FAINT | -0.8 | - | 7 / 22 | 0/9; failed: snr, cleaned, nulls, time_shift, days, detectable, sign_test, not_one_day, orbit | - |
| 2025 WB16 | precovery | TOO_FAINT | 1.0 | - | 61 / 120 | 2/9; failed: snr, nulls, time_shift, days, sign_test, not_one_day, orbit | - |
| 2025 WD6 | precovery | TOO_FAINT | 0.2 | - | 58 / 120 | 1/9; failed: snr, nulls, time_shift, days, detectable, sign_test, not_one_day, orbit | - |
| 2026 AP1 | precovery | TOO_FAINT | -0.9 | - | 8 / 20 | 0/9; failed: snr, cleaned, nulls, time_shift, days, detectable, sign_test, not_one_day, orbit | - |
| 2026 BC2 | precovery | TOO_FAINT | 1.2 | - | 41 / 120 | 2/9; failed: snr, nulls, time_shift, days, sign_test, not_one_day, orbit | - |
| 2026 JM4 | precovery | TOO_FAINT | -0.8 | - | 9 / 20 | 1/9; failed: snr, nulls, time_shift, days, detectable, sign_test, not_one_day, orbit | - |
| 2026 JS1 | precovery | TOO_FAINT | 1.3 | - | 36 / 80 | 1/9; failed: snr, nulls, time_shift, days, detectable, sign_test, not_one_day, orbit | - |
| 2026 KC3 | precovery | TOO_FAINT | 0.3 | - | 74 / 300 | 2/9; failed: snr, nulls, days, detectable, sign_test, not_one_day, orbit | - |
| 2026 SW2 | precovery | TOO_FAINT | 1.0 | - | 60 / 120 | 1/9; failed: snr, nulls, time_shift, days, detectable, sign_test, not_one_day, orbit | - |
| 2026 VD1 | precovery | TOO_FAINT | -1.0 | - | 16 / 20 | 1/9; failed: snr, nulls, time_shift, days, detectable, sign_test, not_one_day, orbit | - |
| 2026 VG18 | precovery | TOO_FAINT | -1.7 | - | 11 / 20 | 1/9; failed: snr, nulls, time_shift, days, detectable, sign_test, not_one_day, orbit | - |
| C/2025 W1 | precovery | TOO_FAINT | 1.3 | 44 | 90 / 120 | 2/9; failed: snr, nulls, time_shift, days, sign_test, not_one_day, orbit | - |
| C/2025 Y1 | precovery | TOO_FAINT | 0.4 | - | 85 / 112 | 2/9; failed: snr, nulls, time_shift, days, sign_test, not_one_day, orbit | - |
| C/2026 B2 | precovery | TOO_FAINT | -2.5 | 221-231 | 50 / 155 | 2/9; failed: snr, nulls, time_shift, detectable, sign_test, not_one_day, orbit | - |
| P/2026 R1 | precovery | TOO_FAINT | -0.8 | - | 72 / 120 | 1/9; failed: snr, nulls, time_shift, days, detectable, sign_test, not_one_day, orbit | - |
| P/2026 T1 | precovery | TOO_FAINT | 0.8 | 19 | 53 / 240 | 2/9; failed: snr, nulls, time_shift, days, sign_test, not_one_day, orbit | - |
| P/2026 U1 | precovery | TOO_FAINT | -0.2 | 220 | 89 / 120 | 2/9; failed: snr, nulls, time_shift, days, sign_test, not_one_day, orbit | - |
| 99942 Apophis | known | NO_PHOTOS | - | - | - / 0 | - | - |
| 101955 Bennu | known | NO_PHOTOS | - | - | - / 0 | - | - |
| C/2025 R2 | precovery | NO_PHOTOS | - | - | - / 0 | - | - |

## Strict reviews of every precovery FOUND (MEASURED)

| Object | S/N | S/N without best day | Frames positive: target vs null max | Frames set aside (star flags) | Known object within 60" (JPL sb_ident) | Orbit refit RMS before -> after | Second method (aperture on median of cleaned frames) |
|-|-|-|-|-|-|-|-|
| 2025 ST20 | 9.1 | 5.6 | 0.82 vs 0.59 | 32% | none (nearest 684") | 0.949 -> 0.943 (1 position, 0.05 sigma) | 44 uJy, S/N 5.2, 0/200 random apertures brighter |
| C/2026 S1 | 6.6 | 4.9 | 0.67 vs 0.61 | 29% | none | 0.980 -> 0.977 (2 positions; leave-one-day-out 0.971 / 0.986) | 18 uJy, S/N 4.5, 0/200 brighter |
| P/2026 V1 | 5.9 | 5.1 | 0.62 vs 0.56 | 25% | none (nearest 201") | 0.703 -> 0.710 (1 position) | 15 uJy, S/N 3.1, 0/200 brighter (weakest second-method result; one day, 2026-09-06, is strongly negative at -4.5) |
| C/2025 L2 | 5.7 | 4.9 | 0.76 vs 0.59 | 23% | none | 0.866 -> 0.865 (1 all-days stacked position) | 30 uJy, S/N 4.7, 0/200 brighter |
| P/2025 Y2 | 5.6 | 4.3 | 0.74 vs 0.60 | 22% | (46890) 1998 RK48, V 19.6, 8.3-8.6 px from the path on 2025-12-25 only: in the background annulus, not the fit box, so it can only lower the flux; without that day S/N 4.9 | 0.918 -> 0.923 (1 all-days stacked position) | 34 uJy, S/N 5.1, 0/200 brighter |

Reading: all five pass every predefined check, and the simpler second method agrees in sign and roughly in strength
(a median is about 1.25x less efficient than the clipped weighted mean, and it has no colour weighting). P/2025 Y2,
C/2025 L2 and P/2026 V1 are marginal (S/N 5.6-5.9, near the threshold); 2025 ST20 and C/2026 S1 are the strongest.
None was seen in a single photo; all are stack detections. Positions are from stacks and only catch moderate orbit
inconsistencies (search +-1.25 px). Nothing was submitted to the MPC.

Known objects (not precovery claims): 433 Eros (S/N 111) and 3I/ATLAS (S/N 14.9) are FOUND = "SPHEREx saw it".

## C/2026 Q1 (HINT, "strong but not every check passed")
S/N 6.1 in the sky-cleaned stack, but the sign test fails (0.57 vs null max 0.65) and the signal rests on 2026-07-09
(0.7 without it). 55% of its frames sit next to bright Milky Way stars (star-halo / overflow flags), including every
2026-07-17 frame (the S/N 12.4 day; chi2 up to 550, bright references). The earlier orbit-RMS increase (0.908 -> 1.122)
came from two bad positions (a star day without references and a noise-picked April day); with positions only from
cleaned, detected days it is 0.908 -> 0.913. A simpler second method on the best July days (median of 28 cleaned frames,
no frame QA; chosen after looking, so not independent) shows a clean point source at the predicted spot (133 uJy,
S/N 15). The comet is probably there, but our strict tests cannot prove it.

## NEOWISE pixel checks (archive-agent leads)
| Object | Result | Why |
|-|-|-|
| 2015 SA (lost) | HINT, not confirmed | only one NEOWISE exposure per band covers the predicted spot; W2 S/N about 4 at the catalog hit, W1 null-scaled 0.8 (a null path reaches 12); the position fits the orbit (0.92" residual; RMS 0.724 -> 0.724) and no static source is there, but one low-S/N exposure cannot be confirmed. No separate page. |
| C/2026 H2 | NOT_SUPPORTED | 11 exposures in the visit; stack null-scaled S/N 0.8; the hit does not recur |
| C/2026 C1 | NOT_SUPPORTED | 14 exposures; nothing at the predicted path |

## Benchmark ("pretend it is new", 10 known asteroids, V 16.2-20.0)
Rewind found 5 of 9 known asteroids that were visible in SPHEREx before the pretend discovery date (plus 3 hints;
1 missed), with 0 false alarms in 10 cases. Blind positions were 0.1-2.8" from the truth. Method: orbit from only the
first 20 days of MPC observations after a hidden date; blind search 20 days before it; truth = the same photometry at
the true positions (S/N >= 5). The blind verdict skips the orbit-refit step, and frames were listed with MOST (which
uses the full orbit). An earlier run had a truth-ordering bug (fixed; that run is discarded).

## Other notes
- Apophis and C/2025 R2: no SPHEREx frames (MOST). Bennu: MOST cannot compute its path, not searched.
- Real-or-fake classifier: held-out accuracy 0.904 (gradient boosting), 0.871 (logistic), 0.823 (rules) vs 0.608 baseline;
  not used for faint stack-only objects.
