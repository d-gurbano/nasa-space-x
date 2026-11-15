"""Static website data that does not depend on the Rewind search: orbit dots for the 3D scene,
planet elements, and the five challenge-star pages (DATA-CONTRACT sections 2, 3, 6).

Orbits: MPCORB (asteroids) + MPC CometEls.txt (comets) + the new-since-2025-04-01 list, all mean
anomalies moved to one common epoch, MJD 61200.0 (JD 2461200.5, 2026-06-09), the MPCORB epoch of
99.9% of its rows. Comets with e >= 1 keep a = q/(1-e) < 0 and M = hyperbolic mean anomaly.
Stars: SPHEREx 21x21 stamps resampled north up, east left (nearest neighbour), one stretch per star."""
from __future__ import annotations

import glob
import json
import os
import warnings

import numpy as np
import pandas as pd

from . import config as C

K_DEG = np.degrees(0.01720209895)  # Gauss constant, deg/day for a = 1 AU
EPOCH_MJD = 61200.0
JD_MJD = 2400000.5
FIELDS = ["a", "e", "i", "node", "peri", "M", "H", "flag"]
FLAG_BITS = {"1": "neo", "2": "pha", "4": "new_since_2025", "8": "comet", "16": "in_rewind"}
NEO_Q = 1.3


# ---------------------------------------------------------------- orbits

def mean_motion(a):
    """Mean motion (deg/day) from semi-major axis (AU); |a| so hyperbolic orbits work too."""
    return K_DEG / np.abs(np.asarray(a, float)) ** 1.5


def propagate_M(M, n, epoch_mjd, to_mjd, e=None):
    """M + n*dt (deg). Elliptic results wrapped to [0, 360); hyperbolic (e >= 1) left unwrapped."""
    M = np.asarray(M, float) + np.asarray(n, float) * (to_mjd - np.asarray(epoch_mjd, float))
    ell = np.ones_like(M, bool) if e is None else np.asarray(e, float) < 1
    return np.where(ell, np.mod(M, 360.0), M)


def flag_bits(q, pha, new, comet, rewind):
    """Combine boolean arrays into the contract flag integer."""
    q = np.asarray(q, float)
    return ((q < NEO_Q) * 1 | np.asarray(pha, bool) * 2 | np.asarray(new, bool) * 4
            | np.asarray(comet, bool) * 8 | np.asarray(rewind, bool) * 16).astype(int)


def mpc_key(name):
    """'(1) Ceres' -> '1', '2020 OF5' -> '2020 OF5' (same style as JPL pdes)."""
    s = pd.Series(name, dtype=str)
    return s.str.extract(r"^\((\d+)\)")[0].fillna(s).values


def read_mpcorb():
    p = os.path.join(C.DATA, "07-answer-keys", "orbits", "mpcorb_parsed.parquet")
    cols = ["name", "H", "M", "peri_arg", "node", "incl", "ecc", "n", "a", "flags_hex", "epoch_jd", "q"]
    d = pd.read_parquet(p, columns=cols)
    flags = d.flags_hex.fillna("0").apply(lambda s: int(s, 16)).values
    n = d.n.where(d.n > 0, pd.Series(mean_motion(d.a), index=d.index))
    return pd.DataFrame({
        "key": mpc_key(d.name), "a": d.a, "e": d.ecc, "i": d.incl, "node": d.node, "peri": d.peri_arg,
        "M": propagate_M(d.M, n, d.epoch_jd - JD_MJD, EPOCH_MJD, d.ecc), "H": d.H, "q": d.q,
        "pha": (flags & 0x8000) > 0, "comet": False})


def _peri_mjd(y, m, d):
    t = pd.to_datetime(pd.DataFrame({"year": y, "month": m, "day": np.floor(d).astype(int)}))
    return (t - pd.Timestamp("1858-11-17")).dt.days.values + (d - np.floor(d))


