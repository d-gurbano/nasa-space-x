"""A0 pilot runner: one object end to end (frames -> ephemeris -> pixels -> photometry
-> null controls -> stack -> PNG stamps).

usage (from project root, after `source env.sh`):
  python code/A0/run_pilot.py piazzia
  python code/A0/run_pilot.py s1
  python code/A0/run_pilot.py h2
"""
import os
import sys
import json
import time
import datetime as dt
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
import rewind as R  # noqa

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(ROOT, "data", "00-pilot")
EXPMID_S = 113.5826 / 2.0  # MJD-AVG = MJD-BEG + XPOSURE/2 (VERIFIED in header)


def ephemeris_table(hz_cmd, frames):
    mid = frames["mjd_start"].values + EXPMID_S / 86400.0
    eS = R.horizons_ephem(hz_cmd, mid, center=R.SPHEREX_CENTER)
    eG = R.horizons_ephem(hz_cmd, mid, center=R.GEOCENTER)
    from astropy.coordinates import SkyCoord
    import astropy.units as u
    cS = SkyCoord(eS.ra.values * u.deg, eS.dec.values * u.deg)
    cG = SkyCoord(eG.ra.values * u.deg, eG.dec.values * u.deg)
    cM = SkyCoord(frames.ra_obj.values * u.deg, frames.dec_obj.values * u.deg)
    out = frames.reset_index(drop=True).copy()
    out["mjd_mid"] = mid
    out["ra_sc"], out["dec_sc"] = eS.ra.values, eS.dec.values
    out["ra_geo"], out["dec_geo"] = eG.ra.values, eG.dec.values
    out["sep_sc_geo_arcsec"] = cS.separation(cG).arcsec
    out["sep_most_sc_arcsec"] = cM.separation(cS).arcsec
    out["sep_most_geo_arcsec"] = cM.separation(cG).arcsec
    for c in ["APmag", "T-mag", "N-mag", "delta", "r", "RA_3sigma", "DEC_3sigma"]:
        if c in eS.columns:
            out["hz_" + c.replace("-", "")] = eS[c].values
    return out


def process_frame(row, tag, nulls, half=20, save=True):
    rec = dict(file=row.file, observationid=row.observationid, det=row.productid,
               mjd_mid=row.mjd_mid, ra=row.ra_sc, dec=row.dec_sc)
    try:
        st = R.read_stamp_http(row.uri, row.ra_sc, row.dec_sc, half=half)
    except Exception as e:  # noqa
        rec.update(status="read_fail", error=str(e)[:200])
        return rec, None
    rec.update(t_read=st.meta["t_read"], bytes=st.meta["bytes"], requests=st.meta["requests"],
               zone_ok=st.meta["zone_ok"], mjd_avg_hdr=st.header.get("MJD-AVG"),
               dt_mid_s=(st.header.get("MJD-AVG", np.nan) - row.mjd_mid) * 86400,
               finast=st.header.get("FINAST"), psf_fwhm=st.header.get("PSF_FWHM"),
               sps_flags=st.header.get("SPS_FLAGS"), x_sc=st.header.get("X_SC"),
               y_sc=st.header.get("Y_SC"), z_sc=st.header.get("Z_SC"),
               l2dqa=st.header.get("L2DQAFLG"))
    p = R.forced_phot(st, row.ra_sc, row.dec_sc)
    rec.update({k: v for k, v in p.items()})
    p2 = R.forced_phot(st, row.ra_sc, row.dec_sc, bad_mask=R.BAD_MASK_WITH_OUTLIER)
    rec.update(status_mo=p2.get("status"), flux_mo_uJy=p2.get("flux_uJy"), err_mo_uJy=p2.get("err_uJy"))
    # geocentric position photometry (to see the parallax effect)
    pg = R.forced_phot(st, row.ra_geo, row.dec_geo)
    rec.update(flux_geo_uJy=pg.get("flux_uJy"), snr_geo=pg.get("snr"))
    if p.get("status") == "ok" and p.get("snr", 0) > 8:
        rec.update(R.psf_centroid(st, row.ra_sc, row.dec_sc))
    nl = []
    for j, (de, dn) in enumerate(nulls):
        r2, d2 = R.offset_radec(row.ra_sc, row.dec_sc, de, dn)
        q = R.forced_phot(st, r2, d2)
        nl.append(dict(file=row.file, null=j, status=q.get("status"), flux_uJy=q.get("flux_uJy"),
                       err_uJy=q.get("err_uJy"), wave_um=q.get("wave_um")))
    if save:
        d = os.path.join(OUT, "stamps_fits", tag)
        os.makedirs(d, exist_ok=True)
        R.save_stamp_fits(st, os.path.join(d, row.file.replace(".fits", "_stamp.fits")),
                          extra=dict(RAPRED=row.ra_sc, DECPRED=row.dec_sc, WAVEUM=p.get("wave_um", np.nan)))
    img, var, good = R.resample_north_up(st, row.ra_sc, row.dec_sc, half_arcsec=60, scale=2.0)
    return rec, (img, var, nl)


