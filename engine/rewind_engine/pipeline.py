"""Steps 4-5: measure one object on its saved stamps, run every control, decide the verdict.

Per frame: (trailed) ePSF forced photometry at the predicted position, at 24 null offsets and
at along-track shifted positions; the same on the static-sky reference stamps (other epoch,
closest wavelength) so every path also gets a sky-subtracted flux; planted fakes on the
null paths for the injection test.
Stacks: sigma-clipped, colour-weighted (each frame weighted by its expected relative flux s_i,
so the stack amplitude A is "fraction of the predicted flux"). Errors are scaled by the
null-path spread."""
from __future__ import annotations

import glob
import json
import os
import time

import numpy as np
import pandas as pd

from . import brightness as B
from . import config as C
from . import fetch as FE
from . import phot as PH
from .pilot import R

N_NULL = 24
SHIFT_UNITS = [-4, -3, -2, -1, 0, 1, 2, 3, 4]
INJ_DMAG = [-1.0, 0.0, 0.5, 1.0, 1.5, 2.0, 3.0]
N_INJ_PATHS = 12
DAY_POS_SNR = 2.0


def null_offsets_px(half, L, n=N_NULL, seed=7):
    """(dx, dy) pixel offsets for null paths that keep the fit box and annulus inside the stamp."""
    rmin = max(4.0, L / 2 + 4)
    rmax = max(rmin + 1, half - 12 - L / 2 - 1)
    rng = np.random.default_rng(seed)
    ang = np.linspace(0, 2 * np.pi, n, endpoint=False) + rng.uniform(0, 0.25, n)
    rad = rng.uniform(rmin, rmax, n)
    return np.c_[rad * np.cos(ang), rad * np.sin(ang)]


def pix_to_radec(st, x, y):
    r, d = st.wcs.all_pix2world([[x, y]], 0)[0]
    return float(r), float(d)


def robust_amp(f, e, s, clip=3.0):
    """Clipped colour-weighted amplitude: stack of f/s with errors e/s (w = s^2/e^2)."""
    f, e, s = (np.asarray(a, float) for a in (f, e, s))
    m = np.isfinite(f) & np.isfinite(e) & (e > 0) & np.isfinite(s) & (s > 0)
    if m.sum() < 3:
        return np.nan, np.nan, np.nan, int(m.sum())
    return R.robust_stack(f[m] / s[m], e[m] / s[m], clip=clip)


REF_MIN_PX = dict(comet=40.0, asteroid=5.0)  # the object must have moved this far between target and reference
_PLANS = {}


def _ref_dt(slug):
    if slug not in _PLANS:
        p = os.path.join(C.WORK, "objects", slug, "refs_plan.csv")
        pl = pd.read_csv(p) if os.path.exists(p) and os.path.getsize(p) > 5 else pd.DataFrame()
        _PLANS[slug] = {FE.stamp_path(slug, a, "ref", b): d for a, b, d in zip(pl.get("file", []), pl.get("ref_file", []),
                                                                             pl.get("dt_days", []))}
    return _PLANS[slug]


def load_refs(slug, file, rate_arcsec_hr=None, comet=False, trail_px=0.0):
    """Static-sky reference stamps of a frame. With a rate, references taken while the object was closer than
    40 px (comets: coma) or 5 px + trail (asteroids) to the target spot are skipped."""
    base = FE.stamp_path(slug, file, "ref", "X").rsplit("__", 1)[0]
    dts = _ref_dt(slug)
    need = REF_MIN_PX["comet" if comet else "asteroid"] + (0 if comet else trail_px)
    out = []
    for p in sorted(glob.glob(base + "__*.fits")):
        if rate_arcsec_hr is not None and p in dts and np.isfinite(dts[p]):
            if abs(dts[p]) * 24 * rate_arcsec_hr / C.PIX_ARCSEC < need:
                continue
        try:
            out.append(R.load_stamp_fits(p))
        except Exception:  # noqa
            pass
    return out