def read_comets(path=None):
    """MPC CometEls.txt (fixed width, 1-based cols: Tp 15-29, q 31-39, e 42-49, peri 52-59,
    node 62-69, i 72-79, H 92-95, designation/name 103-158)."""
    path = path or os.path.join(C.ORBITS, "mpc", "CometEls.txt")
    if not os.path.exists(path):
        print("comets: missing", path)
        return None
    rows = []
    for ln in open(path, encoding="utf-8", errors="replace"):
        try:
            rows.append(dict(y=int(ln[14:18]), m=int(ln[19:21]), d=float(ln[22:29]), q=float(ln[30:39]),
                             e=float(ln[41:49]), peri=float(ln[51:59]), node=float(ln[61:69]),
                             i=float(ln[71:79]), H=float(ln[91:95] or "nan"),
                             key=ln[102:158].split(" (")[0].strip()))
        except ValueError:
            continue
    c = pd.DataFrame(rows)
    return comet_frame(c.key, c.q, c.e, c.i, c.node, c.peri, _peri_mjd(c.y, c.m, c.d), c.H)


def comet_frame(key, q, e, i, node, peri, tp_mjd, H):
    """Comet rows with a = q/(1-e) and M = n*(t - Tp) at EPOCH_MJD."""
    q, e = np.asarray(q, float), np.asarray(e, float)
    a = q / (1 - e)
    M = propagate_M(0.0, mean_motion(a), tp_mjd, EPOCH_MJD, e)
    return pd.DataFrame({"key": list(key), "a": a, "e": e, "i": i, "node": node, "peri": peri, "M": M,
                         "H": H, "q": q, "pha": False, "comet": True})


def read_new():
    """Objects found since 2025-04-01 (JPL SBDB rows with discovery dates)."""
    p = os.path.join(C.TARGETS, "clean", "new_objects_since_2025-04-01.parquet")
    if not os.path.exists(p):
        print("new objects: missing", p)
        return None
    return pd.read_parquet(p)


def new_as_rows(n):
    """Own-element rows for new objects (used when MPC files lack them)."""
    com = n.kind.str.startswith("c").values
    key = np.where(com, n.full_name.str.split(" (", regex=False).str[0], n.pdes)
    a = n.a.where(n.a.notna(), n.q / (1 - n.e))
    e_mjd = n.epoch - JD_MJD
    ast = pd.DataFrame({"key": key, "a": a, "e": n.e, "i": n.i, "node": n.om, "peri": n.w,
                        "M": propagate_M(n.ma, mean_motion(a), e_mjd, EPOCH_MJD, n.e),
                        "H": n.H.where(n.H.notna(), n.M1), "q": n.q, "pha": n.pha.eq("Y").values,
                        "comet": com})
    ok = ast.M.notna() | com
    tp = comet_frame(key, n.q, n.e, n.i, n.om, n.w, n.tp - JD_MJD, ast.H)
    ast.loc[com, "M"] = tp.M.values[com]
    return ast[ok & ast.a.notna()]


def special_phas():
    p = os.path.join(C.TARGETS, "lists", "special_phas.csv")
    return set(pd.read_csv(p).pdes.astype(str)) if os.path.exists(p) else set()


def build_orbits(mpc, comets, new, mba_sample=10000, rewind_desigs=(), seed=2026, pha_keys=()):
    """Select rows (all NEOs, comets, new objects, + random main belt) and set flags."""
    parts = [mpc] + ([comets] if comets is not None else [])
    allr = pd.concat(parts, ignore_index=True).drop_duplicates("key")
    new_keys = set()
    if new is not None and len(new):
        nr = new_as_rows(new)
        new_keys = set(nr.key)
        allr = pd.concat([allr, nr[~nr.key.isin(set(allr.key))]], ignore_index=True)
        allr.loc[allr.key.isin(set(nr.key[nr.pha])), "pha"] = True
    allr["new"] = allr.key.isin(new_keys)
    allr.loc[allr.key.isin(set(pha_keys)), "pha"] = True
    keep = (allr.q < NEO_Q) | allr.comet | allr.new | allr.pha
    mba = allr[~keep & (allr.a > 1.8) & (allr.a < 5.5) & (allr.e < 1)]
    pick = mba.sample(min(mba_sample, len(mba)), random_state=seed).index
    out = allr[keep | allr.index.isin(pick)].copy()
    out["flag"] = flag_bits(out.q, out.pha, out.new, out.comet, out.key.isin(set(rewind_desigs)))
    return out.reset_index(drop=True)


