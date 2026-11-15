"""
fake_mover_filter.py - find things that change in SPHEREx images, and throw
out the ones that are camera artifacts instead of real objects on the sky.

Scope: objects that change or move WITHIN one SPHEREx visit (minutes to days),
such as asteroids and comets. Slow brown dwarfs like WISE 0855 barely move in
one visit, so they end up in the "fixed sky" template; for those use the
motion-following stack in spherex_try.py.

The key fact this filter uses
-----------------------------
SPHEREx photographs a spot in "bursts": 3 or more exposures about 2 minutes
apart. Between those exposures the telescope steps, so the same spot on the sky
lands about 118 pixels further along the detector chip each time. Therefore:
  * anything stuck to the CHIP (after-images, hot pixels, crosstalk, internal
    ghosts) lands somewhere different on the SKY in every exposure;
  * anything REAL stays put on the sky, or drifts steadily if it moves.
A spot that shows up at a consistent sky position in 3+ exposures is real.

How it works (plain language)
-----------------------------
  1. Download every image of the field in one detector (cached).
  2. Throw out whole images NASA marks as bad:
       QA_FAIL (header pass/fail), ASTROMETRY (pointing fit failed),
       ANOMALY_LIST (NASA's list of known-bad images), MISALIGNED (fixed stars
       do not line up after alignment).
  3. Mask bad pixels with NASA's flag list, align every image north-up.
  4. Build a "fixed sky" template (median of all images) and subtract it.
  5. Test each leftover spot against known fake causes:
       ON_STATIC_STAR  on a fixed star: brightness/colour change, not motion
                       (each SPHEREx frame sees a different infrared colour)
       NEAR_MASKED     touches pixels NASA flagged as bad
       TOO_SHARP       one-pixel spike: a cosmic-ray hit
       STREAK          long and thin: satellite trail or cosmic-ray track
       CROSSTALK       32 rows / 64*n columns from a bright star on the chip
  6. Group the clean spots by sky position within each burst, then:
       FEW_FRAMES      seen in fewer than 3 exposures (chip-stuck artifacts end
                       up here because they jump around on the sky)
       CANDIDATE       real and MOVING: drifts steadily within a burst, or is
                       linked across bursts on a straight line at steady speed
       STILL_SOURCE    real spot on the sky in 3+ exposures but no motion seen
                       here (a slow mover or a flash: check other visits)
  7. Look up moving candidates in SkyBoT (known asteroids and comets):
       KNOWN_OBJECT    a catalogued asteroid or comet (real, but not new)

Proof it works: --inject plants test objects (two realistic movers plus one of
each artifact type) into the real images and reports what was caught.

Usage:
  .venv/bin/python fake_mover_filter.py --target wise0855
  .venv/bin/python fake_mover_filter.py --target wise0855 --inject
  .venv/bin/python fake_mover_filter.py --ra 180 --dec 0 --detector 1
"""

import argparse
import csv
import itertools
import warnings
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import requests
from astropy.io import fits
from astropy.wcs import WCS
from reproject import reproject_interp
from scipy import ndimage
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

import spherex_try as base  # search, download, grids, target list, flag list

ANOMALY_URL = ("https://spherex.caltech.edu/system/media_files/binaries/68/original/"
               "SPHEREX_exposure_anomaly_log_20250810.csv")
SKYBOT_URL = "https://ssp.imcce.fr/webservices/skybot/api/conesearch.php"
OVERFLOW_BIT, NONLINEAR_BIT = 1 << 1, 1 << 15

# Thresholds (1 pixel = 6.15 arcsec)
DETECT_SNR = 6.0         # leftover spot must be this strong to be considered
STAR_SNR = 6.0           # fixed stars in the template
ON_STAR_RADIUS = 2.0     # px: spot this close to a fixed star = brightness change
SHARP_LIMIT = 0.85       # fraction of a spot's light in its brightest pixel
                         # (real stars measured up to ~0.8 on this undersampled PSF)
STREAK_RATIO = 2.5       # long axis / short axis
MISALIGN_PX = 0.5        # fixed stars off by more than this = bad alignment
BURST_GAP_HR = 1.0       # exposures closer than this belong to one burst
SAME_SPOT_PX = 1.5       # spots this close in one burst = the same object
MIN_FRAMES = 3           # Backyard Worlds rule: real things show up 3+ times
DRIFT_MIN_PX = 0.4       # smallest in-burst drift we call motion...
DRIFT_SIGMAS = 4.0       # ...and it must be this many times the position error
POS_ERR_FLOOR = 0.10     # px: measured wobble of fixed stars between exposures
                         # in one burst (WISE 0855 field, D6: median 0.10-0.15 px)
LINK_TOL_PX = 1.5        # cross-burst track: max distance from the straight line
MAX_LINK_DAYS = 3.0      # only link bursts of the same visit; an asteroid leaves a
                         # 12' field within hours to days, so months-apart links are chance
MIN_MOTION_PX = 1.0      # cross-burst track must move at least this far
KNOWN_MATCH_ARCSEC = 20.0

