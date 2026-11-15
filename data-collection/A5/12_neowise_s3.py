"""A5 step 12: NEOWISE-R single-exposure detections (2013-12 .. 2024-08) and single-
exposure image stamps, from the IRSA AWS Open Data bucket s3://nasa-irsa-wise
(anonymous; IRSA web services returned 502 all night on Nov 15 2026).
(a) Catalog: wise/neowiser/catalogs/p1bs_psd/healpix_k5/<yearN>/...parquet, one file per
    HEALPix k5 pixel and year; we read only 14 columns and keep rows within 8" of the
    PM+parallax position at each row's MJD. Result: wise/neowise_p1bs_<key>.csv
(b) Images: one W2 (and one W1) L1b frame per visit, 41x41 px (113") stamps read with
    HTTPS byte ranges from wise/neowiser/images/p1bm_frm/<grp>/<scan>/<frame>/...-int-1b.fits"""
import os, re, io, sys, time, json
import numpy as np, pandas as pd, requests
import pyarrow.fs as pafs, pyarrow.parquet as pq
from astropy.io import fits
from astropy.wcs import WCS
from astropy.time import Time
from astropy_healpix import HEALPix
import astropy.units as u
from concurrent.futures import ThreadPoolExecutor
from a5lib import OUT, radec_at, sky_offset_arcsec, manifest_add
from astrometry import ASTRO

B = "nasa-irsa-wise"
HTTP = f"https://{B}.s3.amazonaws.com/"
wd = os.path.join(OUT, "wise"); os.makedirs(os.path.join(wd, "neowise_stamps"), exist_ok=True)
fs = pafs.S3FileSystem(anonymous=True, region="us-west-2")
hp = HEALPix(32, "nested")
COLS = ["source_id", "scan_id", "frame_num", "ra", "dec", "sigra", "sigdec", "mjd", "w1mpro", "w1sigmpro", "w2mpro",
        "w2sigmpro", "w1sat", "w2sat", "w1snr", "w2snr", "qual_frame", "cc_flags", "nb", "w1rchi2", "w2rchi2"]
YEARS = [f"year{i}" for i in range(1, 12)] + ["addendum"]


def list_keys(prefix):
    r = requests.get(HTTP, params={"list-type": "2", "prefix": prefix}, timeout=60)
    return re.findall(r"<Key>(.*?)</Key>", r.text)


def one_file(key, A, k5s, yr):
    out = []
    for k5 in k5s:
        pre = f"wise/neowiser/catalogs/p1bs_psd/healpix_k5/{yr}/neowiser-healpix_k5-{yr}.parquet/healpix_k0={k5 // 1024}/healpix_k5={k5}/"
        for k in list_keys(pre):
            if not k.endswith(".parquet"):
                continue
            f = pq.ParquetFile(fs.open_input_file(f"{B}/{k}"))
            cols = [c for c in COLS if c in f.schema_arrow.names]
            pos = f.read(columns=["ra", "dec", "mjd"]).to_pandas()
            m = pos.mjd.median()
            pra, pdec = radec_at(A["ra"], A["dec"], A["pmra"], A["pmdec"], A["plx"], A["ep"], Time(m, format="mjd"))
            de, dn = sky_offset_arcsec(pra[0], pdec[0], pos.ra.values, pos.dec.values)
            sel = np.where(np.hypot(de, dn) < 40)[0]
            if not len(sel):
                continue
            t = f.read(columns=cols).to_pandas().iloc[sel]
            pr, pd_ = radec_at(A["ra"], A["dec"], A["pmra"], A["pmdec"], A["plx"], A["ep"], Time(t.mjd.values, format="mjd"))
            e, n = sky_offset_arcsec(pr, pd_, t.ra.values, t.dec.values)
            t["d_east_arcsec"], t["d_north_arcsec"] = e, n
            t["pred_ra"], t["pred_dec"] = pr, pd_
            t = t[np.hypot(e, n) < 8]
            t["file"] = k
            out.append(t)
    return pd.concat(out) if out else pd.DataFrame()


