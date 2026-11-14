"""
spherex_try.py - first look at real SPHEREx images of one sky position.

What it does, step by step:
  1. Search IRSA (SIA2) for every SPHEREx image covering the target.
  2. Keep one detector (one slice of the infrared range).
  3. Group the images into "visits" (SPHEREx comes back about every 6 months).
  4. Download small cutouts around the target (a few per visit).
  5. Clean them: mask bad pixels using the FLAGS layer, subtract zodiacal light.
  6. Rotate/straighten every cutout onto one north-up grid (reproject).
  7. Stack the cutouts of each visit into one less-noisy picture.
  8. Save a side-by-side PNG, a blinking GIF and a CSV summary.
  9. For targets that move: stack EVERY frame shifted to follow the target's
     motion (shift-and-stack), so faint movers like WISE 0855 become visible.
     As a check, compare an early and a late half: the measured shift should
     match the predicted one. Saves a motion-stack PNG.

Usage:
  .venv/bin/python spherex_try.py                      # WISE 0855 (default)
  .venv/bin/python spherex_try.py --target barnard
  .venv/bin/python spherex_try.py --ra 133.79 --dec -7.24 --detector 6

Data: SPHEREx DR1 + QR3 from NASA/IPAC IRSA. Acknowledgement and DOIs are in
Planet_X_SPHEREx_Resources_Report.md.
"""

import argparse
import csv
import io
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import requests
from astropy.io import fits
from astropy.time import Time
from astropy.wcs import WCS, FITSFixedWarning
from reproject import reproject_interp
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter
import warnings

warnings.simplefilter("ignore", FITSFixedWarning)
from astropy import log as astropy_log

# SPHEREx headers carry SIP distortion without the "-SIP" CTYPE suffix; astropy
# applies it correctly but prints a long INFO message per file. Hide those.
astropy_log.setLevel("WARNING")

SIA_URL = "https://irsa.ipac.caltech.edu/SIA"
COLLECTIONS = ["spherex_dr1", "spherex_qr3"]  # current data; never mix with QR2
PIXEL_SCALE_ARCSEC = 6.15
CACHE_DIR = Path("spherex_cache")
OUT_DIR = Path("output")

# Test targets. Position is at `epoch` (decimal year); pm = proper motion in
# milliarcseconds per year (pmra already includes the cos(dec) factor).
# Values from Gaia DR3 (Barnard, Eps Indi B, RW Aur, R Dra) and Luhman & Esplin
# 2016 (WISE 0855, approximate AllWISE-era position).
TARGETS = {
    "wise0855": dict(name="WISE 0855-0714", ra=133.795129, dec=-7.245147, epoch=2010.5,
                     pmra=-8118.0, pmdec=680.0, detector=6,
                     note="Only visible at 3.9-5 um, so D5/D6"),
    "barnard": dict(name="Barnard's Star", ra=269.4485, dec=4.7394, epoch=2016.0,
                    pmra=-801.6, pmdec=10362.4, detector=2,
                    note="Saturated: position usable, brightness is not"),
    "epsindib": dict(name="Epsilon Indi B", ra=331.0765, dec=-56.7938, epoch=2016.0,
                     pmra=3982.0, pmdec=-2466.8, detector=4,
                     note="Two brown dwarfs blended into one dot"),
    "rwaur": dict(name="RW Aurigae", ra=76.956, dec=30.401, epoch=2016.0,
                  pmra=2.6, pmdec=-27.4, detector=2,
                  note="Does not move; tests brightness change"),
    "rdra": dict(name="R Draconis", ra=248.167, dec=66.755, epoch=2016.0,
                 pmra=-20.6, pmdec=6.1, detector=2,
                 note="Does not move; pulsating star, many polar visits"),
}

# FLAGS bits to mask (the official mosaic reject list, Explanatory Supplement
# Table 16). NONLINEAR (bit 15) is left out on purpose: it marks saturated
# stars, and masking it would erase bright targets like Barnard's Star.
REJECT_BITS = [0, 2, 6, 7, 9, 10, 11, 14, 17, 20, 22, 23, 24, 25, 26, 27, 28, 29]
REJECT_MASK = sum(1 << b for b in REJECT_BITS)
NONLINEAR_BIT = 1 << 15