def orbit_rows(df):
    """Rounded [a,e,i,node,peri,M,H,flag] lists (NaN H -> null)."""
    r = lambda x, k: np.round(np.asarray(x, float), k)
    cols = [r(df.a, 4), r(df.e, 4), r(df.i, 2), r(df.node, 2), r(df.peri, 2), r(df.M, 2), r(df.H, 1)]
    rows = []
    for vals in zip(*cols, df.flag.astype(int)):
        rows.append([None if (isinstance(v, float) and not np.isfinite(v)) else
                     (int(v) if isinstance(v, (int, np.integer)) else float(v)) for v in vals])
    return rows


def rewind_rows(df, rewind):
    """Make sure every Rewind object has a row (append it from its JPL SBDB orbit if missing), set the in_rewind
    bit, and return (df, {slug: row index})."""
    from . import objects as O
    from .site import sbdb_facts
    slugs = {}
    for o in rewind.itertuples():
        cand = {o.desig, o.desig.replace("C/", "").replace("P/", ""), o.name}
        hit = df.index[df.key.isin(cand)]
        if len(hit):
            i = int(hit[0])
        else:
            facts, orb = sbdb_facts(O.sbdb_record(o.desig), o)
            if orb.get("a") is None or orb.get("epoch_mjd") is None:
                continue
            a, e = orb["a"], orb["e"]
            n = 0.9856076686 / abs(a) ** 1.5
            M = float(propagate_M(orb["M"] or 0.0, n, orb["epoch_mjd"], EPOCH_MJD, e))
            H = facts.get("H") if facts.get("H") is not None else facts.get("M1")
            row = dict(key=o.desig, a=a, e=e, i=orb["i"], node=orb["node"], peri=orb["peri"], M=M, H=H, q=orb["q"],
                       pha=bool(facts.get("pha")), new=False, comet=o.kind == "comet" or "/" in o.desig)
            row["flag"] = int(flag_bits(np.array([row["q"]]), np.array([row["pha"]]), np.array([False]),
                                        np.array([row["comet"]]), np.array([True]))[0])
            df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
            i = len(df) - 1
        df.loc[i, "flag"] = int(df.loc[i, "flag"]) | 16
        slugs[o.slug] = i
    return df, slugs


def write_orbits(site_dir=C.SITE, rewind_desigs=(), mba_sample=10000, rewind=None):
    """site/orbits.json + orbits.bin + orbits.bin.json (with "slugs": {slug: row index} for Rewind objects)."""
    os.makedirs(site_dir, exist_ok=True)
    df = build_orbits(read_mpcorb(), read_comets(), read_new(), mba_sample, rewind_desigs,
                      pha_keys=special_phas())
    slugs = {}
    if rewind is not None:
        df, slugs = rewind_rows(df, rewind)
    meta = {"schema": "rewind-orbits-v1", "epoch_mjd": EPOCH_MJD, "epoch_iso": "2026-06-09",
            "fields": FIELDS, "flag_bits": FLAG_BITS, "slugs": slugs,
            "note": "neo = q < 1.3 AU; pha = MPCORB flag 0x8000 or JPL pha; comets with e >= 1 have "
                    "a < 0 and hyperbolic M; main belt rows are a random sample; H null if unknown"}
    with open(os.path.join(site_dir, "orbits.json"), "w") as f:
        json.dump({**meta, "rows": orbit_rows(df)}, f, separators=(",", ":"))
    arr = df[FIELDS].to_numpy(np.float32)
    arr.tofile(os.path.join(site_dir, "orbits.bin"))
    with open(os.path.join(site_dir, "orbits.bin.json"), "w") as f:
        json.dump({"rows": len(df), "fields": FIELDS, "dtype": "float32", "order": "row-major",
                   "epoch_mjd": EPOCH_MJD, "flag_bits": FLAG_BITS, "slugs": slugs}, f, indent=1)
    print(f"orbits: {len(df)} rows; neo {(df.flag & 1 > 0).sum()}, pha {(df.flag & 2 > 0).sum()}, "
          f"new {(df.flag & 4 > 0).sum()}, comet {(df.flag & 8 > 0).sum()}")
    return df