def run_object(tag, hz_cmd, frames, workers=6, half=20, n_null=24, png_each=True,
               expected=None):
    t0 = time.time()
    os.makedirs(os.path.join(OUT, "tables"), exist_ok=True)
    os.makedirs(os.path.join(OUT, "png", tag), exist_ok=True)
    eph = ephemeris_table(hz_cmd, frames)
    eph.to_csv(os.path.join(OUT, "tables", f"{tag}_ephemeris.csv"), index=False)
    t_eph = time.time() - t0
    nulls = R.null_offsets(n_null)
    recs, imgs, nullrows = [], {}, []
    with ThreadPoolExecutor(workers) as ex:
        futs = {ex.submit(process_frame, row, tag, nulls, half): row.file for row in eph.itertuples()}
        for f in futs:
            rec, extra = f.result()
            recs.append(rec)
            if extra is not None:
                imgs[rec["file"]] = extra[:2]
                nullrows += extra[2]
    t_pix = time.time() - t0 - t_eph
    res = pd.DataFrame(recs).sort_values("mjd_mid")
    if expected is not None:
        res = expected(res, eph)
    res.to_csv(os.path.join(OUT, "tables", f"{tag}_photometry.csv"), index=False)
    nul = pd.DataFrame(nullrows)
    nul.to_csv(os.path.join(OUT, "tables", f"{tag}_nulls.csv"), index=False)
    ok = res[res.status == "ok"]
    summary = dict(tag=tag, n_frames=len(res), n_ok=len(ok), n_read_fail=int((res.status == "read_fail").sum()),
                   status_counts=res.status.value_counts().to_dict(), t_ephemeris_s=round(t_eph, 1),
                   t_pixels_s=round(t_pix, 1), workers=workers,
                   median_t_read_s=float(res.t_read.median()) if "t_read" in res else None,
                   total_bytes=int(res.bytes.sum()) if "bytes" in res else None,
                   sep_sc_geo_arcsec_median=float(eph.sep_sc_geo_arcsec.median()),
                   sep_sc_geo_arcsec_max=float(eph.sep_sc_geo_arcsec.max()),
                   sep_most_sc_arcsec_median=float(eph.sep_most_sc_arcsec.median()),
                   sep_most_geo_arcsec_median=float(eph.sep_most_geo_arcsec.median()))
    # stacks: all, SWIR (D1-3), MWIR (D4-6)
    groups = {"all": ok, "D1-D3": ok[ok.det.isin(["D1", "D2", "D3"])], "D4-D6": ok[ok.det.isin(["D4", "D5", "D6"])]}
    for g, sub in groups.items():
        F, E, S, n = R.weighted_stack(sub.flux_uJy, sub.err_uJy)
        Fg, Eg, Sg, _ = R.weighted_stack(sub.flux_geo_uJy, sub.err_uJy)
        Fmo, Emo, Smo, nmo = R.weighted_stack(sub.flux_mo_uJy, sub.err_mo_uJy)
        # null paths, same frames
        ns = []
        for j in range(n_null):
            q = nul[(nul.null == j) & nul.file.isin(sub.file) & (nul.status == "ok")]
            ns.append(R.weighted_stack(q.flux_uJy, q.err_uJy)[2])
        ns = np.array(ns, float)
        summary[f"stack_{g}"] = dict(n=n, flux_uJy=F, err_uJy=E, snr=S, snr_geo_pos=Sg, snr_outlier_masked=Smo,
                                     ab=(-2.5 * np.log10(F * 1e-6 / 3631) if F > 0 else None),
                                     null_snr_mean=float(np.nanmean(ns)), null_snr_std=float(np.nanstd(ns)),
                                     null_snr_max=float(np.nanmax(np.abs(ns))) if np.isfinite(ns).any() else None,
                                     snr_vs_nulls=(S - np.nanmean(ns)) / np.nanstd(ns) if np.nanstd(ns) > 0 else None,
                                     n_nulls_exceeding=int(np.sum(ns >= S)))
        # image stack (north-up, inverse-variance at the centre)
        st_imgs = [imgs[f] for f in sub.file if f in imgs]
        if st_imgs:
            A = np.array([a for a, v in st_imgs])
            W = np.array([1.0 / np.nanmedian(v) if np.nanmedian(v) > 0 else 0 for a, v in st_imgs])
            m = np.isfinite(A)
            num = np.nansum(np.where(m, A * W[:, None, None], 0), 0)
            den = np.sum(np.where(m, W[:, None, None], 0), 0)
            stack = np.where(den > 0, num / den, np.nan)
            from astropy.io import fits
            fits.writeto(os.path.join(OUT, "png", tag, f"stack_{g}.fits"), stack.astype(np.float32), overwrite=True)
            R.save_png(stack, os.path.join(OUT, "png", tag, f"stack_{g}.png"),
                       title=f"{tag} stack {g} n={len(st_imgs)} PSF S/N={S:.1f}")
            med = np.nanmedian(A, 0)
            R.save_png(med, os.path.join(OUT, "png", tag, f"median_{g}.png"),
                       title=f"{tag} median {g} n={len(st_imgs)}")
    if png_each:
        for r in ok.itertuples():
            if r.file in imgs:
                R.save_png(imgs[r.file][0], os.path.join(OUT, "png", tag, r.file.replace(".fits", ".png")),
                           title=f"{r.observationid} {r.det} {r.wave_um:.3f}um S/N={r.snr:.1f}")
    summary["t_total_s"] = round(time.time() - t0, 1)
    json.dump(summary, open(os.path.join(OUT, "tables", f"{tag}_summary.json"), "w"), indent=1, default=float)
    print(json.dumps(summary, indent=1, default=float))
    return res, nul, summary


