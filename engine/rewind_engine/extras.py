"""Step 4f-h, 7, 8: clone search, orbit check, real-or-fake score, composition, uncertainty cloud."""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import brightness as B

COMP_TEMPLATES = ["stitched_S_0.45-5um", "stitched_C_0.45-5um", "stitched_X_0.45-5um", "stitched_D_0.45-5um"]
COMP_LABEL = {"stitched_S_0.45-5um": "S", "stitched_C_0.45-5um": "C", "stitched_X_0.45-5um": "X", "stitched_D_0.45-5um": "D"}


def composition(obj, out, res, nbins=10):
    """Per-wavelength points (cleaned flux / solar-colour prediction = relative reflectance, normalised
    to the 0.75-1.3 um bins) and a chi-square template match (label: rough match)."""
    rows, ph = out["rows"], out["ph"]
    tg = ph[(ph.path == "target") & (ph.status == "ok")].set_index("file")
    r = rows[rows.file.isin(tg.index)].copy()
    f = tg.loc[r.file]
    use_diff = res.get("cleaned")
    r["f"] = (f.flux - f.ref_flux).values if use_diff else f.flux.values
    r["e"] = (np.hypot(f.err, f.ref_err)).values if use_diff else f.err.values
    r["e"] *= res["main"].get("err_scale", 1.0)
    sol = B.reflected_ujy(r.mag_pred.values, r.wave_um.values, None)
    r["rel"], r["rel_e"] = r.f / sol, r.e / sol
    r = r[np.isfinite(r.rel) & np.isfinite(r.rel_e) & (r.rel_e > 0)]
    if len(r) < 10:
        return None
    edges = np.geomspace(0.74, 5.05, nbins + 1)
    pts = []
    for lo, hi in zip(edges, edges[1:]):
        g = r[(r.wave_um >= lo) & (r.wave_um < hi)]
        if len(g) < 3:
            continue
        w = 1 / g.rel_e ** 2
        pts.append(dict(um=float(np.sqrt(lo * hi)), value=float(np.sum(w * g.rel) / w.sum()), err=float(1 / np.sqrt(w.sum()))))
    if not pts:
        return None
    norm_pts = [p for p in pts if p["um"] < 1.3] or pts[:1]
    nrm = np.mean([p["value"] for p in norm_pts])
    ok_norm = np.isfinite(nrm) and nrm > 0
    if ok_norm:
        for p in pts:
            p["value"], p["err"] = p["value"] / nrm, p["err"] / abs(nrm)
    lam = np.array([p["um"] for p in pts])
    tpl = [dict(name=COMP_LABEL[t], um=[round(x, 3) for x in lam], value=[round(float(v), 3) for v in
           B.template_curve(t, lam) / np.mean(B.template_curve(t, lam[lam < 1.3] if (lam < 1.3).any() else lam[:1]))])
           for t in COMP_TEMPLATES]
    best = None
    snr = res["main"].get("snr_scaled", 0)
    if ok_norm and snr >= 5 and obj.kind != "comet":
        fit = lam < 2.5  # reflected-light part only (thermal dominates beyond for NEOs)
        v = np.array([p["value"] for p in pts])
        e = np.array([p["err"] for p in pts])
        chi = {t["name"]: float(np.sum(((v - np.array(t["value"])) / e)[fit] ** 2)) for t in tpl}
        if fit.sum() >= 3:
            best = min(chi, key=chi.get)
    for p in pts:
        p.update(um=round(p["um"], 3), value=round(p["value"], 3), err=round(p["err"], 3))
    return dict(points=pts, templates=tpl, best_match=best, label="rough match",
                note="relative reflectance = measured flux / solar-colour prediction, normalised below 1.3 um (MEASURED / ESTIMATED model)")


AU_KM = 149597870.7
N_CLOUD = 60


def _props(obj):
    from .pilot import positions
    return positions()._fetch_props(obj.desig)


