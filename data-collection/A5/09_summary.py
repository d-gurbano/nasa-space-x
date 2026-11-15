"""A5 step 9: per-target products from results/<key>_phot.csv + archive stamps.
 - passes (gap > 30 d; long clusters split into 30 d chunks)
 - SPHEREx motion: measured position per pass (free ePSF fit) vs predicted (PM+plx)
 - decades motion: DSS / 2MASS / unTimely(unWISE) / SPHEREx measured vs predicted
 - spectra per pass (+ DR1 HiPS cube spectrum), light curves (RW Aur, R Dra)
 - PNGs: SPHEREx matched-wavelength blink (+GIF), decades montage, track plot
Outputs in results/ and png/. Usage: python 09_summary.py [target ...]"""
import os, sys, glob, json, tarfile, io, warnings
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from astropy.io import fits
from astropy.wcs import WCS
from astropy.time import Time
from scipy.ndimage import map_coordinates, gaussian_filter
from a5lib import OUT, radec_at, sky_offset_arcsec, pos
from astrometry import ASTRO
import rewind as R

warnings.filterwarnings("ignore")
rd = os.path.join(OUT, "results"); pd_ = os.path.join(OUT, "png"); os.makedirs(pd_, exist_ok=True)
PIX = 6.15  # SPHEREx arcsec/px (Explanatory Supplement, VERIFIED via agent16)
LABEL = {"barnard": "Barnard's Star", "eps_indi_b": "Epsilon Indi Ba+Bb", "wise0855": "WISE 0855-0714",
         "rw_aur": "RW Aurigae", "r_dra": "R Draconis"}


def assign_passes(mjd, chunk=1e9):
    o = np.argsort(mjd); m = np.asarray(mjd)[o]
    lab = np.zeros(len(m), int); p = 0; start = m[0] if len(m) else 0
    for i in range(1, len(m)):
        if m[i] - m[i - 1] > 30 or m[i] - start > chunk:
            p += 1; start = m[i]
        lab[i] = p
    out = np.empty(len(m), int); out[o] = lab
    return out


def resample(img, w, ra, dec, half=75.0, scale=1.5):
    n = int(2 * half / scale) + 1; k = (n - 1) / 2
    j, i = np.mgrid[0:n, 0:n]
    e = -(i - k) * scale; nn = (j - k) * scale
    dd = dec + nn / 3600.0
    rr = ra + e / 3600.0 / np.cos(np.radians(dd))
    px, py = w.all_world2pix(rr.ravel(), dd.ravel(), 0)
    a = np.nan_to_num(np.asarray(img, float), nan=np.nanmedian(img))
    return map_coordinates(a, [py, px], order=1, cval=np.nan).reshape(n, n)


def stretch(a):
    """asinh stretch in units of the robust noise, so faint and saturated targets both show."""
    f = np.isfinite(a)
    if not f.any():
        return a, 0, 1
    med = np.nanmedian(a); sd = 1.4826 * np.nanmedian(np.abs(a[f] - med)) or 1.0
    b = np.arcsinh((a - med) / (2 * sd))
    return b, -1.5, max(np.nanpercentile(b[f], 99.8), 3)


def show(ax, a, title, half, marks=()):
    b, lo, hi = stretch(a)
    cm = plt.get_cmap("gray").copy(); cm.set_bad("0.5")
    ax.imshow(b, origin="lower", cmap=cm, vmin=lo, vmax=hi, extent=[half, -half, -half, half])
    for (de, dn, c, m) in marks:
        ax.plot(de, dn, m, color=c, ms=14, mfc="none", mew=1.0)
    ax.set_title(title, fontsize=7); ax.tick_params(labelsize=5)


