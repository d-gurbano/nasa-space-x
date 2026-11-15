# rewind_engine

Offline engine for **Rewind** (NASA Space Apps 2026, team SpaceX). For a newly discovered asteroid or
comet it looks in older NASA SPHEREx images (2025 to now) for the object before its discovery
("precovery"), runs every control we know of, and writes static files for the website
(format: `docs/DATA-CONTRACT.md`). Nothing is ever submitted to the MPC or anywhere else.

## Run

```bash
PY=/Users/rahmanbazarov/Data/programming/SpaceApps2026-Rewind/.venv/bin/python
cd <this worktree>
$PY -m rewind_engine run --objects first --out <MAIN>/data/site      # everything, in order
# or step by step:
$PY -m rewind_engine prepare  --objects c2026s1,eros,2025oz           # MOST + Horizons frame tables
nohup $PY -m rewind_engine fetch --objects first > fetch.log 2>&1 &   # detached, resumable downloads
$PY -m rewind_engine measure  --objects first                         # photometry, controls, verdicts, pages
$PY -m rewind_engine site     --objects first                         # rebuild index.json from saved pages
$PY -m rewind_engine train                                            # real-or-fake classifier
nohup $PY -m rewind_engine benchmark > bench.log 2>&1 &               # "pretend it is new" test
$PY -m pytest tests -q                                                # unit tests
```

`--objects` is `first` (the first-run list), a CSV with the same columns, or slugs/names
separated by commas. Work files go to `<MAIN>/data/results/c2-engine/` (stamps, references, tables,
kete cache, `fetch/state.jsonl` checkpoint). Website files go to `<MAIN>/data/site/`.
Stop a running fetch cleanly with `touch <WORK>/fetch/STOP`; restarting skips everything already on disk.

## What happens per object