REASON_TEXT = {
    "ON_STATIC_STAR": "on a fixed star: brightness/colour change, not motion",
    "NEAR_MASKED": "touches pixels NASA flagged as bad",
    "TOO_SHARP": "one-pixel spike (cosmic-ray hit)",
    "STREAK": "long and thin (satellite or cosmic-ray track)",
    "CROSSTALK": "electronic copy of a bright star (32/64-pixel offset)",
    "FEW_FRAMES": "seen in fewer than 3 exposures (chip artifacts land here)",
    "STILL_SOURCE": "real spot on the sky, but no motion seen in this visit",
    "KNOWN_OBJECT": "moving, and a catalogued asteroid or comet (SkyBoT)",
    "CANDIDATE": "moving like a real object, no known match",
}
FAKE = {"ON_STATIC_STAR", "NEAR_MASKED", "TOO_SHARP", "STREAK", "CROSSTALK", "FEW_FRAMES"}
REASON_COLOR = {
    "ON_STATIC_STAR": "#ffcc00", "NEAR_MASKED": "#8e8e93", "TOO_SHARP": "#ff9500",
    "STREAK": "#ff2d55", "CROSSTALK": "#af52de", "FEW_FRAMES": "#5ac8fa",
    "STILL_SOURCE": "#ffffff", "KNOWN_OBJECT": "#00c7be", "CANDIDATE": "#34c759",
}


# ---------------------------------------------------------------- utilities

def robust_sigma(a):
    a = a[np.isfinite(a)]
    return 1.4826 * np.median(np.abs(a - np.median(a))) if a.size else np.nan


def quiet_nanmedian(cube):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        return np.nanmedian(cube, axis=0)


def find_peaks(img, sigma, snr_min):
    """Spots whose 3x3 sum is snr_min times above the noise; returns (x, y, snr)."""
    filled = np.where(np.isfinite(img), img, 0.0)
    snr = ndimage.uniform_filter(filled, 3) * 9 / (3 * sigma)
    peaks = (snr == ndimage.maximum_filter(snr, size=5)) & (snr >= snr_min)
    ys, xs = np.nonzero(peaks)
    return [(float(x), float(y), float(snr[y, x])) for x, y in zip(xs, ys)]


def centroid(img, x, y, r=1.6):
    """Brightness-weighted center of the spot, to a fraction of a pixel."""
    yy, xx = np.indices(img.shape)
    w = np.where(np.isfinite(img), img, 0.0)
    m = (np.hypot(xx - x, yy - y) <= r) & (w > 0)
    if not m.any():
        return x, y
    return float((xx[m] * w[m]).sum() / w[m].sum()), float((yy[m] * w[m]).sum() / w[m].sum())


def elongation(img, x, y, sigma):
    """Long-axis / short-axis ratio of the spot (1 = round)."""
    xi, yi = int(round(x)), int(round(y))
    y0, x0 = max(yi - 3, 0), max(xi - 3, 0)
    patch = img[y0:yi + 4, x0:xi + 4]
    yy, xx = np.mgrid[y0:y0 + patch.shape[0], x0:x0 + patch.shape[1]]
    w = np.where(np.isfinite(patch) & (patch > 2 * sigma), patch, 0.0)
    if w.sum() <= 0 or (w > 0).sum() < 3:
        return 1.0
    mx, my = (xx * w).sum() / w.sum(), (yy * w).sum() / w.sum()
    c = [[((xx - mx) ** 2 * w).sum(), ((xx - mx) * (yy - my) * w).sum()],
         [((xx - mx) * (yy - my) * w).sum(), ((yy - my) ** 2 * w).sum()]]
    ev = np.linalg.eigvalsh(np.array(c) / w.sum())
    return float(np.sqrt(max(ev[1], 1e-6) / max(ev[0], 1e-6)))


def gaussian_stamp(shape, x, y, flux, sigma_px):
    yy, xx = np.indices(shape)
    g = np.exp(-((xx - x) ** 2 + (yy - y) ** 2) / (2 * sigma_px ** 2))
    return flux * g / (2 * np.pi * sigma_px ** 2)


def split_bursts(mjds):
    """Number the bursts: a new burst starts after a gap of BURST_GAP_HR."""
    order = np.argsort(mjds)
    ids, b = np.zeros(len(mjds), int), 0
    for k in range(1, len(order)):
        if (mjds[order[k]] - mjds[order[k - 1]]) * 24 > BURST_GAP_HR:
            b += 1
        ids[order[k]] = b
    return ids


# ---------------------------------------------------------------- loading

def load_anomaly_list():
    path = base.CACHE_DIR / "anomaly_log.csv"
    base.CACHE_DIR.mkdir(exist_ok=True)
    if not path.exists():
        try:
            path.write_bytes(base.get_with_retry(ANOMALY_URL).content)
        except RuntimeError:
            print("  Could not download NASA's anomaly list; skipping that check.")
            return {}
    with open(path) as fh:
        return {row["OBSID"]: row for row in csv.DictReader(fh)}