def _propagate_cloud(states, ngs, dates_mjd):
    """Positions (heliocentric ecliptic AU) of each state at each date (UTC MJD ~ TDB here)."""
    import kete
    out = []
    order = np.argsort(dates_mjd)
    cur = list(states)
    res = [None] * len(dates_mjd)
    for i in order:
        jd = float(dates_mjd[i]) + 2400000.5
        cur = kete.propagate_n_body(cur, jd, non_gravs=ngs)
        res[i] = [[round(float(v), 5) for v in s.pos] for s in cur]
    return res


def _sigma_km(cloud_at_date):
    p = np.array(cloud_at_date[1:], float)
    if len(p) < 3:
        return None
    w = np.linalg.eigvalsh(np.cov(p.T))
    return float(np.sqrt(max(w[-1], 0)) * AU_KM)


def cloud(obj, orbit_fit, first_frame_mjd=None):
    """Clones from the SBDB covariance ('before') and from the refit with Rewind positions ('after'),
    at 40 dates from 1 year before the first SPHEREx frame (2025-04) to 2 years ahead. Index 0 = nominal."""
    from .frames import iso_to_mjd, mjd_to_iso
    start = (first_frame_mjd or iso_to_mjd("2025-04-15")) - 365.25
    end = iso_to_mjd("2026-11-15") + 2 * 365.25
    dates = np.linspace(start, end, 40)
    pr = _props(obj)
    ss, ng = pr.sample(N_CLOUD, seed=11)
    ngs = [pr.non_grav] + list(ng)
    ngs = ngs if any(n is not None for n in ngs) else None
    before = _propagate_cloud([pr.state] + list(ss), ngs, dates)
    ref = int(np.argmin(np.abs(dates - (iso_to_mjd("2026-11-15") + 365.25))))
    out = dict(dates_mjd=[round(float(d), 2) for d in dates], before=before, after=None,
               before_sigma_km_at=dict(iso=mjd_to_iso(dates[ref]), km=_sigma_km(before[ref])), after_sigma_km_at=None,
               note="after = with the Rewind positions added; null if nothing measured. Positions heliocentric ecliptic J2000 AU, "
                    "first entry per date is the nominal orbit (COMPUTED from the JPL SBDB covariance with kete).")
    fit = (orbit_fit or {}).get("_fit_after")
    if fit is not None:
        sa, _ = fit.uncertain_state.sample(N_CLOUD, seed=11)
        after = _propagate_cloud([fit.state] + list(sa), None, dates)
        out["after"] = after
        out["after_sigma_km_at"] = dict(iso=mjd_to_iso(dates[ref]), km=_sigma_km(after[ref]))
    return out


# ------------------------------------------------------------------ clone search (step 4f)
def _mf_maps(st, trail):
    """Matched-filter flux and error maps (uJy) at every pixel of a stamp, for the (trailed) ePSF."""
    from scipy.ndimage import correlate
    from astropy.stats import sigma_clipped_stats
    from . import phot as PH
    from .pilot import R
    good = ((st.flags & R.BAD_MASK_STRICT) == 0) & np.isfinite(st.image) & np.isfinite(st.variance) & (st.variance > 0)
    _, bkg, _ = sigma_clipped_stats(st.image[good], sigma=3.0, maxiters=5)
    c = (st.image.shape[0] - 1) / 2
    psf_os, _ = R.epsf_zone(st.epsf_table, st.x0 + c, st.y0 + c)
    L = float(np.hypot(*trail))
    n = 7 + 2 * (int(np.ceil(L / 2)) if L >= PH.TRAIL_MIN_PX else 0)
    P = PH.psf_model(psf_os, 0.0, 0.0, n, trail)
    W = np.where(good, 1.0 / np.where(good, st.variance, 1), 0.0)
    D = np.where(good, st.image - bkg, 0.0)
    num = correlate(D * W, P, mode="constant")
    den = correlate(W, P ** 2, mode="constant")
    sc = R.pixel_sr(st) * 1e12
    with np.errstate(divide="ignore", invalid="ignore"):
        F = np.where(den > 0, num / den, np.nan) * sc
        E = np.where(den > 0, 1 / np.sqrt(den), np.nan) * sc
    return F, E


def _sample(mapa, x, y):
    from scipy.ndimage import map_coordinates
    return map_coordinates(mapa, [np.atleast_1d(y), np.atleast_1d(x)], order=1, cval=np.nan)