def measure_frame(slug, r, kind, H, inj_base_ujy):
    """All photometry for one frame. Returns (row dict, list of path rows)."""
    p = FE.stamp_path(slug, r.file)
    st = R.load_stamp_fits(p)
    ra, dec = r.pred_ra, r.pred_dec
    trail = PH.trail_vector_px(st, ra, dec, r.rate_ra, r.rate_dec)
    L = float(np.hypot(*trail))
    half = (st.image.shape[0] - 1) // 2
    x0, y0 = st.wcs.all_world2pix([[ra, dec]], 0)[0]
    lam, bw = PH.wavelength(st, ra, dec)
    s_exp = float(B.expected_ujy(kind, r.mag, [lam], H=H, r_au=r.r_au, delta_au=r.delta_au)[0]) if np.isfinite(lam) else np.nan
    refs = load_refs(slug, r.file, r.rate_arcsec_hr, kind == "comet", L)
    row = dict(file=r.file, mjd=r.mjd_avg, iso=r.iso, det=r.det, wave_um=lam, bw_um=bw, trail_px=L, mag_pred=r.mag,
               sigma_px=r.sigma_px, s_exp_ujy=s_exp, n_refs=len(refs), x=x0, y=y0, half=half)
    paths = []

    def measure(kind_, idx, rr, dd, image=None):
        q = PH.phot(st, rr, dd, trail, image=image)
        rec = dict(file=r.file, path=kind_, idx=idx, status=q.get("status"), flux=q.get("flux"), err=q.get("err"))
        if q.get("status") == "ok" and refs:
            fr = [PH.phot(s2, rr, dd, trail) for s2 in refs]
            fr = [x for x in fr if x.get("status") == "ok"]
            if fr:
                rf = np.array([x["flux"] for x in fr])
                re_ = np.array([x["err"] for x in fr])
                rec.update(ref_flux=float(np.median(rf)), ref_err=float(1.2533 * np.median(re_) / np.sqrt(len(fr))) if len(fr) > 1
                           else float(re_[0]))
        if kind_ == "target":
            rec.update({k: q.get(k) for k in ("chi2", "flag_center", "flag_or", "bkg", "bkg_std", "snr")})
        return rec

    paths.append(measure("target", 0, ra, dec))
    nul = null_offsets_px(half, L)
    null_pos = []
    for j, (dx, dy) in enumerate(nul):
        rr, dd = pix_to_radec(st, x0 + dx, y0 + dy)
        null_pos.append((rr, dd))
        paths.append(measure("null", j, rr, dd))
    # along-track shifts: unit = max(1.5 px, trail length), positions extrapolated with the sky rate
    unit = max(1.5, L)
    rate_px_hr = r.rate_arcsec_hr / C.PIX_ARCSEC
    for k in SHIFT_UNITS:
        if k == 0:
            continue
        shift_px = k * unit
        if abs(shift_px) > half - 12 - L / 2 - 1:
            continue
        dt_hr = shift_px / max(rate_px_hr, 1e-6)
        rr, dd = R.offset_radec(ra, dec, r.rate_ra * dt_hr, r.rate_dec * dt_hr)
        rec = measure("shift", k, rr, dd)
        rec["dt_days"] = dt_hr / 24
        paths.append(rec)
    # injection: plant the predicted flux (x 10^(-0.4 dmag)) on the first N_INJ_PATHS null paths
    if np.isfinite(s_exp):
        for j in range(min(N_INJ_PATHS, len(null_pos))):
            rr, dd = null_pos[j]
            for dm in INJ_DMAG:
                f_in = s_exp * 10 ** (-0.4 * dm)
                img = PH.plant(st, rr, dd, f_in, trail)
                rec = measure("inj", j, rr, dd, image=img)
                rec.update(dmag=dm, f_in=f_in)
                paths.append(rec)
    return row, paths, st