# ---------------------------------------------------------------- planets

# JPL SSD "Approximate Positions of the Planets", Table 1 (1800 AD - 2050 AD), E.M. Standish.
# name: (a, e, I, L, long.peri, long.node) at J2000, then rates per Julian century.
PLANETS = {
    "Mercury": ((0.38709927, 0.20563593, 7.00497902, 252.25032350, 77.45779628, 48.33076593),
                (0.00000037, 0.00001906, -0.00594749, 149472.67411175, 0.16047689, -0.12534081)),
    "Venus": ((0.72333566, 0.00677672, 3.39467605, 181.97909950, 131.60246718, 76.67984255),
              (0.00000390, -0.00004107, -0.00078890, 58517.81538729, 0.00268329, -0.27769418)),
    "Earth": ((1.00000261, 0.01671123, -0.00001531, 100.46457166, 102.93768193, 0.0),
              (0.00000562, -0.00004392, -0.01294668, 35999.37244981, 0.32327364, 0.0)),
    "Mars": ((1.52371034, 0.09339410, 1.84969142, -4.55343205, -23.94362959, 49.55953891),
             (0.00001847, 0.00007882, -0.00813131, 19140.30268499, 0.44441088, -0.29257343)),
    "Jupiter": ((5.20288700, 0.04838624, 1.30439695, 34.39644051, 14.72847983, 100.47390909),
                (-0.00011607, -0.00013253, -0.00183714, 3034.74612775, 0.21252668, 0.20469106)),
    "Saturn": ((9.53667594, 0.05386179, 2.48599187, 49.95424423, 92.59887831, 113.66242448),
               (-0.00125060, -0.00050991, 0.00193609, 1222.49362201, -0.41897216, -0.28867794)),
    "Uranus": ((19.18916464, 0.04725744, 0.77263783, 313.23810451, 170.95427630, 74.01692503),
               (-0.00196176, -0.00004397, -0.00242939, 428.48202785, 0.40805281, 0.04240589)),
    "Neptune": ((30.06992276, 0.00859048, 1.77004347, -55.12002969, 44.96476227, 131.78422574),
                (0.00026291, 0.00005105, 0.00035372, 218.45945325, -0.32241464, -0.00508664)),
}
ELEMS = ["a", "e", "I", "L", "long_peri", "long_node"]


def solve_kepler(M_rad, e, n_iter=30):
    E = M_rad + e * np.sin(M_rad)
    for _ in range(n_iter):
        E = E - (E - e * np.sin(E) - M_rad) / (1 - e * np.cos(E))
    return E


def planet_xyz(name, mjd):
    """Heliocentric ecliptic J2000 position (AU) from the JPL Table 1 elements."""
    el0, rate = PLANETS[name]
    T = (np.asarray(mjd, float) + JD_MJD - 2451545.0) / 36525.0
    a, e, I, L, wbar, node = (x0 + r * T for x0, r in zip(el0, rate))
    w, M = np.radians(wbar - node), np.radians(np.mod(L - wbar + 180, 360) - 180)
    I, node = np.radians(I), np.radians(node)
    E = solve_kepler(M, e)
    xp, yp = a * (np.cos(E) - e), a * np.sqrt(1 - e * e) * np.sin(E)
    cw, sw, cO, sO, cI, sI = np.cos(w), np.sin(w), np.cos(node), np.sin(node), np.cos(I), np.sin(I)
    x = (cw * cO - sw * sO * cI) * xp + (-sw * cO - cw * sO * cI) * yp
    y = (cw * sO + sw * cO * cI) * xp + (-sw * sO + cw * cO * cI) * yp
    z = (sw * sI) * xp + (cw * sI) * yp
    return np.array([x, y, z])


