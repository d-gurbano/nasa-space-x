# Planet X and SPHEREx: Hackathon Resources Report

NASA Space Apps Challenge 2026, challenge page: https://www.spaceappschallenge.org/2026/challenges/planet-x-and-spherex/

I tested every resource live: real queries, real data downloads, notebook source code, and real SPHEREx images of WISE 0855.

**Bottom line:** everything needed to build the tool is available right now. The most useful pieces are the **SIA2 image search**, the **cutout service** and the **AWS S3 bucket**. The S3 bucket is the only SPHEREx source a browser can read directly. IRSA's TAP service and the Data Explorer were failing during testing, so plan around SIA2.

## The goal (from the Details tab)

Build a public web tool where a user enters RA/Dec and sees SPHEREx images of that patch played as a short video, so moving objects stand out.

- **Test targets:** Barnard's Star, Epsilon Indi B, WISE 0855 (RA 08h55m10.831s, Dec -7d14m42.53s), RW Aurigae, R Draconis.
- **Optional ideas from the challenge:**
  - Make the tool easy to update with new data releases.
  - Use the 102 bands creatively, for example by stacking each of the 6 detectors.
  - Generate spectra on the fly.
  - Add or subtract images taken at different times.
  - Let users choose the field of view.
  - Overlay Gaia or WISE data.
  - Accept coordinates in the URL.
  - Show contamination flags.
  - Use tools like Astropy and Aladin (CDS).

---

## What works today

| Resource | Works? | Browser can call it directly (CORS)? | Notes |
|---|---|---|---|
| SIA2 image search | Yes, with occasional 502 errors | No | Main search API; retries usually succeed |
| Cutout service | Yes, about 3 s per cutout | No | Each cutout is about 4 MB (see below) |
| AWS S3 bucket `nasa-irsa-spherex` | Yes | **Yes**, and byte-range reads work | Only SPHEREx source a browser can read directly |
| HiPS all-sky cube (102 wavelength layers) | Yes | **Yes** | Ready-made background map for Aladin |
| TAP (SQL queries) | **Failing** (timeouts and 502s) | No | Same backend as the Data Explorer |
| SPHEREx Data Explorer (web UI) | **Search fails** ("Table Error") | n/a | Broken because TAP is down |
| MOST (asteroid lookup) | Yes | n/a | Eros: 745 SPHEREx images found |
| IRSA WISE catalogs (AllWISE, CatWISE2020) | Yes | No | CatWISE includes proper motions |
| Gaia DR3 via ESA's archive | Yes, about 3 s | No | |
| WiseView's backend | Yes | **Yes** | Undocumented, could break |
| CDS services (VizieR, Aladin site, alasky) | **Mostly down today** | | Aladin Lite itself loads fine from npm/jsDelivr |
| NEOSSat files, CADC, tutorial repo | Yes | | |

---

## 1. NASA/IPAC Infrared Science Archive (IRSA): SPHEREx

Link: https://irsa.ipac.caltech.edu/Missions/spherex.html

### 1.1 The data itself

- **Images:** every pointing produces 6 FITS files, one per detector. Each is about 65 MB, 2040x2040 pixels at **6.15 arcsec per pixel**, with a PSF width of about 9 arcsec.
- **Wavelength:** wavelength changes across each detector. So one sky position is seen at a different wavelength in every exposure, and frames in a time series are at slightly different wavelengths.

| Detector | Wavelength (µm) | Resolution (R) |
|---|---|---|
| D1 | 0.75 to 1.09 | 39 |
| D2 | 1.10 to 1.62 | 41 |
| D3 | 1.63 to 2.41 | 41 |
| D4 | 2.42 to 3.82 | 35 |
| D5 | 3.83 to 4.41 | 112 |
| D6 | 4.42 to 5.00 | 128 |

- **What's inside each file:**
  1. IMAGE (MJy/sr, zodiacal light not subtracted)
  2. FLAGS (bitmask)
  3. VARIANCE
  4. ZODI (zodiacal light model)
  5. EPSF (PSF models)
  6. WCS-WAVE (pixel-to-wavelength table)
