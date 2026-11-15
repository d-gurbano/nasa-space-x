"""A6: download small SPHEREx cutouts (IRSA IBE cutout service, anonymous) around 3I/ATLAS
for every exposure in IRSA's obscore_3I_Atlas.vot. Full frames are ~72 MB x 259 = ~18 GB, too big
for A6's 5 GB budget, so we take 0.08 deg cutouts (~47x47 px, ~5 MB each incl. PSF cube).
usage: python code/A6/get_3iatlas_cutouts.py"""
import re, time, hashlib, os, csv, datetime, requests
from astropy.table import Table
D = "data/06-composition/raw/comet3iatlas"
OUT = f"{D}/cutouts"; os.makedirs(OUT, exist_ok=True)
t = Table.read(f"{D}/obscore_3I_Atlas.vot")
urls = re.findall(r"https://[^ '\"]+\.fits", open(f"{D}/3IATLASImages-curl.sh").read())
man = "data/06-composition/manifest.csv"
rows = []
for r in t:
    det = str(r['spherex_detector']); det = det if det.startswith('D') else 'D' + det
    key = f"level2_{r['obs_id']}{det}_"
    m = [u for u in urls if key in u]
    if not m: print("no url", key); continue
    u = f"{m[0]}?center={r['comet_ra']:.6f},{r['comet_dec']:.6f}&size=0.08"
    fn = f"{OUT}/{os.path.basename(m[0]).replace('.fits','_3I_cut.fits')}"
    if not os.path.exists(fn) or os.path.getsize(fn) < 10000:
        for i in range(5):
            try:
                x = requests.get(u, timeout=300)
                if x.status_code == 200 and x.content[:6] == b"SIMPLE":
                    open(fn, "wb").write(x.content); break
                print("bad", x.status_code, key)
            except Exception as e: print("err", e)
            time.sleep(10 * (i + 1))
        time.sleep(1.0)
    if os.path.exists(fn):
        b = open(fn, "rb").read()
        rows.append([fn.replace("data/06-composition/", ""), u, len(b), hashlib.sha256(b).hexdigest(),
                     datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ")])
        print(len(rows), fn, flush=True)
with open(man, "a", newline="") as f: csv.writer(f).writerows(rows)
print("done", len(rows))