def stack_table(ph, rows, use_diff):
    """Per (path, idx[, dmag]) colour-weighted clipped stacks. Returns DataFrame."""
    s = rows.set_index("file").s_exp_ujy
    ph = ph[ph.status == "ok"].copy()
    ph["s"] = ph.file.map(s)
    if use_diff:
        ph = ph[np.isfinite(ph.get("ref_flux", np.nan))]
        ph["f"] = ph.flux - ph.ref_flux
        ph["e"] = np.hypot(ph.err, ph.ref_err)
    else:
        ph["f"], ph["e"] = ph.flux, ph.err
    keys = ["path", "idx"] + (["dmag"] if "dmag" in ph else [])
    out = []
    for k, g in ph.groupby(keys, dropna=False):
        A, E, S, n = robust_amp(g.f, g.e, g.s)
        out.append(dict(zip(keys, k if isinstance(k, tuple) else (k,)), amp=A, amp_err=E, snr=S, n=n))
    return pd.DataFrame(out, columns=keys + ["amp", "amp_err", "snr", "n"])  # columns kept when nothing was measured


QA_FLAG_BITS = [1, 2, 28, 29]   # OVERFLOW, SUR_ERROR, HALO, SATELLITE_HALO anywhere in the fit box: a bright star is close
QA_CHI2_MAX = 20.0


def qa_drop(ph):
    """Files whose target fit is contaminated (bad PSF fit or bright-star flags in the fit box). Not applied to
    bright objects (median single-frame S/N >= 10), where a large chi2 is just PSF mismatch."""
    t = ph[(ph.path == "target") & (ph.status == "ok")]
    if not len(t) or np.median(t.flux / t.err) >= 10:
        return set()
    mask = sum(1 << b for b in QA_FLAG_BITS)
    flag = t.flag_or.fillna(0).astype(np.int64)
    # bright-star flags always; a poor PSF fit only matters without a static-sky reference (in crowded fields the raw
    # fit is poor because of neighbouring stars, which the reference subtraction removes)
    noref = ~np.isfinite(t.ref_flux) if "ref_flux" in t else np.ones(len(t), bool)
    bad = ((t.chi2 > QA_CHI2_MAX) & noref) | ((flag & mask) != 0)
    return set(t.file[bad])