| Step | Module | Notes |
|-|-|-|
| Object list | `objects.py` | top 30 of the A1 precovery shortlist + all Y1 stack candidates + 2025 OZ (lost) + Apophis, Bennu, Eros, 2024 YR4, 3I/ATLAS (known objects, never precovery claims) |
| Frames + positions | `frames.py` | IRSA MOST finds frames; JPL Horizons with observer = SPHEREx (`500@-163182`) at header MJD-AVG gives RA/Dec, rates, magnitude and the 3-sigma error ellipse. Up to 300 frames per object, ranked by closeness to discovery and predicted brightness |
| Pixels | `fetch.py`, `s3read.py` | compact stamps from the public S3 bucket with HTTPS range reads (pilot reader made ~3x faster by computing HDU offsets from the file end; pixel-identical, checked). Stamp size grows with the uncertainty and trail |
| Static sky | `fetch.plan_refs` | for each frame, other-epoch frames covering the same spot (from the object's own MOST list, else SIA2) at the closest wavelength (WCS-WAVE is fixed per detector) |
| Photometry | `phot.py` | pilot ePSF forced photometry; trailed ePSF if the motion in one exposure is > 1.5 px |
| Colours | `brightness.py` | expected flux at each frame's wavelength: solar colours x reflectance template (A6 library), plus NEATM thermal for asteroids. The stack is weighted by it |
| Controls | `pipeline.py` | 24 null paths, along-track time-shifted paths, per-day split, static-sky subtracted stack, injection of fakes at the predicted brightness and fainter (recovery fraction, limiting magnitude); errors scaled by the null spread |
| Clone search | `extras.clone_search` | if sigma > 2 px: 300 covariance clones, stacked on matched-filter maps; false-alarm rate from 7,800 null trials (frame-permuted and sideways-shifted clones) |
| Orbit check | `extras.orbit_check` | per-day shift-and-stack positions, kete refit (orbitfit.py) with them added, RMS before/after; a blow-up downgrades the verdict |
| Real or fake | `realfake.py` | rules + logistic regression + gradient boosting on labelled stamps (known asteroids vs junk and planted artifacts), test split by frame |
| Verdict | `verdict.py` | FOUND / HINT / TOO_FAINT / NO_PHOTOS, with one plain sentence |
| Cloud | `extras.cloud` | 60 covariance clones at 40 dates (heliocentric ecliptic AU), before and (if measured) after |
| Website | `site.py`, `site_static.py`, `detectives.py`, `images.py` | contract files; PNGs north up, east left, nearest-neighbour, one stretch per object |
| Benchmark | `benchmark.py` | 20 known asteroids, short-arc orbit from the first 20-45 days after a hidden date, blind search before it, truth from the true positions |

Every number in the outputs is labelled MEASURED (from pixels), COMPUTED (arithmetic) or ESTIMATED (model).

## Verdict rules (final)

Frame QA first: frames with bright-star flags (OVERFLOW, SUR_ERROR, HALO, SATELLITE_HALO) in the fit box, and frames
without a static-sky reference whose PSF fit is poor (chi2 > 20), are removed from the target AND every control path
(not applied to objects bright in single frames). Static-sky references must be taken when the object had moved
>= 40 px (comets: coma) or 5 px + trail (asteroids).

FOUND needs all of: sky-cleaned stack S/N >= 5 after null scaling; no null path as high; the time-shift curve peaks
at 0; at least 2 days with S/N >= 2; injection recovers >= 50% of fakes at the predicted brightness; more frames
positive than on every null path (>= 3 sigma, the "sign test"); S/N >= 3 even without the best day; and the orbit
refit with positions from cleaned, detected days stays good (RMS grows < 50%, new points within 3 sigma; leave-one-day-out
refits are reported). HINT = a signal (S/N >= 3) but not every check passes; the sentence names the failing checks.
TOO_FAINT = the injection limit is brighter than the object, or nothing is seen. Known objects use the same tests
(no orbit check), and FOUND there only means "SPHEREx saw it".

Second method (`crosscheck.py`): plain aperture photometry on the median of the sky-cleaned frames, error from 200
random apertures in the same image. Stored for every FOUND; for HINTs it is run on the best days only and labelled
post hoc. `review.py` adds a JPL sb_ident known-object check (within 60") for candidates.

NEOWISE (`neowise.py`): forced photometry in WISE L1b single exposures with the same controls, for catalog hits from
the archive agent; results appear as a `neowise` block on object pages.

## Kaggle runs (faster S3 network)

```bash
$PY kaggle/build_inputs.py --shards 2 [--catchup slug,slug]  # private dataset rewind-c2-inputs + kernel folders in /tmp/c2k
kaggle datasets version -p /tmp/c2k/ds -r zip -t -m "..."     # (create the first time)
kaggle kernels push -p /tmp/c2k/kernels/rewind-c2-engine-all-a   # one CPU kernel per shard, internet on, private
# when done: tar the output on Kaggle (kaggle/pack/pack_main.py, kernel_sources = the shard) and download one file
$PY -m rewind_engine.merge_kaggle      # -> MAIN/data/kaggle/site_merged (MAIN/data/site is only read)
```

The kernel (`kaggle/k1/k1_main.py`) runs prepare -> fetch -> measure -> site per object in 2 download lanes
(measuring one object at a time), throttles IRSA (1 call / 1.5 s) and JPL (1 / 0.5 s) per kernel with a circuit
breaker on 5xx, retries MOST transport errors instead of writing NO_PHOTOS, runs the aperture cross-check on
FOUND/HINT objects, and skips objects already in its output or an attached earlier output. Objects already in the
site index are kept as they are by the merge; Kaggle re-runs of them only go to `kaggle_crosscheck.json`.

## Daily updates later (described only, not set up)

A scheduled GitHub Actions workflow (cron, once a day) would:
1. pull the MPC/JPL lists of objects discovered in the last day (SBDB query on `first_obs`, MPC NEA/Comet
   files) and append the ones whose screen says SPHEREx could have seen them;
2. refresh the SPHEREx spacecraft vectors from Horizons (`code/A2/02_spherex_vectors.py`);
3. run `prepare` + `fetch` + `measure` only for new or changed objects (the checkpoint makes reruns cheap;
   stamps could be cached between runs with `actions/cache` or an S3 bucket);
4. run the unit tests and the benchmark summary as a quality gate (fail the job if the false-alarm count rises);
5. commit the new `site/` JSON and PNGs to the website repo (or upload as a Pages artifact).
A job would need ~1-2 GB of cache and stays under the 6-hour runner limit for a few new objects per day.
Nothing would ever be posted to the MPC.

## Limits (honest)

- Static-sky references are matched in wavelength but not identical; steep-spectrum stars can leave residuals.
- Comet brightness predictions (Horizons T-mag) are rough; coma is modelled as a point source.
- The real-or-fake training negatives are partly synthetic artifacts; its accuracy on real junk may be lower.
- The benchmark lists frames with MOST (full orbit), and skips the orbit-refit step.
- kete covariance clones are linear (Gaussian) samples; for very short arcs the true region can be longer.
