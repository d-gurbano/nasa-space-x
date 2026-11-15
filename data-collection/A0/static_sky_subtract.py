"""Static-sky (template) subtraction at the object's predicted positions.
For each object frame k (position p_k, detector D), find other-epoch frames of the
same detector covering p_k (IRSA SIA2, qr3 + dr1), at least `min_dt` days away, and
measure forced photometry at p_k there. The median of those is the static sky
(stars/galaxies) at p_k; flux_k - static_k is the object's own flux. Wavelengths
differ between epochs (LVF), so this is approximate for sources with steep SEDs.

usage: python code/A0/static_sky_subtract.py C2026H2 D3 3
"""
import os, sys, json, time
import numpy as np, pandas as pd
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(__file__))
import rewind as R
OUT = os.path.join(os.path.dirname(__file__), "..", "..", "data", "00-pilot")


def one(r, n_other, min_dt):
    rec = dict(file=r.file, det=r.det, mjd=r.mjd_mid, ra=r.ra, dec=r.dec, flux_uJy=r.flux_uJy,
               err_uJy=r.err_uJy, wave_um=r.wave_um)
    frames = []
    for coll in ["spherex_qr3", "spherex_dr1"]:
        try:
            s = R.sia2_query(r.ra, r.dec, collection=coll)
            frames.append(s)
        except Exception as e:  # noqa
            rec[f"sia_err_{coll}"] = str(e)[:100]
    s = pd.concat(frames) if frames else pd.DataFrame()
    if len(s) == 0:
        rec["status"] = "no_sia"
        return rec
    s = s[(np.abs(s.t_min - r.mjd_mid) > min_dt) & s.access_url.str.contains(f"{r.det}_spx")]
    rec["n_other_available"] = len(s)
    if len(s) == 0:
        rec["status"] = "no_other_epoch"
        return rec
    idx = np.linspace(0, len(s) - 1, min(n_other, len(s))).astype(int)
    fl, er, wv = [], [], []
    for i in idx:
        o = s.iloc[i]
        uri = "ibe/" + o.access_url.split("/ibe/", 1)[1]
        try:
            st = R.read_stamp_http(uri, r.ra, r.dec, half=15)
            p = R.forced_phot(st, r.ra, r.dec, r_in=6, r_out=12)
            if p.get("status") == "ok":
                fl.append(p["flux_uJy"]); er.append(p["err_uJy"]); wv.append(p["wave_um"])
        except Exception as e:  # noqa
            pass
    rec.update(n_static=len(fl), static_flux_uJy=float(np.median(fl)) if fl else np.nan,
               static_err_uJy=(1.2533 * np.median(er) / np.sqrt(len(er))) if er else np.nan,
               static_waves=";".join(f"{w:.3f}" for w in wv), status="ok" if fl else "static_fail")
    return rec


def run(tag, det, n_other=3, min_dt=5.0, nmax=None, workers=4):
    t0 = time.time()
    ph = pd.read_csv(os.path.join(OUT, "tables", f"{tag}_photometry.csv"))
    ph = ph[(ph.status == "ok") & (ph.det == det)]
    if nmax:
        ph = ph.iloc[np.linspace(0, len(ph) - 1, min(nmax, len(ph))).astype(int)]
    with ThreadPoolExecutor(workers) as ex:
        rows = list(ex.map(lambda r: one(r, n_other, min_dt), ph.itertuples()))
    df = pd.DataFrame(rows)
    df["diff_flux_uJy"] = df.flux_uJy - df.static_flux_uJy
    df["diff_err_uJy"] = np.hypot(df.err_uJy, df.static_err_uJy)
    df.to_csv(os.path.join(OUT, "tables", f"{tag}_{det}_static_subtracted.csv"), index=False)
    ok = df[df.status == "ok"]
    s_raw = R.weighted_stack(ok.flux_uJy, ok.err_uJy)
    s_dif = R.weighted_stack(ok.diff_flux_uJy, ok.diff_err_uJy)
    s_difr = R.robust_stack(ok.diff_flux_uJy, ok.diff_err_uJy)
    out = dict(tag=tag, det=det, n=len(ok), t_s=round(time.time() - t0, 1),
               raw_ivw=[round(float(x), 2) for x in s_raw[:3]], diff_ivw=[round(float(x), 2) for x in s_dif[:3]],
               diff_clipped=[round(float(x), 2) for x in s_difr[:3]],
               diff_median_frame_snr=round(float(np.median(ok.diff_flux_uJy / ok.diff_err_uJy)), 2),
               diff_frac_positive=round(float(np.mean(ok.diff_flux_uJy > 0)), 2))
    json.dump(out, open(os.path.join(OUT, "tables", f"{tag}_{det}_static_subtracted_summary.json"), "w"), indent=1)
    print(df[["file", "wave_um", "flux_uJy", "static_flux_uJy", "n_static", "diff_flux_uJy", "diff_err_uJy"]].round(1).to_string())
    print(json.dumps(out))


if __name__ == "__main__":
    run(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 3,
        nmax=int(sys.argv[4]) if len(sys.argv) > 4 else None)
