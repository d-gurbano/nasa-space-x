"""A5 step 11 (optional): Harvard DASCH plate availability + a few plates.
The official DASCH DR7 API (api.starglass.cfa.harvard.edu, POST /dasch/dr7/queryexps,
/cutout, /lightcurve; no login) takes JSON POST bodies. To keep strictly to GET-only
read access we use the GAVO (Heidelberg, partner) VO mirror of the DASCH plate
index: SIAP2 https://dc.g-vo.org/dasch/q/im/siap2.xml (GET). Its datalink gives
GET links to (downsampled) plate previews / cutouts. Partner justification: it is the
only GET-only route to the US (Harvard) DASCH holdings; data are Harvard's.
Counts all plates per target; downloads up to 3 datalink cutouts per target
(earliest, middle, latest plate with a cutout service), centred on the PM position."""
import os, io, time, json
import numpy as np, pandas as pd, requests
from astropy.io.votable import parse_single_table, parse
from astropy.time import Time
from a5lib import OUT, radec_at, manifest_add
from astrometry import ASTRO

dd = os.path.join(OUT, "dasch"); os.makedirs(dd, exist_ok=True)
SIA = "https://dc.g-vo.org/dasch/q/im/siap2.xml"
log = []
for key, A in ASTRO.items():
    ra, dec = radec_at(A["ra"], A["dec"], A["pmra"], A["pmdec"], A["plx"], A["ep"], Time(1930.0, format="jyear"))
    try:
        r = requests.get(SIA, params={"POS": f"CIRCLE {ra[0]:.5f} {dec[0]:.5f} 0.01", "MAXREC": "20000"}, timeout=300)
        t = parse_single_table(io.BytesIO(r.content)).to_table(use_names_over_ids=True).to_pandas()
        for c in t.columns:
            if t[c].dtype == object:
                t[c] = t[c].astype(str)
        fn = os.path.join(dd, f"{key}_dasch_siap2.csv"); t.to_csv(fn, index=False); manifest_add(fn, r.url)
        tcol = "t_min" if "t_min" in t else None
        yrs = Time(t[tcol].astype(float).values, format="mjd").jyear if tcol and len(t) else np.array([])
        log.append(dict(target=key, n_plates=len(t), first=float(np.nanmin(yrs)) if len(yrs) else None,
                        last=float(np.nanmax(yrs)) if len(yrs) else None, url=r.url))
        print(log[-1], flush=True)
        # a few cutouts via datalink (GET)
        if len(t) and "access_url" in t:
            t["yr"] = yrs
            t = t.sort_values("yr")
            t = t.sort_values('s_pixel_scale').head(max(10, len(t) // 3)).sort_values('yr')  # finer plate scales first
            picks = t.iloc[[0, len(t) // 2, len(t) - 1]] if len(t) >= 3 else t
            for _, row in picks.iterrows():
                try:
                    # SODA sync cutout (GET, fixed-size cutout per GAVO) at the PM position on that date
                    pr, pd_ = radec_at(A["ra"], A["dec"], A["pmra"], A["pmdec"], A["plx"], A["ep"], Time(row.yr, format="jyear"))
                    im = requests.get("http://dc.g-vo.org/dasch/q/dl/dlget", params={"ID": row.obs_publisher_did,
                                      "POS": f"CIRCLE {pr[0]:.5f} {pd_[0]:.5f} 0.05"}, timeout=300)
                    if im.content[:6] != b"SIMPLE":
                        raise RuntimeError("not FITS: " + im.text[:100])
                    fn = os.path.join(dd, f"{key}_dasch_{row.yr:.1f}_{row.dasch_id}.fits")
                    open(fn, "wb").write(im.content); manifest_add(fn, im.url)
                    log.append(dict(target=key, plate_year=float(row.yr), plate=row.dasch_id, instrument=row.instrument_name,
                                    file=os.path.basename(fn), bytes=len(im.content), pred_ra=float(pr[0]), pred_dec=float(pd_[0])))
                    print(log[-1], flush=True)
                except Exception as e:
                    log.append(dict(target=key, step="cutout", err=repr(e)[:150]))
                time.sleep(3)
    except Exception as e:
        log.append(dict(target=key, err=repr(e)[:200]))
        print(log[-1], flush=True)
    time.sleep(2)
json.dump(log, open(os.path.join(dd, "dasch_log.json"), "w"), indent=1, default=str)
