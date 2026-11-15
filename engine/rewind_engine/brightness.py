"""Expected brightness at each SPHEREx wavelength (used to weight frames in the stack, and to plant
fakes of the right brightness). All numbers from here are ESTIMATED (model).

reflected(V, lam): solar colours (pilot table) x a reflectance template from the composition
library (data/06-composition, normalised at 0.55 um).
thermal(...): NEATM-like (Harris 1998) - subsolar temperature from r, eta, bond albedo; Planck
emission integrated over the visible dayside."""
from __future__ import annotations

import functools
import os

import numpy as np
import pandas as pd

from . import config as C
from .pilot import R

H_PLANCK, C_LIGHT, K_B, SIGMA_SB = 6.62607015e-34, 2.99792458e8, 1.380649e-23, 5.670374419e-8
AU_M = 1.495978707e11
S_SUN = 1361.0


def ab_to_ujy(ab):
    return 3631e6 * 10 ** (-0.4 * np.asarray(ab, float))


def ujy_to_ab(f):
    f = np.asarray(f, float)
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(f > 0, -2.5 * np.log10(f / 3631e6), np.nan)


@functools.lru_cache(maxsize=None)
def templates(kind: str = "cent") -> pd.DataFrame:
    """Rows = template_id, columns = channel centre wavelength (um)."""
    d = os.path.join(C.DATA, "06-composition", "derived")
    ch = pd.read_csv(os.path.join(d, "spherex_channels.csv"))
    t = pd.read_csv(os.path.join(d, f"spherex_templates_{kind}.csv")).set_index("template_id")
    t.columns = ch.center_um.values[: t.shape[1]]
    return t


def template_curve(tid: str, lam_um):
    """Reflectance of template tid at lam (flat extrapolation outside its coverage)."""
    if tid in (None, "solar"):
        return np.ones_like(np.asarray(lam_um, float))
    row = templates().loc[tid]
    x, v = row.index.values.astype(float), row.values.astype(float)
    m = np.isfinite(v)
    return np.interp(lam_um, x[m], v[m])


def reflected_ujy(V, lam_um, tid="stitched_S_0.45-5um"):
    lam = np.asarray(lam_um, float)
    ab = np.array([R.expected_ab_reflected(v, l) for v, l in zip(np.broadcast_to(V, lam.shape), lam)])
    r55 = template_curve(tid, np.array([0.55]))[0] if tid not in (None, "solar") else 1.0
    return ab_to_ujy(ab) * template_curve(tid, lam) / r55


def planck_nu(lam_um, T):
    lam = np.asarray(lam_um, float)[..., None] * 1e-6
    nu = C_LIGHT / lam
    with np.errstate(over="ignore"):
        return 2 * H_PLANCK * nu ** 3 / C_LIGHT ** 2 / np.expm1(H_PLANCK * nu / (K_B * T))


def diameter_km(H, pv):
    return 1329.0 / np.sqrt(pv) * 10 ** (-H / 5.0)


def neatm_ujy(lam_um, H, r_au, delta_au, phase_deg, pv=0.15, G=0.15, eta=1.4, eps=0.9, n=40):
    """Thermal flux density (uJy) at lam from a NEATM sphere (nightside cold)."""
    D = diameter_km(H, pv) * 1e3
    A = (0.290 + 0.684 * G) * pv
    Tss = ((1 - A) * S_SUN / (eta * eps * SIGMA_SB * r_au ** 2)) ** 0.25
    lat = (np.arange(n) + 0.5) / n * np.pi - np.pi / 2
    lon = (np.arange(2 * n) + 0.5) / (2 * n) * 2 * np.pi - np.pi
    LA, LO = np.meshgrid(lat, lon, indexing="ij")
    cos_sun = np.cos(LA) * np.cos(LO)  # sub-solar point at lon=0
    a = np.radians(phase_deg)
    cos_obs = np.cos(LA) * np.cos(LO - a)
    dA = (D / 2) ** 2 * np.cos(LA) * (np.pi / n) * (np.pi / n)
    m = (cos_sun > 0) & (cos_obs > 0)
    T = Tss * np.clip(cos_sun[m], 0, None) ** 0.25
    w = cos_obs[m] * dA[m]
    B = planck_nu(lam_um, T)  # (..., npix)
    F = eps * np.sum(B * w, axis=-1) / (delta_au * AU_M) ** 2  # W m-2 Hz-1
    return F * 1e26 * 1e6  # uJy


def phase_from(r_au, delta_au, r_obs_au=1.0):
    c = (r_au ** 2 + delta_au ** 2 - r_obs_au ** 2) / (2 * r_au * delta_au)
    return float(np.degrees(np.arccos(np.clip(c, -1, 1))))


def expected_ujy(kind, V, lam_um, H=None, r_au=None, delta_au=None, pv=0.15, tid=None):
    """Predicted flux density per frame. Comets: solar colours only (dust); asteroids: S-like
    reflectance + NEATM thermal when H, r, delta are known."""
    lam = np.atleast_1d(np.asarray(lam_um, float))
    V = np.broadcast_to(np.asarray(V, float), lam.shape)
    if kind == "comet":
        return reflected_ujy(V, lam, None)
    out = reflected_ujy(V, lam, tid or "stitched_S_0.45-5um")
    if H is not None and np.isfinite(H) and r_au is not None:
        r = np.broadcast_to(np.asarray(r_au, float), lam.shape)
        d = np.broadcast_to(np.asarray(delta_au, float), lam.shape)
        th = np.array([neatm_ujy(l, H, ri, di, phase_from(ri, di), pv=pv)
                       if np.isfinite(ri) and np.isfinite(di) else 0.0 for l, ri, di in zip(lam, r, d)])
        out = out + np.nan_to_num(th)
    return out