def write_planets(site_dir=C.SITE):
    os.makedirs(site_dir, exist_ok=True)
    out = {
        "schema": "rewind-planets-v1",
        "source": "JPL SSD Approximate Positions of the Planets, Table 1 (Standish)",
        "url": "https://ssd.jpl.nasa.gov/planets/approx_pos.html",
        "valid": "1800 AD to 2050 AD", "epoch": "J2000 (JD 2451545.0)",
        "units": {"a": "AU", "e": "1", "angles": "deg", "rates": "per Julian century"},
        "how_to_use": "T = (JD - 2451545.0)/36525; each element = value + rate*T. M = L - long_peri, "
                      "omega = long_peri - long_node; solve Kepler E - e sin E = M; x' = a(cos E - e), "
                      "y' = a sqrt(1-e^2) sin E; rotate by omega, I, long_node to ecliptic J2000.",
        "spherex": "SPHEREx is in low Earth orbit; draw it at Earth's position",
        "planets": [{"name": k, "note": "Earth-Moon barycenter" if k == "Earth" else None,
                     **dict(zip(ELEMS, v[0])), "rates": dict(zip(ELEMS, v[1]))}
                    for k, v in PLANETS.items()],
    }
    with open(os.path.join(site_dir, "planets.json"), "w") as f:
        json.dump(out, f, indent=1)
    return out


# ---------------------------------------------------------------- stars

TT = os.path.join(C.DATA, "05-test-targets")
# pm (mas/yr): Gaia DR3, except WISE 0855 (Kirkpatrick 2021 via SIMBAD); as read in 05-test-targets/REPORT.md
STARS = {
    "barnard": dict(folder="barnard", name="Barnard's Star", pmra=-801.551, pmdec=10362.394,
                    pm_source="Gaia DR3"),
    "wise0855": dict(folder="wise0855", name="WISE 0855-0714", pmra=-8123.7, pmdec=673.2,
                     pm_source="Kirkpatrick et al. 2021 (via SIMBAD)"),
    "epsindib": dict(folder="eps_indi_b", name="Epsilon Indi B", pmra=3981.977, pmdec=-2466.832,
                     pm_source="Gaia DR3"),
    "rwaur": dict(folder="rw_aur", name="RW Aurigae", pmra=2.641, pmdec=-27.398, pm_source="Gaia DR3 (A)"),
    "rdra": dict(folder="r_dra", name="R Draconis", pmra=-20.643, pmdec=6.149, pm_source="Gaia DR3"),
}
OUT_ARCSEC, HALF_ARCSEC, MAX_PX, N_FRAMES = 1.5, 45.0, 512, 40


def _fmt(x):
    return f"{x:.1f}" if x >= 1 else f"{x:.2g}"


def motion_caption(pmra, pmdec):
    asec = np.hypot(pmra, pmdec) / 1000.0
    return f"Moves {_fmt(asec)} arcsec per year, about {_fmt(asec / C.PIX_ARCSEC)} pixels per year"


def out_wcs(ra, dec, scale=OUT_ARCSEC, half=HALF_ARCSEC):
    """North-up TAN grid, RA increasing to the left (east left)."""
    from astropy.wcs import WCS
    n = int(round(2 * half / scale)) + 1
    w = WCS(naxis=2)
    w.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    w.wcs.crval = [ra, dec]
    w.wcs.crpix = [(n + 1) / 2, (n + 1) / 2]
    w.wcs.cdelt = [-scale / 3600, scale / 3600]
    return w, n


def north_up(img, wcs_in, wcs_out, n):
    """Nearest-neighbour resample; returned row 0 = north (top of the PNG)."""
    yy, xx = np.mgrid[0:n, 0:n]
    ra, dec = wcs_out.pixel_to_world_values(xx, yy)
    px, py = wcs_in.world_to_pixel_values(ra, dec)
    ix, iy = np.rint(px).astype(int), np.rint(py).astype(int)
    ok = (ix >= 0) & (ix < img.shape[1]) & (iy >= 0) & (iy < img.shape[0])
    out = np.full((n, n), np.nan)
    out[ok] = img[iy[ok], ix[ok]]
    return out[::-1]