- **Useful per-image quality values:** `L2DQAFLG` (pass/fail), `PSF_FWHM`, `SATSTRKS` (satellite streaks), `AURORA_CONT`, `SHUTTLE_GLOW_CONT`, and counts of flagged pixels.
- **Current data sets:** DR1 plus QR3 are the current processed set. Both are on S3 (DR1: 110 planning-period folders, QR3: 41). QR2 is outdated and no longer searchable.
- **File names:** `level2_[ObsID]D[Detector]_spx_l2b-v[Version]-[ProcDate].fits`

### 1.2 SIA2 image search (tested)

- **How it works:** `https://irsa.ipac.caltech.edu/SIA?COLLECTION=<name>&POS=circle+RA+DEC+R&RESPONSEFORMAT=CSV`
- **Collections (all tested):**
  - `spherex_dr1`
  - `spherex_dr1_deep`
  - `spherex_qr3`
  - `spherex_qr3_deep`
  - `spherex_dr1_cube` (the all-sky cube)
- **What each result row gives you:**
  - `access_url`: direct FITS link
  - `cloud_access`: S3 bucket and key
  - `t_min` / `t_max`: MJD timestamps
  - `energy_bandpassname`: detector, e.g. SPHEREx-D6
  - `em_min` / `em_max`: wavelength range
  - `s_region`: image footprint polygon

  That's everything needed to build a time series.
- DR1 returned 502 errors on several attempts before succeeding, so the tool needs automatic retries.

Example:

```
https://irsa.ipac.caltech.edu/SIA?COLLECTION=spherex_dr1&POS=circle+269.452075+4.693391+0.01&RESPONSEFORMAT=CSV
```

### 1.3 Cutout service (tested)

- **How it works:** add `?center=RA,DEC&size=DEG` (or a size in pixels, e.g. `?center=570,900pix&size=100pix`) to any image URL.
- **Problem:** every cutout carries the full 3.9 MB PSF table, so even a 12x12-pixel cutout is about 4 MB. 100 frames would be about 400 MB, so this needs a server that strips it out.

| Cutout size | Pixels | File size | Time |
|---|---|---|---|
| 0.02° | 12x12 | 3.95 MB | about 3.2 s |
| 0.10° | 58x59 | 4.0 MB | about 3.1 s |
| 0.25° | 146x146 | 4.3 MB | about 3.4 s |

- **Orientation:** cutouts keep the detector's orientation, not north-up. Orientation flips 180° between visits (confirmed on real WISE 0855 frames), and the images include SIP distortion. Frames must be rotated or reprojected before blinking.
- Docs: https://irsa.ipac.caltech.edu/data/SPHEREx/docs/cutout_tool.html and https://irsa.ipac.caltech.edu/ibe/cutouts.html

Example:

```
https://irsa.ipac.caltech.edu/ibe/data/spherex/dr1/level2/<period>/<version>/<det>/<file>.fits?center=133.795129,-7.245147&size=0.06
```

### 1.4 AWS S3 bucket `nasa-irsa-spherex` (tested)

- It's public and needs no login.
- **Top-level folders:** `dr1/` and `qr3/` (QR2 is obsolete). Each holds `level2/` plus every calibration product:
  - `abs_gain_matrix`, `aurora_template`, `dark`, `dichroic`, `epsf`, `gain_factors`
  - `he_template`, `l3_flux_corrections`, `nonfunc_v2`, `nonlinear_pars`, `readnoise_pars`
  - `shuttle_glow_template`, `sip`, `solid_angle_pixel_map`, `spectral_channels`, `spectral_wcs`
  - `xtalk_class1`, `xtalk_class2`, `zodi_scaling_v2`
  - DR1 also has `hips5_cube/`
- It returns `Access-Control-Allow-Origin: *` and supports byte-range reads. **A browser app can read just the pixel rows it needs from the full FITS files with no backend.**
- URL pattern: `https://nasa-irsa-spherex.s3.us-east-1.amazonaws.com/<key from cloud_access>`

### 1.5 TAP (SQL queries)

- **Endpoint:** `https://irsa.ipac.caltech.edu/TAP`. Tables: `spherex.obscore`, `spherex.observation`, `spherex.plane`, `spherex.artifact`, `spherex.provenance_input`.
- TAP gets new data about a day earlier than SIA2.
- **It was down in all my attempts.** One schema listing did get through, which confirmed those five tables.
- The cutouts notebook has a ready-made query that returns cutout URLs sorted by time:

