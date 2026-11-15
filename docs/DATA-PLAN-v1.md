# Rewind - data collection plan (draft, not started)

Goal: collect all data Rewind will really use. When a new asteroid or comet is discovered, find it in older infrared photos (SPHEREx 2025-now, plus NEOWISE/WISE 2010-2024) to sharpen its future path, show what it is made of, and let people help check.

Rules for every agent:
- public data only, read-only, no posting or submitting anywhere (including the MPC)
- no Chinese sources
- no logins
- partner (non-US) data only when it adds clear value, with the reason written down
- every file listed in docs/SOURCES.md with link, credit, license, US or partner
- every number labeled MEASURED, COMPUTED or ESTIMATED
- everything saved inside this folder

## Phase A - gather (7 agents in parallel)

**A1 New objects and risk** -> data/01-new-objects-and-risk
- MPC NEO Confirmation Page snapshot (brand-new unconfirmed objects)
- New designations and MPECs since May 2025 (NEOs, comets)
- JPL Scout (short-arc orbits, impact estimates)
- JPL Sentry risk list
- CNEOS close approaches
- Candidate list ranked by Rewind potential (brightness, discovery date, survey)

**A2 Orbits and full observation history** -> data/02-orbits-and-observations
- For every candidate: current orbit with uncertainty (JPL SBDB/Horizons)
- Full MPC observation history (all years)
- First ground sighting vs credited discovery
- ZTF archive check for earlier sightings
- Orbit-fitting software notes (Find_Orb, JPL tools)
- How to compute "path before vs after"

**A3 SPHEREx core** -> data/03-spherex-core
- Pre-discovery SPHEREx frame lists per candidate (IRSA MOST)
- Frame metadata (time, detector, release DR1/QR3)
- Explanatory Supplement and archive guide
- Flag definitions
- Spectral WCS / per-pixel wavelength calibration
- Anomaly (bad-photo) list
- ePSF (blur shape) notes
- Spacecraft-position keywords
- All-sky 102-channel cube tiles only for our areas
- Tutorial notebooks

**A4 Challenge test targets** -> data/04-test-targets
- Barnard's Star, WISE 0855, Epsilon Indi B, RW Aurigae, R Draconis
- For each: SPHEREx frame lists
- For each: WISE/NEOWISE and 2MASS frame lists for long-term motion
- For each: known motion (CatWISE; Gaia as partner)
- For each: variability references

**A5 What it's made of** -> data/05-composition-library
- SMASS, MITHNEOS, Bus-DeMeo reference spectra
- Lab spectra of rocks and ices (RELAB or similar US sources)
- NEOWISE sizes and albedos
- SPHEREx 3I/ATLAS comet products
- Gaia DR3 asteroid reflectance spectra (partner, if useful)
- Solar spectrum for reflectance
- SOLO public-data check

**A6 Answer keys and junk** -> data/06-answer-keys-and-junk
- Known asteroids inside sample SPHEREx frames (JPL; SkyBoT partner fallback)
- NASA Ames labeled SPHEREx satellite-trail catalog (Zenodo)
- Star catalogs near candidate paths (2MASS, CatWISE; Gaia if needed)
- CelesTrak public satellite list (all satellites, for trail tagging)

**A7 Older infrared rewind** -> data/07-older-infrared
- NEOWISE/WISE frame lists for every candidate (2010-2024)
- Practice cases: past discoveries (2014-2025) with known pre-discovery NEOWISE/ground sightings, for honest numbers
- NEOSSat archive check for top candidates (partner, check only)

## Phase B - download and measure (after A)

**B1 Photo cutouts** -> data/cutouts
- SPHEREx and NEOWISE cutouts at predicted spots for the top ~10 candidates and the 5 test targets
- Control cutouts: empty spots and known asteroids
- Cap about 3 GB

**B2 The measurement** -> data/results
- Forced photometry plus stacking at predicted spots
- Search over the uncertainty area
- Controls: shifted fake paths, shuffled dates, known-asteroid recovery
- Rewind images
- Results table: found / not found / too faint, with signal strength

## Phase C - package (after B)

**C1** README for Dovlet, docs/SOURCES.md (every file, link, credit, license, US or partner), re-download scripts, file checks, short results summary.

## Size, time, decision

- Size: Phase A a few hundred MB, Phase B up to about 3 GB. Disk has 77 GB free.
- Time: Phase A about 60-75 min, Phase B about 45-60 min, Phase C about 15 min.
- Decision: if B2 finds real objects in old photos, build Rewind. If not, keep the data and decide together.
