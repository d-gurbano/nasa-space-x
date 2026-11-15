"""A5 step 13: rebuild data/05-test-targets/manifest.csv from what is on disk.
Keeps the newest logged URL per file (manifest_add log), drops entries whose file was
removed, and adds every SPHEREx stamp (URL = S3 object it was cut from) and any file
written without a log line. Re-runnable."""
import os, glob, datetime
import pandas as pd
from a5lib import OUT, sha256

m = os.path.join(OUT, "manifest.csv")
old = pd.read_csv(m) if os.path.exists(m) else pd.DataFrame(columns=["filename", "url", "bytes", "sha256", "date"])
old = old.drop_duplicates("filename", keep="last")
url_of = dict(zip(old.filename, old.url))
# stamp -> S3 key
for key in ["barnard", "eps_indi_b", "wise0855", "rw_aur", "r_dra"]:
    fr = pd.read_csv(os.path.join(OUT, "frames", f"{key}_frames.csv"))
    for r in fr.itertuples():
        fn = f"stamps/{key}/{r.obs_id}_D{r.detector}_{r.obs_collection.replace('spherex_', '')}.fits"
        url_of.setdefault(fn, f"https://nasa-irsa-spherex.s3.amazonaws.com/{r.key} (byte-range 21x21 stamp)")
rows = []
today = str(datetime.date.today())
for p in sorted(glob.glob(os.path.join(OUT, "**", "*"), recursive=True)):
    if os.path.isdir(p) or p.endswith(("manifest.csv", "REPORT.md")) or "/logs/" in p:
        continue
    rel = os.path.relpath(p, OUT)
    rows.append(dict(filename=rel, url=url_of.get(rel, "derived by code/A5 (see REPORT.md)"),
                     bytes=os.path.getsize(p), sha256=sha256(p), date=today))
pd.DataFrame(rows).to_csv(m, index=False)
print(len(rows), "files,", round(sum(r["bytes"] for r in rows) / 1e6, 1), "MB")