```sql
SELECT
  'https://irsa.ipac.caltech.edu/' || a.uri || '?center={ra},{dec}d&size={size}' AS uri,
  p.time_bounds_lower
FROM spherex.artifact a
JOIN spherex.plane p ON a.planeid = p.planeid
WHERE 1 = CONTAINS(POINT('ICRS', {ra}, {dec}), p.poly)
  AND p.energy_bandpassname = 'SPHEREx-D2'
ORDER BY p.time_bounds_lower
```

### 1.6 HiPS all-sky cube (tested)

- **URL:** `https://irsa.ipac.caltech.edu/data/hips/SPHEREx/spherex_allsky_cube`
- **Format:**
  - HiPS v1.4, equatorial, order 5, 512-pixel PNG tiles.
  - 102 wavelength layers, 0.753 to 4.988 µm. Layer = 17×(band−1)+(channel−1); layers 50 and 51 are blank.
  - Tile URLs follow `Norder3/Dir0/Npix100_40.png`. An `Allsky_<layer>.png` overview and `Moc.fits` exist too.
  - CORS is allowed from any origin.
- **FITS cubes:** under `dr1/hips5_cube/hips_20261026/` on S3 and IRSA, 12,288 tiles of about 1.8°×1.8°.
- **Limit:** it's a stack of all DR1 data with no time information. Good as a static background in Aladin and for wavelength browsing, not for motion.

### 1.7 Web tools (opened in a browser)

Link: https://irsa.ipac.caltech.edu/applications/spherex

- **Spectral Image Search:** search by position, time range, and band or wavelength. The search was failing because TAP is down.
- **Spectrophotometry Tool:** gives a spectrum for a source.
  - Point-source or galaxy (Sersic) model.
  - Band filters and **a time range**.
  - Jobs take minutes, or hours with deep-field data.
  - This is the main route to "spectra on the fly", but as a batch job.
- **Mosaic Tool:** builds custom image stacks.
  - Size 0.1 to 300 arcmin, rotation, 6.15″ per pixel or coarser, wavelength range.
  - **It has no time filter**, so it can't make per-epoch frames.
- **Cutout Tool:** cutouts via the Data Explorer, a direct URL or Python (all covered above).
- **Source Discovery Tool:** a notebook plus Python package (covered in section 2).

### 1.8 MOST, Moving Object Search Tool (tested)

- **Link:** https://irsa.ipac.caltech.edu/applications/MOST
- **API:** `https://irsa.ipac.caltech.edu/cgi-bin/MOST/nph-most?catalog=spherex&input_type=name_input&obj_name=Eros&obs_begin=2025-08-01&obs_end=2026-06-30&output_mode=Brief`
- I asked for asteroid Eros and got 745 SPHEREx images, each with the predicted RA/Dec, distances, magnitude and image URL.
- Plain names can be ambiguous ("Ceres" failed), so use `Name:AST` or a NAIF ID.
- It's useful for an "asteroid mode": known objects can be marked on the frames.

### 1.9 Other IRSA items

- **Catalog search (Gator):**
  - AllWISE: `catalog=allwise_p3as_psd` (tested)
  - CatWISE2020: `catalog=catwise_2020` (tested). It has proper motions, which is good for a WISE overlay.
  - Example: `https://irsa.ipac.caltech.edu/cgi-bin/Gator/nph-query?catalog=catwise_2020&spatial=cone&objstr=133.795129+-7.245147&radius=30&outfmt=1`
- **SPLICES:** about 9 million infrared-bright point sources likely to show ice absorption. Catalog search or a 3.1 GB FITS download.
- **Comet 3I/ATLAS:** a table of every observation with the predicted comet position, plus wget/curl download scripts. It's a ready-made moving-object test case.
- **Spectral calibrations:** a tar file with channel maps and transmission curves at 17, 34, 51 or 68 sub-channels per detector.
- **Archive User Guide:** https://caltech-ipac.github.io/spherex-archive-documentation/ (file naming, directory layout, API details).
- **Video tutorials:** IRSA YouTube channel, SPHEREx playlist ("IRSA Tutorial 13xx").

### 1.10 Explanatory Supplement (84-page PDF, downloaded and read)