def get_with_retry(url, params=None, tries=4, timeout=120):
    """IRSA often returns 502 errors; just try again a few times."""
    for attempt in range(1, tries + 1):
        try:
            r = requests.get(url, params=params, timeout=timeout)
            if r.status_code == 200:
                return r
            print(f"    HTTP {r.status_code}, retry {attempt}/{tries}")
        except requests.RequestException as e:
            print(f"    {type(e).__name__}, retry {attempt}/{tries}")
        time.sleep(2 * attempt)
    raise RuntimeError(f"Failed after {tries} tries: {url}")


def position_at(target, year):
    """Move a catalog position to a given date using proper motion."""
    dt = year - target["epoch"]
    dec = target["dec"] + target["pmdec"] / 3.6e6 * dt
    ra = target["ra"] + target["pmra"] / 3.6e6 * dt / np.cos(np.radians(target["dec"]))
    return ra, dec


def search_images(ra, dec, detector):
    """Step 1-2: find every SPHEREx image of this spot in one detector."""
    rows = []
    for coll in COLLECTIONS:
        params = {"COLLECTION": coll, "POS": f"circle {ra} {dec} 0.01", "RESPONSEFORMAT": "CSV"}
        r = get_with_retry(SIA_URL, params)
        found = list(csv.DictReader(io.StringIO(r.text)))
        print(f"  {coll}: {len(found)} images (all detectors)")
        rows += found
    band = f"SPHEREx-D{detector}"
    rows = [r for r in rows if r["energy_bandpassname"] == band]
    rows.sort(key=lambda r: float(r["t_min"]))
    print(f"  Detector D{detector}: {len(rows)} images")
    return rows


def group_into_visits(rows, gap_days=3.0):
    """Step 3: split the time-sorted list wherever there is a gap of days."""
    visits, current = [], []
    for row in rows:
        if current and float(row["t_min"]) - float(current[-1]["t_min"]) > gap_days:
            visits.append(current)
            current = []
        current.append(row)
    if current:
        visits.append(current)
    return visits


def pick_evenly(items, n):
    if len(items) <= n:
        return items
    idx = np.linspace(0, len(items) - 1, n).round().astype(int)
    return [items[i] for i in idx]


def download_cutout(row, ra, dec, size_deg):
    """Step 4: fetch a cutout (cached on disk, ~4 MB each)."""
    CACHE_DIR.mkdir(exist_ok=True)
    fname = CACHE_DIR / f"{row['obs_id']}_{row['energy_bandpassname'][-2:]}_{ra:.4f}_{dec:.4f}_{size_deg}.fits"
    if not fname.exists():
        url = f"{row['access_url']}?center={ra},{dec}&size={size_deg}"
        try:
            fname.write_bytes(get_with_retry(url).content)
        except RuntimeError:
            print(f"  gave up on {row['obs_id']} (IRSA kept failing); skipping it")
            return None
    return fname


def wavelength_at(hdul, ra, dec):
    """Which infrared color this cutout saw at the target (via WCS-WAVE)."""
    try:
        hdr = hdul["IMAGE"].header
        x, y = WCS(hdr).world_to_pixel_values(ra, dec)
        spec = WCS(hdr, fobj=hdul, key="W")
        spec.sip = None
        wl, _ = spec.pixel_to_world_values(x, y)
        return float(wl)
    except Exception:
        return float("nan")


def clean_and_reproject(path, target_wcs, shape, ra, dec):
    """Steps 5-6: mask bad pixels, remove zodiacal light, align north-up."""
    with fits.open(path) as hdul:
        img = hdul["IMAGE"].data.astype(float)
        flags = hdul["FLAGS"].data.astype(np.int64)
        zodi = hdul["ZODI"].data.astype(float) if "ZODI" in hdul else 0.0
        wcs_in = WCS(hdul["IMAGE"].header)
        wl = wavelength_at(hdul, ra, dec)
        img = img - zodi
        bad = (flags & REJECT_MASK) != 0
        frac_bad = float(bad.mean())
        # Was the target pixel itself flagged as saturated/nonlinear?
        tx, ty = wcs_in.world_to_pixel_values(ra, dec)
        tx, ty = int(round(float(tx))), int(round(float(ty)))
        nonlinear = bool(0 <= ty < flags.shape[0] and 0 <= tx < flags.shape[1]
                         and flags[ty, tx] & NONLINEAR_BIT)
        img[bad] = np.nan
        aligned, _ = reproject_interp((img, wcs_in), target_wcs, shape_out=shape)
    return aligned, wl, frac_bad, nonlinear


