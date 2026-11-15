"""A5 step 4: SPHEREx DR1 all-sky 102-channel HiPS cube spectrum at each target.
Source: s3://nasa-irsa-spherex/dr1/hips5_cube/hips_20261026/Norder5/DirD/NpixN_cube.fits
(HEALPix order-5 nested tiles, 512x512 px each, HPX projection, ~12.9"/px, 102 planes).
Only a 15x15 px box per plane is read (HTTPS byte ranges; ~6 KB per plane per HDU).
Photometry: aperture r=2.5 px (32") minus median annulus 4-7 px, summed MJy/sr*sr -> uJy.
No aperture correction (ESTIMATED: ~5-15% low for a point source). Saves box cubes too."""
import os, io, json
import numpy as np, pandas as pd
import astropy.units as u
from astropy.io import fits
from astropy.wcs import WCS
from astropy.time import Time
from astropy_healpix import HEALPix
from concurrent.futures import ThreadPoolExecutor
from a5lib import OUT, radec_at, manifest_add
from astrometry import ASTRO, EPS_INDI_A
import rewind as R

BASE = "https://nasa-irsa-spherex.s3.amazonaws.com/dr1/hips5_cube/hips_20261026/Norder5/"
hp = HEALPix(32, "nested")
cd = os.path.join(OUT, "cube"); os.makedirs(cd, exist_ok=True)
H = 7


def layout(url):
    st = dict(bytes=0, requests=0)
    off, lay = 0, {}
    for k in range(8):
        try:
            h, hl = R._read_header(url, off, st)
        except Exception:
            break
        name = h.get("EXTNAME", "PRIMARY") if k else "PRIMARY"
        dl = R._data_len(h)
        lay[name] = (h, off, off + hl, dl)
        off += hl + dl
    return lay


targets = dict(ASTRO); targets["eps_indi_A"] = EPS_INDI_A
rows = []
for key, A in targets.items():
    # cube built from 2025-07..2026-02 data (header DATE-BEG/END of tile; checked per tile below)
    ra, dec = radec_at(A["ra"], A["dec"], A["pmra"], A["pmdec"], A["plx"], A["ep"], Time(2025.9, format="jyear"))
    ra, dec = float(ra[0]), float(dec[0])
    npix = int(hp.lonlat_to_healpix(ra * u.deg, dec * u.deg))
    url = BASE + f"Dir{(npix // 10000) * 10000}/Npix{npix}_cube.fits"
    lay = layout(url)
    hI = lay["IMAGE"][0]
    h2 = fits.Header()
    for c in hI.cards:
        k = c.keyword
        if k in ("NAXIS3", "WCSAXES") or k.endswith("3") and k[:-1] in ("CTYPE", "CNAME", "CUNIT", "CRPIX", "CDELT", "CRVAL") or k.startswith(("PS3_", "PV3_", "PC3_")) or k in ("PC1_3", "PC2_3"):
            continue
        h2[k] = c.value
    h2["NAXIS"] = 2; h2["WCSAXES"] = 2
    w = WCS(h2)
    x, y = w.all_world2pix([[ra, dec]], 0)[0]
    xi, yi = int(round(x)), int(round(y))
    print(key, npix, list(lay), x, y, lay["PRIMARY"][0].get("DATE-BEG"), lay["PRIMARY"][0].get("DATE-END"))
    if not (H <= xi < 512 - H and H <= yi < 512 - H):
        print("  WARNING near tile edge", xi, yi)
    nx = 512

    def plane_box(ext, k, bitpix=4, dt=">f4"):
        h, _, dloc, _ = lay[ext]
        start = dloc + (k * 512 * 512 + (yi - H) * nx) * bitpix
        raw = R._range(url, start, (2 * H + 1) * nx * bitpix)
        a = np.frombuffer(raw, dtype=dt).reshape(2 * H + 1, nx)[:, xi - H:xi + H + 1]
        return a
    exts = [e for e in lay if e not in ("PRIMARY",) and lay[e][0].get("NAXIS") == 3]
    with ThreadPoolExecutor(8) as ex:
        cubes = {}
        for e in exts:
            dt = ">f4" if lay[e][0]["BITPIX"] == -32 else ">i4"
            cubes[e] = np.array(list(ex.map(lambda k: plane_box(e, k, 4, dt), range(102))))
    # spectral channel table
    sc_ext = [e for e in lay if "SPECTRAL" in e or e == "WCS-WAVE"]
    tabs = {}
    for e in sc_ext:
        h, off, dloc, dl = lay[e]
        raw = R._range(url, off, (dloc - off) + dl)
        prim = fits.PrimaryHDU().header.tostring().encode()
        tabs[e] = fits.open(io.BytesIO(prim + raw))[1].data
    chan = pd.DataFrame(np.array(tabs["SPECTRAL_CHANNELS"]).tolist(), columns=tabs["SPECTRAL_CHANNELS"].names)
    # save the box cube
    hb = w[yi - H:yi + H + 1, xi - H:xi + H + 1].to_header()
    hl = fits.HDUList([fits.PrimaryHDU(header=fits.Header(lay["PRIMARY"][0]))])
    for e, c in cubes.items():
        hh = hb.copy(); hh["EXTNAME"] = e; hh["BUNIT"] = lay[e][0].get("BUNIT", "")
        hl.append(fits.ImageHDU(c, header=hh))
    hl.append(fits.BinTableHDU(tabs["SPECTRAL_CHANNELS"], name="SPECTRAL_CHANNELS"))
    fn = os.path.join(cd, f"{key}_cube_box15.fits"); hl.writeto(fn, overwrite=True)
    manifest_add(fn, url + " (15x15 px x 102 plane byte-range subset)")
    # photometry
    img = cubes["IMAGE"]
    j, i = np.mgrid[0:2 * H + 1, 0:2 * H + 1]
    xs, ys = x - (xi - H), y - (yi - H)
    rr = np.hypot(i - xs, j - ys)
    pixsr = hp.pixel_area.to(u.sr).value / (512 ** 2)
    for k in range(102):
        p = img[k]
        ann = (rr >= 4) & (rr <= 7) & np.isfinite(p)
        ap = (rr <= 2.5)
        bk = np.nanmedian(p[ann]) if ann.sum() > 5 else np.nan
        f = np.nansum(p[ap] - bk) * pixsr * 1e12 if np.isfinite(p[ap]).all() else np.nan
        sd = np.nanstd(p[ann]) * np.sqrt(ap.sum()) * pixsr * 1e12
        rows.append(dict(target=key, channel=k, detector=int(chan.DETECTOR[k]), wave_um=float(chan.WAVELENGTH[k]),
                         bw_um=float(chan.BANDWIDTH[k]), flux_uJy=f, err_bkg_uJy=sd,
                         ab_mag=-2.5 * np.log10(f * 1e-6 / 3631) if f > 0 else np.nan,
                         peak_MJysr=float(np.nanmax(p[rr <= 1.5])) if np.isfinite(p[rr <= 1.5]).any() else np.nan,
                         nhits_center=int(cubes["NHITS"][k][yi - (yi - H), xi - (xi - H)]) if "NHITS" in cubes else -1,
                         flags_center=int(cubes["FLAGS"][k][H, H]) if "FLAGS" in cubes else -1,
                         tile=url, ra_used=ra, dec_used=dec))
df = pd.DataFrame(rows)
df["flags_center_names"] = df.flags_center.apply(R.decode_flags)
df.to_csv(os.path.join(cd, "cube_spectra.csv"), index=False)
print(df.groupby("target").agg(n=("flux_uJy", "count"), med_ab=("ab_mag", "median"), nh=("nhits_center", "median")))