def load_frame(path, row, anomalies, detector):
    with fits.open(path) as hdul:
        hdr = hdul["IMAGE"].header
        zodi = hdul["ZODI"].data.astype(float) if "ZODI" in hdul else 0.0
        fr = dict(obsid=row["obs_id"], mjd=float(row["t_min"]),
                  raw=hdul["IMAGE"].data.astype(float) - zodi,
                  flags=hdul["FLAGS"].data.astype(np.int64), wcs=WCS(hdr),
                  wcs_chip=WCS(hdr, key="A"),  # cutout pixel -> pixel on the detector chip
                  psf_sigma=float(hdr.get("PSF_FWHM", 9.0)) / base.PIXEL_SCALE_ARCSEC / 2.355,
                  reasons=[])
    if str(hdr.get("L2DQAFLG", "Pass")).strip().lower() != "pass":
        fr["reasons"].append("QA_FAIL")
    if int(hdr.get("FINAST", 0)) != 0:
        fr["reasons"].append("ASTROMETRY")
    a = anomalies.get(fr["obsid"])
    if a is not None and str(a.get(f"BAND_{detector}_AFFECTED", "0")).strip() not in ("", "0"):
        fr["reasons"].append(f"ANOMALY_LIST ({a.get('ANOMALY_NAME', '?')})")
    fr["sigma_raw"] = robust_sigma(fr["raw"])
    return fr


# ---------------------------------------------------------------- test objects

