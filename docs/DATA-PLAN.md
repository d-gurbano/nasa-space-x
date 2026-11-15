# Rewind - full data collection plan v2 (draft, not started)

Goal: find newly discovered and LOST asteroids and comets in older infrared and archive photos (SPHEREx 2025-now first, then NEOWISE/WISE and other archives) to sharpen their future paths, show what they are made of, let people help check, and train our own AI ("Expected Sky").

Decisions so far:
- partner data (Gaia, Euclid, SsODNet, SkyBoT) is allowed where useful, with the reason written down; NASA/US data is the core
- lost asteroids are added
- AI training data is added
- no Chinese sources
- Harvard 100-year plates: optional, not decided

Rules for every agent:
- public data, read-only, never submit or post anything (including the MPC)
- no logins (Space-Track only later if needed, with Rahman logging in, kept private)
- every file goes in docs/SOURCES.md with link, credit, license, US or partner, release version and file hash
- every number labeled MEASURED, COMPUTED or ESTIMATED
- everything stays inside this folder

## Step 0 - Pilot (run first)

**A0** One candidate end to end:
1. Find the object.
2. Find its SPHEREx frames.
3. Read its pixels (AWS or cutout).
4. Measure.
5. Check it against known answers.

Purpose: find problems before scaling up.

## Phase A - gather (9 agents in parallel, after the pilot)

**A1 Targets** -> data/01-targets
- Every object discovered since May 2025: NEOs, comets, main-belt
- MPC NEO Confirmation Page and JPL Scout (live)
- New MPECs
- LOST asteroids: single-opposition and high-uncertainty objects, poorly observed NEOs
- Sentry risk list and PHAs
- Active asteroids and interstellar objects
- Ranked target lists

**A2 Orbits, history and position engine** -> data/02-orbits
- MPCORB full orbit list
- Full MPC observation history (all years)
- JPL SBDB orbits with uncertainty
- Find_Orb
- kete (NASA/IPAC position engine) set up to predict positions as seen from SPHEREx
- JPL Horizons with SPHEREx as the observer, as a cross-check
- How to compute "path before vs after"

**A3 SPHEREx core** -> data/03-spherex
- Every release: QR2 (downloadable until Feb 2027), QR3, DR1, deep fields
- Frame metadata
- Direct pixel reads from the AWS copy
- Explanatory Supplement and flags
- Per-pixel wavelength calibration
- Anomaly list and ePSF
- Spacecraft position keywords
- The pipeline's per-frame known-asteroid files, if public
- All-sky 102-channel cube tiles for our areas

**A4 Other old photos** -> data/04-other-archives
- WISE/NEOWISE single exposures and catalogs (2010-2024)
- CATCH multi-survey search: Catalina, Spacewatch, NEAT, LONEOS, Pan-STARRS, ZTF and others
- TESS full-frame images
- Spitzer archive
- DECam deep images (NOIRLab)
- Euclid (partner) where it covers targets

**A5 Challenge test targets** -> data/05-test-targets
- Barnard's Star, WISE 0855, Epsilon Indi B, RW Aurigae, R Draconis
- For each: SPHEREx, WISE/NEOWISE, 2MASS and DSS plates
- For each: Gaia/CatWISE motion and variability references
- For each, optional: Harvard DASCH plates (1885-1992)

**A6 What it's made of** -> data/06-composition
- SMASS, MITHNEOS, Bus-DeMeo
- RELAB lab spectra (rocks, ices)
- NEOWISE sizes and albedos
- LCDB and ALCDEF spin data
- SPHEREx comet catalog (68 comets) and 3I/ATLAS products
- Gaia DR3 asteroid spectra and SsODNet (partner)
- Solar spectrum

**A7 Answer keys and junk** -> data/07-answer-keys
- kete-computed known-asteroid positions for every SPHEREx frame we use
- Pipeline known-asteroid files, if public
- NASA Ames labeled trail catalog
- SPHEREx anomaly list and flags
- CelesTrak satellite and debris catalog
- SkyBoT (partner) as a fallback

**A8 AI training data** -> data/08-ai-training
- SPHEREx ecliptic-pole deep fields: many repeat photos of the same patches for training Expected Sky
- Fake-object injection kit using the real ePSF and wavelength maps
- NEOWISE practice cases: past discoveries with known pre-discovery answers, for honest numbers
- Train / validation / test splits frozen and kept separate

**A9 People layer** -> data/09-people
- Discovery stories: who, where, when (MPEC credits)
- Asteroid name meanings (MPC citations)
- NASA public-domain media (no logos)
- Close-approach facts in plain words

## Phase B - download and measure (after A)

- **B1:** pixels and cutouts for all ranked targets plus controls, from SPHEREx first, then NEOWISE and the other archives
- **B2:** measurement: forced photometry, stacking, search over the uncertainty area, controls (shifted fake paths, shuffled dates, known-asteroid recovery), results table found / not found / too faint
- **B3:** lost-asteroid recovery attempts, same method
- **B4:** build the frozen AI training set

## Phase C - package

**C1** README for Dovlet, docs/SOURCES.md, re-download scripts, file checks, results summary.

## Practical limits

- Disk: 77 GB free on this Mac, so cap local data at about 50 GB. Use an external drive or cloud if more is needed.
- Full SPHEREx is hundreds of TB, so we collect every photo that touches our targets plus the pole training fields, not everything.
- Time: pilot about 15 min, Phase A about 1.5-2.5 h, Phase B about 1.5-2 h, Phase C about 20 min.
- Deadline: Sun Nov 15, 9:59 PM Arizona.