def clone_search(obj, fr, out, res, n_clones=300, n_perm=20, sigma_min_px=2.0, seed=5):
    """For uncertain objects (median 1-sigma > ~2 px): sample orbit clones from the covariance, stack
    along each clone, and compare the best clone with the same number of trials on null paths
    (frame-permuted clones and clones shifted sideways by 8-16 px). Report the best clone only if
    its false-alarm rate times the number of clones is below 0.05."""
    from . import fetch as FE
    from . import phot as PH
    from .pilot import R, positions
    rows = out["rows"]
    if not len(rows) or np.nanmedian(rows.sigma_px) <= sigma_min_px:
        return None
    P = positions()
    frs = fr.set_index("file").loc[rows.file]
    jd = P.utc_mjd_to_tdb_jd(frs.mjd_avg.values)
    pred = P.predict(obj.desig, jd, observer="spherex", n_samples=n_clones, return_samples=True)
    samp = pred.attrs.get("samples", {})
    F, E, X, Y, S = [], [], [], [], []
    for k, (f, r) in enumerate(frs.iterrows()):
        st = R.load_stamp_fits(FE.stamp_path(obj.slug, f))
        trail = PH.trail_vector_px(st, r.pred_ra, r.pred_dec, r.rate_ra, r.rate_dec)
        mf, me = _mf_maps(st, trail)
        key = min(samp, key=lambda j: abs(j - jd[k])) if samp else None
        if key is None or abs(key - jd[k]) > 1e-6:
            continue
        ra_s, de_s = samp[key]
        x, y = st.wcs.all_world2pix(np.c_[ra_s, de_s], 0).T
        F.append(mf), E.append(me), X.append(x), Y.append(y), S.append(rows.set_index("file").s_exp_ujy.get(f, np.nan))
    if len(F) < 3:
        return dict(n_clones=n_clones, false_alarm_rate=None, note="too few frames with clone positions")
    X, Y, S = np.array(X), np.array(Y), np.array(S)  # (frames, clones)
    nfr, ncl = X.shape

    def stack_paths(xx, yy):
        snr = np.full(xx.shape[1], np.nan)
        f = np.array([_sample(F[i], xx[i], yy[i]) for i in range(nfr)])
        e = np.array([_sample(E[i], xx[i], yy[i]) for i in range(nfr)])
        from .pipeline import robust_amp
        for c in range(xx.shape[1]):
            snr[c] = robust_amp(f[:, c], e[:, c], S)[2]
        return snr
    real = stack_paths(X, Y)
    rng = np.random.default_rng(seed)
    nulls = []
    for _ in range(n_perm):  # break path coherence: each frame takes a different clone
        idx = np.array([rng.permutation(ncl) for _ in range(nfr)])
        nulls.append(stack_paths(np.take_along_axis(X, idx, 1), np.take_along_axis(Y, idx, 1)))
    # sideways shifts (perpendicular to the mean clone spread)
    dx, dy = X - X.mean(1, keepdims=True), Y - Y.mean(1, keepdims=True)
    ang = np.arctan2(np.nanmedian(dy * np.sign(dx + 1e-9)), np.nanmedian(np.abs(dx))) + np.pi / 2
    for d in (-16, -12, -8, 8, 12, 16):
        nulls.append(stack_paths(X + d * np.cos(ang), Y + d * np.sin(ang)))
    nulls = np.concatenate(nulls)
    best = int(np.nanargmax(real)) if np.isfinite(real).any() else None
    bs = float(real[best]) if best is not None else np.nan
    nn = np.isfinite(nulls).sum()
    far = float(np.sum(nulls >= bs) / nn) if nn and np.isfinite(bs) else None
    far_bound = far if far else (1.0 / nn if nn else None)
    sig = bool(np.isfinite(bs) and bs >= 5 and far_bound is not None and far_bound * ncl < 0.05)
    return dict(n_clones=int(ncl), n_null_trials=int(nn), best_clone_snr=round(bs, 2) if np.isfinite(bs) else None,
                null_trial_snr_p99=float(np.nanpercentile(nulls, 99)) if nn else None,
                false_alarm_rate=far, significant=sig,
                best_clone_index=best if sig else None, frames=int(nfr),
                note="clone stacks use matched-filter maps without static-sky subtraction; nulls are frame-permuted and sideways-shifted clones")


