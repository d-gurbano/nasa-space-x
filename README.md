# Rewind - every discovery has a past

NASA Space Apps Challenge 2026, challenge "Planet X and SPHEREx". Team SpaceX: Rahman Bazarov, Dovlet Gurbanov.

When a new comet or asteroid is discovered, Rewind looks for it in older NASA SPHEREx photos taken before anyone knew it was there. Earlier positions make its future path more certain. The public site is an interactive 3D solar system with a time slider. When the slider passes a date where SPHEREx caught an object before its discovery, the real old photo appears.

## Results (MEASURED unless noted)
- 265 newly discovered comets and asteroids searched in SPHEREx QR3/DR1 photos (Mac run plus Kaggle runs; 12/12 overlapping objects agree).
- 8 found in older SPHEREx photos (stack detections that pass every check). 7 of them were seen before the first known observation anywhere, 4 to 20 days earlier, including the potentially hazardous asteroid 2025 YH5 (18 days, S/N 34 in the stack, seen on 8 separate days).
- Benchmark ("pretend it is new", 30 cases): found 10 of 18 known objects that were visible, 7 hints, 1 missed, 0 false alarms in 23 real cases and 22 empty-sky decoys; median position error 0.5 arcsec.
- Orbit impact (COMPUTED): 0-7% today; about 6x (2025 ST20) and 3x (2025 YH5) if run on the day of discovery.
- Honest limits: the finds are stack-only, not reported to the Minor Planet Center; public SPHEREx photos lag about 6 weeks.
Details: docs/RESULTS.md, docs/IMPACT.md, docs/LIVE.md.

## Layout
- `web/`: the website (Vite + three.js + TypeScript). Real results data is in `web/public/data/`.
  - Run: `cd web && npm install && npm run dev`
  - Build: `npm run build` (static files in `web/dist`)
- `engine/`: the Rewind engine (Python): frame finding (IRSA MOST), positions as seen from SPHEREx (JPL Horizons / kete), S3 byte-range pixel reader, sky-cleaned stacking, null paths, time shift, injection tests, orbit refit, verdicts, website export. Kaggle runner in `engine/kaggle/`.
- `data-collection/`: the scripts that gathered the input data (target lists, orbits, SPHEREx metadata, other archives, composition library, answer keys, AI training data, public-facing content).
- `docs/`: the data contract, results, impact, sources and design references.

## Data and credits
This research uses NASA SPHEREx data from the NASA/IPAC Infrared Science Archive (IRSA), plus JPL Horizons and SBDB, the Minor Planet Center, NEOWISE/WISE, and the other sources listed in docs/SOURCES.md. Partner data (for example ESA Gaia) is used only where it adds value. Nothing was submitted to the MPC or any other service.

## AI use
The code was written with AI coding assistance (Claude Code) under the team's direction and review. The real-or-fake classifier and the Expected Sky test are machine-learning models trained on SPHEREx data. No AI-generated images are used as data.
