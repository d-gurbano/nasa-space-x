"""A1 - SBDB per-object records with full covariance (cov=mat), discovery info and close approaches for the top-N
of each ranked list, so B1/B3 can compute real uncertainty regions. Resumable. Usage: python fetch_cov_top.py [N]"""
import sys, pathlib, json, time
import pandas as pd
from common import get, save, D

N = int(sys.argv[1]) if len(sys.argv) > 1 else 150
out = D / "raw/sbdb_cov"
todo = []
for lst in ["a_spherex_precovery_candidates", "b_lost_recovery_candidates", "c_neowise_practice_cases"]:
    df = pd.read_parquet(D / f"lists/{lst}.parquet").head(N)
    todo += [(lst[0], str(s), str(d)) for s, d in zip(df["spkid"], df["designation"])]
seen = set()
for tag, spk, des in todo:
    if spk in seen: continue
    seen.add(spk)
    f = out / f"{spk}.json"
    if f.exists(): continue
    try:
        r = get("https://ssd-api.jpl.nasa.gov/sbdb.api", params={"spk": spk, "cov": "mat", "discovery": "1", "ca-data": "1", "phys-par": "1", "full-prec": "1"}, pause=1.0)
        save(f"sbdb_cov/{spk}.json", r.content, r.url)
    except Exception as ex:
        print("fail", des, ex)
print("done", len(seen))
