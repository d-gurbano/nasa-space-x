"""Time-shifted fake-path control + per-day consistency, using the saved stamps.
A real moving object should give signal only at dt=0 along its own path, and on
several independent days (each day is a different sky position).

usage: python code/A0/timeshift_control.py C2026S1 "DES=C/2026 S1;CAP;NOFRAG"
"""
import os, sys, json
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(__file__))
import rewind as R
OUT = os.path.join(os.path.dirname(__file__), "..", "..", "data", "00-pilot")
SHIFTS = [-0.3, -0.2, -0.1, -0.05, 0.0, 0.05, 0.1, 0.2, 0.3]


def run(tag, hz_cmd, dets=("D1", "D2", "D3")):
    ph = pd.read_csv(os.path.join(OUT, "tables", f"{tag}_photometry.csv"))
    ph = ph[ph.status == "ok"]
    ph = ph[ph.det.isin(dets)].reset_index(drop=True)
    rows = []
    for dt in SHIFTS:
        e = R.horizons_ephem(hz_cmd, ph.mjd_mid.values + dt, center=R.SPHEREX_CENTER)
        for k, r in ph.iterrows():
            st = R.load_stamp_fits(os.path.join(OUT, "stamps_fits", tag, r.file.replace(".fits", "_stamp.fits")))
            p = R.forced_phot(st, e.ra.iloc[k], e.dec.iloc[k])
            rows.append(dict(dt=dt, file=r.file, det=r.det, day=int(r.mjd_mid), status=p.get("status"),
                             flux_uJy=p.get("flux_uJy"), err_uJy=p.get("err_uJy"), psf=st.meta["psf"]))
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUT, "tables", f"{tag}_timeshift.csv"), index=False)
    summ = {}
    for dt, g in df[df.status == "ok"].groupby("dt"):
        F, E, S, n = R.robust_stack(g.flux_uJy, g.err_uJy)
        summ[f"dt={dt:+.2f}d"] = dict(n=n, flux_uJy=round(F, 2), snr=round(S, 2))
    z = df[(df.dt == 0) & (df.status == "ok")]
    perday = {}
    for d, g in z.groupby("day"):
        F, E, S, n = R.robust_stack(g.flux_uJy, g.err_uJy)
        perday[str(d)] = dict(n=n, flux_uJy=round(F, 2), err_uJy=round(E, 2), snr=round(S, 2))
    out = dict(timeshift=summ, per_day_dt0=perday)
    json.dump(out, open(os.path.join(OUT, "tables", f"{tag}_timeshift_summary.json"), "w"), indent=1)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    run(sys.argv[1], sys.argv[2])
