"""NEOWISE pixel check of catalog-level precovery hits (2015 SA, C/2026 C1, C/2026 H2).

For each target: all NEOWISE-R single exposures of the visit (+-1.5 d) whose footprint holds the predicted
position (kete, observer = WISE kernel, frame mid-time), W1+W2 L1b cutouts (int, unc, msk) from IRSA IBE,
forced Gaussian-PSF photometry (trailed when the motion in 7.7 s exceeds 1 px) at the predicted position
and at the catalog hit, then the SPHEREx-engine controls: 24 null paths (fixed sky offsets 20-50"),
along-track time-shifted paths, a static-sky check at the hit position (other-visit exposures + AllWISE /
CatWISE2020 / NEOWISE single-exposure catalog), a clipped inverse-variance stack along the path and a
positional (offset) fit, and for 2015 SA a kete orbit refit with the NEOWISE point.

Labels: MEASURED (pixels or archive catalog values), COMPUTED (arithmetic on those), ESTIMATED (models).
Read-only public data; nothing is submitted anywhere.

    python -m rewind_engine.neowise [slug ...]        # run (default: all three)
    from rewind_engine.neowise import neowise_frames_for_site
"""
from __future__ import annotations

import io
import json
import os
import sys
import time

import numpy as np
import pandas as pd
import requests
from astropy.io import ascii, fits
from astropy.time import Time
from astropy.wcs import WCS
from scipy.special import erf

from . import config as C
from . import images as IM
from .objects import slugify
from .pilot import orbitfit, positions

OUT = os.path.join(C.WORK, "neowise")
CUT = os.path.join(OUT, "cutouts")
A4 = os.path.join(C.DATA, "04-other-archives")
UA = {"User-Agent": "Rewind-SpaceApps2026-c2-engine (read-only research)"}
IBE = "https://irsa.ipac.caltech.edu/ibe/data/wise/neowiser/p1bm_frm"
GATOR = "https://irsa.ipac.caltech.edu/cgi-bin/Gator/nph-query"

PIX = 2.754                      # arcsec / px, L1b (header PXSCAL)
FWHM = {1: 6.1, 2: 6.4}          # arcsec
WAVE = {1: 3.4, 2: 4.6}          # um
F0_JY = {1: 309.540, 2: 171.787}  # Vega zero points (Wright et al. 2010)
EXPTIME_S = 7.7
WINDOW_D = 1.5
N_NULL = 24
SHIFT_UNITS = [-4, -3, -2, -1, 0, 1, 2, 3, 4]   # x 1 FWHM of along-track displacement
SHIFT_DAYS = [-0.2, -0.1, -0.05, 0.05, 0.1, 0.2]
# L1b mask bits treated as bad: static bad-pixel bits 0-7, broken / saturated reads 9-20, dynamic bad 21,
# unreliable non-linearity 26, spikes 27, unclassified outliers 29, NaN 31 (latents, bit 30, are kept)
BAD_BITS = sum(1 << b for b in list(range(0, 8)) + list(range(9, 22)) + [26, 27, 29, 31])
OBLIQ = np.radians(23.4392911)

TARGETS = {
    "2015sa": dict(desig="2015 SA", comet=False, primary=2),
    "c2026c1": dict(desig="C/2026 C1", comet=True, primary=1),
    "c2026h2": dict(desig="C/2026 H2", comet=True, primary=2),
}


# ----------------------------------------------------------------------------------------- HTTP

def get(url, params=None, timeout=300, tries=5):
    last = None
    for k in range(tries):
        try:
            r = requests.get(url, params=params, timeout=timeout, headers=UA)
            if r.status_code in (429, 500, 502, 503, 504):
                last = f"HTTP {r.status_code}"
                time.sleep(4 * 2 ** k)
                continue
            return r
        except Exception as e:  # network hiccup
            last = repr(e)
            time.sleep(4 * 2 ** k)
    raise RuntimeError(f"{url}: {last}")


def gator(catalog, ra, dec, radius_arcsec):
    """IRSA Gator cone search -> DataFrame (cached under OUT/gator)."""
    d = os.path.join(OUT, "gator")
    os.makedirs(d, exist_ok=True)
    fn = os.path.join(d, f"{catalog}_{ra:.5f}_{dec:+.5f}_{radius_arcsec:.0f}.tbl")
    if not os.path.exists(fn):
        r = get(GATOR, dict(catalog=catalog, spatial="cone", objstr=f"{ra:.6f} {dec:+.6f}", radius=radius_arcsec, outfmt=1))
        if r.status_code != 200:
            raise RuntimeError(f"gator {catalog} HTTP {r.status_code}")
        open(fn, "w").write(r.text)
        time.sleep(0.5)
    txt = open(fn).read()
    if "RowsRetrieved =                 0" in txt or "|" not in txt:
        return pd.DataFrame()
    return ascii.read(txt, format="ipac").to_pandas()


def frame_path(scan, frame, band, kind):
    ext = "fits" if kind == "int" else "fits.gz"
    return f"{scan[-2:]}/{scan}/{int(frame):03d}/{scan}{int(frame):03d}-w{band}-{kind}-1b.{ext}"


def cutout(scan, frame, band, kind, ra, dec, size_arcsec, tag):
    os.makedirs(CUT, exist_ok=True)
    fn = os.path.join(CUT, f"{scan}{int(frame):03d}_w{band}_{kind}_{tag}.fits")
    if os.path.exists(fn):
        return fn if os.path.getsize(fn) > 500 else None
    url = f"{IBE}/{frame_path(scan, frame, band, kind)}?center={ra:.6f},{dec:.6f}&size={size_arcsec:.0f}arcsec"
    try:
        r = get(url, timeout=300, tries=2)
        ok = r.status_code == 200 and len(r.content) > 500
    except RuntimeError as e:  # IBE answers HTTP 500 when the centre is off the frame
        print("cutout failed", repr(e)[:200], flush=True)
        r, ok = None, False
    open(fn, "wb").write(r.content if ok else b"")
    time.sleep(0.25)
    return fn if ok else None


