"""A5 step 2: list every SPHEREx L2 frame covering each target (SIA2 on IRSA, all
collections we know of), with times, detector, band. Position used = adopted
astrometry propagated to 2026.0 (motion over the mission is < 16", frames are 3.5 deg).
Writes frames/<key>_sia2_<collection>.csv and frames/<key>_frames.csv (deduplicated)."""
import os, io, json, time
import numpy as np, pandas as pd
from astropy.time import Time
from astropy.io.votable import parse_single_table
from a5lib import OUT, get, radec_at
from astrometry import ASTRO

COLLS = ["spherex_qr2", "spherex_qr3", "spherex_dr1", "spherex_qr2_deep", "spherex_qr3_deep",
         "spherex_dr1_deep", "spherex_deep"]
fd = os.path.join(OUT, "frames"); os.makedirs(fd, exist_ok=True)
log = []
for key, A in ASTRO.items():
    ra, dec = radec_at(A["ra"], A["dec"], A["pmra"], A["pmdec"], A["plx"], A["ep"], Time(2026.0, format="jyear"))
    ra, dec = float(ra[0]), float(dec[0])
    parts = []
    for c in COLLS:
        p = dict(COLLECTION=c, POS=f"CIRCLE {ra} {dec} 0.001", RESPONSEFORMAT="VOTABLE", MAXREC="20000")
        try:
            r = get("https://irsa.ipac.caltech.edu/SIA", p, timeout=300)
            t = parse_single_table(io.BytesIO(r.content)).to_table(use_names_over_ids=True)
            df = t.to_pandas()
            n = len(df)
            if n:
                df["collection_queried"] = c
                df.to_csv(os.path.join(fd, f"{key}_sia2_{c}.csv"), index=False)
                parts.append(df)
            log.append(dict(target=key, collection=c, n=n, url=r.url))
        except Exception as e:
            log.append(dict(target=key, collection=c, n=-1, url=repr(e)[:300]))
            n = -1
        print(key, c, n)
        time.sleep(1)
    if parts:
        df = pd.concat(parts, ignore_index=True)
        df["key"] = df["cloud_access"].str.extract(r'"key":\s*"([^"]+)"')[0]
        df["detector"] = df["energy_bandpassname"].str.extract(r"D(\d)")[0].astype(int)
        df["date"] = Time(df["t_min"].values, format="mjd").isot
        keep = ["obs_collection", "obs_id", "detector", "t_min", "t_max", "date", "em_min", "em_max",
                "s_ra", "s_dec", "key", "access_url", "obs_release_date"]
        df[keep].sort_values("t_min").to_csv(os.path.join(fd, f"{key}_frames.csv"), index=False)
json.dump(log, open(os.path.join(fd, "sia2_log.json"), "w"), indent=1)
