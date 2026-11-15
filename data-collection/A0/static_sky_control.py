"""Static-sky control: measure the SAME sky position (where the moving object was in
frame k) in other-epoch frames (found with IRSA SIA2) when the object was elsewhere.
Whatever flux shows up there is the star/galaxy background the object was sitting on.

usage: python code/A0/static_sky_control.py piazzia 8
"""
import os, sys, time
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(__file__))
import rewind as R

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(ROOT, "data", "00-pilot")


def run(tag, nmax=8, min_dt_days=3.0, collection="spherex_dr1"):
    ph = pd.read_csv(os.path.join(OUT, "tables", f"{tag}_photometry.csv"))
    ph = ph[ph.status == "ok"]
    # one frame per observation group, spread over detectors
    pick = ph.groupby("det").head(2).head(nmax)
    rows = []
    for r in pick.itertuples():
        t0 = time.time()
        s = R.sia2_query(r.ra, r.dec, collection=collection)
        t_sia = time.time() - t0
        s = s[(np.abs(s.t_min - r.mjd_mid) > min_dt_days)]
        det = r.det
        s = s[s.access_url.str.contains(f"{r.observationid[:0]}") & s.access_url.str.contains(f"D{det[1]}_spx")]
        if len(s) == 0:
            rows.append(dict(file=r.file, det=det, status="no_other_epoch", t_sia=t_sia))
            continue
        o = s.iloc[len(s) // 2]
        uri = "ibe/" + o.access_url.split("/ibe/", 1)[1]
        st = R.read_stamp_http(uri, r.ra, r.dec, half=20)
        p = R.forced_phot(st, r.ra, r.dec)
        rows.append(dict(file=r.file, det=det, mjd_obj=r.mjd_mid, flux_obj_uJy=r.flux_uJy, err_obj_uJy=r.err_uJy,
                         wave_obj=r.wave_um, other_obs=o.obs_id, other_mjd=o.t_min, n_other_epochs=len(s),
                         status=p.get("status"), flux_static_uJy=p.get("flux_uJy"), err_static_uJy=p.get("err_uJy"),
                         wave_static=p.get("wave_um"), snr_static=p.get("snr"), t_sia=t_sia))
        time.sleep(0.5)
    df = pd.DataFrame(rows)
    df["static_frac_of_obj"] = df.flux_static_uJy / df.flux_obj_uJy
    df.to_csv(os.path.join(OUT, "tables", f"{tag}_static_sky_control.csv"), index=False)
    print(df.round(3).to_string())
    return df


if __name__ == "__main__":
    run(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 8)