def load_frame(scan, frame, band, ra, dec, size, tag):
    """int+unc+msk cutouts -> dict, or None."""
    fi = cutout(scan, frame, band, "int", ra, dec, size, tag)
    if not fi:
        return None
    fu = cutout(scan, frame, band, "unc", ra, dec, size, tag)
    fm = cutout(scan, frame, band, "msk", ra, dec, size, tag)
    if not (fi and fu and fm):
        return None
    hi = fits.open(fi)[0]
    img = hi.data.astype(float)
    unc = fits.open(fu)[0].data.astype(float)
    msk = fits.open(fm)[0].data.astype(np.int64)
    if img.shape != unc.shape or img.shape != msk.shape:
        return None
    bad = ((msk & BAD_BITS) != 0) | ~np.isfinite(img) | ~np.isfinite(unc) | (unc <= 0)
    h = hi.header
    return dict(scan=scan, frame=int(frame), band=band, img=img, unc=unc, bad=bad, wcs=WCS(h), magzp=float(h["MAGZP"]),
                mjd=float(h["MJD_OBS"]), iso=str(h["DATE_OBS"]), file=fi,
                key=f"wise/neowiser/p1bm_frm/{frame_path(scan, frame, band, 'int')}")


# ----------------------------------------------------------------------------------- photometry

def _gauss_pix(x0, y0, sig, X, Y):
    """Pixel-integrated circular Gaussian (unit total flux) centred on (x0, y0)."""
    s2 = np.sqrt(2) * sig
    gx = 0.5 * (erf((X + 0.5 - x0) / s2) - erf((X - 0.5 - x0) / s2))
    gy = 0.5 * (erf((Y + 0.5 - y0) / s2) - erf((Y - 0.5 - y0) / s2))
    return gx * gy


def phot(fr, ra, dec, trail_arcsec=(0.0, 0.0), r_fit=3.5, r_in=7.0, r_out=12.0):
    """Forced PSF photometry at (ra, dec). trail_arcsec = (east, north) motion during the exposure.
    Returns dict(flux_dn, err_dn, snr, x, y, ok)."""
    w = fr["wcs"]
    x, y = (float(v) for v in w.all_world2pix([[ra, dec]], 0)[0])
    ny, nx = fr["img"].shape
    out = dict(x=x, y=y, flux_dn=np.nan, err_dn=np.nan, snr=np.nan, ok=False)
    mg = int(r_out) + 2
    if not (mg <= x <= nx - 1 - mg and mg <= y <= ny - 1 - mg):
        out["why"] = "edge"
        return out
    x0, y0 = int(round(x)), int(round(y))
    sl = (slice(y0 - int(r_out) - 1, y0 + int(r_out) + 2), slice(x0 - int(r_out) - 1, x0 + int(r_out) + 2))
    d, u, b = fr["img"][sl], fr["unc"][sl], fr["bad"][sl]
    Y, X = np.mgrid[sl[0], sl[1]]
    R = np.hypot(X - x, Y - y)
    ann = (R >= r_in) & (R <= r_out) & ~b
    if ann.sum() < 30:
        out["why"] = "annulus"
        return out
    a = d[ann]
    for _ in range(3):
        med, mad = np.median(a), 1.4826 * np.median(np.abs(a - np.median(a)))
        a = a[np.abs(a - med) <= 3 * max(mad, 1e-6)]
    bkg = np.median(a)
    sig = FWHM[fr["band"]] / 2.3548 / PIX
    te, tn = trail_arcsec
    L = np.hypot(te, tn) / PIX
    if L > 1.0:  # trailed PSF: average of Gaussians along the segment
        xe, ye = (float(v) for v in w.all_world2pix([[ra + te / 3600 / np.cos(np.radians(dec)) / 2, dec + tn / 3600 / 2]], 0)[0])
        n = max(5, int(np.ceil(L * 3)))
        P = np.mean([_gauss_pix(x + (xe - x) * s, y + (ye - y) * s, sig, X, Y) for s in np.linspace(-1, 1, n)], 0)
    else:
        P = _gauss_pix(x, y, sig, X, Y)
    fit = (R <= r_fit + L / 2)
    good = fit & ~b
    if P[good].sum() < 0.6 * P[fit].sum():
        out["why"] = "masked"
        return out
    iv = 1.0 / u[good] ** 2
    den = np.sum(P[good] ** 2 * iv)
    f = np.sum(P[good] * (d[good] - bkg) * iv) / den
    e = 1.0 / np.sqrt(den)
    out.update(flux_dn=float(f), err_dn=float(e), snr=float(f / e), bkg=float(bkg), ok=True, trail_px=float(L))
    return out


def dn_to_ujy(dn, band, magzp):
    return F0_JY[band] * 1e6 * np.asarray(dn, float) * 10 ** (-0.4 * magzp)


def vega_mag(dn, magzp):
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(np.asarray(dn) > 0, magzp - 2.5 * np.log10(np.asarray(dn, float)), np.nan)


def robust_stack(flux, err, clip=3.0):
    """pilot R.robust_stack (sigma-clipped inverse-variance mean, MAD on chi) that also returns the keep mask.
    With 1-2 values: plain inverse-variance mean."""
    f, e = np.asarray(flux, float), np.asarray(err, float)
    m = np.isfinite(f) & np.isfinite(e) & (e > 0)
    keep = m.copy()
    if m.sum() == 0:
        return np.nan, np.nan, np.nan, 0, keep
    if m.sum() >= 3:
        for _ in range(5):
            ff, ee = f[keep], e[keep]
            med = np.median(ff)
            chi = (f - med) / e
            ck = chi[keep]
            s = 1.4826 * np.median(np.abs(ck - np.median(ck)))
            new = m & (np.abs(chi - np.median(ck)) <= clip * max(s, 1.0))
            if (new == keep).all():
                break
            keep = new
    w = 1 / e[keep] ** 2
    F = np.sum(w * f[keep]) / np.sum(w)
    E = 1 / np.sqrt(np.sum(w))
    return float(F), float(E), float(F / E), int(keep.sum()), keep


# ------------------------------------------------------------------------------------ geometry

def offset_radec(ra, dec, de_arcsec, dn_arcsec):
    return ra + de_arcsec / 3600 / np.cos(np.radians(dec)), dec + dn_arcsec / 3600


def sep_en(ra0, dec0, ra1, dec1):
    """(east, north) arcsec of (ra1, dec1) relative to (ra0, dec0), small-angle."""
    return (((ra1 - ra0 + 180) % 360 - 180) * np.cos(np.radians(dec0)) * 3600, (dec1 - dec0) * 3600)