def summarize(ph, rows, obj, qa=True):
    """Stacks and controls -> checks dict (contract 'checks' + extras)."""
    drop = qa_drop(ph) if qa else set()
    n_all = int((ph[ph.path == "target"].status == "ok").sum())
    ph_all = ph
    ph = ph[~ph.file.isin(drop)]
    n_ref_ok = int(np.isfinite(ph[ph.path == "target"].get("ref_flux", pd.Series(dtype=float))).sum())
    use_diff = n_ref_ok >= 10
    res = dict(n_frames_measured=n_all, n_qa_dropped=len(drop), n_with_static_ref=n_ref_ok, cleaned=use_diff)
    for mode in ([True, False] if use_diff else [False]):
        tab = stack_table(ph, rows, mode)
        tag = "diff" if mode else "raw"
        t = tab[tab.path == "target"].iloc[0] if (tab.path == "target").any() else None
        nl = tab[tab.path == "null"].snr.values.astype(float)
        res[tag] = dict(target_snr=float(t.snr) if t is not None else np.nan, amp=float(t.amp) if t is not None else np.nan,
                        amp_err=float(t.amp_err) if t is not None else np.nan, n=int(t.n) if t is not None else 0,
                        null_mean=float(np.nanmean(nl)) if len(nl) else np.nan, null_std=float(np.nanstd(nl)) if len(nl) else np.nan,
                        null_n=int(np.isfinite(nl).sum()), tab=tab)
    m = res["diff" if use_diff else "raw"]
    k = max(1.0, m["null_std"]) if np.isfinite(m["null_std"]) else 1.0
    m["err_scale"] = k
    m["snr_scaled"] = (m["target_snr"] - (m["null_mean"] if np.isfinite(m["null_mean"]) else 0)) / k
    nl = m["tab"][m["tab"].path == "null"].snr.values.astype(float)
    m["null_exceed"] = int(np.sum(nl >= m["target_snr"]))
    # time shift
    sh = m["tab"][m["tab"].path.isin(["shift", "target"])].copy()
    sh["k"] = np.where(sh.path == "target", 0, sh.idx)
    # fast movers: every shifted position can fall outside the stamp, then there are no shift rows at all
    dtmap = ph[ph.path == "shift"].groupby("idx").dt_days.median().to_dict() if "dt_days" in ph else {}
    sh["dt_days"] = [0.0 if kk == 0 else dtmap.get(kk, np.nan) for kk in sh.k]
    sh = sh.sort_values("k")
    m["time_shift"] = dict(shifts_days=[round(float(x), 4) for x in sh.dt_days], snr=[round(float(x), 2) for x in sh.snr])
    others = sh[sh.k != 0].snr.values
    m["shift_peak_at_zero"] = bool(len(others) > 0 and np.isfinite(m["target_snr"]) and m["target_snr"] > np.nanmax(others))
    # per-day split (cleaned stack per UTC day)
    tg = ph[(ph.path == "target") & (ph.status == "ok")].copy()
    tg["day"] = tg.file.map(rows.set_index("file").mjd).astype(float).astype(int)
    tg["s"] = tg.file.map(rows.set_index("file").s_exp_ujy)
    if use_diff:
        tg = tg[np.isfinite(tg.ref_flux)]
        tg["f"], tg["e"] = tg.flux - tg.ref_flux, np.hypot(tg.err, tg.ref_err)
    else:
        tg["f"], tg["e"] = tg.flux, tg.err
    days = []
    for d, g in tg.groupby("day"):
        A, E, S, n = robust_amp(g.f, g.e, g.s)
        days.append(dict(day=int(d), iso=pd.Timestamp(d - 40587, unit="D").strftime("%Y-%m-%d") if False else None,
                         n_frames=int(len(g)), snr=float(S / k) if np.isfinite(S) else np.nan, amp=A))
    for dd in days:
        from .frames import mjd_to_iso
        dd["iso"] = mjd_to_iso(dd["day"])
    m["days"] = days
    # sign test: fraction of frames with positive (cleaned) flux, target vs null paths
    allp = ph[ph.status == "ok"].copy()
    if use_diff:
        allp = allp[np.isfinite(allp.ref_flux)]
        allp["f"] = allp.flux - allp.ref_flux
    else:
        allp["f"] = allp.flux
    tpos = float((allp[allp.path == "target"].f > 0).mean()) if (allp.path == "target").any() else np.nan
    npos = allp[allp.path == "null"].groupby("idx").f.apply(lambda x: (x > 0).mean())
    tt = allp[allp.path == "target"]
    m["median_frame_snr"] = float(np.median(tt.flux / tt.err)) if len(tt) else np.nan
    m["frac_positive"] = dict(target=tpos, null_mean=float(npos.mean()) if len(npos) else np.nan,
                              null_std=float(npos.std()) if len(npos) > 1 else np.nan,
                              null_max=float(npos.max()) if len(npos) else np.nan)
    dd3 = [x for x in days if x["n_frames"] >= 3 and np.isfinite(x["snr"])]
    m["days_positive"] = int(sum(x["snr"] >= DAY_POS_SNR for x in dd3))
    # does the stack rest on one day? re-stack without the best day
    if dd3:
        best = max(dd3, key=lambda x: x["snr"])["day"]
        g = tg[tg.day != best]
        A, E, S, n = robust_amp(g.f, g.e, g.s)
        m["snr_without_best_day"] = float((S - (m["null_mean"] if np.isfinite(m["null_mean"]) else 0)) / k) if np.isfinite(S) else np.nan
        m["best_day"] = int(best)
    m["days_tested"] = len(dd3)
    # injection: fraction of fake paths recovered at S/N_scaled >= 5, per dmag
    inj = m["tab"][m["tab"].path == "inj"]
    curve = []
    for dm, g in inj.groupby("dmag"):
        sc = (g.snr - (m["null_mean"] if np.isfinite(m["null_mean"]) else 0)) / k
        curve.append(dict(dmag=float(dm), recovered=float(np.mean(sc >= 5)), median_snr=float(np.nanmedian(sc)),
                          median_amp=float(np.nanmedian(g.amp))))
    m["injection_curve"] = curve
    m["recovered_at_pred"] = next((c["recovered"] for c in curve if c["dmag"] == 0.0), np.nan)
    # limiting magnitude (50% recovery), relative to the predicted magnitude
    lim_dm = np.nan
    cs = sorted(curve, key=lambda c: c["dmag"])
    for a, b in zip(cs, cs[1:]):
        if a["recovered"] >= 0.5 > b["recovered"]:
            lim_dm = a["dmag"] + (a["recovered"] - 0.5) / (a["recovered"] - b["recovered"]) * (b["dmag"] - a["dmag"])
            break
    if not np.isfinite(lim_dm) and cs:
        lim_dm = cs[-1]["dmag"] if cs[-1]["recovered"] >= 0.5 else (cs[0]["dmag"] - 0.5 if cs[0]["recovered"] < 0.5 else np.nan)
    m["limit_dmag"] = lim_dm
    res["main"] = m
    if qa and drop:
        r0 = summarize(ph_all, rows, obj, qa=False)["main"]
        res["snr_before_qa"] = float(r0["snr_scaled"]) if np.isfinite(r0["snr_scaled"]) else np.nan
        res["qa_fraction"] = len(drop) / max(n_all, 1)
    return res