def centroid_image(img, w, ra, dec, search=12.0):
    """Peak + flux-weighted centroid near the prediction on a generic image (DSS/2MASS/unWISE).
    Returns measured minus predicted (east, north) arcsec, or None."""
    try:
        sc = np.abs(w.proj_plane_pixel_scales()[0].to_value("arcsec")) if hasattr(w.proj_plane_pixel_scales()[0], "to_value") else abs(w.proj_plane_pixel_scales()[0]) * 3600
    except Exception:
        sc = 1.0
    x, y = w.all_world2pix([[ra, dec]], 0)[0]
    a = np.asarray(img, float)
    r = int(np.ceil(search / sc))
    xi, yi = int(round(x)), int(round(y))
    if not (r + 3 <= xi < a.shape[1] - r - 3 and r + 3 <= yi < a.shape[0] - r - 3):
        return None
    sub = gaussian_filter(np.nan_to_num(a[yi - r:yi + r + 1, xi - r:xi + r + 1]), 1.0)
    bk = np.nanmedian(a[max(yi - 4 * r, 0):yi + 4 * r, max(xi - 4 * r, 0):xi + 4 * r])
    sd = 1.4826 * np.nanmedian(np.abs(a[max(yi - 4 * r, 0):yi + 4 * r, max(xi - 4 * r, 0):xi + 4 * r] - bk))
    jy, jx = np.unravel_index(np.argmax(sub), sub.shape)
    py, px = yi - r + jy, xi - r + jx
    if (a[py, px] - bk) < 8 * sd:
        return None
    h = max(2, int(round(3.0 / sc)))
    box = a[py - h:py + h + 1, px - h:px + h + 1] - bk
    box[box < 0] = 0
    jj, ii = np.mgrid[-h:h + 1, -h:h + 1]
    cx, cy = px + (box * ii).sum() / box.sum(), py + (box * jj).sum() / box.sum()
    rb, db = w.all_pix2world([[cx, cy]], 0)[0]
    de, dn = sky_offset_arcsec(ra, dec, rb, db)
    return float(de), float(dn), float((a[py, px] - bk) / sd)