def aperture_snr(img, x, y, r=1.6, r_in=4, r_out=8):
    """Signal-to-noise inside a small circle, using a ring around it as background."""
    yy, xx = np.indices(img.shape)
    d = np.hypot(xx - x, yy - y)
    ap = img[(d <= r) & np.isfinite(img)]
    ann = img[(d >= r_in) & (d <= r_out) & np.isfinite(img)]
    if ap.size == 0 or ann.size < 5:
        return float("nan")
    bg, sig = np.median(ann), np.std(ann)
    return float((ap - bg).sum() / (sig * np.sqrt(ap.size)))


def centroid(img, x, y, r=2.0, r_in=4, r_out=8):
    """Brightness-weighted center of the blob near (x, y), to a fraction of a pixel."""
    yy, xx = np.indices(img.shape)
    d = np.hypot(xx - x, yy - y)
    ann = img[(d >= r_in) & (d <= r_out) & np.isfinite(img)]
    w = img - np.median(ann)
    m = (d <= r) & np.isfinite(w) & (w > 0)
    if not m.any():
        return float("nan"), float("nan")
    return float((xx[m] * w[m]).sum() / w[m].sum()), float((yy[m] * w[m]).sum() / w[m].sum())


def nanmean_quiet(cube):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        return np.nanmean(cube, axis=0)


def motion_stack(target, rows, paths, ra, dec, size_deg):
    """Shift-and-stack: line every frame up on the target's predicted position for
    that frame's date, then average. A faint mover adds up into a visible dot.
    Also builds a fixed-sky stack and an early-vs-late check as a control."""
    fixed_wcs, shape = make_target_wcs(ra, dec, size_deg)
    following, fixed, mjds = [], [], []
    for row, path in zip(rows, paths):
        if path is None:  # download failed
            continue
        mjd = float(row["t_min"])
        pra, pdec = position_at(target, Time(mjd, format="mjd").decimalyear)
        follow_wcs, _ = make_target_wcs(pra, pdec, size_deg)  # grid that moves with it
        try:
            img_follow, *_ = clean_and_reproject(path, follow_wcs, shape, pra, pdec)
            img_fixed, *_ = clean_and_reproject(path, fixed_wcs, shape, ra, dec)
        except Exception as e:
            print(f"  skipped {row['obs_id']}: {e}")
            continue
        following.append(img_follow - np.nanmedian(img_follow))
        fixed.append(img_fixed - np.nanmedian(img_fixed))
        mjds.append(mjd)

    mjds = np.array(mjds)
    c = (shape[0] - 1) / 2  # target sits at the center of the following grid
    follow_img = nanmean_quiet(np.array(following))
    fixed_img = nanmean_quiet(np.array(fixed))

    # Control: split frames into an early and a late half on the FIXED grid and
    # measure where the blob is in each. A real mover shifts by the predicted amount.
    split = np.median(mjds)
    halves = []
    for name, sel in (("early", mjds < split), ("late", mjds >= split)):
        img = nanmean_quiet(np.array(fixed)[sel])
        year = Time(mjds[sel].mean(), format="mjd").decimalyear
        px, py = fixed_wcs.world_to_pixel_values(*position_at(target, year))
        cx, cy = centroid(img, float(px), float(py))
        halves.append(dict(name=name, n=int(sel.sum()), date=Time(mjds[sel].mean(), format="mjd").iso[:10],
                           px=float(px), py=float(py), cx=cx, cy=cy,
                           snr=aperture_snr(img, float(px), float(py))))
    e, l = halves
    return dict(follow_img=follow_img, fixed_img=fixed_img, n=len(mjds), center=c,
                snr_follow=aperture_snr(follow_img, c, c),
                fixed_px=fixed_wcs.world_to_pixel_values(ra, dec),
                snr_fixed=aperture_snr(fixed_img, *fixed_wcs.world_to_pixel_values(ra, dec)),
                halves=halves,
                pred_shift=(l["px"] - e["px"], l["py"] - e["py"]),
                meas_shift=(l["cx"] - e["cx"], l["cy"] - e["cy"]))


