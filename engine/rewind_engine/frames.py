"""Step 2: which SPHEREx frames saw the object, and where exactly it was (as seen from SPHEREx).

MOST (IRSA, catalog=spherex) finds the frames; Horizons with CENTER=500@-163182 gives the
astrometric RA/Dec, rates, magnitude and the 3-sigma plane-of-sky error ellipse at the header
mid-time MJD-AVG = MJD-BEG + 57.56 s."""
from __future__ import annotations

import os
import time

import numpy as np
import pandas as pd
from astropy.time import Time

from . import config as C
from .pilot import R

SPHEREX_START = "2025-04-01"
TODAY = "2026-11-14"
HZ_QUANT = "1,3,9,19,20,36,37"


def iso_to_mjd(iso: str) -> float:
    return float(Time(iso[:10]).mjd)


def mjd_to_iso(mjd: float, full: bool = False) -> str:
    t = Time(float(mjd), format="mjd")
    return t.isot[:19] if full else t.isot[:10]


def obj_dir(slug: str) -> str:
    d = os.path.join(C.WORK, "objects", slug)
    os.makedirs(d, exist_ok=True)
    return d


def window(obj) -> tuple[str, str]:
    """MOST search window. Precovery: SPHEREx start to discovery. Lost: whole SPHEREx era
    (frames inside the observed arc are dropped later). Known: whole era."""
    if obj.role == "precovery" and isinstance(obj.disc_iso, str):
        end = min(obj.disc_iso, TODAY)
        return SPHEREX_START, end
    return SPHEREX_START, TODAY


def most_frames(obj) -> pd.DataFrame:
    d = obj_dir(obj.slug)
    b, e = window(obj)
    cache = os.path.join(d, "most.tbl")
    if b >= e:
        return pd.DataFrame()
    try:
        df = R.most_query(obj.most_name, b, e, cache=cache)
    except Exception as ex:  # MOST returns an error page if nothing is found or the name is unknown
        open(os.path.join(d, "most_error.txt"), "w").write(str(ex)[:2000])
        return pd.DataFrame()
    if len(df) == 0:
        return df
    df["mjd_avg"] = df.mjd_start.astype(float) + C.MJD_AVG_OFFSET_S / 86400.0
    df["det"] = df.productid.astype(str)
    if obj.role == "precovery" and isinstance(obj.disc_iso, str):
        df = df[df.mjd_start < iso_to_mjd(obj.disc_iso)]
    return df.drop_duplicates("file").sort_values("mjd_avg").reset_index(drop=True)


def horizons_at(obj, mjd) -> pd.DataFrame:
    # unique times only: the 6 detectors of an exposure share MJD-AVG, and a TLIST chunk of identical times
    # makes Horizons fail ("Bad dates -- start must be earlier than stop")
    mjd = np.asarray(mjd, float)
    u, inv = np.unique(mjd, return_inverse=True)
    e = R.horizons_ephem(obj.hz_cmd, u, center=R.SPHEREX_CENTER, quantities=HZ_QUANT)
    if len(e) < len(u):
        raise RuntimeError(f"Horizons returned {len(e)} of {len(u)} times")
    e = e.iloc[inv].reset_index(drop=True)
    e["mjd_utc"] = mjd
    ren = {"dRA*cosD": "rate_ra", "d(DEC)/dt": "rate_dec", "T-mag": "mag", "APmag": "mag",
           "SMAA_3sig": "smaa3", "SMIA_3sig": "smia3", "Theta": "theta", "r": "r_au", "delta": "delta_au"}
    e = e.rename(columns={k: v for k, v in ren.items() if k in e.columns})
    for c in ["mag", "smaa3", "smia3", "theta", "rate_ra", "rate_dec"]:
        if c not in e:
            e[c] = np.nan
        e[c] = pd.to_numeric(e[c], errors="coerce")
    return e[["mjd_utc", "ra", "dec", "rate_ra", "rate_dec", "mag", "r_au", "delta_au", "smaa3", "smia3", "theta"]]