def catalog(key):
    fn = os.path.join(wd, f"neowise_p1bs_{key}.csv")
    if os.path.exists(fn):
        return pd.read_csv(fn)
    A = ASTRO[key]
    tt = Time(np.linspace(2013.9, 2024.7, 12), format="jyear")
    ra, dec = radec_at(A["ra"], A["dec"], A["pmra"], A["pmdec"], A["plx"], A["ep"], tt)
    k5s = sorted(set(int(x) for x in hp.lonlat_to_healpix(ra * u.deg, dec * u.deg)))
    t0 = time.time()
    with ThreadPoolExecutor(4) as ex:
        parts = list(ex.map(lambda y: one_file(key, A, k5s, y), YEARS))
    df = pd.concat(parts, ignore_index=True).sort_values("mjd")
    df.to_csv(fn, index=False)
    manifest_add(fn, f"s3://{B}/wise/neowiser/catalogs/p1bs_psd/healpix_k5/<year>/... k5={k5s} (row extract)")
    print(key, "neowise rows", len(df), "k5", k5s, round(time.time() - t0), "s", flush=True)
    return df


def rng(url, a, n):
    for k in range(4):
        try:
            r = requests.get(url, headers={"Range": f"bytes={a}-{a + n - 1}"}, timeout=120)
            if r.status_code in (200, 206):
                return r.content
        except Exception:
            pass
        time.sleep(2 * (k + 1))
    raise RuntimeError("range fail " + url)


def stamp(key, row, band, half=20):
    sid, fnum = str(row.scan_id), int(row.frame_num)
    url = f"{HTTP}wise/neowiser/images/p1bm_frm/{sid[-2:]}/{sid}/{fnum:03d}/{sid}{fnum:03d}-w{band}-int-1b.fits"
    out = os.path.join(wd, "neowise_stamps", f"{key}_{sid}{fnum:03d}_w{band}.fits")
    if os.path.exists(out):
        return out
    raw = rng(url, 0, 28800)
    h = fits.Header.fromstring(raw.decode("ascii", "replace")[: raw.find(b"END" + b" " * 77) + 80])
    hl = len(raw[: raw.find(b"END" + b" " * 77) + 80]); hl = ((hl + 2879) // 2880) * 2880
    w = WCS(h)
    x, y = w.all_world2pix([[row.pred_ra, row.pred_dec]], 0)[0]
    xi, yi = int(round(x)), int(round(y))
    nx, ny = h["NAXIS1"], h["NAXIS2"]
    y0, y1 = max(yi - half, 0), min(yi + half + 1, ny)
    x0, x1 = max(xi - half, 0), min(xi + half + 1, nx)
    bp = abs(h["BITPIX"]) // 8
    blk = np.frombuffer(rng(url, hl + y0 * nx * bp, (y1 - y0) * nx * bp), dtype=">f4" if h["BITPIX"] == -32 else ">i4").reshape(y1 - y0, nx)[:, x0:x1]
    w2 = w[y0:y1, x0:x1]
    hh = h.copy(); hh.update(w2.to_header())
    for k in ("NAXIS1", "NAXIS2"):
        hh.remove(k, ignore_missing=True)
    hh["PREDRA"], hh["PREDDEC"], hh["SRCURL"] = float(row.pred_ra), float(row.pred_dec), url[:68]
    fits.PrimaryHDU(blk.astype(np.float32), header=hh).writeto(out, overwrite=True)
    manifest_add(out, url + " (byte-range 41x41 stamp)")
    return out


if __name__ == "__main__":
    for key in (sys.argv[1:] or list(ASTRO)):
        df = catalog(key)
        if not len(df):
            continue
        df["visit"] = np.r_[0, np.cumsum(np.diff(df.mjd.values) > 5)]
        picks = df.loc[df.groupby("visit")["w2snr"].idxmax()] if "w2snr" in df else df.groupby("visit").head(1)
        n = 0
        for r in picks.itertuples():
            for b in (2, 1):
                try:
                    stamp(key, r, b); n += 1
                except Exception as e:
                    print("stamp fail", key, r.scan_id, b, repr(e)[:100], flush=True)
        print(key, "visits", df.visit.nunique(), "stamps", n, flush=True)
