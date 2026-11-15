"""Independent cross-check with a deliberately simple second method: plain aperture photometry on the MEDIAN of
the sky-cleaned (target minus static reference) north-up frames. No PSF fit, no colour weighting, no clipping.
The error comes from the same aperture placed at 200 random empty spots of the same median image, so the S/N is
empirical. Only frames that pass the frame QA and have a reference are used."""
from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd

from . import config as C
from . import fetch as FE
from . import images as IM
from .pilot import R

SCALE = 2.0          # arcsec per pixel of the median image
R_AP = 6.0           # aperture radius, arcsec (~1 SPHEREx pixel; PSF FWHM ~6-9")
R_IN, R_OUT = 15.0, 30.0
UJY_PER_MJYSR_ARCSEC2 = 1e12 / 206264.80624709636 ** 2


def aperture(img, x, y, scale=SCALE):
    n = img.shape[0]
    jj, ii = np.mgrid[0:n, 0:n]
    r = np.hypot(ii - x, jj - y) * scale
    ap, an = (r <= R_AP) & np.isfinite(img), (r >= R_IN) & (r <= R_OUT) & np.isfinite(img)
    if ap.sum() < 3 or an.sum() < 20:
        return np.nan
    return float(np.sum(img[ap] - np.median(img[an])) * scale ** 2 * UJY_PER_MJYSR_ARCSEC2)


def run(slug, kind="comet", half_arcsec=100.0, seed=1, qa=True, mjd_min=None, days=None):
    from .pipeline import load_refs, qa_drop
    d = os.path.join(C.WORK, "objects", slug)
    fr = pd.read_csv(os.path.join(d, "frames.csv")).set_index("file")
    ph = pd.read_csv(os.path.join(d, "paths_phot.csv"), keep_default_na=False, na_values=[""])
    for c in ("flux", "err", "ref_flux", "chi2", "flag_or"):
        ph[c] = pd.to_numeric(ph[c], errors="coerce")
    drop = qa_drop(ph) if qa else set()
    t = ph[(ph.path == "target") & (ph.status == "ok") & np.isfinite(ph.ref_flux) & ~ph.file.isin(drop)]
    imgs = []
    for f in t.file:
        r = fr.loc[f]
        if mjd_min is not None and r.mjd_avg < mjd_min:
            continue
        if days is not None and int(r.mjd_avg) not in days:
            continue
        st = R.load_stamp_fits(FE.stamp_path(slug, f))
        refs = load_refs(slug, f, r.rate_arcsec_hr, kind == "comet", r.trail_px)
        if not refs:
            continue
        a = IM.north_up(st, r.pred_ra, r.pred_dec, half_arcsec=half_arcsec, scale=SCALE, order=1)
        b = np.nanmedian([IM.north_up(s2, r.pred_ra, r.pred_dec, half_arcsec=half_arcsec, scale=SCALE, order=1)
                          for s2 in refs], 0)
        imgs.append(a - b)
    if len(imgs) < 5:
        return dict(slug=slug, n_frames=len(imgs), note="too few cleaned frames")
    med = np.nanmedian(imgs, 0)
    k = (med.shape[0] - 1) / 2
    f0 = aperture(med, k, k)
    rng = np.random.default_rng(seed)
    rand = []
    lim = k - (R_OUT / SCALE) - 1
    while len(rand) < 200:
        x, y = rng.uniform(k - lim, k + lim, 2)
        if np.hypot(x - k, y - k) * SCALE < 2 * R_IN:  # keep the random apertures off the target
            continue
        v = aperture(med, x, y)
        if np.isfinite(v):
            rand.append(v)
    rand = np.array(rand)
    mu, sd = float(np.median(rand)), float(1.4826 * np.median(np.abs(rand - np.median(rand))))
    out = dict(slug=slug, method="aperture on median of cleaned frames", n_frames=len(imgs), flux_ujy=round(f0, 2),
               random_aperture_median=round(mu, 2), random_aperture_sigma=round(sd, 2), snr=round((f0 - mu) / sd, 2),
               frac_random_brighter=float(np.mean(rand >= f0)), aperture_arcsec=R_AP, label="MEASURED")
    out.update(qa=qa, mjd_min=mjd_min)
    out.update(days=sorted(days) if days is not None else None)
    tag = "" if qa and mjd_min is None and days is None else f"_qa{int(qa)}_{mjd_min}_{'pos' if days else ''}"
    json.dump(out, open(os.path.join(d, f"crosscheck{tag}.json"), "w"), indent=1)
    lo, hi = np.nanpercentile(med, [5, 99.8])
    IM.save(med, os.path.join(d, f"crosscheck_median{tag}.png"), lo, hi)
    return out