def make_target_wcs(ra, dec, size_deg):
    n = int(round(size_deg * 3600 / PIXEL_SCALE_ARCSEC))
    w = WCS(naxis=2)
    w.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    w.wcs.crval = [ra, dec]
    w.wcs.crpix = [(n + 1) / 2, (n + 1) / 2]
    w.wcs.cdelt = [-PIXEL_SCALE_ARCSEC / 3600, PIXEL_SCALE_ARCSEC / 3600]
    return w, (n, n)


def main():
    ap = argparse.ArgumentParser(description="First look at SPHEREx multi-epoch images")
    ap.add_argument("--target", choices=TARGETS, default="wise0855")
    ap.add_argument("--ra", type=float, help="custom RA in degrees (overrides --target)")
    ap.add_argument("--dec", type=float, help="custom Dec in degrees")
    ap.add_argument("--detector", type=int, choices=range(1, 7), help="1-6")
    ap.add_argument("--size", type=float, default=0.08, help="cutout size in degrees")
    ap.add_argument("--per-visit", type=int, default=4, help="cutouts to stack per visit")
    ap.add_argument("--no-motion-stack", action="store_true",
                    help="skip step 5 (stacking every frame along the target's motion)")
    args = ap.parse_args()

    if args.ra is not None and args.dec is not None:
        target = dict(name=f"RA {args.ra} Dec {args.dec}", ra=args.ra, dec=args.dec,
                      epoch=2026.0, pmra=0.0, pmdec=0.0, detector=args.detector or 2, note="")
        slug = f"ra{args.ra}_dec{args.dec}"
    else:
        target = TARGETS[args.target]
        slug = args.target
    detector = args.detector or target["detector"]

    # Center on where the target is in mid-2026, not on its old catalog spot.
    ra, dec = position_at(target, 2026.0)
    print(f"\nTarget: {target['name']}  (centered at RA {ra:.5f}, Dec {dec:.5f} for 2026.0)")
    if target["note"]:
        print(f"Note: {target['note']}")

    print("\n[1] Searching IRSA SIA2...")
    rows = search_images(ra, dec, detector)
    if not rows:
        print("No images found. Try another --detector.")
        return

    visits = group_into_visits(rows)
    print(f"\n[2] {len(visits)} visits found:")
    for i, v in enumerate(visits, 1):
        t0 = Time(float(v[0]["t_min"]), format="mjd").iso[:10]
        print(f"  Visit {i}: {t0}  ({len(v)} images)")

    picks = [(i, row) for i, v in enumerate(visits) for row in pick_evenly(v, args.per_visit)]
    print(f"\n[3] Downloading {len(picks)} cutouts ({args.size} deg, ~4 MB each, cached)...")
    with ThreadPoolExecutor(max_workers=6) as pool:
        paths = list(pool.map(lambda p: download_cutout(p[1], ra, dec, args.size), picks))

    print("\n[4] Cleaning, aligning north-up and stacking each visit...")
    target_wcs, shape = make_target_wcs(ra, dec, args.size)
    per_visit = {}
    for (vi, row), path in zip(picks, paths):
        if path is None:  # download failed
            continue
        try:
            aligned, wl, frac_bad, nonlin = clean_and_reproject(path, target_wcs, shape, ra, dec)
        except Exception as e:
            print(f"  skipped {row['obs_id']}: {e}")
            continue
        per_visit.setdefault(vi, []).append(
            dict(img=aligned, wl=wl, bad=frac_bad, nonlin=nonlin, mjd=float(row["t_min"]),
                 obs_id=row["obs_id"]))

    stacks, summary = [], []
    for vi in sorted(per_visit):
        frames = per_visit[vi]
        cube = np.array([f["img"] for f in frames])
        # Corners outside every rotated cutout are all-NaN; that is expected.
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            stack = np.nanmedian(cube, axis=0)
        stack -= np.nanmedian(stack)  # remove leftover background
        mjd = float(np.mean([f["mjd"] for f in frames]))
        wls = [f["wl"] for f in frames]
        stacks.append(dict(img=stack, mjd=mjd, date=Time(mjd, format="mjd").iso[:10],
                           wl_min=np.nanmin(wls), wl_max=np.nanmax(wls), n=len(frames),
                           nonlin=any(f["nonlin"] for f in frames)))
        for f in frames:
            summary.append([vi + 1, f["obs_id"], f"{f['mjd']:.4f}", f"{f['wl']:.4f}",
                            f"{f['bad']:.3f}", f["nonlin"]])

    # Predicted target position on each visit's date, in aligned-pixel units.
    for s in stacks:
        year = Time(s["mjd"], format="mjd").decimalyear
        pra, pdec = position_at(target, year)
        s["px"], s["py"] = target_wcs.world_to_pixel_values(pra, pdec)

    OUT_DIR.mkdir(exist_ok=True)
    all_pix = np.concatenate([s["img"][np.isfinite(s["img"])] for s in stacks])
    vmin, vmax = np.percentile(all_pix, [1, 99.7])  # same brightness scale for all

    # Direction of motion on the image (for the arrow), from proper motion.
    n_pix = shape[0]
    pm_total = np.hypot(target["pmra"], target["pmdec"])
    arrow_len = n_pix * 0.12
    if pm_total > 100:  # only draw an arrow for objects that really move (>0.1"/yr)
        # North is up (+y), east is left (-x) in these images.
        adx = -target["pmra"] / pm_total * arrow_len
        ady = target["pmdec"] / pm_total * arrow_len
    else:
        adx = ady = None
    circle_r = 3.0  # pixels (~18 arcsec, about two star-blob widths)
    label = target["name"].split(" (")[0]

    def show(ax, s):
        img = np.arcsinh((s["img"] - vmin) / (vmax - vmin) * 10) / np.arcsinh(10)
        ax.imshow(img, origin="lower", cmap="gray", vmin=0, vmax=1)
        # Highlight the target: circle + name + motion arrow, at its predicted
        # position for this visit's date.
        ax.add_patch(plt.Circle((s["px"], s["py"]), circle_r, fill=False,
                                color="#ff3b30", lw=1.6))
        ax.plot(s["px"], s["py"], marker="+", color="#ff3b30", ms=6, mew=1)
        ax.annotate(label, (s["px"], s["py"] + circle_r + 1), color="#ff3b30",
                    fontsize=8, ha="center", va="bottom", fontweight="bold")
        if adx is not None:
            # Arrow starts just below-right of the circle and points along the motion.
            x0, y0 = s["px"] + circle_r * 1.3, s["py"] - circle_r * 1.3
            ax.annotate("", xy=(x0 + adx, y0 + ady), xytext=(x0, y0),
                        arrowprops=dict(arrowstyle="->", color="#ffcc00", lw=1.4))
        sat = "  SATURATED" if s["nonlin"] else ""
        ax.set_title(f"{s['date']}  ({s['n']} frames)\n{s['wl_min']:.2f}-{s['wl_max']:.2f} um{sat}",
                     fontsize=8)
        ax.set_xticks([]), ax.set_yticks([])

    # Side-by-side image
    fig, axes = plt.subplots(1, len(stacks), figsize=(3 * len(stacks), 3.6), squeeze=False)
    for ax, s in zip(axes[0], stacks):
        show(ax, s)
    fig.suptitle(f"{target['name']} - SPHEREx D{detector}, north up, east left, "
                 f"{args.size * 60:.1f}' wide. Red circle = where the target should be, yellow arrow = its direction of motion", fontsize=10)
    fig.tight_layout()
    png = OUT_DIR / f"{slug}_D{detector}_visits.png"
    fig.savefig(png, dpi=130)
    plt.close(fig)

    # Blink GIF (1 frame per second, well under the 3 flashes/second safety limit)
    fig, ax = plt.subplots(figsize=(4, 4.4))

    def frame(i):
        ax.clear()
        show(ax, stacks[i])

    anim = FuncAnimation(fig, frame, frames=len(stacks))
    gif = OUT_DIR / f"{slug}_D{detector}_blink.gif"
    anim.save(gif, writer=PillowWriter(fps=1))
    plt.close(fig)

    csv_path = OUT_DIR / f"{slug}_D{detector}_frames.csv"
    with open(csv_path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["visit", "obs_id", "mjd", "wavelength_um_at_target", "frac_pixels_masked",
                    "target_saturated"])
        w.writerows(summary)

    print(f"\nWrote:\n  {png}\n  {gif}\n  {csv_path}")
    for s in stacks:
        print(f"  {s['date']}: {s['n']} frames, wavelength {s['wl_min']:.3f}-{s['wl_max']:.3f} um"
              + ("  (target saturated)" if s["nonlin"] else ""))

    # ---- Step 5: motion-following stack (shift-and-stack) over ALL frames ----
    if pm_total <= 100 or args.no_motion_stack:
        if pm_total <= 100:
            print("\n[5] Motion stack skipped: this target does not move noticeably.")
        return
    print(f"\n[5] Motion-following stack: downloading all {len(rows)} frames (cached)...")
    with ThreadPoolExecutor(max_workers=6) as pool:
        all_paths = list(pool.map(lambda r: download_cutout(r, ra, dec, args.size), rows))
    ms = motion_stack(target, rows, all_paths, ra, dec, args.size)

    fig, axes = plt.subplots(1, 2, figsize=(8, 4.4))
    panels = [
        (axes[0], ms["fixed_img"], ms["fixed_px"],
         f"Fixed sky: stars sharp, mover smeared\nS/N at target {ms['snr_fixed']:.1f}"),
        (axes[1], ms["follow_img"], (ms["center"], ms["center"]),
         f"Following its motion: mover sharp\nS/N at target {ms['snr_follow']:.1f}"),
    ]
    for ax, img, (px, py), title in panels:
        v0, v1 = np.nanpercentile(img, [1, 99.7])
        ax.imshow(np.arcsinh((img - v0) / (v1 - v0) * 10) / np.arcsinh(10),
                  origin="lower", cmap="gray", vmin=0, vmax=1)
        ax.add_patch(plt.Circle((px, py), circle_r, fill=False, color="#ff3b30", lw=1.6))
        ax.set_title(title, fontsize=9)
        ax.set_xticks([]), ax.set_yticks([])
    fig.suptitle(f"{label}: all {ms['n']} D{detector} frames stacked (north up, east left)",
                 fontsize=10)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    ms_png = OUT_DIR / f"{slug}_D{detector}_motion_stack.png"
    fig.savefig(ms_png, dpi=130)
    plt.close(fig)

    e, l = ms["halves"]
    px6 = PIXEL_SCALE_ARCSEC
    if not np.isfinite(ms["snr_follow"]):
        print("  The target's center is blank in the data: it is so bright that the")
        print("  pipeline masks its overexposed core. Its brightness and exact shift")
        print("  cannot be measured this way; the images still show its halo moving.")
        print(f"  Predicted shift between halves: {np.hypot(*ms['pred_shift']) * px6:.1f} arcsec")
        print(f"\nWrote:\n  {ms_png}")
        return
    print(f"  Fixed-sky stack S/N at target:        {ms['snr_fixed']:.1f}")
    print(f"  Motion-following stack S/N at target: {ms['snr_follow']:.1f}")
    print(f"  Early half ({e['date']}, {e['n']} frames): S/N {e['snr']:.1f}")
    print(f"  Late half  ({l['date']}, {l['n']} frames): S/N {l['snr']:.1f}")
    print(f"  Predicted shift early->late: dx {ms['pred_shift'][0]:+.2f} px, dy {ms['pred_shift'][1]:+.2f} px"
          f"  ({np.hypot(*ms['pred_shift']) * px6:.1f} arcsec)")
    print(f"  Measured shift  early->late: dx {ms['meas_shift'][0]:+.2f} px, dy {ms['meas_shift'][1]:+.2f} px"
          f"  ({np.hypot(*ms['meas_shift']) * px6:.1f} arcsec)")
    print("  (x: + is west/right, y: + is north/up. A real mover's measured shift"
          " should match the predicted one.)")
    print(f"\nWrote:\n  {ms_png}")


if __name__ == "__main__":
    main()