def rank_frames(fr: pd.DataFrame, obj, cap: int = C.MAX_FRAMES) -> pd.DataFrame:
    """Keep the ~cap most useful frames: closest to discovery (or to the observed arc for lost
    objects) and predicted brightest. score = mag + log10(1 + dt/5 d)."""
    m = fr["mag"].fillna(30.0).values
    if obj.role == "precovery" and isinstance(obj.disc_iso, str):
        dt = iso_to_mjd(obj.disc_iso) - fr.mjd_avg.values
    elif obj.role == "lost":
        lo, hi = iso_to_mjd(obj.earliest_obs_iso), iso_to_mjd(obj.last_obs_iso) + 1
        inside = (fr.mjd_avg.values >= lo) & (fr.mjd_avg.values <= hi)
        dt = np.where(fr.mjd_avg.values > hi, fr.mjd_avg.values - hi, lo - fr.mjd_avg.values)
        m = np.where(inside, m + 5, m)  # inside the arc adds no new information
    else:
        dt = np.zeros(len(fr))
    fr = fr.assign(score=m + np.log10(1 + np.clip(dt, 0, None) / 5.0), dt_ref_days=dt)
    keep = fr.nsmallest(cap, "score") if len(fr) > cap else fr
    return keep.sort_values("mjd_avg").reset_index(drop=True)


def stamp_half(sigma3_px: float, trail_px: float) -> int:
    need = max(24.0, (sigma3_px if np.isfinite(sigma3_px) else 0) + 14, trail_px / 2 + 14)
    return int(min(64, np.ceil(need)))


def prepare(obj, cap: int = C.MAX_FRAMES, max_ephem: int = 1500) -> pd.DataFrame:
    """MOST + Horizons -> frames.csv (one row per detector file kept for photometry)."""
    d = obj_dir(obj.slug)
    out = os.path.join(d, "frames.csv")
    if os.path.exists(out):
        return pd.read_csv(out)
    fr = most_frames(obj)
    if len(fr) == 0:
        pd.DataFrame().to_csv(out, index=False)
        return pd.DataFrame()
    fr["n_most_total"] = len(fr)
    if len(fr) > max_ephem:  # pre-thin by time distance to the reference date before asking Horizons
        tmp = rank_frames(fr.assign(mag=0.0), obj, cap=max_ephem)
        fr = fr[fr.file.isin(tmp.file)].reset_index(drop=True)
    eph = horizons_at(obj, fr.mjd_avg.values)
    eph.index = fr.index[: len(eph)]
    fr = fr.iloc[: len(eph)].copy()
    for c in eph.columns:
        if c != "mjd_utc":
            fr["pred_" + c if c in ("ra", "dec") else c] = eph[c].values
    fr = rank_frames(fr, obj, cap)
    rate = np.hypot(fr.rate_ra, fr.rate_dec)  # arcsec/hour
    fr["rate_arcsec_hr"] = rate
    fr["trail_px"] = rate * C.EXPTIME_S / 3600.0 / C.PIX_ARCSEC
    fr["sigma_px"] = fr.smaa3 / 3.0 / C.PIX_ARCSEC  # 1-sigma major axis in pixels
    fr["half"] = [stamp_half(3 * s, t) for s, t in zip(fr.sigma_px, fr.trail_px)]
    fr["iso"] = [mjd_to_iso(m, True) for m in fr.mjd_avg]
    cols = ["file", "uri", "release", "observationid", "det", "mjd_start", "mjd_avg", "iso", "pred_ra", "pred_dec", "ra_obj",
            "dec_obj", "rate_ra", "rate_dec", "rate_arcsec_hr", "trail_px", "mag", "r_au", "delta_au", "smaa3", "smia3",
            "theta", "sigma_px", "half", "score", "dt_ref_days", "n_most_total"]
    fr = fr[[c for c in cols if c in fr.columns]]
    fr.to_csv(out, index=False)
    return fr