def measure_object(obj, max_workers=6, verbose=True):
    from concurrent.futures import ThreadPoolExecutor
    from . import objects as O
    d = os.path.join(C.WORK, "objects", obj.slug)
    fr_path = os.path.join(d, "frames.csv")
    fr = pd.read_csv(fr_path) if os.path.exists(fr_path) and os.path.getsize(fr_path) > 2 else pd.DataFrame()
    if len(fr) == 0:
        return dict(slug=obj.slug, verdict="NO_PHOTOS", n_frames=0)
    fr = fr[[os.path.exists(FE.stamp_path(obj.slug, f)) for f in fr.file]]
    if len(fr) == 0:
        return dict(slug=obj.slug, verdict="PENDING", n_frames=0)
    sb = O.sbdb_record(obj.desig)
    H = _sbdb_H(sb) if obj.kind != "comet" else None
    t0 = time.time()
    rows, paths = [], []

    def one(r):
        try:
            row, p, _ = measure_frame(obj.slug, r, "comet" if obj.kind == "comet" else "asteroid", H, None)
            return row, p
        except Exception as e:  # noqa
            return dict(file=r.file, error=str(e)[:200]), []
    with ThreadPoolExecutor(max_workers) as ex:
        for row, p in ex.map(one, fr.itertuples()):
            rows.append(row)
            paths += p
    rows = pd.DataFrame(rows)
    ph = pd.DataFrame(paths)
    rows.to_csv(os.path.join(d, "frame_phot.csv"), index=False)
    ph.to_csv(os.path.join(d, "paths_phot.csv"), index=False)
    if verbose:
        print(f"{obj.slug}: {len(rows)} frames, {len(ph)} path measurements in {time.time() - t0:.0f}s", flush=True)
    return dict(slug=obj.slug, rows=rows, ph=ph, H=H)


def _sbdb_H(sb):
    try:
        for p in sb.get("phys_par", []):
            if p["name"] == "H":
                return float(p["value"])
    except Exception:  # noqa
        pass
    return None


def measure_all(objs):
    """Measure the given objects, then rebuild the index from every object measured so far."""
    from . import report, site
    for o in objs.itertuples():
        try:
            report.run_object(o)
        except Exception as ex:  # noqa
            import traceback
            traceback.print_exc()
            print(f"{o.slug}: measure failed: {ex}", flush=True)
    return site.rebuild_index()
