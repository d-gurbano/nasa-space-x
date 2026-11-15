"""A5 step 5: SIMBAD (Harvard mirror; CDS Strasbourg returned 404 on Nov 14-15 2026),
AAVSO VSX JSON (needs a browser-like User-Agent, plain requests got 403), and VizieR
(Harvard mirror) VSX + General Catalogue of Variable Stars rows. Saved raw."""
import os, json, time
import requests
from a5lib import OUT, manifest_add

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 Chrome/120 Safari/537.36"}
rd = os.path.join(OUT, "refs"); os.makedirs(rd, exist_ok=True)
NAMES = {"barnard": "Barnard's star", "eps_indi_b": "eps Ind B", "eps_indi_A": "eps Ind A",
         "wise0855": "WISE J085510.83-071442.5", "rw_aur": "RW Aur", "r_dra": "R Dra",
         "eps_indi_Ba": "eps Ind Ba", "eps_indi_Bb": "eps Ind Bb"}
log = []
for k, n in NAMES.items():
    for nm, url, p, ext in [
        ("simbad", "https://simbad.harvard.edu/simbad/sim-id", {"Ident": n, "output.format": "ASCII"}, "txt"),
        ("vsx", "https://www.aavso.org/vsx/index.php", {"view": "api.object", "ident": n, "format": "json"}, "json"),
    ]:
        fn = os.path.join(rd, f"{k}_{nm}.{ext}")
        if os.path.exists(fn) and os.path.getsize(fn) > 0:
            continue
        try:
            r = requests.get(url, params=p, headers=UA, timeout=60)
            open(fn, "wb").write(r.content)
            manifest_add(fn, r.url)
            log.append(dict(target=k, service=nm, status=r.status_code, bytes=len(r.content), url=r.url))
        except Exception as e:
            log.append(dict(target=k, service=nm, status="ERR " + repr(e)[:100]))
        time.sleep(1.5)
# VizieR (Harvard mirror): GCVS for RW Aur / R Dra
for k, n in [("rw_aur", "RW Aur"), ("r_dra", "R Dra")]:
    for cat in ["B/gcvs/gcvs_cat", "B/vsx/vsx"]:
        p = {"-source": cat, "-c": n, "-c.rs": "30", "-out.all": ""}
        fn = os.path.join(rd, f"{k}_vizier_{cat.replace('/', '_')}.tsv")
        if os.path.exists(fn):
            continue
        r = requests.get("https://vizier.cfa.harvard.edu/viz-bin/asu-tsv", params=p, headers=UA, timeout=60)
        open(fn, "wb").write(r.content); manifest_add(fn, r.url)
        log.append(dict(target=k, service="vizier " + cat, status=r.status_code, bytes=len(r.content), url=r.url))
        time.sleep(1.5)
json.dump(log, open(os.path.join(rd, "refs_log.json"), "a"), indent=1)
for l in log:
    print(l)