# ------------------------------------------------------------------ orbit check (step 4g)
def _day_offsets(obj, fr, out, res, grid=1.25, step=0.25, min_nominal_snr=3.0, all_days=False):
    """Per-day shift-and-stack position: grid of (east, north) offsets around the prediction, cleaned
    colour-weighted stack S/N at each, quadratic peak. Returns list of dicts (frame time, ra, dec, sigma)."""
    from . import fetch as FE
    from . import phot as PH
    from .pipeline import load_refs, robust_amp
    from .pilot import R
    from .pipeline import qa_drop
    rows = out["rows"]
    tg = out["ph"][(out["ph"].path == "target") & (out["ph"].status == "ok")]
    drop = qa_drop(out["ph"])
    if res.get("cleaned"):
        tg = tg[np.isfinite(tg.ref_flux)]
    rows = rows[rows.file.isin(tg.file) & ~rows.file.isin(drop)].copy()
    rows["day"] = rows.mjd.astype(int) if not all_days else int(np.median(rows.mjd))
    # only days that are detected at the predicted spot (avoids picking the best of 81 noise positions)
    day_snr = {d["day"]: d["snr"] for d in res["main"].get("days", [])}
    if all_days:
        day_snr = {int(np.median(rows.mjd)): res["main"].get("snr_scaled", -np.inf)}
    frs = fr.set_index("file")
    offs = np.arange(-grid, grid + 1e-9, step) * C_PIX
    pts = []
    for day, g in rows.groupby("day"):
        if len(g) < 3 or not (day_snr.get(day, -np.inf) >= min_nominal_snr):
            continue
        cache = []
        for r in g.itertuples():
            st = R.load_stamp_fits(FE.stamp_path(obj.slug, r.file))
            f = frs.loc[r.file]
            trail = PH.trail_vector_px(st, f.pred_ra, f.pred_dec, f.rate_ra, f.rate_dec)
            refs = load_refs(obj.slug, r.file, f.rate_arcsec_hr, obj.kind == "comet", float(np.hypot(*trail))) if res.get("cleaned") else []
            if res.get("cleaned") and not refs:
                continue
            cache.append((st, refs, f, trail, r.s_exp_ujy))
        if len(cache) < 3:
            continue
        snr = np.full((len(offs), len(offs)), np.nan)
        for i, de in enumerate(offs):
            for j, dn in enumerate(offs):
                fl, er, ss = [], [], []
                for st, refs, f, trail, s in cache:
                    ra, dec = R.offset_radec(f.pred_ra, f.pred_dec, de, dn)
                    q = PH.phot(st, ra, dec, trail)
                    if q.get("status") != "ok":
                        continue
                    v, e = q["flux"], q["err"]
                    if refs:
                        rq = [PH.phot(s2, ra, dec, trail) for s2 in refs]
                        rq = [x for x in rq if x.get("status") == "ok"]
                        if not rq:
                            continue
                        v -= np.median([x["flux"] for x in rq])
                        e = np.hypot(e, np.median([x["err"] for x in rq]))
                    fl.append(v), er.append(e), ss.append(s)
                snr[j, i] = robust_amp(fl, er, ss)[2]
        if not np.isfinite(snr).any():
            continue
        j, i = np.unravel_index(np.nanargmax(snr), snr.shape)
        peak = snr[j, i] / res["main"].get("err_scale", 1.0)

        def q1(a, k):  # 1-D quadratic refinement
            if 0 < k < len(a) - 1 and np.isfinite(a[k - 1:k + 2]).all():
                d = a[k - 1] - 2 * a[k] + a[k + 1]
                return float(np.clip(0.5 * (a[k - 1] - a[k + 1]) / d, -0.5, 0.5)) if d < 0 else 0.0
            return 0.0
        de = offs[i] + q1(snr[j, :], i) * step * C_PIX
        dn = offs[j] + q1(snr[:, i], j) * step * C_PIX
        on_edge = i in (0, len(offs) - 1) or j in (0, len(offs) - 1)
        mid = g.iloc[len(g) // 2]
        f = frs.loc[mid.file]
        ra, dec = R.offset_radec(f.pred_ra, f.pred_dec, de, dn)
        sigma = max(1.0, 1.2 * C_PIX / max(peak, 1e-3))  # ESTIMATED: ~FWHM/(S/N), floor 1 arcsec
        pts.append(dict(day=int(day), mjd=float(f.mjd_avg), ra=float(ra), dec=float(dec), d_east=float(de), d_north=float(dn),
                        snr=float(peak), sigma_arcsec=float(sigma), on_edge=bool(on_edge)))
    return pts


C_PIX = 6.15


def orbit_check(obj, fr, out, res, min_day_snr=5.0):
    """Measure per-day positions (cleaned frames only, days detected at the predicted spot, peak S/N >= 5),
    refit the orbit with them (kete least squares, orbitfit.py), compare residual RMS before/after, and refit
    leaving out one day at a time to find a single bad day. ok = fit converges, RMS grows < 50 %, every new
    point within 3 sigma."""
    from .pilot import orbitfit, positions
    OF = orbitfit()
    P = positions()
    pts = [p for p in _day_offsets(obj, fr, out, res) if p["snr"] >= min_day_snr and not p["on_edge"]]
    combined = False
    if not pts and res["main"].get("snr_scaled", 0) >= min_day_snr:  # one position from the stack of all cleaned frames
        pts = [p for p in _day_offsets(obj, fr, out, res, all_days=True) if p["snr"] >= min_day_snr and not p["on_edge"]]
        combined = bool(pts)
    if not pts:
        return dict(ok=False, new_points=0, note="no cleaned per-day stack bright enough for a position (S/N >= 5 at the "
                                                  "predicted spot and at the peak)")
    obs = OF.fetch_obs(obj.desig)
    f0 = OF.fit(obs)
    rows = [(float(P.utc_mjd_to_tdb_jd([p["mjd"]])[0]), p["ra"], p["dec"], p["sigma_arcsec"], "spherex") for p in pts]
    sig = np.array([p["sigma_arcsec"] for p in pts])

    def refit(sel):
        f = OF.fit(OF.add_precovery(obs, [rows[i] for i in sel]), initial_state=f0.state)
        rn = np.array(f.residuals[-len(sel):], float) if len(sel) else np.zeros((0, 2))
        return f, rn
    f1, res_new = refit(list(range(len(rows))))
    new_chi = np.hypot(res_new[:, 0], res_new[:, 1]) / sig if res_new.ndim == 2 and len(res_new) else None
    ok = bool(f1.converged and f1.rms <= 1.5 * max(f0.rms, 1e-6) and (new_chi is None or np.all(new_chi < 3)))
    loo = []
    if len(rows) >= 2:
        for i in range(len(rows)):
            fi, _ = refit([j for j in range(len(rows)) if j != i])
            loo.append(dict(left_out_day=pts[i]["day"], rms_arcsec=round(float(fi.rms), 3)))
    return dict(ok=ok, rms_arcsec_before=round(float(f0.rms), 3), rms_arcsec_after=round(float(f1.rms), 3), new_points=len(rows),
                new_point_resid_arcsec=[round(float(np.hypot(*r)), 2) for r in res_new] if res_new.ndim == 2 else None,
                new_point_resid_sigma=[round(float(x), 2) for x in new_chi] if new_chi is not None else None,
                combined_all_days=combined, leave_one_out=loo, positions=[{k: (round(v, 6) if isinstance(v, float) else v) for k, v in p.items()} for p in pts],
                note="rms = kete fit RMS; positions ESTIMATED sigma = 1.2 px / S/N. Positions come only from cleaned days already "
                     "detected at the predicted spot, searched within +-1.25 px, so this check only catches moderate inconsistencies.",
                _fit_after=f1)


def real_or_fake(obj, out, res):
    from . import realfake
    return realfake.score_object(obj, out, res)
