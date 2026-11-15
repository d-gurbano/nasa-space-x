"""A5 step 6: unWISE long baseline (2010-2020).
(a) unWISE tile list (tiles.fits) -> tile containing each target.
(b) unTimely catalog (Meisner et al. 2023, neo7): per-epoch detections from the
    time-resolved unWISE coadds, W2 (and W1 for Eps Indi B), 16 epochs ~2010-2020.
    Only the rows within 60" of the predicted track are kept (raw .cat.fits.gz files
    are deleted after extraction to save disk; URL + sha256 are logged in manifest).
(c) unwise.me full-depth cutouts (allwise = 2010-2011, neo7 = 2010-2020) for montages.
The time-resolved coadd IMAGES are not on unwise.me or the NERSC portal (404)."""
import os, io, gzip, tarfile, json, time
import numpy as np, pandas as pd, requests
from astropy.io import fits
from astropy.table import Table
from astropy.time import Time
from a5lib import OUT, radec_at, sky_offset_arcsec, manifest_add, sha256
from astrometry import ASTRO

U = "https://unwise.me/data/"
wd = os.path.join(OUT, "wise"); os.makedirs(wd, exist_ok=True)
tiles_fn = os.path.join(wd, "unwise_tiles.fits")
if not os.path.exists(tiles_fn):
    r = requests.get(U + "allwise/unwise-coadds/fulldepth/tiles.fits", timeout=120)
    open(tiles_fn, "wb").write(r.content); manifest_add(tiles_fn, r.url)
tiles = Table.read(tiles_fn).to_pandas()
tiles["coadd_id"] = tiles["coadd_id"].str.decode("ascii") if tiles["coadd_id"].dtype == object and isinstance(tiles["coadd_id"].iloc[0], bytes) else tiles["coadd_id"]
rows = []
summ = []
for key, A in ASTRO.items():
    ra, dec = radec_at(A["ra"], A["dec"], A["pmra"], A["pmdec"], A["plx"], A["ep"], Time(2015.5, format="jyear"))
    ra, dec = float(ra[0]), float(dec[0])
    d = np.hypot((tiles.ra - ra + 180) % 360 - 180, 0) * np.cos(np.radians(dec))
    sep = np.degrees(np.arccos(np.clip(np.sin(np.radians(dec)) * np.sin(np.radians(tiles.dec)) +
                                       np.cos(np.radians(dec)) * np.cos(np.radians(tiles.dec)) * np.cos(np.radians(tiles.ra - ra)), -1, 1)))
    tile = tiles.coadd_id.iloc[int(np.argmin(sep))].strip()
    print(key, tile, round(float(sep.min()), 3))
    bands = ["w1", "w2"] if key in ("eps_indi_b", "barnard", "rw_aur", "r_dra") else ["w2"]
    for b in bands:
        for e in range(16):
            url = f"{U}neo7/untimely-catalog/{tile[:3]}/{tile}/{tile}_{b}_e{e:03d}.cat.fits.gz"
            try:
                r = requests.get(url, timeout=180)
            except Exception as ex:
                summ.append(dict(target=key, band=b, epoch=e, status="ERR " + repr(ex)[:80])); continue
            if r.status_code != 200:
                summ.append(dict(target=key, band=b, epoch=e, status=r.status_code)); continue
            h = fits.open(io.BytesIO(gzip.decompress(r.content)))
            t = Table(h[1].data).to_pandas()
            mjd = float(np.nanmedian(t["MJDMEAN"])) if "MJDMEAN" in t else np.nan
            pra, pdec = radec_at(A["ra"], A["dec"], A["pmra"], A["pmdec"], A["plx"], A["ep"], Time(mjd, format="mjd"))
            de, dn = sky_offset_arcsec(pra[0], pdec[0], t["ra"].values, t["dec"].values)
            near = t[np.hypot(de, dn) < 60].copy()
            near["d_east_arcsec"] = de[np.hypot(de, dn) < 60]; near["d_north_arcsec"] = dn[np.hypot(de, dn) < 60]
            near["target"] = key; near["band"] = b; near["epoch"] = e; near["tile"] = tile
            near["pred_ra"] = pra[0]; near["pred_dec"] = pdec[0]; near["url"] = url
            near["sha256_gz"] = __import__("hashlib").sha256(r.content).hexdigest()
            rows.append(near)
            summ.append(dict(target=key, band=b, epoch=e, status=200, bytes=len(r.content), nrows=len(t), near=len(near), mjd=mjd))
            time.sleep(0.5)
        print(key, b, "done")
df = pd.concat(rows, ignore_index=True)
for c in df.columns:
    if df[c].dtype == object:
        df[c] = df[c].astype(str)
df.to_csv(os.path.join(wd, "untimely_near_targets.csv"), index=False)
pd.DataFrame(summ).to_csv(os.path.join(wd, "untimely_download_log.csv"), index=False)
manifest_add(os.path.join(wd, "untimely_near_targets.csv"), U + "neo7/untimely-catalog/ (extract, see untimely_download_log.csv)")

# (c) unwise.me cutouts (full depth) - W1+W2 image only, 61 px = 168"
for key, A in ASTRO.items():
    for ver, ep in [("allwise", 2010.6), ("neo7", 2015.5)]:
        fn = os.path.join(wd, f"{key}_unwise_{ver}.tar.gz")
        if os.path.exists(fn):
            continue
        ra, dec = radec_at(A["ra"], A["dec"], A["pmra"], A["pmdec"], A["plx"], A["ep"], Time(ep, format="jyear"))
        p = dict(version=ver, ra=f"{ra[0]:.6f}", dec=f"{dec[0]:.6f}", size="61", bands="12", file_img_m="on")
        r = requests.get("https://unwise.me/cutout_fits", params=p, timeout=180)
        open(fn, "wb").write(r.content); manifest_add(fn, r.url)
        time.sleep(1)
print("done")