def null_offsets(n=N_NULL):
    k = np.arange(n)
    ang = np.radians(k * 360 / n + 7.5)
    rad = 20 + 10 * (k % 4)  # 20, 30, 40, 50 arcsec
    return np.c_[rad * np.sin(ang), rad * np.cos(ang)]  # (east, north)


def utc_to_tdb(mjd_utc):
    return Time(np.atleast_1d(np.asarray(mjd_utc, dtype=float)), format="mjd", scale="utc").tdb.jd


def predict(desig, mjd_utc, n_samples=0):
    P = positions()
    jd = utc_to_tdb(mjd_utc)
    df = P.predict(desig, list(jd), observer="neowise", engine="kete", n_samples=n_samples)
    df["mjd_utc"] = np.atleast_1d(mjd_utc)
    return df


def elongation(df):
    """Solar elongation (deg) of the predicted positions as seen from WISE."""
    import kete
    out = []
    for jd, ra, dec in zip(df.jd_tdb, df.ra_deg, df.dec_deg):
        o = np.array(list(kete.spice.get_state("wise", jd).pos))  # heliocentric ecliptic AU
        s = -o / np.linalg.norm(o)
        v = np.array([np.cos(np.radians(dec)) * np.cos(np.radians(ra)), np.cos(np.radians(dec)) * np.sin(np.radians(ra)), np.sin(np.radians(dec))])
        ve = np.array([v[0], np.cos(OBLIQ) * v[1] + np.sin(OBLIQ) * v[2], -np.sin(OBLIQ) * v[1] + np.cos(OBLIQ) * v[2]])
        out.append(np.degrees(np.arccos(np.clip(np.dot(s, ve), -1, 1))))
    return np.array(out)


# ------------------------------------------------------------------------------- frame discovery

def hit_rows(desig):
    c = pd.read_csv(os.path.join(A4, "wise", "neowise_candidates_ranked.csv"))
    return c[(c.designation == desig) & c.strong].sort_values("mjd").reset_index(drop=True)


