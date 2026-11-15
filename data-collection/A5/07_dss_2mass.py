"""A5 step 7: decades baseline images.
DSS (STScI dss_search, all plate surveys) and 2MASS (IRSA 2MASS SIA v1 + Atlas image,
cut to 3' with Cutout2D; full Atlas image not kept). Every stamp is centred on the
proper-motion position at the plate/exposure date (two-step for DSS: a tiny request
gives DATE-OBS, then the real 5' request at the propagated position)."""
import os, io, time, json
import numpy as np, pandas as pd, requests
from astropy.io import fits
from astropy.io.votable import parse_single_table
from astropy.time import Time
from astropy.wcs import WCS
from astropy.nddata import Cutout2D
from astropy.coordinates import SkyCoord
import astropy.units as u
from a5lib import OUT, radec_at, manifest_add
from astrometry import ASTRO, EPS_INDI_A

dd = os.path.join(OUT, "dss"); os.makedirs(dd, exist_ok=True)
td = os.path.join(OUT, "2mass"); os.makedirs(td, exist_ok=True)
SURVEYS = ["poss1_blue", "poss1_red", "poss2ukstu_blue", "poss2ukstu_red", "poss2ukstu_ir", "quickv"]
DSS = "https://archive.stsci.edu/cgi-bin/dss_search"
UA = {"User-Agent": "Mozilla/5.0 Chrome/120"}
log = []


def plate_date(h):
    """DSS DATE-OBS sometimes has minutes > 59 (e.g. '1950-07-09T06:75:00'); parse by hand."""
    v = str(h.get("DATE-OBS", "")).strip()
    try:
        d, tm = (v.split("T") + ["00:00:00"])[:2]
        hh, mm, ss = (float(x) for x in (tm.split(":") + ["0", "0"])[:3])
        return Time(d) + (hh / 24 + mm / 1440 + ss / 86400) * u.day
    except Exception:
        return None


T = dict(ASTRO); T["eps_indi_A"] = EPS_INDI_A
for key, A in T.items():
    ra0, dec0 = radec_at(A["ra"], A["dec"], A["pmra"], A["pmdec"], A["plx"], A["ep"], Time(1990.0, format="jyear"))
    for sv in SURVEYS:
        fn = os.path.join(dd, f"{key}_{sv}.fits")
        if os.path.exists(fn):
            h2 = fits.getheader(fn); t2 = plate_date(h2)
            log.append(dict(target=key, survey=sv, status="ok (exists)", date=t2.isot if t2 else None, plate=h2.get("PLTLABEL"),
                            pred_ra=h2.get("PREDRA"), pred_dec=h2.get("PREDDEC")))
            continue
        try:
            r = requests.get(DSS, params=dict(v=sv, r=f"{ra0[0]:.6f}", d=f"{dec0[0]:.6f}", e="J2000", h="1", w="1", f="fits"), timeout=120, headers=UA)
            if not r.content.startswith(b"SIMPLE"):
                log.append(dict(target=key, survey=sv, status="no plate", note=r.text[:120])); continue
            h = fits.getheader(io.BytesIO(r.content))
            t = plate_date(h)
            ra, dec = radec_at(A["ra"], A["dec"], A["pmra"], A["pmdec"], A["plx"], A["ep"], t) if t else (ra0, dec0)
            r2 = requests.get(DSS, params=dict(v=sv, r=f"{ra[0]:.6f}", d=f"{dec[0]:.6f}", e="J2000", h="5", w="5", f="fits"), timeout=180, headers=UA)
            hl = fits.open(io.BytesIO(r2.content)); hl[0].header["PREDRA"] = float(ra[0]); hl[0].header["PREDDEC"] = float(dec[0])
            hl.writeto(fn, overwrite=True); manifest_add(fn, r2.url)
            h2 = fits.getheader(fn)
            t2 = plate_date(h2)
            log.append(dict(target=key, survey=sv, status="ok", date=t2.isot if t2 else None, plate=h2.get("PLTLABEL"),
                            pred_ra=float(ra[0]), pred_dec=float(dec[0]), bytes=len(r2.content), url=r2.url,
                            same_date=(t is not None and t2 is not None and abs((t - t2).jd) < 1)))
        except Exception as e:
            log.append(dict(target=key, survey=sv, status="ERR " + repr(e)[:150]))
        print(log[-1].get("target"), log[-1].get("survey"), log[-1].get("status"), log[-1].get("date"), flush=True)
        time.sleep(2)
pd.DataFrame(log).to_csv(os.path.join(dd, "dss_log.csv"), index=False)

# 2MASS
log2 = []
for key, A in T.items():
    ra0, dec0 = radec_at(A["ra"], A["dec"], A["pmra"], A["pmdec"], A["plx"], A["ep"], Time(1999.5, format="jyear"))
    try:
        r = requests.get("https://irsa.ipac.caltech.edu/cgi-bin/2MASS/IM/nph-im_sia",
                         params=dict(POS=f"{ra0[0]:.6f},{dec0[0]:.6f}", SIZE="0.001", FORMAT="image/fits"), timeout=180)
        tb = parse_single_table(io.BytesIO(r.content)).to_table(use_names_over_ids=True).to_pandas()
    except Exception as e:
        log2.append(dict(target=key, status="SIA ERR " + repr(e)[:150])); continue
    tb.to_csv(os.path.join(td, f"{key}_sia.csv"), index=False)
    urlcol = [c for c in tb.columns if "url" in c.lower() or "download" in c.lower()][0]
    bandcol = [c for c in tb.columns if c.lower() in ("band", "filter")]
    for i, row in tb.iterrows():
        band = str(row[bandcol[0]]).strip() if bandcol else str(i)
        fn = os.path.join(td, f"{key}_2mass_{band}_{i}.fits")
        if os.path.exists(fn):
            continue
        try:
            rr = requests.get(str(row[urlcol]).strip(), timeout=300)
            hd = fits.open(io.BytesIO(rr.content))
            h = hd[0].header
            date = h.get("DATE-OBS", h.get("ORDATE"))
            try:
                t = Time(h["DATE-OBS"] + ("T" + h["UT"] if "UT" in h and "T" not in h["DATE-OBS"] else ""))
            except Exception:
                t = Time(1999.5, format="jyear")
            ra, dec = radec_at(A["ra"], A["dec"], A["pmra"], A["pmdec"], A["plx"], A["ep"], t)
            w = WCS(h)
            c = Cutout2D(hd[0].data, SkyCoord(ra[0] * u.deg, dec[0] * u.deg), 180 * u.arcsec, wcs=w, mode="partial")
            hh = h.copy(); hh.update(c.wcs.to_header())
            hh["PREDRA"] = float(ra[0]); hh["PREDDEC"] = float(dec[0])
            fits.PrimaryHDU(c.data.astype(np.float32), header=hh).writeto(fn, overwrite=True)
            manifest_add(fn, str(row[urlcol]).strip() + " (3' Cutout2D by A5)")
            log2.append(dict(target=key, band=band, status="ok", date=t.isot, full_bytes=len(rr.content)))
        except Exception as e:
            log2.append(dict(target=key, band=band, status="ERR " + repr(e)[:150]))
        print(log2[-1], flush=True)
        time.sleep(1.5)
pd.DataFrame(log2).to_csv(os.path.join(td, "2mass_log.csv"), index=False)
