"""A5 step 1: catalog astrometry/photometry for the 5 challenge targets.
Gaia DR3 (IRSA mirror gaia_dr3_source, ESA archive timed out), CatWISE2020, AllWISE,
2MASS PSC - all via IRSA Simple Cone Search. Writes catalogs/*.csv and targets.json."""
import os, json
import numpy as np
from astropy.time import Time
from a5lib import TARGETS, OUT, scs, radec_at, manifest_add

cat_dir = os.path.join(OUT, "catalogs")
os.makedirs(cat_dir, exist_ok=True)
log = []
adopted = {}
for key, T in TARGETS.items():
    print("==", key)
    res = {}
    # Gaia DR3 cone around the 2016 position
    g, url = scs("gaia_dr3_source", T["ra"], T["dec"], 0.01)
    if key == "eps_indi_b":  # primary Eps Indi A (Gaia DR3 6412595290592307840 area, 2016 pos ~330.8737 -56.7978)
        gA, urlA = scs("gaia_dr3_source", 330.8737, -56.7978, 0.01)
        pA = os.path.join(cat_dir, "eps_indi_A_gaia_dr3_cone.csv")
        gA.write(pA, overwrite=True, format="csv"); manifest_add(pA, urlA); log.append(("gaia_dr3_source", "eps_indi_A", urlA, len(gA)))
    p = os.path.join(cat_dir, f"{key}_gaia_dr3_cone.csv")
    g.write(p, overwrite=True, format="csv"); manifest_add(p, url); log.append(("gaia_dr3_source", key, url, len(g)))
    # positions at ~2015.4 (CatWISE epoch) and 2000 (2MASS) for the WISE/2MASS cones
    for tab, ep, sr in [("catwise_2020", 2015.4, 0.012), ("allwise_p3as_psd", 2010.5, 0.012), ("fp_psc", 2000.0, 0.012)]:
        if key == "wise0855":
            # WISE 0855: PM -8.12"/yr in RA -> shift the cone centre (PM from Luhman & Esplin 2016)
            ra_c, dec_c = radec_at(133.7951, -7.2451, -8118, 680, 0, 2010.4, Time(ep, format="jyear"))
        elif key == "barnard":
            ra_c, dec_c = radec_at(T["ra"], T["dec"], -801.6, 10362.4, 547.0, 2016.0, Time(ep, format="jyear"))
        elif key == "eps_indi_b":
            ra_c, dec_c = radec_at(T["ra"], T["dec"], 3982.0, -2466.8, 270.7, 2016.0, Time(ep, format="jyear"))
        else:
            ra_c, dec_c = [T["ra"]], [T["dec"]]
        try:
            t, url = scs(tab, float(ra_c[0]), float(dec_c[0]), sr)
            p = os.path.join(cat_dir, f"{key}_{tab}_cone.csv")
            t.write(p, overwrite=True, format="csv"); manifest_add(p, url)
            log.append((tab, key, url, len(t)))
            print(tab, len(t))
        except Exception as e:
            log.append((tab, key, "FAILED " + repr(e)[:200], 0)); print(tab, "FAIL", e)
json.dump(log, open(os.path.join(cat_dir, "query_log.json"), "w"), indent=1)