def archive_points(key, A):
    """Decades: measured vs predicted on DSS, 2MASS, unWISE full-depth (allwise), unTimely."""
    pts, panels = [], []
    for fn in sorted(glob.glob(os.path.join(OUT, "dss", f"{key}_*.fits"))):
        h = fits.open(fn)[0]
        v = str(h.header.get("DATE-OBS", ""))
        try:
            d, tm = v.split("T"); hh, mm, ss = (float(x) for x in (tm.split(":") + ["0", "0"])[:3])
            t = Time(d) + (hh / 24 + mm / 1440 + ss / 86400)
        except Exception:
            continue
        w = WCS(h.header)
        ra, dec = pos(A, t)
        c = centroid_image(h.data, w, ra[0], dec[0], search=15)
        sv = os.path.basename(fn)[len(key) + 1:-5]
        pts.append(dict(source="DSS " + sv, year=t.jyear, pred_ra=ra[0], pred_dec=dec[0],
                        d_east=c[0] if c else np.nan, d_north=c[1] if c else np.nan, snr=c[2] if c else np.nan))
        panels.append((t.jyear, f"DSS {sv} {t.jyear:.1f}", h.data, w, ra[0], dec[0]))
    for fn in sorted(glob.glob(os.path.join(OUT, "2mass", f"{key}_2mass_*.fits"))):
        h = fits.open(fn)[0]
        try:
            ud = str(h.header["UT_DATE"]).strip()
            t = Time(f"20{ud[:2]}-{ud[2:4]}-{ud[4:6]}T{h.header['UT'].strip()}" if int(ud[:2]) < 50 else f"19{ud[:2]}-{ud[2:4]}-{ud[4:6]}T{h.header['UT'].strip()}")
        except Exception:
            continue
        w = WCS(h.header)
        ra, dec = pos(A, t)
        c = centroid_image(h.data, w, ra[0], dec[0], search=8)
        b = os.path.basename(fn).split("_")[-2]
        pts.append(dict(source="2MASS " + b, year=t.jyear, pred_ra=ra[0], pred_dec=dec[0],
                        d_east=c[0] if c else np.nan, d_north=c[1] if c else np.nan, snr=c[2] if c else np.nan))
        if b == "K":
            panels.append((t.jyear, f"2MASS Ks {t.jyear:.1f}", h.data, w, ra[0], dec[0]))
    dl = os.path.join(OUT, "dasch", "dasch_log.json")
    if os.path.exists(dl):
        for e in json.load(open(dl)):
            if e.get("target") != key or "file" not in e:
                continue
            fn = os.path.join(OUT, "dasch", e["file"])
            try:
                h = fits.open(fn)[0]
                w = WCS(h.header).celestial
                t = Time(e["plate_year"], format="jyear")
                ra, dec = pos(A, t)
                img = h.data if h.data.ndim == 2 else h.data[0]
                c = centroid_image(img, w, ra[0], dec[0], search=20)
                pts.append(dict(source=f"DASCH {e['plate']}", year=t.jyear, pred_ra=ra[0], pred_dec=dec[0],
                                d_east=c[0] if c else np.nan, d_north=c[1] if c else np.nan, snr=c[2] if c else np.nan))
                panels.append((t.jyear, f"Harvard plate {e['plate']} {t.jyear:.1f}", img, w, ra[0], dec[0]))
            except Exception as ex:
                print("dasch panel fail", fn, repr(ex)[:80])
    for ver, yr in [("allwise", 2010.6), ("neo7", 2015.5)]:
        fn = os.path.join(OUT, "wise", f"{key}_unwise_{ver}.tar.gz")
        if not os.path.exists(fn):
            continue
        try:
            tf = tarfile.open(fn)
            m = [x for x in tf.getmembers() if "w2-img" in x.name]
            if m:
                h = fits.open(io.BytesIO(tf.extractfile(m[0]).read()))[0]
                w = WCS(h.header)
                ra, dec = pos(A, Time(yr, format="jyear"))
                panels.append((yr, f"unWISE W2 {ver} (~{yr:.0f}, coadd)", h.data, w, ra[0], dec[0]))
        except Exception:
            pass
    nw = os.path.join(OUT, "wise", f"neowise_p1bs_{key}.csv")
    if os.path.exists(nw):
        n = pd.read_csv(nw)
        if len(n):
            n = n.sort_values("mjd"); n["visit"] = np.r_[0, np.cumsum(np.diff(n.mjd.values) > 5)]
            for v, g in n.groupby("visit"):
                if len(g) < 3:
                    continue
                pts.append(dict(source=f"NEOWISE visit {v:02d}", year=Time(g.mjd.median(), format="mjd").jyear,
                                d_east=float(np.median(g.d_east_arcsec)), d_north=float(np.median(g.d_north_arcsec)), snr=float(np.median(g.w2snr))))
    ut = os.path.join(OUT, "wise", "untimely_near_targets.csv")
    if os.path.exists(ut):
        u = pd.read_csv(ut, low_memory=False)
        u = u[(u.target == key) & (u.band == "w2")]
        for e, g in u.groupby("epoch"):
            g = g[np.hypot(g.d_east_arcsec, g.d_north_arcsec) < 6]
            if not len(g):
                continue
            g = g.iloc[np.argmax(g.flux.values)]
            pts.append(dict(source=f"unTimely W2 e{e:02d}", year=Time(g.MJDMEAN, format="mjd").jyear, pred_ra=g.pred_ra,
                            pred_dec=g.pred_dec, d_east=g.d_east_arcsec, d_north=g.d_north_arcsec, snr=g.flux / max(g.dflux, 1e-9)))
    return pd.DataFrame(pts), sorted(panels, key=lambda p: p[0])