def visit_frames(desig, mjd_hit):
    """All NEOWISE-R frames within +-WINDOW_D of mjd_hit whose footprint should hold the predicted position.
    Sources: (1) A4 MOST table, (2) Gator frame-index cones along the predicted track at times when the
    solar elongation is within 3 deg of 90 (WISE always looks at ~90 deg). Returns DataFrame of candidates."""
    tg = mjd_hit + np.arange(-WINDOW_D, WINDOW_D + 1e-9, 0.01)
    trk = predict(desig, tg)
    trk["elong"] = elongation(trk)
    sel = trk[np.abs(trk.elong - 90) < 3.0]
    cones, cur = [], None
    for r in sel.itertuples():
        if cur is None or np.hypot(*sep_en(cur[0], cur[1], r.ra_deg, r.dec_deg)) > 0.25 * 3600:
            cur = (r.ra_deg, r.dec_deg)
            cones.append(cur)
    if not cones:  # elongation model excluded everything: still search around the track midpoint
        mid = trk.iloc[len(trk) // 2]
        cones.append((mid.ra_deg, mid.dec_deg))
    rows = []
    for ra, dec in cones:
        g = gator("neowiser_p1bs_frm", ra, dec, 0.85 * 3600)
        if len(g):
            rows.append(g[(g.mjd > mjd_hit - WINDOW_D) & (g.mjd < mjd_hit + WINDOW_D)])
    g = pd.concat(rows).drop_duplicates(["scan_id", "frame_num"]) if rows else pd.DataFrame(columns=["scan_id", "frame_num", "mjd", "ra", "dec"])
    most = pd.read_parquet(os.path.join(A4, "wise", "most_wise_frames.parquet"))
    most = most[(most.designation == desig) & (np.abs(most.mjd_obs - mjd_hit) < WINDOW_D)]
    m = most.drop_duplicates(["scan_id", "frame_num"])[["scan_id", "frame_num", "mjd_obs"]].rename(columns={"mjd_obs": "mjd"})
    m["in_most"] = True
    g = g[["scan_id", "frame_num", "mjd", "ra", "dec"]].copy()
    allf = pd.concat([g, m]).groupby(["scan_id", "frame_num"], as_index=False).agg(
        mjd=("mjd", "first"), ra_ctr=("ra", "first"), dec_ctr=("dec", "first"), in_most=("in_most", "any"))
    allf["in_most"] = allf.in_most.fillna(False).astype(bool)
    for c in ("mjd", "ra_ctr", "dec_ctr"):
        allf[c] = pd.to_numeric(allf[c], errors="coerce")
    pr = predict(desig, allf.mjd.values)
    allf["pred_ra"], allf["pred_dec"] = pr.ra_deg.values, pr.dec_deg.values
    allf["dist_ctr_deg"] = [np.hypot(*sep_en(a, b, c, d)) / 3600 if np.isfinite(a) else np.nan
                            for a, b, c, d in zip(allf.ra_ctr, allf.dec_ctr, allf.pred_ra, allf.pred_dec)]
    allf = allf[(allf.dist_ctr_deg < 0.56) | allf.in_most].sort_values("mjd").reset_index(drop=True)
    meta = dict(n_track_times=len(tg), n_track_times_elong_ok=int(len(sel)), n_gator_cones=len(cones),
                elong_range_deg=[float(trk.elong.min()), float(trk.elong.max())], n_most=int(len(m)),
                n_candidates=int(len(allf)))
    return allf, meta


# ------------------------------------------------------------------------------------- per target

def measure_paths(frames, pred, paths):
    """frames: list of frame dicts; pred: per-frame dict(ra, dec, te, tn); paths: {name: per-frame list of (ra, dec)}.
    Returns DataFrame path, i, flux_dn, err_dn, snr."""
    rows = []
    for name, pos in paths.items():
        for i, fr in enumerate(frames):
            ra, dec = pos[i]
            p = phot(fr, ra, dec, trail_arcsec=(pred[i]["te"], pred[i]["tn"]))
            rows.append(dict(path=name, i=i, band=fr["band"], flux_dn=p["flux_dn"], err_dn=p["err_dn"], snr=p["snr"]))
    return pd.DataFrame(rows)


def stack_paths(tab, band):
    out = {}
    for name, g in tab[tab.band == band].groupby("path", sort=False):
        F, E, S, n, keep = robust_stack(g.flux_dn.values, g.err_dn.values)
        out[name] = dict(flux_dn=F, err_dn=E, snr=S, n=n, keep=keep, idx=g.i.values)
    return out


def north_up(fr, ra, dec, half=60.0, scale=1.375):
    n = int(round(2 * half / scale)) + 1
    k = (n - 1) / 2
    j, i = np.mgrid[0:n, 0:n]
    de, dn = -(i - k) * scale, (j - k) * scale
    rr, dd = offset_radec(ra, dec, de.ravel(), dn.ravel())
    px, py = fr["wcs"].all_world2pix(np.c_[rr, dd], 0).T
    img = fr["img"].copy()
    good = ~fr["bad"]
    img = img - np.median(img[good])
    ix, iy = np.round(px).astype(int), np.round(py).astype(int)
    ny, nx = img.shape
    ins = (ix >= 0) & (ix < nx) & (iy >= 0) & (iy < ny)
    out = np.full(n * n, np.nan)
    ok = ins.copy()
    ok[ins] = good[iy[ins], ix[ins]]
    out[ok] = img[iy[ok], ix[ok]]
    return out.reshape(n, n)


def static_check(desig, slug, hit, n_visits=6):
    """Is there a static source at the catalog-hit position? Other-visit exposures (forced phot + stack),
    the NEOWISE single-exposure catalog at that spot over all epochs, AllWISE and CatWISE2020."""
    ra, dec, mjd = float(hit.ra), float(hit.dec), float(hit.mjd)
    res = dict(ra=ra, dec=dec, _label="MEASURED (archive pixels and catalogs); stacks COMPUTED")
    fr = gator("neowiser_p1bs_frm", ra, dec, 0.5 * 3600)
    fr = fr[(fr.dist < 0.36 * 3600) & (fr.qual_frame > 0)].copy()
    res["n_frames_all_epochs_covering"] = int(len(fr))
    other = fr[np.abs(fr.mjd - mjd) > 5].sort_values("mjd")
    vis = (other.mjd.diff().fillna(99) > 3).cumsum()
    other = other.assign(visit=vis.values)
    res["n_other_visits"] = int(other.visit.nunique())
    picks = []
    vids = other.visit.unique()
    for v in vids[np.unique(np.linspace(0, len(vids) - 1, min(n_visits, len(vids))).round().astype(int))] if len(vids) else []:
        picks.append(other[other.visit == v].sort_values("dist").iloc[0])
    table = []
    for band in (1, 2):
        f_, e_ = [], []
        for p in picks:
            fd = load_frame(p.scan_id, int(p.frame_num), band, ra, dec, 120, f"{slug}_static")
            if fd is None:
                continue
            ph = phot(fd, ra, dec)
            table.append(dict(band=f"W{band}", scan_id=p.scan_id, frame_num=int(p.frame_num), mjd=fd["mjd"], snr=ph["snr"],
                              flux_dn=ph["flux_dn"], err_dn=ph["err_dn"]))
            f_.append(ph["flux_dn"]); e_.append(ph["err_dn"])
        F, E, S, n, _ = robust_stack(f_, e_)
        res[f"W{band}_other_visit_stack"] = dict(snr=S, flux_dn=F, err_dn=E, n=n)
    res["other_visit_frames"] = table
    ps = gator("neowiser_p1bs_psd", ra, dec, 3.0)
    if len(ps):
        ps = ps[np.abs(ps.mjd - mjd) > 0.01]
    res["neowise_single_exposure_detections_within_3arcsec_other_epochs"] = int(len(ps))
    res["of_which_snr_ge_5_any_band"] = int(((ps.w1snr >= 5) | (ps.w2snr >= 5)).sum()) if len(ps) else 0
    for cat, key in (("allwise_p3as_psd", "allwise"), ("catwise_2020", "catwise2020")):
        try:
            g = gator(cat, ra, dec, 15.0)
            if len(g):
                g = g.sort_values("dist")
                r0 = g.iloc[0]
                w1 = next((r0[c] for c in ("w1mpro", "w1mpro_pm") if c in g.columns), np.nan)
                w2 = next((r0[c] for c in ("w2mpro", "w2mpro_pm") if c in g.columns), np.nan)
                res[key] = dict(nearest_arcsec=float(r0.dist), w1=float(w1) if np.isfinite(w1) else None,
                                w2=float(w2) if np.isfinite(w2) else None, n_within_15=int(len(g)))
            else:
                res[key] = dict(nearest_arcsec=None, n_within_15=0)
        except Exception as e:
            res[key] = dict(error=repr(e))
    near = [res[k].get("nearest_arcsec") for k in ("allwise", "catwise2020") if isinstance(res.get(k), dict)]
    cat_static = any(x is not None and x <= 3.0 for x in near)
    pix_static = any((res[f"W{b}_other_visit_stack"]["snr"] or 0) >= 3 for b in (1, 2))
    res["static"] = bool(cat_static or pix_static)
    res["static_rule"] = "static if an AllWISE/CatWISE2020 source lies within 3\" or the other-visit stack has S/N >= 3 in W1 or W2"
    return res


def chance_rate(hit, band, radius_arcsec):
    """Expected number of non-AllWISE single-exposure sources with SNR >= the hit SNR inside the search circle,
    from the source density in the hit's own exposure (Gator cone 600")."""
    g = gator("neowiser_p1bs_psd", float(hit.ra), float(hit.dec), 600.0)
    g = g[np.abs(g.mjd - float(hit.mjd)) < 1e-4]
    snr = float(getattr(hit, f"w{band}snr"))
    n_same = int(((g[f"w{band}snr"] >= snr) & g.allwise_cntr.isna()).sum()) if len(g) else 0
    area = np.pi * 600.0 ** 2
    lam = n_same / area * np.pi * radius_arcsec ** 2
    return dict(n_non_allwise_ge_snr_in_600arcsec=n_same, search_radius_arcsec=float(radius_arcsec),
                expected_in_search_circle=float(lam), p_at_least_one=float(1 - np.exp(-lam)),
                _label="MEASURED counts; rate COMPUTED (Poisson); frame-edge truncation ignored")


def expected_mag(t, pr_row):
    """ESTIMATED expected W1/W2 Vega magnitudes. Asteroids: S-type reflected + NEATM thermal (pv 0.15, eta 1.4).
    Comets: reflected solar colours from the SBDB M1/K1 total magnitude (coma as a point source)."""
    from . import brightness as B
    V = float(pr_row.vmag)
    out = {}
    for band in (1, 2):
        lam = WAVE[band]
        if t["comet"]:
            f = float(B.expected_ujy("comet", V, lam)[0])
            th = 0.0
        else:
            import kete
            H = positions()._fetch_props(t["desig"]).h_mag
            f = float(B.reflected_ujy(V, np.atleast_1d(lam), "stitched_S_0.45-5um")[0])
            th = float(B.neatm_ujy(lam, H, float(pr_row.r_au), float(pr_row.delta_au), float(pr_row.phase_deg)))
            out["H"] = float(H)
        out[f"W{band}"] = float(-2.5 * np.log10((f + th) / (F0_JY[band] * 1e6)))
        out[f"W{band}_thermal_fraction"] = float(th / (f + th))
        if not t["comet"]:  # model range: albedo 0.05-0.5, beaming eta 1.0-2.5
            mags = []
            for pv in (0.05, 0.15, 0.5):
                for eta in (1.0, 1.4, 2.5):
                    th2 = float(B.neatm_ujy(lam, H, float(pr_row.r_au), float(pr_row.delta_au), float(pr_row.phase_deg), pv=pv, eta=eta))
                    mags.append(-2.5 * np.log10((f + th2) / (F0_JY[band] * 1e6)))
            out[f"W{band}_range_pv0.05-0.5_eta1.0-2.5"] = [float(min(mags)), float(max(mags))]
    out["V_pred"] = V
    out["_label"] = "ESTIMATED"
    return out


def orbit_check(desig, hit, sigma=1.0):
    OF = orbitfit()
    P = positions()
    obs = OF.fetch_obs(desig)
    f0 = OF.fit(obs)
    jd = float(utc_to_tdb(float(hit.mjd))[0])
    new = OF.add_precovery(obs, [(jd, float(hit.ra), float(hit.dec), sigma, "neowise")])
    f1 = OF.fit(new, initial_state=f0.state)

    def resid(fit):
        p = P.predict(desig, [jd], observer="neowise", state=fit.state, n_samples=0).iloc[0]
        e, n = sep_en(p.ra_deg, p.dec_deg, float(hit.ra), float(hit.dec))
        return float(e), float(n)

    r0, r1 = resid(f0), resid(f1)
    first = min(o.epoch.jd for o in obs)
    last = max(o.epoch.jd for o in obs)
    return dict(n_obs_mpc=len(obs), n_used_before=int(sum(f0.included)), n_used_after=int(sum(f1.included)),
                rms_before=float(f0.rms), rms_after=float(f1.rms), converged_after=bool(f1.converged),
                neowise_point_included=bool(list(f1.included)[-1]),
                neowise_resid_before_fit_arcsec=dict(east=r0[0], north=r0[1], total=float(np.hypot(*r0))),
                neowise_resid_after_fit_arcsec=dict(east=r1[0], north=r1[1], total=float(np.hypot(*r1))),
                sigma_used_arcsec=sigma, arc_days_before=float(last - first), arc_days_after=float(last - min(first, jd)),
                arc_extension_days=float(max(0.0, first - jd)),
                rms_note="kete OrbitFit.rms (weighted, MPC obs with EFCC18 debias / station weights)",
                _label="COMPUTED (kete least-squares fit)")


def run_target(slug):
    t = TARGETS[slug]
    desig = t["desig"]
    od = os.path.join(OUT, slug)
    os.makedirs(od, exist_ok=True)
    hits = hit_rows(desig)
    mjd_hit = float(hits.mjd.mean())
    pb = t["primary"]
    print(f"[{slug}] hits {len(hits)} mjd {mjd_hit:.4f}", flush=True)

    # predicted position + 3-sigma at the hit time (kete covariance, Horizons cross-check)
    pr_hit = predict(desig, [float(h) for h in hits.mjd], n_samples=200)
    try:
        hz = positions().predict(desig, list(pr_hit.jd_tdb), observer="neowise", engine="horizons")
    except Exception as e:
        print(f"[{slug}] horizons failed {e!r}"[:300])
        hz = pd.DataFrame(dict(ra_deg=[np.nan] * len(pr_hit), dec_deg=[np.nan] * len(pr_hit)))
    pred_info = []
    for k, h in hits.iterrows():
        p = pr_hit.iloc[k]
        e, n = sep_en(p.ra_deg, p.dec_deg, h.ra, h.dec)
        ang = np.radians(p.pa_major_deg)
        a_ = e * np.sin(ang) + n * np.cos(ang)
        b_ = e * np.cos(ang) - n * np.sin(ang)
        mahal3 = np.hypot(a_ / max(p.sigma_major_3s_arcsec, 1e-3), b_ / max(p.sigma_minor_3s_arcsec, 1e-3))
        s_cat = 3 * np.hypot(h.sigra, h.sigdec) / np.sqrt(2)  # 3-sigma catalog position error (per axis, mean)
        mahal3c = np.hypot(a_ / np.hypot(p.sigma_major_3s_arcsec, s_cat), b_ / np.hypot(p.sigma_minor_3s_arcsec, s_cat))
        hze, hzn = sep_en(p.ra_deg, p.dec_deg, hz.ra_deg.iloc[k], hz.dec_deg.iloc[k])
        pred_info.append(dict(source_id=h.source_id, mjd=float(h.mjd), iso=str(h.date_utc), hit_ra=float(h.ra), hit_dec=float(h.dec),
                              pred_ra=float(p.ra_deg), pred_dec=float(p.dec_deg), hit_offset_east=float(e), hit_offset_north=float(n),
                              hit_offset_arcsec=float(np.hypot(e, n)), sigma3_major=float(p.sigma_major_3s_arcsec),
                              sigma3_minor=float(p.sigma_minor_3s_arcsec), pa_major=float(p.pa_major_deg),
                              hit_in_units_of_3sigma_ellipse=float(mahal3), hit_in_units_of_3sigma_ellipse_incl_catalog_error=float(mahal3c), horizons_minus_kete_arcsec=float(np.hypot(hze, hzn)),
                              rate_arcsec_per_s=float(np.hypot(p.dra_cosdec_deg_per_day, p.ddec_deg_per_day) * 3600 / 86400),
                              cat_w1=float(h.w1mpro), cat_w1snr=float(h.w1snr), cat_w2=float(h.w2mpro), cat_w2snr=float(h.w2snr),
                              delta_au=float(p.delta_au), r_au=float(p.r_au), phase_deg=float(p.phase_deg)))
    print(f"[{slug}] pred", json.dumps(pred_info, default=float)[:600], flush=True)

    # frames of the visit
    cand, fmeta = visit_frames(desig, mjd_hit)
    cand.to_csv(os.path.join(od, "visit_frame_candidates.csv"), index=False)
    print(f"[{slug}] candidate frames {len(cand)} {fmeta}", flush=True)
    size = 200
    frames, pred = [], []
    for c in cand.itertuples():
        for band in (1, 2):
            fd = load_frame(c.scan_id, c.frame_num, band, c.pred_ra, c.pred_dec, size, slug)
            if fd is None:
                continue
            x, y = fd["wcs"].all_world2pix([[c.pred_ra, c.pred_dec]], 0)[0]
            ny, nx = fd["img"].shape
            if not (2 <= x <= nx - 3 and 2 <= y <= ny - 3):
                continue
            frames.append(fd)
    # exact per-exposure predictions at the header mid-times (+ rates for trailing)
    mj = np.array([f["mjd"] for f in frames])
    pr = predict(desig, mj)
    for f, p in zip(frames, pr.itertuples()):
        te = p.dra_cosdec_deg_per_day * 3600 * EXPTIME_S / 86400
        tn = p.ddec_deg_per_day * 3600 * EXPTIME_S / 86400
        pred.append(dict(ra=p.ra_deg, dec=p.dec_deg, te=te, tn=tn, rate=np.hypot(p.dra_cosdec_deg_per_day, p.ddec_deg_per_day) * 3600 / 86400))
    nb = {b: sum(f["band"] == b for f in frames) for b in (1, 2)}
    print(f"[{slug}] frames with position inside: W1 {nb[1]} W2 {nb[2]}", flush=True)

    # paths
    paths = {"target": [(p["ra"], p["dec"]) for p in pred]}
    for j, (de, dn) in enumerate(null_offsets()):
        paths[f"null{j:02d}"] = [offset_radec(p["ra"], p["dec"], de, dn) for p in pred]
    for k, h in enumerate(pred_info):  # path shifted by the catalog hit's offset
        paths[f"hitoffset{k}"] = [offset_radec(p["ra"], p["dec"], h["hit_offset_east"], h["hit_offset_north"]) for p in pred]
    # time-shifted paths (kete at t + dt): FWHM units of along-track displacement, plus fixed days
    rate_med = float(np.median([p["rate"] for p in pred]))  # arcsec/s
    shifts = {f"shift{u:+d}fwhm": u * FWHM[pb] / rate_med / 86400 for u in SHIFT_UNITS if u != 0}
    shifts.update({f"shift{d:+.2f}d": d for d in SHIFT_DAYS})
    shifts = {k: v for k, v in shifts.items() if abs(v * rate_med * 86400) < size / 2 - 20}
    for name, dt in shifts.items():
        ps = predict(desig, mj + dt)
        paths[name] = list(zip(ps.ra_deg, ps.dec_deg))
    tab = measure_paths(frames, pred, paths)

    # hit-position photometry in the hit exposure (catalog position, fixed)
    hit_phot = []
    for k, h in hits.iterrows():
        for i, f in enumerate(frames):
            if f["scan"] == h.scan_id and f["frame"] == int(h.frame_num):
                ph_hit = phot(f, h.ra, h.dec, trail_arcsec=(pred[i]["te"], pred[i]["tn"]))
                ph_pred = phot(f, pred[i]["ra"], pred[i]["dec"], trail_arcsec=(pred[i]["te"], pred[i]["tn"]))
                ph_pt = phot(f, h.ra, h.dec)
                hit_phot.append(dict(source_id=h.source_id, band=f"W{f['band']}", snr_at_hit_trailed=ph_hit["snr"],
                                     snr_at_hit_point_psf=ph_pt["snr"], snr_at_prediction=ph_pred["snr"],
                                     flux_ujy_at_hit=float(dn_to_ujy(ph_hit["flux_dn"], f["band"], f["magzp"])),
                                     mag_at_hit=float(vega_mag(ph_hit["flux_dn"], f["magzp"])),
                                     lim5_mag=float(vega_mag(5 * ph_hit["err_dn"], f["magzp"])),
                                     trail_px=ph_hit.get("trail_px", 0.0)))

    # stacks per band + controls
    stacks = {}
    for band in (1, 2):
        if nb[band] == 0:
            continue
        st = stack_paths(tab, band)
        tg = st["target"]
        nl = np.array([v["snr"] for k, v in st.items() if k.startswith("null")])
        nl = nl[np.isfinite(nl)]
        nm, ns = (float(nl.mean()), float(nl.std())) if len(nl) else (np.nan, np.nan)
        kk = max(1.0, ns) if np.isfinite(ns) else 1.0
        curve = []
        for name, dt in sorted(shifts.items(), key=lambda kv: kv[1]):
            curve.append(dict(name=name, dt_days=float(dt), along_track_arcsec=float(dt * rate_med * 86400), snr=st[name]["snr"]))
        curve.append(dict(name="zero", dt_days=0.0, along_track_arcsec=0.0, snr=tg["snr"]))
        curve.sort(key=lambda c: c["dt_days"])
        far = [c["snr"] for c in curve if abs(c["along_track_arcsec"]) >= FWHM[band] and np.isfinite(c["snr"])]
        stacks[f"W{band}"] = dict(
            n_exposures=int(nb[band]), n_used=int(tg["n"]), snr_raw=tg["snr"], flux_dn=tg["flux_dn"], err_dn=tg["err_dn"],
            mag=float(vega_mag(tg["flux_dn"], np.median([f["magzp"] for f in frames if f["band"] == band]))),
            null_n=int(len(nl)), null_mean=nm, null_std=ns, null_max=float(nl.max()) if len(nl) else np.nan,
            snr_scaled=float((tg["snr"] - (nm if np.isfinite(nm) else 0)) / kk),
            null_exceed=int(np.sum(nl >= tg["snr"])) if np.isfinite(tg["snr"]) else None,
            hitoffset_paths={k: dict(snr=v["snr"], n=v["n"]) for k, v in st.items() if k.startswith("hitoffset")},
            time_shift_curve=curve,
            shift_peak_at_zero=bool(len(far) > 0 and np.isfinite(tg["snr"]) and tg["snr"] > max(far)),
            _label="MEASURED per-exposure fluxes; stack, null statistics and scaling COMPUTED")
        # hit-offset path without the hit exposure itself (independent confirmation)
        for k, h in hits.iterrows():
            g = tab[(tab.band == band) & (tab.path == f"hitoffset{k}")]
            m = np.array([not (frames[i]["scan"] == h.scan_id and frames[i]["frame"] == int(h.frame_num)) for i in g.i])
            F, E, S, n, _ = robust_stack(g.flux_dn.values[m], g.err_dn.values[m])
            stacks[f"W{band}"]["hitoffset_paths"][f"hitoffset{k}"]["snr_excluding_hit_exposure"] = S
            stacks[f"W{band}"]["hitoffset_paths"][f"hitoffset{k}"]["n_excluding_hit_exposure"] = n
        stacks[f"W{band}"]["_keep"] = dict(zip(tg["idx"].tolist(), tg["keep"].tolist()))

    # positional consistency: S/N map of stacked forced photometry on a grid of constant sky offsets
    pos = {}
    s3 = max(h["sigma3_major"] for h in pred_info)
    R_s = max(15.0, s3 + 6.0)
    grid = np.arange(-R_s, R_s + 1e-6, 1.0 if R_s <= 20 else 1.5)
    bf = [i for i, f in enumerate(frames) if f["band"] == pb]
    if bf:
        def smap(idx):
            best = (-np.inf, 0, 0)
            for de in grid:
                for dn in grid:
                    if np.hypot(de, dn) > R_s:
                        continue
                    fl, er = [], []
                    for i in idx:
                        ra, dec = offset_radec(pred[i]["ra"], pred[i]["dec"], de, dn)
                        p = phot(frames[i], ra, dec, trail_arcsec=(pred[i]["te"], pred[i]["tn"]))
                        fl.append(p["flux_dn"]); er.append(p["err_dn"])
                    S = robust_stack(fl, er)[2]
                    if np.isfinite(S) and S > best[0]:
                        best = (S, de, dn)
            return best
        S, de, dn = smap(bf)
        ph = pred_info[0]
        ang = np.radians(ph["pa_major"])
        a_ = de * np.sin(ang) + dn * np.cos(ang)
        b_ = de * np.cos(ang) - dn * np.sin(ang)
        pos = dict(band=f"W{pb}", search_radius_arcsec=R_s, peak_snr=float(S), peak_offset_east=float(de), peak_offset_north=float(dn),
                   peak_offset_arcsec=float(np.hypot(de, dn)),
                   peak_in_units_of_3sigma_ellipse=float(np.hypot(a_ / max(ph["sigma3_major"], 1e-3), b_ / max(ph["sigma3_minor"], 1e-3))),
                   _label="COMPUTED (peak of stacked forced-photometry S/N over constant sky offsets)")
        if len(bf) >= 4:
            h1, h2 = bf[: len(bf) // 2], bf[len(bf) // 2:]
            S1, e1, n1 = smap(h1)
            S2, e2, n2 = smap(h2)
            pos.update(first_half=dict(snr=float(S1), east=float(e1), north=float(n1)), second_half=dict(snr=float(S2), east=float(e2), north=float(n2)),
                       halves_offset_difference_arcsec=float(np.hypot(e1 - e2, n1 - n2)))
        else:
            pos["halves"] = "not possible: fewer than 4 exposures"

    # static checks, chance coincidence, expected brightness, orbit
    static = [static_check(desig, slug, h) for h in hits.itertuples()]
    chance = []
    for h in hits.itertuples():
        bh = 2 if h.w2snr >= h.w1snr else 1
        chance.append(dict(source_id=h.source_id, band=f"W{bh}", **chance_rate(h, bh, float(h.radius_used_arcsec))))
    exp_mag = expected_mag(t, pr_hit.iloc[0])
    orbit = None
    if slug == "2015sa":
        orbit = {}
        for sgm in (1.0, 1.5):
            try:
                orbit[f"sigma_{sgm}"] = orbit_check(desig, hits.iloc[0], sigma=sgm)
            except Exception as e:
                orbit[f"sigma_{sgm}"] = dict(error=repr(e))

    # PNGs (W1 and W2; one stretch per object and band for the single exposures, one for the stack)
    cut = {}
    frame_png = {}
    for band in (1, 2):
        idx = [i for i, f in enumerate(frames) if f["band"] == band]
        if not idx:
            continue
        cuts = [north_up(frames[i], pred[i]["ra"], pred[i]["dec"]) for i in idx]
        v = np.concatenate([c[np.isfinite(c)] for c in cuts])
        med, mad = np.median(v), 1.4826 * np.median(np.abs(v - np.median(v)))
        lo, hi = med - 3 * mad, med + 10 * mad
        os.makedirs(os.path.join(od, "frames"), exist_ok=True)
        for i, c in zip(idx, cuts):
            name = f"frames/{frames[i]['scan']}{frames[i]['frame']:03d}_w{band}.png"
            IM.save(c, os.path.join(od, name), lo, hi, upscale=5)
            frame_png[i] = name
        keep = stacks[f"W{band}"]["_keep"]
        use = [c for i, c in zip(idx, cuts) if keep.get(i, False)] or cuts
        stk = IM.clipped_mean(use) if len(use) >= 3 else np.nanmean(use, 0)
        sv = stk[np.isfinite(stk)]
        smed, smad = np.median(sv), 1.4826 * np.median(np.abs(sv - np.median(sv)))
        IM.save(stk, os.path.join(od, f"stack_w{band}.png"), smed - 3 * smad, smed + 10 * smad, upscale=5)
        cut[f"W{band}"] = dict(png=f"stack_w{band}.png", n=len(use), frame_stretch_dn=[float(lo), float(hi)])
    # per-exposure table + site records
    rows = []
    for i, f in enumerate(frames):
        g = tab[(tab.path == "target") & (tab.i == i)].iloc[0]
        keep = stacks[f"W{f['band']}"]["_keep"].get(i, False)
        rows.append(dict(key=f["key"], scan_id=f["scan"], frame_num=f["frame"], mjd=round(f["mjd"], 7), iso=f["iso"], band=f"W{f['band']}",
                         wavelength_um=WAVE[f["band"]], pred_ra=round(pred[i]["ra"], 7), pred_dec=round(pred[i]["dec"], 7),
                         flux=float(dn_to_ujy(g.flux_dn, f["band"], f["magzp"])), flux_err=float(dn_to_ujy(g.err_dn, f["band"], f["magzp"])),
                         flux_dn=g.flux_dn, err_dn=g.err_dn, snr=g.snr, mag=float(vega_mag(g.flux_dn, f["magzp"])),
                         lim5_mag=float(vega_mag(5 * g.err_dn, f["magzp"])), trail_arcsec=float(np.hypot(pred[i]["te"], pred[i]["tn"])),
                         magzp=f["magzp"], used=bool(keep), png=frame_png.get(i), survey="NEOWISE"))
    ft = pd.DataFrame(rows).sort_values(["mjd", "band"])
    ft.to_csv(os.path.join(od, "exposures.csv"), index=False)
    tab.to_csv(os.path.join(od, "paths_photometry.csv"), index=False)
    for v in stacks.values():
        v.pop("_keep", None)
    res = dict(slug=slug, designation=desig, survey="NEOWISE", generated=time.strftime("%Y-%m-%d %H:%M"),
               hits=pred_info, hits_label="catalog values MEASURED (A4 Gator); predictions ESTIMATED (kete SBDB orbit, observer WISE)",
               frame_search=fmeta, exposures_in_visit=nb, single_frame_at_hit=hit_phot,
               single_frame_label="MEASURED (forced Gaussian PSF on L1b int/unc/msk; trailed when motion in 7.7 s > 1 px); flux in uJy uses MAGZP + Vega F0, no aperture/colour correction (ESTIMATED calibration)",
               stacks=stacks, position=pos, static=static, chance_coincidence=chance, expected_brightness=exp_mag, orbit=orbit,
               stack_png=cut, frames_csv="exposures.csv")
    res["verdict"], res["verdict_reasons"] = decide(res, t)
    with open(os.path.join(od, "result.json"), "w") as fh:
        json.dump(_clean(res), fh, indent=1)
    print(f"[{slug}] verdict {res['verdict']}: {res['verdict_reasons']}", flush=True)
    return res


def decide(res, t):
    pb = f"W{t['primary']}"
    s = res["stacks"].get(pb, {})
    n = s.get("n_exposures", 0)
    snr = s.get("snr_scaled", np.nan)
    checks = dict(
        multi_exposure=n >= 2,
        snr_ge_5=bool(np.isfinite(snr) and snr >= 5),
        nulls_below=bool(s.get("null_exceed", 1) == 0),
        time_shift_peak_at_zero=bool(s.get("shift_peak_at_zero")),
        not_static=not any(st["static"] for st in res["static"]),
        position_consistent=bool(res["position"].get("peak_in_units_of_3sigma_ellipse", 99) <= 1.0
                                 and res["position"].get("halves_offset_difference_arcsec", 99) <= 4.0),
        hit_recurs_in_other_exposures=bool(any((v.get("snr_excluding_hit_exposure") or 0) >= 3 for v in s.get("hitoffset_paths", {}).values())),
        hit_inside_ellipse=bool(all(h["hit_in_units_of_3sigma_ellipse_incl_catalog_error"] <= 1.0 for h in res["hits"])),
        **{"chance_p_lt_0.01": bool(all(c["p_at_least_one"] < 0.01 for c in res["chance_coincidence"]))},
        brightness_plausible=bool(abs(res["expected_brightness"].get(pb, 99) - min(h[f"cat_{pb.lower()}"] for h in res["hits"])) < 2.0),
    )
    if res.get("orbit"):
        o = res["orbit"].get("sigma_1.0", {})
        checks["orbit_ok"] = bool(o.get("neowise_point_included") and o.get("neowise_resid_after_fit_arcsec", {}).get("total", 99) < 3.0)
    core = ["multi_exposure", "snr_ge_5", "nulls_below", "time_shift_peak_at_zero", "not_static", "position_consistent"]
    if all(checks[k] for k in core) and checks.get("orbit_ok", True):
        v = "CONFIRMED-LIKELY"
    elif checks["not_static"] and (checks["snr_ge_5"] or checks["hit_recurs_in_other_exposures"] or (np.isfinite(snr) and snr >= 3.5)
                                   or (s.get("snr_raw", 0) >= 3 and checks["hit_inside_ellipse"] and checks["chance_p_lt_0.01"])):
        v = "HINT"
    else:
        v = "NOT_SUPPORTED"
    return v, checks


def _clean(o):
    if isinstance(o, dict):
        return {str(k): _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    if isinstance(o, (np.floating, float)):
        return None if not np.isfinite(o) else round(float(o), 4)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, np.ndarray):
        return _clean(o.tolist())
    return o


# --------------------------------------------------------------------------------------- website

def neowise_frames_for_site(slug):
    """Per-exposure records for the website object page (from a finished run), plus stack PNG and verdict.
    PNG paths are relative to OUT/<slug>/."""
    slug = slugify(slug) if slug not in TARGETS else slug
    od = os.path.join(OUT, slug)
    fn = os.path.join(od, "result.json")
    if not os.path.exists(fn):
        return None
    res = json.load(open(fn))
    ft = pd.read_csv(os.path.join(od, "exposures.csv"))
    keys = ["key", "mjd", "iso", "band", "wavelength_um", "pred_ra", "pred_dec", "flux", "flux_err", "snr", "used", "png", "survey"]
    frames = []
    for r in ft[keys].to_dict("records"):
        r = {k: (None if isinstance(v, float) and not np.isfinite(v) else v) for k, v in r.items()}
        r["used"] = bool(r["used"])
        frames.append(r)
    pb = f"W{TARGETS[slug]['primary']}"
    st = res["stacks"].get(pb, {})
    return dict(frames=frames, flux_unit="uJy (ESTIMATED calibration)", base_dir=od,
                stack_png=res["stack_png"].get(pb, {}).get("png"), stack_png_all={k: v["png"] for k, v in res["stack_png"].items()},
                stack_band=pb, stack_snr=st.get("snr_scaled"), verdict=res["verdict"], verdict_checks=res["verdict_reasons"])


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for s in (sys.argv[1:] or list(TARGETS)):
        run_target(s)