# ------------------------------------------------------------------ targets
def expected_piazzia(res, eph):
    m = eph.set_index("file")["hz_APmag"]
    res["V_horizons"] = res.file.map(m)
    res["ab_expected_solar"] = [R.expected_ab_reflected(v, w) if np.isfinite(w) else np.nan
                                for v, w in zip(res.V_horizons, res.wave_um.fillna(np.nan))]
    res["ab_meas_minus_exp"] = res.ab_mag - res.ab_expected_solar
    return res


def main(which):
    if which == "piazzia":
        d = R.most_query("1000", "2025-05-01", "2026-11-10", cache=os.path.join(OUT, "tmp", "most_1000.txt"))
        fr = d[d.mjd_start.astype(int).isin([60930, 60931, 60932])].sort_values("mjd_start")
        return run_object("piazzia", "1000;", fr, expected=expected_piazzia)
    if which == "s1":
        d = R.most_query("C/2026 S1", "2026-09-10", "2026-09-16", cache=os.path.join(OUT, "tmp", "most_s1_brief.txt"))
        fr = d[d.mjd_start < 61299.0].sort_values("mjd_start")  # before 2026-09-16 00:00 UTC (discovery date)
        return run_object("C2026S1", "DES=C/2026 S1;CAP;NOFRAG", fr)
    if which == "h2":
        d = R.most_query("C/2026 H2", "2026-03-15", "2026-04-16", cache=os.path.join(OUT, "tmp", "most_h2.txt"))
        fr = d[d.mjd_start < 61146.0].sort_values("mjd_start")  # before 2026-04-16 00:00 UTC
        return run_object("C2026H2", "DES=C/2026 H2;CAP;NOFRAG", fr)


if __name__ == "__main__":
    main(sys.argv[1])
