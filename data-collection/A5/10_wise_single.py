"""A5 step 10: WISE / NEOWISE single-exposure (L1b) frames, 2010-2024.
IRSA IBE search per target (allsky 4band, 3band cryo, postcryo 2band, neowiser), then
IBE cutouts (100") of up to 2 W2 frames + 1 W1 frame per visit (visit = gap > 5 d),
centred on the PM position at the frame time. Checkpointed: re-runnable.
IRSA returned 502/timeouts often on Nov 15 2026; failures are logged, not fatal."""
import os, io, time, json
import numpy as np, pandas as pd, requests
from astropy.io import ascii
from astropy.time import Time
from a5lib import OUT, radec_at, manifest_add
from astrometry import ASTRO

wd = os.path.join(OUT, "wise", "single"); os.makedirs(wd, exist_ok=True)
SETS = [("allsky", "4band_p1bm_frm"), ("cryo_3band", "3band_p1bm_frm"), ("postcryo", "2band_p1bm_frm"), ("neowiser", "p1bm_frm")]
IBE = "https://irsa.ipac.caltech.edu/ibe/"
logf = os.path.join(wd, "log.jsonl")


def get(url, params=None, timeout=240, tries=4):
    last = None
    for k in range(tries):
        try:
            r = requests.get(url, params=params, timeout=timeout)
            if r.status_code == 200:
                return r
            last = r.status_code
        except Exception as e:
            last = repr(e)[:100]
        time.sleep(10 * (k + 1))
    raise RuntimeError(f"{url} {last}")


def log(d):
    open(logf, "a").write(json.dumps(d) + "\n"); print(d, flush=True)


for key, A in ASTRO.items():
    ra, dec = radec_at(A["ra"], A["dec"], A["pmra"], A["pmdec"], A["plx"], A["ep"], Time(2017.0, format="jyear"))
    for ds, tab in SETS:
        fn = os.path.join(wd, f"{key}_{ds}_frames.tbl")
        if not os.path.exists(fn):
            try:
                r = get(f"{IBE}search/wise/{ds}/{tab}", dict(POS=f"{ra[0]:.6f},{dec[0]:.6f}"))
                open(fn, "w").write(r.text); log(dict(target=key, ds=ds, step="search", status="ok", url=r.url))
            except Exception as e:
                log(dict(target=key, ds=ds, step="search", status="fail", err=str(e))); continue
            time.sleep(2)
        try:
            t = ascii.read(fn, format="ipac").to_pandas()
        except Exception:
            continue
        if not len(t):
            continue
        t = t.sort_values("mjd")
        t["visit"] = np.r_[0, np.cumsum(np.diff(t.mjd.values) > 5)]
        pick = []
        for v, g in t.groupby("visit"):
            pick += [r for _, r in g[g.band == 2].iloc[[0, len(g[g.band == 2]) // 2]].iterrows()] if (g.band == 2).sum() >= 2 else [r for _, r in g[g.band == 2].iterrows()]
            pick += [r for _, r in g[g.band == 1].iloc[:1].iterrows()]
        for r in pick:
            sid, fnum, b = str(r.scan_id).strip(), int(r.frame_num), int(r.band)
            out = os.path.join(wd, f"{key}_{ds}_{sid}{fnum:03d}_w{b}.fits")
            if os.path.exists(out):
                continue
            pra, pdec = radec_at(A["ra"], A["dec"], A["pmra"], A["pmdec"], A["plx"], A["ep"], Time(float(r.mjd), format="mjd"))
            url = f"{IBE}data/wise/{ds}/{tab}/{sid[-2:]}/{sid}/{fnum:03d}/{sid}{fnum:03d}-w{b}-int-1b.fits"
            try:
                rr = get(url, dict(center=f"{pra[0]:.6f},{pdec[0]:.6f}", size="100arcsec", gzip="false"), timeout=180)
                if not rr.content.startswith(b"SIMPLE"):
                    raise RuntimeError("not FITS")
                open(out, "wb").write(rr.content); manifest_add(out, rr.url)
                log(dict(target=key, ds=ds, step="cutout", status="ok", file=os.path.basename(out), mjd=float(r.mjd), visit=int(r.visit)))
            except Exception as e:
                log(dict(target=key, ds=ds, step="cutout", status="fail", url=url, err=str(e)[:150]))
            time.sleep(1.0)
print("done")