Link: https://irsa.ipac.caltech.edu/data/SPHEREx/docs/SPHEREx_Expsupp.pdf

**Pixel flags (Table 16), for a contamination overlay:**

| Bit | Flag | Bit | Flag |
|---|---|---|---|
| 0 | TRANSIENT | 17 | PERSIST |
| 1 | OVERFLOW | 19 | OUTLIER |
| 2 | SUR_ERROR | 20 | CROSSTALK |
| 6 | NONFUNC | 21 | SOURCE |
| 7 | DICHROIC | 22 | GHOST |
| 9 | MISSING_DATA | 23 | GHOST_FPA |
| 10 | HOT | 24 | GHOST_EXT |
| 11 | COLD | 25 | STREAK |
| 12 | FULLSAMPLE | 26 | BLOOM |
| 14 | PHANMISS | 27 | SNOWBALL |
| 15 | NONLINEAR | 28 | HALO |
| | | 29 | SATELLITE_HALO |

**Flags the official mosaics reject (use the same list):** TRANSIENT, SUR_ERROR, NONFUNC, DICHROIC, MISSING_DATA, HOT, COLD, PHANMISS, NONLINEAR, PERSIST, CROSSTALK, GHOST, GHOST_FPA, GHOST_EXT, STREAK, BLOOM, SNOWBALL, HALO, SATELLITE_HALO.

**Other useful sections:**
- Section 1.4: survey strategy. Full sky twice a year; spacecraft rotation alternates 0°/180°.
- Section 2.3: image artifacts (ghosts, satellite streaks, aurora, shuttle glow).
- Section 2.4: known limitations.
- Section 2.5: the all-sky cubes.
- Section 3.4: the mosaic algorithm.
- List of known bad images: https://spherex.caltech.edu/page/anomalyimages

---

## 2. SPHEREx tutorial notebooks

Links: https://caltech-ipac.github.io/irsa-tutorials/spherex/ (source: https://github.com/Caltech-IPAC/irsa-tutorials, `tutorials/spherex/`)

| Notebook | What it shows | Relevance |
|---|---|---|
| **Intro** | SIA2 search with astroquery, reading the file contents, the pixel-to-wavelength conversion (with distortion turned off), flags, variance, zodiacal light and PSF | Core "how to read a file" reference |
| **Cutouts** | The TAP query, then **parallel** cutout downloads with retries, merged into one file sorted by time | **Closest to the challenge**: basically a time series of frames |
| **PSF** | Picking the right PSF for a position; S3 links for the PSF files | Needed if you do photometry |
| **Source Discovery Tool** | Read from S3 (`cloud_access`), subtract a local background, align two detectors (D2/D4), subtract them, find sources (SExtractor/`sep`), interactive bokeh/Firefly views, then photometry | Ready-made difference-image pipeline; includes a full Python package and conda file |
| **Mosaic Cube** | Quick spectrum from a cube, emission-line map, side-by-side with GALEX | Spectrum display ideas |
| **HiPS Cube** | Properties, layer-to-wavelength table, Firefly view, FITS tile download, quick spectrum from one tile | Fastest "spectrum at a point" with no job queue |

**Libraries used:** astropy, astroquery, pyvo, numpy, matplotlib, photutils, reproject, firefly_client, sep, bokeh, hpgeom.

---

## 3. WiseView (model and inspiration)

Link: http://byw.tools/wiseview

**Features to copy:**
- Choice of W1, W2 or W1+W2 colour
- Field-of-view and zoom controls, blink speed
- Sliding time window and difference imaging
- Shift-and-add along an assumed motion
- Separate scan directions and skip-epoch options
- Brightness/stretch/invert controls
- Gaia overlay, synthetic test objects
- Coordinates and settings saved in the URL
- One-click links to Legacy Survey, SIMBAD, VizieR and Zooniverse

**How it's built** (from its JavaScript, `static/flash3.js`):
1. The browser calls an AWS Lambda (`png-animation`) with RA/Dec/size/settings.
2. The Lambda renders PNG frames into a public S3 bucket and returns JSON with the frame list, dates and image coordinates.
3. The browser just preloads the PNGs and blinks them.
4. The Gaia overlay asks for Gaia DR3 and **moves each star from its 2015.5 position to each frame's date using proper motion**.

