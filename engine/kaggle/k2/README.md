# K2: Kaggle kernel "rewind-c2-ai"

One script, `k2_main.py`, does the following on a Kaggle GPU machine with internet. It re-downloads the A8 AI-training set "v2", builds per-patch time series, trains two small models and compares them with the simple methods.

Every comparison uses the same held-out data for every method. The output is `report.md`, `metrics.json`, `run_log.txt`, a few CSVs and PNGs, and small model weights, all in `/kaggle/working`. Pixels stay in `--tmp` (`/kaggle/tmp` if it exists, else `/tmp/k2tmp`), so they are not saved as output.

Labels: MEASURED, COMPUTED, ESTIMATED.

## What "v2" is

- **Definition.** A8 `build_patches.py select_v2 8` writes `data/08-ai-training/index/frames_selected_v2.parquet`.
  - It lists **8,792 SPHEREx L2 frames** (MEASURED) for 10 sky clusters of 3x3 patches each.
  - For each cluster and detector it takes 8 times the v1 frame count, evenly spaced in time and capped by what IRSA SIA2 listed. It also keeps every frame that was already downloaded.
  - Per cluster (MEASURED): NEP-A 2,177, NEP-B 1,156, NEP-C 1,159, NEP-D 642, SEP-A 1,583, SEP-B 607, ECL-1 340, ECL-2 382, MID-1 365, MID-2 381.
- **What exists locally (MEASURED).**
  - `raw/` holds 1,573 frames (4.6 GB). v1 and the v2 build used 1,522 of them: 14,289 patch-epochs.
  - The v2 fetch (`run_v2_fetch.sh`) started after `STOP_FETCH` had been created (03:01). It exited at 03:25 with all 7,219 remaining frames marked "stop" and none downloaded (`logs/fetch_v2.log`).
  - So `patches_v2/`, `baselines_v2/` and `injected_test_v2/` hold the same 1,522 frames as v1. `NUMBERS-v2.md` equals `NUMBERS-v1.md`.
  - `labeled_v2/` (and `labeled/`) are empty because `labeled_set.py` crashed in both builds. `splits_baselines.splits` merges `frames.parquet` on `frame_id`. Frames that sit in two pole clusters duplicate rows there, so `sp.loc[frame_id]` returns a DataFrame and `L.split.unique()` fails with "unhashable Series". The kernel does not use that code path.
- **What the kernel downloads.** All 8,792 v2 frames from `s3://nasa-irsa-spherex`, using anonymous HTTPS Range reads with the unchanged A8 `fetch_frame`. Raw pixels are not shipped, so every frame is fetched again.
  - Each frame takes 9 cutouts of 96x96 px (IMAGE, VARIANCE, ZODI, FLAGS, per-pixel wavelength and bandwidth, ePSF zones) plus a 64x64 north-up resample.
  - Bytes read: about 6 MB per frame (MEASURED in the smoke run, 107 MB / 18 frames), so about 50-80 GB in total (ESTIMATED).
  - Storage: 1.9 MB per frame compressed (MEASURED on one frame), so about 17 GB of raw files. Consolidated patches add about 14 GB (ESTIMATED: 2.5 GB x 8,792 / 1,522). Raw files are deleted after consolidation (`--keep-raw` keeps them).
  - **IRSA queries: 0.** The frame list and S3 keys come from the shipped parquet, so IRSA SIA2 is not needed (it returns 502 today).
  - Download safeguards:
    - retries: 4 per HTTP range in `rewind._range`, then 3 per frame
    - circuit breaker: 25 consecutive failed frames trigger a 120 s pause; the stage gives up after 3 pauses
    - disk guard: the download stops while free disk can still hold the consolidated copy
    - time box: 180 min
    - the download is resumable and the log shows MB/s, frames/s and ETA every minute

## Stages and time boxes