def inject(frames, grid_wcs, n):
    """Plant realistic movers and one of each artifact type into the raw images.
    Returns the answer key."""
    good = sorted([f for f in frames if not f["reasons"]], key=lambda f: f["mjd"])
    bursts = split_bursts(np.array([f["mjd"] for f in good]))
    by_burst = {}
    for f, b in zip(good, bursts):
        by_burst.setdefault(int(b), []).append(f)
    ordered = [by_burst[b] for b in sorted(by_burst)]
    # two consecutive bursts with 3+ exposures each, less than 3 days apart
    pair = next(((a, b) for a, b in zip(ordered, ordered[1:])
                 if len(a) >= 3 and len(b) >= 3 and b[0]["mjd"] - a[-1]["mjd"] < 3), None)
    if pair is None:
        print("  No two nearby bursts with 3+ exposures: cannot run the injection test.")
        return []
    b1, b2 = pair[0][:4], pair[1][:4]

    def sky(px, py):
        return grid_wcs.pixel_to_world_values(px, py)

    def plant(f, ra, dec, flux, pixel=False):
        x, y = (float(v) for v in f["wcs"].world_to_pixel_values(ra, dec))
        h, w = f["raw"].shape
        if not (2 <= x < w - 2 and 2 <= y < h - 2):
            return False
        if pixel:
            f["raw"][int(round(y)), int(round(x))] += flux
        else:
            f["raw"] += gaussian_stamp(f["raw"].shape, x, y, flux, f["psf_sigma"])
        return True

    def flux_for(f, snr):  # total flux giving roughly this S/N in a 3x3 box
        return snr * 3 * f["sigma_raw"] / 0.8

    spots = [(0.25, 0.25), (0.75, 0.25), (0.25, 0.75), (0.75, 0.75), (0.5, 0.2), (0.2, 0.5),
             (0.8, 0.55)]
    pos = [(sx * (n - 1), sy * (n - 1)) for sx, sy in spots]
    truth = []

    # 1) FAST ASTEROID: 50"/hour (typical main-belt speed), seen in one burst only.
    v = 50 / base.PIXEL_SCALE_ARCSEC  # px per hour
    x0, y0 = pos[5]
    t0 = b1[0]["mjd"]
    path = [(x0 + v * 0.8 * (f["mjd"] - t0) * 24, y0 + v * 0.6 * (f["mjd"] - t0) * 24) for f in b1]
    hit = [f["obsid"] for f, (x, y) in zip(b1, path) if plant(f, *sky(x, y), flux_for(f, 20))]
    truth.append(dict(kind="FAST_ASTEROID", real=True, frames=hit, path=path))

    # 2) SLOW MOVER: drifts ~11 px between two bursts a day or so apart.
    x0, y0 = pos[0]
    span = (b2[-1]["mjd"] - t0) * 24
    vx, vy = 10.0 / span, 4.0 / span
    use = b1 + b2
    path = [(x0 + vx * (f["mjd"] - t0) * 24, y0 + vy * (f["mjd"] - t0) * 24) for f in use]
    hit = [f["obsid"] for f, (x, y) in zip(use, path) if plant(f, *sky(x, y), flux_for(f, 15))]
    truth.append(dict(kind="SLOW_MOVER", real=True, frames=hit, path=path))

    # 3) CHIP-STUCK GLITCH (after-image / hot pixel): the same pixel ON THE
    #    DETECTOR CHIP lights up in 3 exposures. The telescope steps ~116 chip
    #    pixels between exposures, so in our sky-centered cutouts it shows up in
    #    one exposure and lands outside the cutout (elsewhere on the sky) in the
    #    others, exactly as a real chip artifact does.
    x, y = pos[1]
    ra, dec = sky(x, y)
    xr, yr = (float(v) for v in b1[0]["wcs"].world_to_pixel_values(ra, dec))
    chip_x, chip_y = (float(v) for v in b1[0]["wcs_chip"].pixel_to_world_values(xr, yr))
    hit, path = [], []
    for f in b1[:3]:
        cx_, cy_ = (float(v) for v in f["wcs_chip"].world_to_pixel_values(chip_x, chip_y))
        h, w = f["raw"].shape
        if 2 <= cx_ < w - 2 and 2 <= cy_ < h - 2:
            f["raw"] += gaussian_stamp(f["raw"].shape, cx_, cy_, flux_for(f, 15), f["psf_sigma"])
            hit.append(f["obsid"])
            path.append(tuple(float(v) for v in grid_wcs.world_to_pixel_values(
                *f["wcs"].pixel_to_world_values(cx_, cy_))))
    truth.append(dict(kind="CHIP_STUCK_GLITCH", real=False, frames=hit, path=path))

    # 4) ONE-EXPOSURE FLASH (e.g. a persistence hit landing in our field once)
    f = b2[0]
    x, y = pos[2]
    plant(f, *sky(x, y), flux_for(f, 15))
    truth.append(dict(kind="ONE_EXPOSURE_FLASH", real=False, frames=[f["obsid"]], path=[(x, y)]))

    # 5) COSMIC RAY (single hot pixel)
    f = b2[1]
    x, y = pos[3]
    plant(f, *sky(x, y), 40 * f["sigma_raw"], pixel=True)
    truth.append(dict(kind="COSMIC_RAY", real=False, frames=[f["obsid"]], path=[(x, y)]))

    # 6) SATELLITE STREAK
    f = b2[2]
    x, y = pos[4]
    for k in np.linspace(-8, 8, 33):
        plant(f, *sky(x + k, y + 0.4 * k), flux_for(f, 4))
    truth.append(dict(kind="SATELLITE_STREAK", real=False, frames=[f["obsid"]], path=[(x, y)]))

    # 7) CROSSTALK copy 32 chip rows from the brightest star, in 3 exposures
    hit, path = [], []
    for f in b2[:3]:
        raw = np.where(np.isfinite(f["raw"]), f["raw"], -np.inf)
        by, bx = np.unravel_index(np.argmax(raw), raw.shape)
        for dy in (32, -32):
            if 2 <= by + dy < raw.shape[0] - 2:
                f["raw"] += gaussian_stamp(raw.shape, bx, by + dy, flux_for(f, 12), f["psf_sigma"])
                hit.append(f["obsid"])
                path.append(tuple(float(v) for v in grid_wcs.world_to_pixel_values(
                    *f["wcs"].pixel_to_world_values(bx, by + dy))))
                break
    if hit:
        truth.append(dict(kind="CROSSTALK_COPY", real=False, frames=hit, path=path))

    # 8) A FIXED STAR BRIGHTENS (what the colour-per-frame effect looks like)
    f0 = b1[0]
    stars = find_peaks(np.where(np.isfinite(f0["raw"]), f0["raw"], np.nan), f0["sigma_raw"], 20)
    if stars:
        sx, sy, _ = sorted(stars, key=lambda s: s[2])[len(stars) // 2]
        ra, dec = f0["wcs"].pixel_to_world_values(sx, sy)
        hit = [f["obsid"] for f in b1[:3] if plant(f, ra, dec, flux_for(f, 15))]
        truth.append(dict(kind="STAR_BRIGHTENS", real=False, frames=hit,
                          path=[tuple(float(v) for v in grid_wcs.world_to_pixel_values(ra, dec))]))
    return truth


# ---------------------------------------------------------------- spot checks

def check_crosstalk(fr, x_raw, y_raw):
    """Bright/saturated pixel 32 rows or 64*n columns away on the chip?"""
    raw, flags = fr["raw"], fr["flags"]
    h, w = raw.shape
    thr = 30 * fr["sigma_raw"]
    xi, yi = int(round(x_raw)), int(round(y_raw))
    for dx, dy in [(0, 32), (0, -32)] + [(64 * k, 0) for k in (-2, -1, 1, 2)]:
        for ex, ey in itertools.product((-1, 0, 1), repeat=2):
            tx, ty = xi + dx + ex, yi + dy + ey
            if 0 <= tx < w and 0 <= ty < h and (
                    (np.isfinite(raw[ty, tx]) and raw[ty, tx] > thr)
                    or flags[ty, tx] & (OVERFLOW_BIT | NONLINEAR_BIT)):
                return True
    return False


def sharpness(fr, x_raw, y_raw):
    raw = fr["raw"]
    xi, yi = int(round(x_raw)), int(round(y_raw))
    if not (3 <= xi < raw.shape[1] - 3 and 3 <= yi < raw.shape[0] - 3):
        return 0.0
    patch = raw[yi - 3:yi + 4, xi - 3:xi + 4]
    bg = np.nanmedian(np.concatenate([patch[0], patch[-1], patch[1:-1, 0], patch[1:-1, -1]]))
    core = patch[2:5, 2:5] - bg
    if not np.all(np.isfinite(core)) or core.sum() <= 0:
        return 0.0
    return float(core.max() / core.sum())


# ---------------------------------------------------------------- grouping

def fit_line(pts):
    """Straight-line, steady-speed fit of position vs time. Returns
    (vx, vy in px/hour, rms px, hours spanned)."""
    t = np.array([(p["mjd"] - pts[0]["mjd"]) * 24 for p in pts])
    X, Y = np.array([p["cx"] for p in pts]), np.array([p["cy"] for p in pts])
    if np.ptp(t) == 0:
        return 0.0, 0.0, 0.0, 0.0
    px, py = np.polyfit(t, X, 1), np.polyfit(t, Y, 1)
    rms = float(np.sqrt(np.mean((np.polyval(px, t) - X) ** 2 + (np.polyval(py, t) - Y) ** 2)))
    return float(px[0]), float(py[0]), rms, float(np.ptp(t))


def group_spots(clean, burst_of):
    """Within each burst, gather spots at the same sky position (allowing a small
    drift), one per exposure."""
    groups, taken = [], set()
    for d in sorted(clean, key=lambda d: d["mjd"]):
        if id(d) in taken:
            continue
        g = [d]
        taken.add(id(d))
        for e in sorted(clean, key=lambda e: e["mjd"]):
            if id(e) in taken or burst_of[e["obsid"]] != burst_of[d["obsid"]]:
                continue
            if any(e["obsid"] == m["obsid"] for m in g):
                continue
            last = g[-1]
            if np.hypot(e["cx"] - last["cx"], e["cy"] - last["cy"]) <= SAME_SPOT_PX:
                g.append(e)
                taken.add(id(e))
        groups.append(dict(members=g, burst=burst_of[d["obsid"]]))
    for g in groups:
        m = g["members"]
        g["cx"], g["cy"] = np.mean([p["cx"] for p in m]), np.mean([p["cy"] for p in m])
        g["mjd"] = np.mean([p["mjd"] for p in m])
        # 2 sightings still give a motion estimate (used to check links); only
        # 3+ can prove motion on their own.
        vx, vy, rms, hours = fit_line(m) if len(m) >= 2 else (0.0, 0.0, 0.0, 0.0)
        drift = np.hypot(vx, vy) * hours
        # Position error: at least the measured star wobble, more for faint spots.
        snr = np.mean([p["snr"] for p in m])
        err = max(rms, POS_ERR_FLOOR, 1.5 / snr)
        g.update(vx=vx, vy=vy, rms=rms, drift=drift, hours=hours, err=err,
                 drifting=len(m) >= 3 and drift >= DRIFT_MIN_PX and drift >= DRIFT_SIGMAS * err)
    return groups


def link_bursts(groups):
    """Link groups from different bursts into straight-line tracks. With 3+ bursts
    the line itself is the test. With only 2 bursts any two spots make a line, so
    we accept the link only if neither spot has another possible partner."""
    usable = [g for g in groups if len(g["members"]) >= 2]
    tracks, used = [], set()

    def compatible(g, vx, vy):
        # The motion the link implies inside this spot's own burst must match the
        # motion we actually measured there, within the position noise.
        mismatch = np.hypot(vx - g.get("vx", 0.0), vy - g.get("vy", 0.0)) * g.get("hours", 0.0)
        return mismatch <= max(DRIFT_MIN_PX, DRIFT_SIGMAS * g.get("err", POS_ERR_FLOOR))
    # 3+ bursts: try every combination of one group per burst (small numbers)
    by_burst = {}
    for g in usable:
        by_burst.setdefault(g["burst"], []).append(g)
    bursts = sorted(by_burst)
    for k in range(min(len(bursts), 5), 2, -1):
        for bs in itertools.combinations(bursts, k):
            for combo in itertools.product(*(by_burst[b] for b in bs)):
                if any(id(g) in used for g in combo):
                    continue
                times = sorted(g["mjd"] for g in combo)
                if times[-1] - times[0] > MAX_LINK_DAYS:
                    continue
                pts = sorted([dict(mjd=g["mjd"], cx=g["cx"], cy=g["cy"]) for g in combo],
                             key=lambda p: p["mjd"])
                vx, vy, rms, _ = fit_line(pts)
                if rms <= LINK_TOL_PX and all(compatible(g, vx, vy) for g in combo):
                    used.update(id(g) for g in combo)
                    tracks.append(dict(groups=list(combo), vx=vx, vy=vy, rms=rms))
    # 2 bursts: a link must agree with what each spot did inside its own burst,
    # and must be the only such link for both spots.
    def link_ok(a, b):
        dt = (b["mjd"] - a["mjd"]) * 24
        if dt == 0 or abs(dt) > MAX_LINK_DAYS * 24:
            return False
        vx, vy = (b["cx"] - a["cx"]) / dt, (b["cy"] - a["cy"]) / dt
        return compatible(a, vx, vy) and compatible(b, vx, vy)

    left = [g for g in usable if id(g) not in used]
    for a in left:
        if id(a) in used:
            continue
        partners = [b for b in left if b["burst"] != a["burst"] and id(b) not in used and link_ok(a, b)]
        if len(partners) == 1:
            b = partners[0]
            back = [c for c in left if c["burst"] != b["burst"] and id(c) not in used and link_ok(c, b)]
            # One end needs 3+ exposures and the other 2+, so motion was measured on
            # both ends (2+2 pairs proved to be chance matches in crowded fields).
            sizes = sorted((len(a["members"]), len(b["members"])))
            if len(back) == 1 and sizes[0] >= 2 and sizes[1] >= MIN_FRAMES:
                pts = sorted([dict(mjd=g["mjd"], cx=g["cx"], cy=g["cy"]) for g in (a, b)],
                             key=lambda p: p["mjd"])
                vx, vy, rms, _ = fit_line(pts)
                used.update((id(a), id(b)))
                tracks.append(dict(groups=sorted([a, b], key=lambda g: g["mjd"]),
                                   vx=vx, vy=vy, rms=rms))
    for tr in tracks:
        xs = [g["cx"] for g in tr["groups"]]
        ys = [g["cy"] for g in tr["groups"]]
        tr["moved"] = float(np.hypot(np.ptp(xs), np.ptp(ys)))
    return tracks, used


def skybot_lookup(mjd, ra, dec):
    try:
        r = requests.get(SKYBOT_URL, params={"-ep": mjd + 2400000.5, "-ra": ra, "-dec": dec,
                                            "-rd": 0.02, "-mime": "json", "-output": "object",
                                            "-loc": "500"}, timeout=40)
        objs = r.json() if r.status_code == 200 and r.text.strip().startswith("[") else []
    except Exception:
        return None, "SkyBoT unreachable"
    near = [o for o in objs if float(o.get("d (arcsec)", 1e9)) <= KNOWN_MATCH_ARCSEC]
    if not near:
        return None, "no known object nearby"
    o = min(near, key=lambda o: float(o["d (arcsec)"]))
    return o, (f"{o.get('Name')} ({o.get('Class')}, V={o.get('VMag (mag)')}, "
               f"{float(o['d (arcsec)']):.1f}\" away)")


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description="Find movers in SPHEREx images and filter out fakes")
    ap.add_argument("--target", choices=base.TARGETS, default="wise0855")
    ap.add_argument("--ra", type=float)
    ap.add_argument("--dec", type=float)
    ap.add_argument("--detector", type=int, choices=range(1, 7))
    ap.add_argument("--size", type=float, default=0.2, help="field width in degrees")
    ap.add_argument("--max-frames", type=int, default=80, help="cap on images used")
    ap.add_argument("--inject", action="store_true", help="plant test objects to prove the filter")
    ap.add_argument("--no-skybot", action="store_true", help="skip the known-asteroid lookup")
    args = ap.parse_args()

    if args.ra is not None and args.dec is not None:
        name, slug = f"RA {args.ra} Dec {args.dec}", f"ra{args.ra}_dec{args.dec}"
        ra, dec, detector = args.ra, args.dec, args.detector or 2
    else:
        t = base.TARGETS[args.target]
        name, slug = t["name"], args.target
        ra, dec = base.position_at(t, 2026.0)
        detector = args.detector or t["detector"]
    print(f"\nField: {name}  RA {ra:.4f} Dec {dec:.4f}  detector D{detector}  "
          f"{args.size * 60:.0f}' wide{'  [INJECTION TEST]' if args.inject else ''}")

    print("\n[1] Finding and downloading images...")
    rows = base.pick_evenly(base.search_images(ra, dec, detector), args.max_frames)
    with ThreadPoolExecutor(max_workers=6) as pool:
        paths = list(pool.map(lambda r: base.download_cutout(r, ra, dec, args.size), rows))
    anomalies = load_anomaly_list()
    frames = []
    for row, path in zip(rows, paths):
        if path is None:
            continue
        try:
            frames.append(load_frame(path, row, anomalies, detector))
        except Exception as e:
            print(f"  could not read {row['obs_id']}: {e}")
    print(f"  {len(frames)} images loaded")

    grid_wcs, shape = base.make_target_wcs(ra, dec, args.size)
    truth = []
    if args.inject:
        print("\n[*] Planting test objects (answer key kept aside)...")
        truth = inject(frames, grid_wcs, shape[0])
        for tr in truth:
            print(f"  {tr['kind']:<19} in {len(tr['frames'])} exposure(s): "
                  f"{'real, should be KEPT' if tr['real'] else 'fake, should be THROWN OUT'}")

    print("\n[2] Masking bad pixels and aligning...")
    for fr in frames:
        img = np.where((fr["flags"] & base.REJECT_MASK) != 0, np.nan, fr["raw"])
        fr["aligned"], _ = reproject_interp((img, fr["wcs"]), grid_wcs, shape_out=shape)
        fr["aligned"] -= np.nanmedian(fr["aligned"])

    good = [f for f in frames if not f["reasons"]]
    if len(good) < 5:
        print("Fewer than 5 usable images: not enough to build a fixed-sky template.")
        return
    template = quiet_nanmedian(np.array([f["aligned"] for f in good]))
    stars = find_peaks(template, robust_sigma(template), STAR_SNR)
    star_xy = np.array([(s[0], s[1]) for s in stars]) if stars else np.zeros((0, 2))
    star_radius = np.array([ON_STAR_RADIUS + 1.5 * np.log10(max(s[2], STAR_SNR) / STAR_SNR)
                            for s in stars])
    yy, xx = np.indices(shape)
    blind = np.zeros(shape, bool)
    for (sx, sy), r in zip(star_xy, star_radius):
        blind |= np.hypot(xx - sx, yy - sy) <= r
    blind_pct = 100 * blind[np.isfinite(template)].mean()
    print(f"  Fixed-sky template from {len(good)} images: {len(stars)} fixed stars; "
          f"{blind_pct:.0f}% of the field is close to a fixed star, where movers cannot be "
          "confirmed" + ("  (CROWDED FIELD)" if blind_pct > 25 else ""))

    for fr in good:  # alignment check on bright fixed stars
        offs = []
        for sx, sy, _ in [s for s in stars if s[2] > 15][:15]:
            tx, ty = centroid(template, sx, sy)
            fx, fy = centroid(fr["aligned"], sx, sy)
            offs.append(np.hypot(fx - tx, fy - ty))
        if len(offs) >= 3 and np.median(offs) > MISALIGN_PX:
            fr["reasons"].append(f"MISALIGNED ({np.median(offs):.2f} px)")
    good = [f for f in frames if not f["reasons"]]
    img_reasons = Counter(r.split(" (")[0] for f in frames for r in f["reasons"])
    print(f"\n[3] Image-level checks: {len(good)} of {len(frames)} images pass"
          + "".join(f"; {k}: {v}" for k, v in img_reasons.items()))

    print("\n[4] Subtracting fixed sky and testing every leftover spot...")
    dets = []
    for fr in good:
        diff = fr["aligned"] - template
        sig = robust_sigma(diff)
        for x, y, snr in find_peaks(diff, sig, DETECT_SNR):
            d = dict(obsid=fr["obsid"], mjd=fr["mjd"], x=x, y=y, snr=snr, reasons=[])
            d["cx"], d["cy"] = centroid(diff, x, y)
            # Brighter stars leave bigger leftover wings when the colour changes,
            # so their "on a fixed star" zone grows with brightness.
            if len(star_xy) and np.any(np.hypot(*(star_xy - (x, y)).T) <= star_radius):
                d["reasons"].append("ON_STATIC_STAR")
            xi, yi = int(round(x)), int(round(y))
            if not np.all(np.isfinite(fr["aligned"][max(yi - 1, 0):yi + 2, max(xi - 1, 0):xi + 2])):
                d["reasons"].append("NEAR_MASKED")
            d["ra"], d["dec"] = (float(v) for v in grid_wcs.pixel_to_world_values(x, y))
            xr, yr = (float(v) for v in fr["wcs"].world_to_pixel_values(d["ra"], d["dec"]))
            d["sharp"] = sharpness(fr, xr, yr)
            if d["sharp"] > SHARP_LIMIT:
                d["reasons"].append("TOO_SHARP")
            d["elong"] = elongation(diff, x, y, sig)
            if d["elong"] > STREAK_RATIO:
                d["reasons"].append("STREAK")
            if check_crosstalk(fr, xr, yr):
                d["reasons"].append("CROSSTALK")
            dets.append(d)
    clean = [d for d in dets if not d["reasons"]]
    print(f"  {len(dets)} leftover spots: {len(dets) - len(clean)} explained by an artifact "
          f"check, {len(clean)} left")

    print("\n[5] Grouping by sky position (real things stay put on the sky; chip artifacts jump)...")
    burst_of = dict(zip([f["obsid"] for f in good], split_bursts(np.array([f["mjd"] for f in good]))))
    groups = group_spots(clean, burst_of)
    tracks, linked = link_bursts(groups)
    objects = []  # every surviving real thing, moving or not
    for tr in tracks:
        members = [m for g in tr["groups"] for m in g["members"]]
        verdict = "CANDIDATE" if tr["moved"] >= MIN_MOTION_PX else "STILL_SOURCE"
        objects.append(dict(members=members, verdict=verdict, how="across bursts",
                            speed=np.hypot(tr["vx"], tr["vy"]), rms=tr["rms"], moved=tr["moved"]))
    for g in groups:
        if id(g) in linked:
            continue
        if len(g["members"]) < MIN_FRAMES:
            for m in g["members"]:
                m["reasons"].append("FEW_FRAMES")
            continue
        verdict = "CANDIDATE" if g["drifting"] else "STILL_SOURCE"
        objects.append(dict(members=g["members"], verdict=verdict, how="within one burst",
                            speed=np.hypot(g["vx"], g["vy"]), rms=g["rms"], moved=g["drift"]))
    for ob in objects:
        for m in ob["members"]:
            m["reasons"].append(ob["verdict"])

    movers = [o for o in objects if o["verdict"] == "CANDIDATE"]
    if movers and not args.no_skybot:
        print(f"  Checking {len(movers)} moving object(s) against known asteroids/comets (SkyBoT)...")
        for ob in movers:
            mid = ob["members"][len(ob["members"]) // 2]
            obj, ob["skybot"] = skybot_lookup(mid["mjd"], mid["ra"], mid["dec"])
            if obj is not None:
                ob["verdict"] = "KNOWN_OBJECT"
                for m in ob["members"]:
                    m["reasons"][-1] = "KNOWN_OBJECT"

    # ------------------------------------------------------------ report
    def final(d):
        return d["reasons"][0] if d["reasons"] else "?"

    counts = Counter(final(d) for d in dets)
    print("\n[6] Result: why each leftover spot was kept or thrown out")
    for k, text in REASON_TEXT.items():
        if counts.get(k):
            print(f"  {counts[k]:>4}  {k:<15} {text}")
    print(f"\n  Real objects found: "
          f"{sum(o['verdict'] == 'CANDIDATE' for o in objects)} moving candidate(s), "
          f"{sum(o['verdict'] == 'KNOWN_OBJECT' for o in objects)} known asteroid/comet(s), "
          f"{sum(o['verdict'] == 'STILL_SOURCE' for o in objects)} still source(s)")
    for i, ob in enumerate(objects, 1):
        print(f"   #{i} {ob['verdict']:<12} {len(ob['members'])} exposures, {ob['how']}, "
              f"moved {ob['moved']:.2f} px, {ob['speed'] * base.PIXEL_SCALE_ARCSEC:.0f}\"/hr, "
              f"fit error {ob['rms']:.2f} px" + (f"; SkyBoT: {ob['skybot']}" if ob.get("skybot") else ""))

    if truth:
        print("\n[7] INJECTION TEST: was each planted object handled correctly?")
        ok_count = 0
        for tr in truth:
            near = [d for d in dets if d["obsid"] in tr["frames"]
                    and min(np.hypot(d["x"] - px, d["y"] - py) for px, py in tr["path"]) <= 2.5]
            got = Counter(final(d) for d in near)
            verdict = got.most_common(1)[0][0] if near else "not detected"
            if tr["real"]:
                ok = verdict in ("CANDIDATE", "KNOWN_OBJECT")
                want = "kept as a moving candidate"
            else:
                ok = verdict in FAKE or verdict == "not detected"
                want = "thrown out"
            ok_count += ok
            print(f"  {'PASS' if ok else 'FAIL'}  {tr['kind']:<19} -> {verdict:<15} (should be {want})")
        print(f"\n  {ok_count} of {len(truth)} planted objects handled correctly")

    # ------------------------------------------------------------ outputs
    base.OUT_DIR.mkdir(exist_ok=True)
    tag = f"{slug}_D{detector}" + ("_inject" if args.inject else "")
    csv_path = base.OUT_DIR / f"{tag}_movers.csv"
    with open(csv_path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["obs_id", "mjd", "ra", "dec", "x", "y", "snr", "sharpness", "elongation",
                    "verdict", "all_reasons"])
        for d in sorted(dets, key=lambda d: d["mjd"]):
            w.writerow([d["obsid"], f"{d['mjd']:.5f}", f"{d['ra']:.6f}", f"{d['dec']:.6f}",
                        f"{d['cx']:.2f}", f"{d['cy']:.2f}", f"{d['snr']:.1f}", f"{d['sharp']:.2f}",
                        f"{d['elong']:.2f}", final(d), ";".join(d["reasons"])])

    fig, ax = plt.subplots(figsize=(8.5, 8))
    v0, v1 = np.nanpercentile(template, [1, 99.7])
    ax.imshow(np.arcsinh((template - v0) / (v1 - v0) * 10) / np.arcsinh(10),
              origin="lower", cmap="gray", vmin=0, vmax=1)
    for reason in FAKE:
        pts = [d for d in dets if final(d) == reason]
        if pts:
            # Fixed-star leftovers are by far the most common; draw them as faint
            # dots so they do not hide everything else.
            small = reason == "ON_STATIC_STAR"
            ax.scatter([d["cx"] for d in pts], [d["cy"] for d in pts], s=4 if small else 26,
                       facecolors=REASON_COLOR[reason] if small else "none",
                       edgecolors="none" if small else REASON_COLOR[reason],
                       alpha=0.35 if small else 1.0, lw=1.0,
                       label=f"thrown out: {reason} ({len(pts)})")
    for ob in objects:
        c = REASON_COLOR[ob["verdict"]]
        ms = sorted(ob["members"], key=lambda m: m["mjd"])
        ax.plot([m["cx"] for m in ms], [m["cy"] for m in ms], "-o", color=c, ms=6, lw=1.6,
                mfc="none", label=f"kept: {ob['verdict']}")
    for tr in truth:
        px, py = zip(*tr["path"])
        ax.plot(px, py, ":", color="#ff3b30", lw=1)
        ax.annotate(f"planted: {tr['kind']}", (px[0], py[0]), color="#ff3b30", fontsize=7,
                    xytext=(4, 6), textcoords="offset points")
    h, l = ax.get_legend_handles_labels()
    uniq = dict(zip(l, h))
    ax.legend(uniq.values(), uniq.keys(), loc="upper left", fontsize=7, framealpha=0.6)
    ax.set_xticks([]), ax.set_yticks([])
    ax.set_title(f"{name} D{detector}: every leftover spot after removing the fixed sky\n"
                 f"({len(good)} images, north up, east left, {args.size * 60:.0f}' wide)", fontsize=9)
    fig.tight_layout()
    png = base.OUT_DIR / f"{tag}_movers.png"
    fig.savefig(png, dpi=130)
    plt.close(fig)
    print(f"\nWrote:\n  {png}\n  {csv_path}")


if __name__ == "__main__":
    main()