**The backend is live** and allows CORS from any origin; it returned real unWISE frames for WISE 0855. You could use it for a WISE overlay, but it's undocumented and could break.

---

## 4. Gaia DR3

Link: https://archive.stsci.edu/missions-and-data/gaia

- The MAST page links to ESA's Gaia archive (https://gea.esac.esa.int/archive/), MAST Portal, astroquery, CasJobs and VO services.
- **Tested:** ESA's Gaia TAP at `https://gea.esac.esa.int/tap-server/tap/sync` returned Barnard's Star with pmDec 10,362 mas/yr and parallax 547 mas (G=8.19) in about 3 seconds. There's no CORS, so call it through your own server.
- **Scale:** Barnard's Star moves about 10″ per year, roughly **1.7 SPHEREx pixels per year**. That's visible over the roughly one-year span of SPHEREx data, but only by a few pixels, so good alignment matters.
- The MAST catalogs API path I tried returned 404. VizieR was down during testing.

Example query:

```sql
SELECT source_id, ra, dec, pmra, pmdec, parallax, phot_g_mean_mag
FROM gaiadr3.gaia_source
WHERE 1=CONTAINS(POINT('ICRS',ra,dec), CIRCLE('ICRS',269.448,4.74,0.02))
```

---

## 5. NEOSSat (Canadian Space Agency)