| stage | does | box | expected on a T4/P100 (ESTIMATED) |
|-|-|-|-|
| realfake | engine features + 3x15x15 CNN stamps from `data/07-answer-keys/labeled_set`; GB vs CNN vs rules vs majority; 2 split kinds x 5 seeds | 45 min | 5-15 min |
| download | v2 frames from S3 | 180 min | 40-150 min (depends on Kaggle-to-AWS throughput, unknown; the shared Mac link gave 0.4-1.5 MB/s) |
| build | A8 `cmd_consolidate` into `patches_v2k/` and an index; deletes raw | 60 min (not interruptible) | 15-40 min, peak RAM about 8 GB |
| staticref | A8 static-sky reference for the 45 val + test patches, 4 processes | 60 min | 10-25 min |
| es_train | Expected-Sky U-Net | 90 min | 20-50 min |
| es_eval | residuals, injections, false positives | 75 min | 15-40 min |

- **Total:** about 2-5 h expected. Hard cap `--max-hours 10.5`.
- **Robustness:** each stage writes `metrics.json` (atomically) and `report.md` when it ends. A failed stage is logged with its traceback and the next stages still run. A stage whose input failed is marked "skipped".
- **Disk:** needs about 35 GB peak in `--tmp`.
- **Smoke run:** `--smoke` runs every stage on 18 frames (detector 4, three clusters) and 110 labeled stamps. It takes about 5 min on a laptop, most of it the download.

## (a) Real or fake: splits and metrics

- **Samples.** This is exactly the engine's `realfake.build_training`:
  - real: known-asteroid stamps with S/N >= 5
  - fake: artifacts planted into empty stamps with |S/N| <= 5 (cosmic, hot pair, streak, ringing) that reach S/N >= 5
  - the kernel plants 2 artifacts per empty stamp (`--n-art-per`; the engine uses 1)
  - the GB features and the CNN stamps come from the same samples
- **Splits.** `GroupShuffleSplit`, 30% test.
  - `by_frame`: groups = OBSID, the same as the engine
  - `by_sky_region`: groups = 10x10 deg sky cells (RA scaled by cos Dec). Each frame is assigned to the cell of its median stamp position, so this split is also by frame.
  - 5 seeds per split kind. Every model is scored on the identical test indices.
- **Training.**
  - GB uses the engine's settings and is retrained on each training split. The shipped `models.joblib` was trained on a different split, so it is not reused.
  - CNN: the epoch count is chosen on an inner group split of the training set, then the CNN is refit on all of it. Predictions average the 8 flips and rotations.
- **Metrics (MEASURED).**
  - accuracy at 0.5
  - ROC AUC
  - recall of real, recall of fake, precision of real
  - fraction correct per fake type
  - majority-class accuracy
- **Seed 0 (COMPUTED):** paired bootstrap 95% CIs over test samples for accuracy, AUC and CNN minus GB. The verdict says "no significant difference" when the CI contains 0.

## (b) Expected Sky: splits and metrics

- **Model.** A U-Net (0.47 M params).
  - Input: the K=6 other epochs of the same detector, more than 1 day away, closest in wavelength. For each: asinh-scaled image, wavelength offset in target channel widths, and a mask.
  - It also gets the base: the mean of the 2 closest refs.
  - Output: `pred = base * (1 + g) + h`. The head is zero-initialised, so the untrained model equals the engine-style baseline.
  - Loss: Huber of (pred - data)/sqrt(VARIANCE) on good pixels.
- **Region split** (A8 frozen clusters):
  - train: NEP-A, NEP-B, SEP-A, ECL-1, MID-1, epochs before MJD 61200 (2026-06-17)
  - val: NEP-C, used for early stopping and noise calibration
  - test: NEP-D, SEP-B, ECL-2, MID-2
  - Test results are split into `region` (epochs before 61200) and `region+time` (later epochs). The pole clusters share exposures, and `region+time` exposures were never trained on in any cluster, so it is the strict test.
- **Baselines**, on identical pixels:
  - `engine_2ref`: mean of the 2 closest-wavelength other-epoch patches, which is what the engine does
  - `a8_staticref`: the A8 `baselines_v2` per-pixel linear fit in wavelength