def run(key):
    A = ASTRO[key]
    df = pd.read_csv(os.path.join(rd, f"{key}_phot.csv"))
    df = df[df.mjd.notna()].copy()
    df["pass"] = assign_passes(df.mjd.values, chunk=30 if key == "r_dra" else 1e9)
    # best flux: strict if ok and unsaturated, else wing fit
    df["flux_best"] = np.where((df.status == "ok") & (~df.saturated), df.flux_uJy, df.get("w_flux_uJy"))
    df["err_best"] = np.where((df.status == "ok") & (~df.saturated), df.err_uJy, df.get("w_err_uJy"))
    df["flux_method"] = np.where((df.status == "ok") & (~df.saturated), "strict_epsf", np.where(df.w_status == "ok", "wing_epsf_saturated", "none"))
    df["ab_best"] = -2.5 * np.log10(df.flux_best.clip(lower=1e-3) * 1e-6 / 3631)
    df.to_csv(os.path.join(rd, f"{key}_phot_passes.csv"), index=False)
    # ---- SPHEREx motion per pass
    ok = df[(df.c_err_px < 0.3) & (~df.c_hit_bound.fillna(True).astype(bool))].copy() if "c_err_px" in df else df.iloc[:0]
    if key == "wise0855":
        ok = ok[ok.wave_um > 3.9]
    rows = []
    ref_ra, ref_dec = A["ra"], A["dec"]
    for p, g in ok.groupby("pass"):
        if len(g) < 3:
            continue
        me, mn = np.median(g.c_east_arcsec), np.median(g.c_north_arcsec)
        se, sn = 1.2533 * g.c_east_arcsec.std() / np.sqrt(len(g)), 1.2533 * g.c_north_arcsec.std() / np.sqrt(len(g))
        t = np.median(g.mjd)
        pra, pdec = pos(A, Time(t, format="mjd"))
        pe, pn = sky_offset_arcsec(ref_ra, ref_dec, pra[0], pdec[0])
        rows.append(dict(pass_=p, mjd=t, date=Time(t, format="mjd").isot[:10], n=len(g), resid_east=me, resid_north=mn,
                         err_east=se, err_north=sn, pred_east_from_ref=float(pe), pred_north_from_ref=float(pn),
                         meas_east_from_ref=float(pe + me), meas_north_from_ref=float(pn + mn)))
    mot = pd.DataFrame(rows)
    summ = dict(target=key, n_frames=len(df), n_passes=int(df["pass"].nunique()), n_centroid_ok=len(ok),
                n_saturated=int(df.saturated.sum()), ref=f"Gaia/adopted position at epoch {A['ep']}")
    if len(mot) >= 2:
        a, b = mot.iloc[0], mot.iloc[-1]
        pe, pn = b.pred_east_from_ref - a.pred_east_from_ref, b.pred_north_from_ref - a.pred_north_from_ref
        me, mn = b.meas_east_from_ref - a.meas_east_from_ref, b.meas_north_from_ref - a.meas_north_from_ref
        summ.update(first_pass=a.date, last_pass=b.date, pred_shift_arcsec=float(np.hypot(pe, pn)),
                    meas_shift_arcsec=float(np.hypot(me, mn)), pred_shift_px=float(np.hypot(pe, pn) / PIX),
                    meas_shift_px=float(np.hypot(me, mn) / PIX), meas_minus_pred_arcsec=float(np.hypot(me - pe, mn - pn)),
                    meas_err_arcsec=float(np.hypot(np.hypot(a.err_east, b.err_east), np.hypot(a.err_north, b.err_north))),
                    pred_vec=[float(pe), float(pn)], meas_vec=[float(me), float(mn)])
    mot.to_csv(os.path.join(rd, f"{key}_spherex_motion_per_pass.csv"), index=False)
    # ---- decades
    arch, panels = archive_points(key, A)
    if len(mot):
        for r in mot.itertuples():
            arch = pd.concat([arch, pd.DataFrame([dict(source=f"SPHEREx pass {r.pass_}", year=Time(r.mjd, format="mjd").jyear,
                                                       d_east=r.resid_east, d_north=r.resid_north, snr=np.nan)])], ignore_index=True)
    if len(arch):
        arch["pred_east_from_ref"], arch["pred_north_from_ref"] = np.nan, np.nan
        for i, r in arch.iterrows():
            pra, pdec = pos(A, Time(r.year, format="jyear"))
            e, n = sky_offset_arcsec(ref_ra, ref_dec, pra[0], pdec[0])
            arch.loc[i, "pred_east_from_ref"], arch.loc[i, "pred_north_from_ref"] = float(e), float(n)
        arch["meas_east_from_ref"] = arch.pred_east_from_ref + arch.d_east
        arch["meas_north_from_ref"] = arch.pred_north_from_ref + arch.d_north
        arch["resid_arcsec"] = np.hypot(arch.d_east, arch.d_north)
        # target too faint for the survey (WISE 0855: J~25, invisible on plates and in 2MASS; Eps Indi B
        # V~24, invisible on blue plates): any 'peak' there is a background star. Also reject any
        # archive centroid > 5" from the prediction (confusion, blends, saturation halos).
        inv = {"wise0855": ("DSS", "2MASS", "DASCH"), "eps_indi_b": ("DSS poss2ukstu_blue", "DSS poss1", "DASCH")}.get(key, ())
        arch["note"] = ""
        bad_inv = arch.source.str.startswith(inv) if inv else np.zeros(len(arch), bool)
        arch.loc[bad_inv, "note"] = "target too faint for this survey; peak is not the target"
        bad_far = (arch.resid_arcsec > np.where(arch.source.str.startswith("DASCH"), 10, 5)) & ~arch.source.str.startswith("SPHEREx")
        arch.loc[bad_far & ~bad_inv, "note"] = "nearest peak > 5 arcsec from prediction (confused or not detected)"
        arch.loc[bad_inv | bad_far, ["d_east", "d_north", "resid_arcsec"]] = np.nan
        arch["meas_east_from_ref"] = arch.pred_east_from_ref + arch.d_east
        arch["meas_north_from_ref"] = arch.pred_north_from_ref + arch.d_north
        arch.sort_values("year").to_csv(os.path.join(rd, f"{key}_decades_positions.csv"), index=False)
        good = arch[arch.resid_arcsec.notna()]
        if len(good) >= 2:
            g0, g1 = good.sort_values("year").iloc[0], good.sort_values("year").iloc[-1]
            summ.update(decades_first=f"{g0.source} {g0.year:.1f}", decades_last=f"{g1.source} {g1.year:.1f}",
                        decades_pred_shift_arcsec=float(np.hypot(g1.pred_east_from_ref - g0.pred_east_from_ref, g1.pred_north_from_ref - g0.pred_north_from_ref)),
                        decades_meas_shift_arcsec=float(np.hypot(g1.meas_east_from_ref - g0.meas_east_from_ref, g1.meas_north_from_ref - g0.meas_north_from_ref)),
                        decades_median_resid_arcsec=float(good.resid_arcsec.median()), decades_n_points=int(len(good)))
    # ---- spectra per pass
    cube = pd.read_csv(os.path.join(OUT, "cube", "cube_spectra.csv"))
    cube = cube[cube.target == key]
    fig, ax = plt.subplots(figsize=(7, 4), dpi=120)
    cols = plt.cm.viridis(np.linspace(0, 1, df["pass"].nunique()))
    for c, (p, g) in zip(cols, df.groupby("pass")):
        g = g[g.flux_best > 0]
        s = g.flux_method == "strict_epsf"
        lab = f"pass {p} {Time(g.mjd.median(), format='mjd').isot[:10]} (n={len(g)})" if len(g) else None
        ax.errorbar(g.wave_um[s], g.flux_best[s] / 1e3, g.err_best[s] / 1e3, fmt="o", ms=2.5, color=c, label=lab, lw=0.5)
        ax.plot(g.wave_um[~s], g.flux_best[~s] / 1e3, "x", ms=3, color=c, label=None if s.any() else lab)
    if len(cube):
        ax.plot(cube.wave_um, cube.flux_uJy / 1e3, "r-", lw=0.8, label="DR1 all-sky cube (aperture, no ap. corr.)")
    ax.set_yscale("log"); ax.set_xlabel("wavelength at target [um]"); ax.set_ylabel("flux [mJy]")
    ax.set_title(f"{LABEL[key]} - SPHEREx spectrum per pass (o strict ePSF, x saturated wing fit)", fontsize=8)
    ax.legend(fontsize=5, ncol=2); fig.tight_layout(); fig.savefig(os.path.join(pd_, f"{key}_spectra_per_pass.png")); plt.close(fig)
    # ---- light curve (relative to a reference spectrum)
    if key in ("rw_aur", "r_dra"):
        g = df[df.flux_best > 0].copy()
        lb = np.log(g.wave_um.values)
        bins = np.arange(np.log(0.74), np.log(5.1), 0.02)
        idx = np.digitize(lb, bins)
        ref = g.groupby(idx).flux_best.transform("median")
        g["dmag_vs_median_sed"] = -2.5 * np.log10(g.flux_best / ref)
        if len(cube) and cube.flux_uJy.notna().sum() > 20:
            cc = cube[cube.flux_uJy > 0]
            g["dmag_vs_cube"] = -2.5 * np.log10(g.flux_best / np.interp(g.wave_um, cc.wave_um, cc.flux_uJy))
        # pass-to-pass change at matched wavelength: each frame vs the nearest-wavelength frame
        # (|dlam|/lam < 1%, same detector) in the first pass. MEASURED, saturated stars = wing fits.
        p0 = g[g["pass"] == g["pass"].min()]
        dm = []
        for r in g.itertuples():
            q = p0[p0.detector == r.detector]
            if not len(q):
                dm.append(np.nan); continue
            j = int(np.argmin(np.abs(q.wave_um.values - r.wave_um)))
            dm.append(-2.5 * np.log10(r.flux_best / q.flux_best.values[j]) if abs(q.wave_um.values[j] - r.wave_um) / r.wave_um < 0.01 else np.nan)
        g["dmag_vs_pass0_matched"] = dm
        summ["lc_pass_vs_first_matched_median_mag"] = {f"pass{int(p)}_{Time(h.mjd.median(), format='mjd').isot[:10]}_{b}": float(np.nanmedian(h.dmag_vs_pass0_matched)) for (p, b), h in g.assign(b=np.where(g.detector <= 3, "D1-3", "D4-6")).groupby(["pass", "b"]) if h.dmag_vs_pass0_matched.notna().sum() >= 3}
        g.to_csv(os.path.join(rd, f"{key}_lightcurve.csv"), index=False)
        fig, axs = plt.subplots(2, 1, figsize=(7, 5), dpi=120, sharex=True)
        for ax, sel, nm in [(axs[0], g.detector <= 3, "D1-D3 (0.75-2.4 um)"), (axs[1], g.detector >= 4, "D4-D6 (2.4-5.0 um)")]:
            h = g[sel]
            sc = ax.scatter(Time(h.mjd, format="mjd").decimalyear, h.dmag_vs_median_sed, c=h.wave_um, s=6, cmap="plasma",
                            marker="o")
            hs = h[h.saturated]
            ax.scatter(Time(hs.mjd, format="mjd").decimalyear, hs.dmag_vs_median_sed, s=18, facecolors="none", edgecolors="k", lw=0.4, label="saturated (wing fit)")
            ax.invert_yaxis(); ax.set_ylabel("mag - median at same wavelength", fontsize=7); ax.set_title(nm, fontsize=7)
            plt.colorbar(sc, ax=ax, label="um"); ax.legend(fontsize=5)
        axs[1].set_xlabel("year")
        fig.suptitle(f"{LABEL[key]} - SPHEREx light curve (each point one exposure)", fontsize=8)
        fig.tight_layout(); fig.savefig(os.path.join(pd_, f"{key}_lightcurve.png")); plt.close(fig)
        summ["lc_scatter_mag_D13"] = float(g[g.detector <= 3].dmag_vs_median_sed.std())
        summ["lc_scatter_mag_D46"] = float(g[g.detector >= 4].dmag_vs_median_sed.std())
    # ---- matched-wavelength blink
    lamlo, lamhi = (3.9, 5.0) if key == "wise0855" else (0.75, 5.0)
    cand = df[(df.wave_um >= lamlo) & (df.wave_um <= lamhi)]
    if key == "wise0855":
        cand = cand[cand.w_snr > 3] if "w_snr" in cand else cand
    passes = sorted(cand["pass"].unique())
    # use the passes with most frames (max 4) and the frame set with the smallest wavelength spread
    pc = cand.groupby("pass").size().sort_values(ascending=False)
    use = sorted(pc.index[:4]) if key == "r_dra" else passes
    best = None
    for r0 in cand[cand["pass"] == use[0]].itertuples():
        sel = [r0]
        for p in use[1:]:
            g = cand[cand["pass"] == p]
            if not len(g):
                break
            sel.append(g.iloc[int(np.argmin(np.abs(g.wave_um.values - r0.wave_um)))])
        if len(sel) != len(use):
            continue
        spread = np.ptp([s.wave_um for s in sel]) / r0.wave_um
        score = spread - 0.002 * np.nanmin([getattr(s, "w_snr", 0) or 0 for s in sel]) / 100
        if best is None or score < best[0]:
            best = (score, sel)
    blink = []
    if best:
        half = 60.0
        sel = best[1]
        fig, axs = plt.subplots(1, len(sel) + 1, figsize=(2.6 * (len(sel) + 1), 2.9), dpi=130)
        imgs = []
        r_last = sel[-1]
        cra, cdec = r_last.pred_ra, r_last.pred_dec
        for ax, s in zip(axs, sel):
            st = R.load_stamp_fits(os.path.join(OUT, s.file))
            a = resample(st.image - np.nanmedian(st.image), st.wcs, cra, cdec, half, 1.5)
            imgs.append(a)
            e, n = sky_offset_arcsec(cra, cdec, s.pred_ra, s.pred_dec)
            show(ax, a, f"{s.date[:10]} D{s.detector} {s.wave_um:.3f}um", half, marks=[(e, n, "red", "o")])
            blink.append(dict(file=s.file, date=s.date, detector=s.detector, wave_um=s.wave_um, pred_east=float(e), pred_north=float(n)))
        d = imgs[-1] - imgs[0]
        show(axs[-1], d, "last - first", half, marks=[(b["pred_east"], b["pred_north"], c, "o") for b, c in [(blink[0], "cyan"), (blink[-1], "red")]])
        for ax in axs:
            ax.set_xlabel("E <-  offset [arcsec]", fontsize=5)
        fig.suptitle(f"{LABEL[key]}: SPHEREx matched-wavelength blink (north up, east left; red = predicted position at that date)", fontsize=7)
        fig.tight_layout(); fig.savefig(os.path.join(pd_, f"{key}_spherex_blink.png")); plt.close(fig)
        try:
            from matplotlib.animation import FuncAnimation, PillowWriter
            fig, ax = plt.subplots(figsize=(3.2, 3.2), dpi=110)
            imgs = [stretch(i)[0] for i in imgs]
            lo, hi = -1.5, max(np.nanpercentile(np.concatenate([i[np.isfinite(i)] for i in imgs]), 99.8), 3)
            im = ax.imshow(imgs[0], origin="lower", cmap="gray", vmin=lo, vmax=hi, extent=[half, -half, -half, half])
            ttl = ax.set_title("", fontsize=7)
            mk, = ax.plot([], [], "o", mfc="none", color="red", ms=14)

            def upd(k):
                im.set_data(imgs[k]); ttl.set_text(f"{blink[k]['date'][:10]} {blink[k]['wave_um']:.3f} um"); mk.set_data([blink[k]["pred_east"]], [blink[k]["pred_north"]])
                return im, ttl, mk
            FuncAnimation(fig, upd, frames=len(imgs)).save(os.path.join(pd_, f"{key}_spherex_blink.gif"), writer=PillowWriter(fps=1))
            plt.close(fig)
        except Exception as e:
            summ["gif_error"] = repr(e)[:80]
    json.dump(blink, open(os.path.join(rd, f"{key}_blink_set.json"), "w"), indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    summ["blink_set"] = [f"{b['date'][:10]} {b['wave_um']:.3f}um" for b in blink]
    # ---- decades montage + track plot
    sp = [p for p in panels]
    st_last = None
    if blink:
        st = R.load_stamp_fits(os.path.join(OUT, blink[-1]["file"]))
        bl = blink[-1]
        rr = df[df.file == bl["file"]].iloc[0]
        sp.append((Time(rr.mjd, format="mjd").jyear, f"SPHEREx {bl['date'][:10]} {bl['wave_um']:.2f}um", st.image - np.nanmedian(st.image), st.wcs, rr.pred_ra, rr.pred_dec))
    if sp:
        half = 60.0
        ncol = min(len(sp), 5); nrow = int(np.ceil(len(sp) / ncol)) + 1
        fig = plt.figure(figsize=(2.4 * ncol, 2.5 * nrow), dpi=120)
        ra26, dec26 = pos(A, Time(2026.5, format="jyear"))
        for k, (yr, ttl, img, w, pra, pdec) in enumerate(sp):
            ax = fig.add_subplot(nrow, ncol, k + 1)
            a = resample(img, w, pra, pdec, half, 1.0 if "SPHEREx" not in ttl else 1.5)
            e26, n26 = sky_offset_arcsec(pra, pdec, ra26[0], dec26[0])
            mk = [(0, 0, "red", "o")]
            if abs(e26) < half and abs(n26) < half:
                mk.append((float(e26), float(n26), "cyan", "+"))
            show(ax, a, ttl, half, mk)
        ax = fig.add_subplot(nrow, 1, nrow)
        tt = np.linspace(1950, 2027, 400)
        pra, pdec = pos(A, Time(tt, format="jyear"))
        e, n = sky_offset_arcsec(A["ra"], A["dec"], pra, pdec)
        ax.plot(tt, np.hypot(e, n) * np.sign(tt - A["ep"]), "k-", lw=0.7, label="predicted distance from adopted position (signed by time)")
        if len(arch):
            g = arch[arch.resid_arcsec.notna()]
            ax.plot(g.year, np.hypot(g.meas_east_from_ref, g.meas_north_from_ref) * np.sign(g.year - A["ep"]), "ro", ms=3, label="measured (DSS, 2MASS, unTimely, SPHEREx)")
        ax.set_xlabel("year", fontsize=6); ax.set_ylabel("arcsec", fontsize=6); ax.legend(fontsize=5); ax.tick_params(labelsize=5)
        fig.suptitle(f"{LABEL[key]}: 70 years of motion. Each image centred on the predicted position at its date (red circle); cyan + = 2026 position", fontsize=7)
        fig.tight_layout(); fig.savefig(os.path.join(pd_, f"{key}_decades_montage.png")); plt.close(fig)
    json.dump(summ, open(os.path.join(rd, f"{key}_summary.json"), "w"), indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    print(json.dumps(summ, default=lambda o: o.item() if hasattr(o, "item") else str(o))[:1500])


if __name__ == "__main__":
    for k in (sys.argv[1:] or list(ASTRO)):
        run(k)