def png_xy(wcs_out, n, k, ra, dec):
    """Star position in PNG pixels (origin top-left, x right, y down)."""
    x, y = wcs_out.world_to_pixel_values(ra, dec)
    return [round(float((x + 0.5) * k), 1), round(float((n - 1 - y + 0.5) * k), 1)]


def save_png(a, lo, hi, k, path):
    """Shared sqrt stretch, NaN -> black, saturated (+inf) -> white, integer nearest-neighbour upscale."""
    from PIL import Image
    v = np.sqrt(np.clip((np.nan_to_num(a, nan=lo, posinf=hi) - lo) / max(hi - lo, 1e-12), 0, 1))
    im = np.kron((v * 255).astype(np.uint8), np.ones((k, k), np.uint8))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    Image.fromarray(im, "L").save(path)


def iso(mjd, date_only=False):
    from astropy.time import Time
    s = Time(float(mjd), format="mjd", scale="utc").isot[:19]
    return s[:10] if date_only else s + "Z"


def star_frames(folder):
    """All stamps of one target with pass number. results/phot_passes.csv lists every stamp (the
    stamps/<t>_index.csv files miss later additions); fall back to the index + 20-day gaps."""
    pp = os.path.join(TT, "results", f"{folder}_phot_passes.csv")
    p = os.path.join(TT, "stamps", f"{folder}_index.csv")
    if os.path.exists(pp):
        ix = pd.read_csv(pp).rename(columns={"mjd": "mjd_avg"})
        ix["file"] = [os.path.join(TT, f) for f in ix.file]
    elif os.path.exists(p):
        ix = pd.read_csv(p)
        ix = ix[ix.status == "ok"]
    else:
        return None
    ix = ix[ix.file.apply(os.path.exists)].sort_values("mjd_avg").reset_index(drop=True)
    if "pass" not in ix or ix["pass"].isna().any():
        ix["pass"] = np.cumsum(np.r_[0, np.diff(ix.mjd_avg) > 20])
    return ix


def load_stamp(path):
    """Background-subtracted image; masked pixels with the OVERFLOW flag (bit 1, saturated) -> +inf."""
    from astropy.io import fits
    from astropy.wcs import WCS
    with warnings.catch_warnings(), fits.open(path) as h:
        warnings.simplefilter("ignore")
        img = h[0].data.astype(float)
        img -= np.nanmedian(img)
        img[np.isnan(img) & (h["FLAGS"].data & 2 > 0)] = np.inf
        return img, WCS(h[0].header)


def stack_snr(folder):
    """sqrt(sum snr^2) over measured frames (inverse-variance combination), or None."""
    p = os.path.join(TT, "results", f"{folder}_phot.csv")
    if not os.path.exists(p):
        return None
    ph = pd.read_csv(p)
    s = ph.snr.where(ph.snr.notna(), ph.get("w_snr")).astype(float)
    s = s[np.isfinite(s) & (s > 0)]
    return round(float(np.sqrt((s ** 2).sum())), 1) if len(s) else None


def star_note(slug, sm, n_frames):
    if "meas_shift_arcsec" in sm and slug in ("barnard", "wise0855", "epsindib"):
        return (f"Between {sm['first_pass']} and {sm['last_pass']} SPHEREx measured a shift of "
                f"{sm['meas_shift_arcsec']:.1f} arcsec, against {sm['pred_shift_arcsec']:.1f} arcsec "
                f"predicted from the catalogue proper motion.")
    if slug == "rwaur":
        return ("RW Aur barely moves (under 0.03 arcsec per year); what SPHEREx shows is a young "
                "T Tauri star whose brightness changes from pass to pass.")
    if slug == "rdra":
        return (f"R Dra is a Mira variable near the ecliptic pole, so SPHEREx sees it almost every "
                f"month; it is saturated in {sm.get('n_saturated', '?')} of {sm.get('n_frames', n_frames)} "
                f"frames, so these pictures show its glow, not precise brightness.")
    return "SPHEREx pictures of this star across its passes."