- **Mission page** (https://www.asc-csa.gc.ca/eng/satellites/neossat/): a 15 cm telescope with a 0.85° field at 3″ per pixel. It can track moving targets and is aimed at asteroids, satellites and exoplanet transits.
- **CADC** (https://www.cadc-ccda.hia-iha.nrc-cnrc.gc.ca/en/neossat/):
  - The NEOSSat collection has **773,583 observations** (counted via CADC's TAP).
  - Processing levels: RAW, CLEAN, COR, and CORD (dark-subtracted, the best one).
  - It also hosts SSOIS for solar-system lookups; my API call to it returned 404.
- **CSA open data directory** (https://data.asc-csa.gc.ca/users/OpenData_DonneesOuvertes/pub/NEOSSAT/):
  - `ASTRO/2017` through `2026`: one folder per day; the newest has about 180 files of about 2 MB each.
  - `C2020-F3/`: 215 cleaned frames of Comet NEOWISE.
  - `Ephemeris/`
  - Space Apps workshop slides from 2019 and 2020.
  - Supporting documents, including the FITS user guide PDF.
- **Tutorial repo** (https://github.com/asc-csa/NEOSSAT_Tutorial):
  - Notebook 01: download by date from the CSA site or by position from CADC, then display.
  - Notebook 02: dark subtraction and stacking, **streak detection** (LSD, Hough), and **moving-object detection** with frame differencing and OpenCV optical flow.
  - Uses OpenCV, scikit-image and pylsd. Bilingual, MIT-style license.
- **Relevance:** optional extra data for asteroids, and the detection algorithms carry over to SPHEREx.

---

## 6. Coverage of the 5 test targets (live SIA2 counts)

| Target | Coordinates used (deg) | DR1 | QR3 | Deep fields | Separate visits |
|---|---|---|---|---|---|
| Barnard's Star | 269.452075, +4.693391 | 240 | 123 | 0 | 7 |
| Eps Indi B | 331.0438, -56.7828 | 345 | 120 | 0 | 7 |
| WISE 0855 | 133.795129, -7.245147 | 258 | 0 | 0 | 4 |
| RW Aur | 76.95642, +30.40144 | 226 | 109 | 0 | 6 |
| R Dra | 248.1675, +66.7551 | 413 | 126 | **1,954** (deep field) | 18+ |

Every target has all 6 detectors and several separate visits about 6 months apart, so there's enough for a blink sequence.

---

## 7. End-to-end test: WISE 0855 from real SPHEREx data

I ran the search, pulled 4 D6 (4.4 to 5.0 µm) cutouts from different visits, read the pixels, rotated the flipped frames, and drew them:

![WISE 0855 SPHEREx frames](wise0855_spherex_frames.png)

What this showed:
- The full path from search to cutout to pixels to display works today.
- Single exposures are **noisy**, so stacking each visit (as the challenge suggests) is essential.
- The 180° flip between visits is real. After rotating, the static stars line up.
- WISE 0855 moves about 8″ per year, so it has drifted away from the coordinate the challenge gives. The tool should move catalog markers to each frame's date using proper motion, as WiseView does.

---

## 8. Useful things not on the Resources list

- **Aladin Lite v3:** the challenge suggests it. CDS's own site was down during testing, but npm `aladin-lite` (3.9.2-beta) and `https://cdn.jsdelivr.net/npm/aladin-lite@3/dist/aladin.js` both work.
- **CDS SPHEREx HiPS:** CDS lists SPHEREx QR2 HiPS maps (`CDS/P/SPHEREx/QR2/D1` to `D6`, plus `color`) in its registry, but their tiles weren't loading during testing.
- **IRSA catalogs:** CatWISE2020 and AllWISE overlays via IRSA Gator (tested).
- **unWISE images:** the time-resolved WISE coadds behind WiseView (via its backend or unwise.me).
- **CDS Sesame name resolver:** `https://cds.unistra.fr/cgi-bin/nph-sesame/-oI/SNV?RW%20Aur` works and allows CORS from any origin, but was very slow (about 95 s) during testing.

---

## 9. Limitations to design around

1. **CORS:** only the S3 bucket, the HiPS cube and WiseView's backend can be called directly from a browser. SIA2, the cutout service, TAP and Gaia all need a small proxy server.
2. **Cutout size:** 4 MB each, so you need a server to trim them, or read pixel rows straight from S3.
3. **Orientation:** frames are detector-oriented, flip 180° between visits and have distortion, so they must be reprojected to a common north-up grid.
4. **Wavelength:** wavelength varies across each detector, so frames of one spot in one detector aren't at exactly the same wavelength. Stack per detector, or match by wavelength.
5. **Noise:** single exposures are noisy; stack per visit and per detector.
6. **Moving targets:** fast movers like WISE 0855 drift away from old catalog coordinates. Move overlay positions to each frame's date using proper motion.
7. **IRSA reliability:** 502 errors and timeouts were common during testing. Add retries, caching and a fallback from TAP to SIA2.

---

## 10. Quick reference: endpoints

| Purpose | Endpoint |
|---|---|
| SPHEREx image search | `https://irsa.ipac.caltech.edu/SIA?COLLECTION=spherex_dr1&POS=circle+RA+DEC+R&RESPONSEFORMAT=CSV` |
| SPHEREx cutout | `<access_url>?center=RA,DEC&size=DEG` |
| SPHEREx S3 (browser-friendly) | `https://nasa-irsa-spherex.s3.us-east-1.amazonaws.com/<key>` |
| SPHEREx TAP | `https://irsa.ipac.caltech.edu/TAP/sync?LANG=ADQL&FORMAT=csv&QUERY=...` |
| SPHEREx HiPS cube | `https://irsa.ipac.caltech.edu/data/hips/SPHEREx/spherex_allsky_cube` |
| Asteroids / comets (MOST) | `https://irsa.ipac.caltech.edu/cgi-bin/MOST/nph-most?catalog=spherex&...` |
| WISE catalogs | `https://irsa.ipac.caltech.edu/cgi-bin/Gator/nph-query?catalog=catwise_2020&...` |
| Gaia DR3 | `https://gea.esac.esa.int/tap-server/tap/sync` |
| Aladin Lite | `https://cdn.jsdelivr.net/npm/aladin-lite@3/dist/aladin.js` |
| NEOSSat files | `https://data.asc-csa.gc.ca/users/OpenData_DonneesOuvertes/pub/NEOSSAT/` |
| NEOSSat (CADC) | `https://www.cadc-ccda.hia-iha.nrc-cnrc.gc.ca/en/neossat/` |

**Required acknowledgement for SPHEREx data:** "This publication makes use of data products from the Spectro-Photometer for the History of the Universe, Epoch of Reionization and Ices Explorer (SPHEREx), which is a joint project of the Jet Propulsion Laboratory and the California Institute of Technology, and is funded by the National Aeronautics and Space Administration." DOIs: DR1 images 10.26131/IRSA678, all-sky cube 10.26131/IRSA679, QR3 10.26131/IRSA662.
