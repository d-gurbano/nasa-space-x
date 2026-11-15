"""A5 step 3: compact SPHEREx stamps (21x21 px = 129", IMAGE/FLAGS/VARIANCE/ZODI + ePSF
zone + WCS-WAVE table) for EVERY frame listed in frames/<key>_frames.csv, centred on
the proper-motion + parallax position at the exposure time. Pilot method: HTTPS byte
ranges on the public S3 bucket (code/A0/rewind.read_stamp_http).
Usage: python 03_stamps.py [target ...]   (default: all 5). Re-runnable (skips done)."""
import os, sys, time, traceback
import numpy as np, pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from astropy.time import Time
from a5lib import OUT, radec_at, TARGETS
from astrometry import ASTRO
import rewind as R

HALF = 10
NTHREAD = 12


def do_one(key, row, A, sdir):
    fn = os.path.join(sdir, f"{row.obs_id}_D{row.detector}_{row.obs_collection.replace('spherex_', '')}.fits")
    if os.path.exists(fn):
        return dict(file=fn, status="exists")
    t_mid = row.t_min + 57.56 / 86400.0  # MJD-AVG = MJD-BEG + 57.56 s (pilot lesson)
    ra, dec = radec_at(A["ra"], A["dec"], A["pmra"], A["pmdec"], A["plx"], A["ep"], Time(t_mid, format="mjd"))
    ra, dec = float(ra[0]), float(dec[0])
    try:
        st = R.read_stamp_http("ibe/data/spherex/" + row.key, ra, dec, half=HALF)
    except Exception as e:
        return dict(file=fn, status="fail", err=repr(e)[:200])
    lam, bw = R.wavelength_at(st.wave_table, st.meta["x_full"], st.meta["y_full"])
    R.save_stamp_fits(st, fn, extra=dict(PREDRA=ra, PREDDEC=dec, WAVEUM=lam, BWUM=bw,
                                         XFULLT=float(st.meta["x_full"]), YFULLT=float(st.meta["y_full"])))
    return dict(file=fn, status="ok", obs_id=row.obs_id, detector=row.detector, collection=row.obs_collection,
                mjd_avg=st.header.get("MJD-AVG"), pred_ra=ra, pred_dec=dec, wave_um=lam, bw_um=bw,
                x_full=st.meta["x_full"], y_full=st.meta["y_full"], s3_key=row.key, bytes_read=st.meta["bytes"],
                t_read=st.meta["t_read"])


def run(key):
    A = ASTRO[key]
    fr = pd.read_csv(os.path.join(OUT, "frames", f"{key}_frames.csv")).drop_duplicates("key")
    if os.environ.get("A5_REVERSE"):  # second worker walks the list from the end (re-run safe: skips existing)
        fr = fr.iloc[::-1]
    sdir = os.path.join(OUT, "stamps", key); os.makedirs(sdir, exist_ok=True)
    idx_path = os.path.join(OUT, "stamps", f"{key}_index{'_rev' if os.environ.get('A5_REVERSE') else ''}.csv")
    done = pd.read_csv(idx_path) if os.path.exists(idx_path) else pd.DataFrame()
    out = []
    t0 = time.time()
    with ThreadPoolExecutor(NTHREAD) as ex:
        futs = [ex.submit(do_one, key, r, A, sdir) for r in fr.itertuples()]
        for i, f in enumerate(as_completed(futs)):
            res = f.result()
            if res["status"] != "exists":
                out.append(res)
            if i % 50 == 0:
                print(key, i, len(fr), round(time.time() - t0), res["status"], flush=True)
            if len(out) and len(out) % 100 == 0:
                pd.concat([done, pd.DataFrame(out)]).to_csv(idx_path, index=False)
    allr = pd.concat([done, pd.DataFrame(out)], ignore_index=True)
    allr.to_csv(idx_path, index=False)
    print(key, "done", (allr.status == "ok").sum(), "ok", (allr.status == "fail").sum(), "fail", round(time.time() - t0), "s", flush=True)


if __name__ == "__main__":
    keys = sys.argv[1:] or ["barnard", "eps_indi_b", "wise0855", "rw_aur", "r_dra"]
    for k in keys:
        run(k)