def write_star(slug, site_dir=C.SITE, n_frames=N_FRAMES):
    """site/stars/<slug>/manifest.json and its PNGs."""
    s = STARS[slug]
    ix = star_frames(s["folder"])
    if ix is None or not len(ix):
        print(f"stars: {slug} has no stamps, skipped")
        return None
    out_dir = os.path.join(site_dir, "stars", slug)
    for old in glob.glob(os.path.join(out_dir, "*", "*.png")):
        os.remove(old)
    ra0, dec0 = float(ix.pred_ra.mean()), float(ix.pred_dec.mean())
    w_out, n = out_wcs(ra0, dec0)
    k = MAX_PX // n
    cube = np.array([north_up(*load_stamp(f), w_out, n) for f in ix.file])
    lo, hi = np.percentile(cube[np.isfinite(cube)], [1.0, 99.7])

    seasons = []
    for i, (p, g) in enumerate(ix.groupby("pass")):
        rel = f"seasons/s{i:02d}.png"
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            save_png(np.nanmedian(cube[g.index], 0), lo, hi, k, os.path.join(out_dir, rel))
        seasons.append({"iso": iso(g.mjd_avg.median(), True), "n_frames": len(g), "png": rel})

    pick = np.unique(np.linspace(0, len(ix) - 1, min(n_frames, len(ix))).round().astype(int))
    frames = []
    for j, i in enumerate(pick):
        r, rel = ix.iloc[i], f"frames/f{j:03d}.png"
        save_png(cube[i], lo, hi, k, os.path.join(out_dir, rel))
        frames.append({"iso": iso(r.mjd_avg), "mjd": round(float(r.mjd_avg), 6),
                       "wavelength_um": round(float(r.wave_um), 4), "detector": int(r.detector),
                       "png": rel, "pred_xy": png_xy(w_out, n, k, r.pred_ra, r.pred_dec)})

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        save_png(np.nanmedian(cube, 0), lo, hi, k, os.path.join(out_dir, "stack.png"))
    sp = os.path.join(TT, "results", f"{s['folder']}_summary.json")
    sm = json.load(open(sp)) if os.path.exists(sp) else {}
    man = {"slug": slug, "name": s["name"], "ra": round(ra0, 6), "dec": round(dec0, 6),
           "radec_note": "mean predicted position over the SPHEREx frames (PNG centre)",
           "pm": {"pmra_mas_yr": s["pmra"], "pmdec_mas_yr": s["pmdec"],
                  "total_mas_yr": round(float(np.hypot(s["pmra"], s["pmdec"])), 1), "source": s["pm_source"]},
           "image": {"arcsec_per_png_px": round(OUT_ARCSEC / k, 4), "size_px": n * k,
                     "orientation": "north up, east left", "stretch": "sqrt, shared p1-p99.7 of all frames; saturated pixels white, no-data black",
                     "spherex_pixel_arcsec": C.PIX_ARCSEC},
           "seasons": seasons, "frames": frames, "n_frames_total": len(ix),
           "stack": {"png": "stack.png", "snr": stack_snr(s["folder"]), "n_frames": len(ix),
                     "snr_method": "sqrt(sum of per-frame SNR^2) from results/phot.csv"},
           "motion_caption": motion_caption(s["pmra"], s["pmdec"]),
           "note": star_note(slug, sm, len(ix))}
    with open(os.path.join(out_dir, "manifest.json"), "w") as f:
        json.dump(man, f, indent=1)
    print(f"stars: {slug} {len(ix)} stamps, {len(seasons)} seasons, {len(frames)} frames")
    return man


def write_stars(site_dir=C.SITE):
    return {slug: write_star(slug, site_dir) for slug in STARS}


def write_static(site_dir=C.SITE, rewind_desigs=(), rewind=None):
    write_orbits(site_dir, rewind_desigs, rewind=rewind)
    write_planets(site_dir)
    write_stars(site_dir)