- **Metrics (MEASURED; CIs COMPUTED):**
  - **Residual chi** = (data - prediction)/sqrt(VARIANCE): robust std, RMS, and fraction with |chi| > 5. Given for all pixels and for pixels within 4 px of bright static sources.
  - **False positives:** matched-filter (ePSF) S/N > 5 where nothing was injected, measured at bright stars and at random spots. Each method's S/N is first divided by its robust S/N scatter at random val spots, so all methods use the same 5-sigma meaning.
  - **Injection recovery:** completeness (calibrated S/N >= 5 at the true position, overall and for sources with predicted S/N > 5) and median recovered/injected flux. Two injection sets, both made with the A8 kit (real ePSF, LVF wavelength, shot noise):
    - `frozen_v2`: the frozen `injected_test_v2/truth.parquet` tracks (1,984 injections, mostly ECL-2 and MID-2), re-injected on the same frames
    - `fresh`: one point source 1-4 px from a bright star plus one isolated source per test epoch, AB 16-20.5
  - Each is split into "near bright, 4 px or closer" and "isolated".
- **Verdict:** `es_eval.verdict` states plainly whether the U-Net beats the better baseline on each headline number. Read it together with the CIs. A loss (the U-Net not beating the baseline) is reported as a loss.

## Local CPU preview of (a) (MEASURED 2026-11-15, full labeled set, same code)

| split, seed 0 | CNN | GB | majority |
|-|-|-|-|
| by_sky_region, 274 test samples | accuracy 0.982, AUC 0.996 | accuracy 0.934, AUC 0.986 | 0.573 |

- CI of CNN - GB AUC: [0.002, 0.021] (COMPUTED).
- Over 5 sky splits: CNN accuracy 0.971 +/- 0.009, GB 0.937 +/- 0.009.
- by_frame, seed 0: the CI of the CNN - GB AUC difference is [-0.007, 0.024], so there is no significant AUC difference. The accuracy difference is [0.017, 0.071].
- This result holds only for these planted artifacts.

## Inputs

`k2_inputs_manifest.txt` lists 954 files, 63.5 MB (MEASURED):
- code: A0 `rewind.py`, A8 `build_patches`, `inject` and `splits_baselines`, and 5 `rewind_engine` modules (these come from the c2-kaggle worktree)
- the v2 frame list
- the frozen injection truth
- the 07 labeled set: 941 FITS stamps, 63 MB, the only pixels shipped

The kernel finds the dataset by globbing `/kaggle/input/**/rewind_inputs/MARKER`, or takes `--inputs-root`. It copies the A8 code into `--tmp` and runs it with `A8_VERSION=v2k`, so the shipped `v1`/`v2` names are never written.

## Risks

- **Download rate** is the main unknown. If it is slow, the time box keeps fewer frames: the clusters are interleaved, and the report gives the real count. The set is only bigger than v1 if more than 1,522 frames arrive.
- **Disk:** about 35 GB peak. If `/kaggle/tmp` is smaller, the disk guard stops the download early (reported).
- **The real-or-fake test is narrow.** The fakes are planted artifacts, so a model can learn the planting recipe. The data are small (about 1,000 samples, 100 frames, 21 sky cells), so the CIs are wide.
- **Expected Sky approximations:**
  - The matched filter samples the native ePSF on the aligned grid, ignoring blur from bilinear resampling. This applies to every method equally.
  - Injections are added only to the target epoch. The predictions use other epochs only, so they do not change.
- **Static-reference coverage:** the A8 reference covers 20-42% of pixels in sparse ecliptic and mid-latitude patches in v1 (A8 REPORT). Tables compare methods only on pixels where all of them predict, and give engine vs U-Net separately for epochs without an A8 reference.
- **Local smoke test:** run on the Mac with MAIN's python plus a read-only PYTHONPATH link to an existing torch 2.5.1. A new pip-installed venv in `/tmp` could not load compiled libraries: macOS blocks them because the files carry a quarantine attribute. Kaggle images ship torch.
