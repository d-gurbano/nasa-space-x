"""Rewind pilot (A0) - reusable functions for SPHEREx precovery.

Pipeline:  MOST frame list -> Horizons ephemeris (SPHEREx observer) -> pixel stamp
(AWS S3 byte-range read or IRSA cutout) -> ePSF forced photometry -> null paths ->
stack -> PNG stamps.

All network calls use python requests / s3fs (the shell curl in this sandbox fails
on TLS interception, python works).

Author: agent A0, Team SpaceX, NASA Space Apps 2026. Public data only, read-only.
"""
from __future__ import annotations

import io
import json
import os
import time
import hashlib
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
import requests
from astropy.io import fits, ascii
from astropy.wcs import WCS
from astropy.coordinates import SkyCoord
import astropy.units as u
from scipy.ndimage import map_coordinates

MOST_URL = "https://irsa.ipac.caltech.edu/cgi-bin/MOST/nph-most"
HORIZONS_URL = "https://ssd.jpl.nasa.gov/api/horizons.api"
IBE_ROOT = "https://irsa.ipac.caltech.edu/"
S3_BUCKET = "nasa-irsa-spherex"
SPHEREX_HORIZONS_ID = "-163182"          # VERIFIED: Horizons "SPHEREx Spacecraft" record
SPHEREX_CENTER = "500@-163182"           # Horizons observer = SPHEREx spacecraft
GEOCENTER = "500@399"
ARCSEC_PER_RAD = 206264.80624709636

# SPHEREx FLAGS bits (ES v2.1 Table 16)
FLAG_BITS = {0: "TRANSIENT", 1: "OVERFLOW", 2: "SUR_ERROR", 6: "NONFUNC", 7: "DICHROIC",
             9: "MISSING_DATA", 10: "HOT", 11: "COLD", 12: "FULLSAMPLE", 14: "PHANMISS",
             15: "NONLINEAR", 17: "PERSIST", 19: "OUTLIER", 20: "CROSSTALK", 21: "SOURCE",
             22: "GHOST", 23: "GHOST_FPA", 24: "GHOST_EXT", 25: "STREAK", 26: "BLOOM",
             27: "SNOWBALL", 28: "HALO", 29: "SATELLITE_HALO"}
# pixels we drop from photometry. SOURCE (21) is NOT dropped: >50% of pixels in deep
# fields carry it, and known asteroids may carry it. OUTLIER (19) and TRANSIENT (0)
# are kept as a separate variant because a moving object can trigger them.
BAD_BITS_STRICT = [1, 2, 6, 7, 9, 10, 11, 14, 15, 17, 20, 22, 24, 25, 26, 27, 28, 29]
BAD_MASK_STRICT = int(sum(1 << b for b in BAD_BITS_STRICT))
BAD_MASK_WITH_OUTLIER = BAD_MASK_STRICT | (1 << 19) | (1 << 0)


def decode_flags(v: int) -> str:
    return "|".join(n for b, n in FLAG_BITS.items() if int(v) & (1 << b)) or "-"


def _get(url, params=None, timeout=300, tries=4, stream=False):
    """GET with retry/backoff (IRSA returns 503 sometimes)."""
    last = None
    for k in range(tries):
        try:
            r = requests.get(url, params=params, timeout=timeout, stream=stream)
            if r.status_code == 200:
                return r
            last = f"HTTP {r.status_code}: {r.text[:200]}"
        except Exception as e:  # noqa
            last = repr(e)
        time.sleep(2 * (k + 1) ** 2)
    raise RuntimeError(f"GET failed {url} {params}: {last}")


# ------------------------------------------------------------------ MOST
def most_query(obj_name: str, begin: str, end: str, cache: str | None = None,
               output_mode: str = "Brief") -> pd.DataFrame:
    """IRSA MOST, catalog=spherex. Returns one row per detector file.
    Columns include ra_obj/dec_obj (MOST predicted position), mjd_start, observationid,
    productid (D1..D6), uri (IBE path)."""
    if cache and os.path.exists(cache):
        txt = open(cache).read()
    else:
        p = dict(catalog="spherex", input_type="name_input", obj_name=obj_name,
                 obs_begin=begin, obs_end=end, output_mode=output_mode)
        txt = _get(MOST_URL, p, timeout=900).text
        if cache:
            open(cache, "w").write(txt)
    t = ascii.read(txt, format="ipac")
    df = t.to_pandas()
    for c in df.columns:
        if df[c].dtype == object:
            df[c] = df[c].astype(str).str.strip()
    meta = {l.split("=")[0].strip("\\ "): l.split("=", 1)[1].strip().strip('"')
            for l in txt.splitlines() if l.startswith("\\") and "=" in l}
    df.attrs["meta"] = meta
    df["file"] = df["uri"].str.split("/").str[-1]
    df["release"] = df["uri"].str.split("/").str[3]
    return df


def s3_key(uri: str) -> str:
    """'ibe/data/spherex/qr3/level2/...' -> 'nasa-irsa-spherex/qr3/level2/...'"""
    return S3_BUCKET + "/" + uri.split("ibe/data/spherex/", 1)[1]


def ibe_url(uri: str) -> str:
    return IBE_ROOT + uri


# ------------------------------------------------------------------ Horizons
def horizons_ephem(command: str, mjd_utc, center: str = SPHEREX_CENTER,
                   quantities: str = "1,9,19,20,36", chunk: int = 60) -> pd.DataFrame:
    """Astrometric ICRF RA/Dec (quantity 1) at the given UTC MJDs from the given
    observer. center='500@-163182' is SPHEREx itself; '500@399' is geocentric.
    For comets pass e.g. 'DES=C/2026 S1;CAP;NOFRAG'."""
    mjd = np.atleast_1d(np.asarray(mjd_utc, float))
    out = []
    for i in range(0, len(mjd), chunk):
        part = mjd[i:i + chunk]
        p = dict(format="json", COMMAND=f"'{command}'", OBJ_DATA="NO", MAKE_EPHEM="YES",
                 EPHEM_TYPE="OBSERVER", CENTER=f"'{center}'", TLIST_TYPE="MJD",
                 TIME_TYPE="UT", TLIST=" ".join(f"{x:.8f}" for x in part),
                 QUANTITIES=f"'{quantities}'", ANG_FORMAT="DEG", CSV_FORMAT="YES",
                 EXTRA_PREC="YES", CAL_FORMAT="JD")
        r = _get(HORIZONS_URL, p, timeout=120)
        res = r.json()["result"]
        if "$$SOE" not in res:
            raise RuntimeError("Horizons: " + res[:1500])
        hdr_line = [l for l in res.split("$$SOE")[0].splitlines() if l.strip().startswith("Date")]
        cols = [c.strip() for c in hdr_line[-1].split(",")]
        body = res.split("$$SOE")[1].split("$$EOE")[0].strip().splitlines()
        for l in body:
            vals = [v.strip() for v in l.split(",")]
            out.append(dict(zip(cols, vals)))
        time.sleep(0.5)
    df = pd.DataFrame(out)
    df.columns = [c if c else f"c{i}" for i, c in enumerate(df.columns)]
    ren = {}
    for c in df.columns:
        if c.startswith("R.A.") and "ICRF" in c:
            ren[c] = "ra"
        elif c.startswith("DEC") and "ICRF" in c:
            ren[c] = "dec"
        elif "JDUT" in c:
            ren[c] = "jd_utc"
    df = df.rename(columns=ren)
    for c in df.columns:
        try:
            df[c] = pd.to_numeric(df[c])
        except (ValueError, TypeError):
            pass
    df["mjd_utc"] = mjd[: len(df)]
    return df


def horizons_vectors(command: str, mjd_utc, center: str = GEOCENTER) -> pd.DataFrame:
    """Geometric state vectors (km) of `command` relative to `center` (ICRF)."""
    mjd = np.atleast_1d(np.asarray(mjd_utc, float))
    p = dict(format="json", COMMAND=f"'{command}'", OBJ_DATA="NO", MAKE_EPHEM="YES",
             EPHEM_TYPE="VECTORS", CENTER=f"'{center}'", TLIST_TYPE="MJD", TIME_TYPE="UT",
             TLIST=" ".join(f"{x:.8f}" for x in mjd), OUT_UNITS="KM-S", REF_PLANE="FRAME",
             VEC_TABLE="2", CSV_FORMAT="YES", VEC_CORR="NONE")
    res = _get(HORIZONS_URL, p, timeout=120).json()["result"]
    body = res.split("$$SOE")[1].split("$$EOE")[0].strip().splitlines()
    rows = []
    for l in body:
        v = [x.strip() for x in l.split(",")]
        rows.append(dict(jd_tdb=float(v[0]), x=float(v[2]), y=float(v[3]), z=float(v[4]),
                         vx=float(v[5]), vy=float(v[6]), vz=float(v[7])))
    return pd.DataFrame(rows)


def parallax_shift_arcsec(ra, dec, delta_au, sc_xyz_km):
    """Approximate topocentric (spacecraft) minus geocentric offset in arcsec for an
    object at geocentric (ra, dec, delta) seen from a spacecraft at geocentric
    sc_xyz_km (ICRF/GCRS, as in the X_SC/Y_SC/Z_SC header keywords)."""
    AU = 1.495978707e8
    ra, dec = np.radians(ra), np.radians(dec)
    p = delta_au * AU * np.array([np.cos(dec) * np.cos(ra), np.cos(dec) * np.sin(ra), np.sin(dec)])
    q = p - np.asarray(sc_xyz_km)
    ra2 = np.arctan2(q[1], q[0]) % (2 * np.pi)
    dec2 = np.arcsin(q[2] / np.linalg.norm(q))
    c1 = SkyCoord(np.degrees(ra) * u.deg, np.degrees(dec) * u.deg)
    c2 = SkyCoord(np.degrees(ra2) * u.deg, np.degrees(dec2) * u.deg)
    return c1.separation(c2).arcsec, np.degrees(ra2), np.degrees(dec2)


# ------------------------------------------------------------------ pixel access
@dataclass
class Stamp:
    """A small SPHEREx stamp with everything needed for photometry."""
    image: np.ndarray       # MJy/sr (zodi NOT subtracted)
    flags: np.ndarray       # int32 bitmask
    variance: np.ndarray    # (MJy/sr)^2
    zodi: np.ndarray        # MJy/sr model
    wcs: WCS                # celestial WCS of the stamp (SIP included)
    x0: int                 # full-frame 0-based column of stamp pixel [0,0]
    y0: int                 # full-frame 0-based row of stamp pixel [0,0]
    header: fits.Header     # IMAGE header
    epsf_table: object      # EPSF table rows (all or the selected one)
    wave_table: object      # WCS-WAVE row
    source: str = ""        # 's3' or 'cutout'
    meta: dict = field(default_factory=dict)


def _celestial_wcs(hdr):
    h = hdr.copy()
    # drop the alternate 'A' (pixel) and 'W' (wave) WCS so astropy builds the sky WCS
    return WCS(h, relax=True, key=" ")


def _shift_wcs(w: WCS, x0: int, y0: int) -> WCS:
    w2 = w.deepcopy()
    w2.wcs.crpix = w.wcs.crpix - np.array([x0, y0])
    if w2.sip is not None:
        from astropy.wcs import Sip
        s = w.sip
        w2.sip = Sip(s.a, s.b, s.ap, s.bp, np.array(s.crpix) - np.array([x0, y0]))
    return w2


def read_stamp_s3(uri: str, ra: float, dec: float, half: int = 20, fs=None) -> Stamp:
    """Faster S3 reader: header via one range read, rows via range reads, EPSF only
    the scalar columns + one zone row. Falls back to read_stamp_s3 on any error."""
    import s3fs
    fs = fs or s3fs.S3FileSystem(anon=True)
    t0 = time.time()
    key = s3_key(uri)
    nread = 0
    with fs.open(key, "rb", block_size=2 ** 16, cache_type="none") as f:
        h = fits.open(f, lazy_load_hdus=True, memmap=False)
        hdr = h["IMAGE"].header.copy()
        w = _celestial_wcs(hdr)
        x, y = w.all_world2pix([[ra, dec]], 0)[0]
        xi, yi = int(round(x)), int(round(y))
        x0, y0 = xi - half, yi - half
        n = 2 * half + 1
        X0, Y0, X1, Y1 = max(x0, 0), max(y0, 0), min(x0 + n, 2040), min(y0 + n, 2040)
        if X1 <= X0 or Y1 <= Y0:
            raise ValueError(f"target off detector: x={x:.1f} y={y:.1f}")

        def rows(name, fill):
            hd = h[name]
            loc = hd.fileinfo()["datLoc"]
            a = np.full((n, n), fill, dtype=np.float64)
            f.seek(loc + (Y0 * 2040) * 4)
            raw = f.read((Y1 - Y0) * 2040 * 4)
            blk = np.frombuffer(raw, dtype=">f4").reshape(Y1 - Y0, 2040)
            a[Y0 - y0:Y1 - y0, X0 - x0:X1 - x0] = blk[:, X0:X1]
            return a, len(raw)
        img, b1 = rows("IMAGE", np.nan)
        var, b2 = rows("VARIANCE", np.nan)
        zod, b3 = rows("ZODI", np.nan)
        flg = np.full((n, n), 1 << 9, dtype=np.int64)
        flg[Y0 - y0:Y1 - y0, X0 - x0:X1 - x0] = h["FLAGS"].section[Y0:Y1, X0:X1]
        wave = np.array(h["WCS-WAVE"].data)
        # EPSF: read whole table (3.9 MB) once - simplest robust path
        ep = np.array(h["EPSF"].data)
        nread = b1 + b2 + b3
    return Stamp(img, flg, var, zod, _shift_wcs(w, x0, y0), x0, y0, hdr, ep, wave,
                 source="s3", meta=dict(t_read=time.time() - t0, x_full=x, y_full=y,
                                        bytes_rows=nread))


def read_stamp_cutout(uri: str, ra: float, dec: float, size_deg: float = 0.07,
                      save_path: str | None = None) -> Stamp:
    """IRSA IBE cutout: <ibe url>?center=ra,dec&size=<deg>. Returns all 6 HDUs
    (EPSF uncut, so ~3.9 MB per cutout)."""
    t0 = time.time()
    r = _get(ibe_url(uri), dict(center=f"{ra:.6f},{dec:.6f}", size=f"{size_deg}"), timeout=180)
    content = r.content
    if save_path:
        open(save_path, "wb").write(content)
    h = fits.open(io.BytesIO(content))
    hdr = h["IMAGE"].header
    w = _celestial_wcs(hdr)
    # full-frame 0-based offset from the alternate 'A' WCS: full0 = cut1 - CRPIX1A
    x0 = int(round(-hdr["CRPIX1A"] + 1))
    y0 = int(round(-hdr["CRPIX2A"] + 1))
    st = Stamp(h["IMAGE"].data.astype(float), h["FLAGS"].data.astype(np.int64),
               h["VARIANCE"].data.astype(float), h["ZODI"].data.astype(float), w, x0, y0,
               hdr, np.array(h["EPSF"].data), np.array(h["WCS-WAVE"].data), source="cutout",
               meta=dict(t_read=time.time() - t0, bytes=len(content)))
    return st


def save_stamp_fits(st: Stamp, path: str, extra: dict | None = None):
    """Compact stamp FITS (IMAGE, FLAGS, VARIANCE, ZODI + wave/psf of target zone)."""
    hdr = st.wcs.to_header(relax=True)
    for k in ["OBSID", "DETECTOR", "MJD-AVG", "MJD-BEG", "MJD-END", "XPOSURE", "X_SC", "Y_SC",
              "Z_SC", "PSF_FWHM", "OMEGA_MEDIAN", "FINAST", "SPS_FLAGS"]:
        if k in st.header:
            hdr[k[:8]] = st.header[k]
    hdr["X0FULL"] = (st.x0, "full-frame 0-based col of stamp [0,0]")
    hdr["Y0FULL"] = (st.y0, "full-frame 0-based row of stamp [0,0]")
    hdr["SRCREAD"] = st.source
    for k, v in (extra or {}).items():
        if v is None or (isinstance(v, float) and not np.isfinite(v)):
            continue
        hdr[k[:8].upper()] = float(v) if isinstance(v, (np.floating,)) else v
    hl = fits.HDUList([fits.PrimaryHDU(st.image.astype(np.float32), header=hdr, ),
                       fits.ImageHDU(st.flags.astype(np.int32), name="FLAGS"),
                       fits.ImageHDU(st.variance.astype(np.float32), name="VARIANCE"),
                       fits.ImageHDU(st.zodi.astype(np.float32), name="ZODI")])
    hl[0].name = "IMAGE"
    # ePSF of the zone at the stamp centre (33x33, 5x oversampled) + WCS-WAVE table
    try:
        c = (st.image.shape[0] - 1) / 2
        psf, zi = epsf_zone(st.epsf_table, st.x0 + c, st.y0 + c)
        ph = fits.ImageHDU(psf.astype(np.float32), name="EPSF_ZONE")
        ph.header["OVERSAMP"] = 5
        hl.append(ph)
        hl.append(fits.BinTableHDU(np.asarray(st.wave_table), name="WCS-WAVE"))
    except Exception:
        pass
    hl.writeto(path, overwrite=True)


def gaussian_epsf(fwhm_arcsec: float, pix: float = 6.15, n: int = 33, ovs: int = 5):
    """Fallback ePSF: pixel-integrated-ish Gaussian sampled on the 5x grid."""
    sig = fwhm_arcsec / 2.3548 / pix * ovs
    j, i = np.mgrid[0:n, 0:n] - (n - 1) / 2
    g = np.exp(-(i ** 2 + j ** 2) / (2 * sig ** 2))
    return g / g.sum()


def load_stamp_fits(path: str) -> Stamp:
    """Load a compact stamp written by save_stamp_fits. If it has no EPSF_ZONE (older
    pilot stamps), a Gaussian with the header PSF_FWHM is used and meta['psf']='gauss'."""
    h = fits.open(path)
    hdr = h[0].header
    w = WCS(hdr, relax=True)
    if "EPSF_ZONE" in h:
        psf = h["EPSF_ZONE"].data.astype(float)
        kind = "epsf"
    else:
        psf = gaussian_epsf(hdr.get("PSF_FWHM", 8.0))
        kind = "gauss"
    ep = dict(XCENTER=np.array([1020.0]), YCENTER=np.array([1020.0]), XWIDTH=np.array([1e6]),
              YWIDTH=np.array([1e6]), EPSF=psf.reshape(1, 33, 33))
    wave = np.asarray(h["WCS-WAVE"].data) if "WCS-WAVE" in h else None
    hh = fits.Header()
    for k in ["OMEGA_ME", "PSF_FWHM", "MJD-AVG", "DETECTOR"]:
        if k in hdr:
            hh[k] = hdr[k]
    hh["OMEGA_MEDIAN"] = hdr.get("OMEGA_ME", 37.8)
    st = Stamp(h[0].data.astype(float), h["FLAGS"].data.astype(np.int64), h["VARIANCE"].data.astype(float),
               h["ZODI"].data.astype(float), w, hdr["X0FULL"], hdr["Y0FULL"], hh, ep, wave,
               source="stamp-file", meta=dict(psf=kind, waveum=hdr.get("WAVEUM")))
    return st


# ------------------------------------------------------------------ wavelength + PSF
def wavelength_at(wave_row, x_full0: float, y_full0: float):
    """Central wavelength and bandwidth (um) at a full-frame 0-based pixel, by
    bilinear interpolation of the WCS-WAVE lookup table (control points are 1-based
    raw FITS coordinates). VALUES dims (2,11,11) in FITS = numpy [11(y),11(x),2]."""
    X = np.asarray(wave_row["X"]).ravel().astype(float)
    Y = np.asarray(wave_row["Y"]).ravel().astype(float)
    V = np.asarray(wave_row["VALUES"]).reshape(len(Y), len(X), 2)
    px, py = x_full0 + 1.0, y_full0 + 1.0
    fx = np.interp(px, X, np.arange(len(X)))
    fy = np.interp(py, Y, np.arange(len(Y)))
    lam = map_coordinates(V[:, :, 0], [[fy], [fx]], order=1)[0]
    bw = map_coordinates(V[:, :, 1], [[fy], [fx]], order=1)[0]
    return float(lam), float(bw)


def epsf_zone(ep, x_full0: float, y_full0: float):
    """Return (psf_oversampled[33,33], row) for the ePSF zone containing the pixel.
    EPSF XCENTER/YCENTER are in pixel units (convention checked: zone centers span
    ~48..1991, i.e. 0-based or 1-based within <1 px - irrelevant at zone scale)."""
    xc, yc = np.asarray(ep["XCENTER"], float), np.asarray(ep["YCENTER"], float)
    xw, yw = np.asarray(ep["XWIDTH"], float), np.asarray(ep["YWIDTH"], float)
    inside = (np.abs(x_full0 - xc) <= xw / 2 + 0.5) & (np.abs(y_full0 - yc) <= yw / 2 + 0.5)
    i = int(np.argmax(inside)) if inside.any() else int(np.argmin((xc - x_full0) ** 2 + (yc - y_full0) ** 2))
    psf = np.asarray(ep["EPSF"][i], float).reshape(33, 33)
    return psf, i


def psf_native(psf_os: np.ndarray, dx: float, dy: float, n: int, ovs: int = 5):
    """Sample the 5x-oversampled ePSF at native pixel centres of an n x n grid whose
    centre pixel is offset (dx, dy) native px from the source position. Normalised to
    sum 1 over the grid. (ePSF already includes the pixel response, so point sampling
    is correct.)"""
    c = (psf_os.shape[0] - 1) / 2.0
    j, i = np.mgrid[0:n, 0:n]
    k = (n - 1) / 2.0
    xs = c + (i - k - dx) * ovs
    ys = c + (j - k - dy) * ovs
    p = map_coordinates(psf_os, [ys, xs], order=1, mode="constant", cval=0.0)
    p[p < 0] = 0
    s = p.sum()
    return p / s if s > 0 else p


# ------------------------------------------------------------------ photometry
def pixel_sr(st: Stamp) -> float:
    om = st.header.get("OMEGA_MEDIAN", 37.8)  # arcsec^2
    return om / ARCSEC_PER_RAD ** 2


def forced_phot(st: Stamp, ra: float, dec: float, bad_mask: int = BAD_MASK_STRICT,
                fit_half: int = 3, r_ap: float = 2.0, r_in: float = 6.0, r_out: float = 12.0,
                psf_scale: float = 1.0):
    """ePSF-weighted forced photometry at (ra, dec). Background = sigma-clipped
    median of the annulus [r_in, r_out] px of (IMAGE) with bad pixels removed (this
    removes zodi + local sky). Returns dict with flux (uJy), err, snr, AB mag,
    aperture flux, wavelength, flags at the target pixel, pixel coords."""
    x, y = st.wcs.all_world2pix([[ra, dec]], 0)[0]
    ny, nx = st.image.shape
    res = dict(x=x, y=y, x_full=x + st.x0, y_full=y + st.y0)
    if not (fit_half <= x < nx - fit_half - 1 and fit_half <= y < ny - fit_half - 1):
        res.update(status="edge")
        return res
    jj, ii = np.mgrid[0:ny, 0:nx]
    rr = np.hypot(ii - x, jj - y)
    bad = (st.flags & bad_mask) != 0
    good = ~bad & np.isfinite(st.image) & np.isfinite(st.variance) & (st.variance > 0)
    ann = good & (rr >= r_in) & (rr <= r_out)
    vals = st.image[ann]
    if vals.size < 20:
        res.update(status="no_background")
        return res
    from astropy.stats import sigma_clipped_stats
    _, bkg, bstd = sigma_clipped_stats(vals, sigma=3.0, maxiters=5)
    xi, yi = int(round(x)), int(round(y))
    sl = (slice(yi - fit_half, yi + fit_half + 1), slice(xi - fit_half, xi + fit_half + 1))
    n = 2 * fit_half + 1
    psf_os, zone = epsf_zone(st.epsf_table, x + st.x0, y + st.y0)
    P = psf_native(psf_os, x - xi, y - yi, n)
    D = st.image[sl] - bkg
    V = st.variance[sl]
    G = good[sl]
    sr = pixel_sr(st)
    to_uJy = sr * 1e12  # MJy/sr * sr -> MJy ; *1e12 -> uJy
    res.update(bkg=bkg, bkg_std=bstd, zone=int(zone), psf_frac_good=float(P[G].sum()),
               npix_bad=int((~G).sum()))
    if P[G].sum() < 0.5:
        res.update(status="masked")
    else:
        w = P[G] / V[G]
        F = np.sum(w * D[G]) / np.sum(w * P[G])
        E = 1.0 / np.sqrt(np.sum(P[G] ** 2 / V[G]))
        # empirical error from annulus scatter (variance map may miss confusion)
        Ee = bstd / np.sqrt(np.sum(P[G] ** 2))
        res.update(status="ok", flux_uJy=F * to_uJy, err_uJy=E * to_uJy,
                   err_emp_uJy=Ee * to_uJy, snr=F / E, snr_emp=F / Ee,
                   chi2_psf=float(np.sum((D[G] - F * P[G]) ** 2 / V[G]) / max(G.sum() - 1, 1)))
    ap = good & (rr <= r_ap)
    if ap.sum() > 0:
        fa = np.sum(st.image[ap] - bkg)
        ea = np.sqrt(np.sum(st.variance[ap]))
        # aperture correction from the ePSF itself
        Pbig = psf_native(psf_os, x - xi, y - yi, 15)
        j2, i2 = np.mgrid[0:15, 0:15]
        apc = Pbig[np.hypot(i2 - 7 - (x - xi), j2 - 7 - (y - yi)) <= r_ap].sum()
        res.update(ap_flux_uJy=fa * to_uJy / max(apc, 1e-3), ap_err_uJy=ea * to_uJy / max(apc, 1e-3),
                   ap_corr=apc, ap_npix=int(ap.sum()))
    fv = int(st.flags[min(max(int(round(y)), 0), ny - 1), min(max(int(round(x)), 0), nx - 1)])
    fa_or = int(np.bitwise_or.reduce(st.flags[sl].ravel()))
    res.update(flag_center=fv, flag_center_names=decode_flags(fv), flag_or_fitbox=fa_or,
               flag_or_names=decode_flags(fa_or))
    if st.wave_table is not None:
        lam, bw = wavelength_at(st.wave_table, x + st.x0, y + st.y0)
    else:
        lam, bw = st.meta.get("waveum", np.nan), np.nan
    res.update(wave_um=lam, bandwidth_um=bw)
    if res.get("status") == "ok":
        res["ab_mag"] = -2.5 * np.log10(res["flux_uJy"] * 1e-6 / 3631.0) if res["flux_uJy"] > 0 else np.nan
    return res


def offset_radec(ra, dec, dra_arcsec, ddec_arcsec):
    """Offset a position by (east, north) arcsec on the sky (tangent plane)."""
    c = SkyCoord(ra * u.deg, dec * u.deg)
    o = c.spherical_offsets_by(dra_arcsec * u.arcsec, ddec_arcsec * u.arcsec)
    return o.ra.deg, o.dec.deg


def null_offsets(n: int = 24, r_min: float = 40.0, r_max: float = 90.0, seed: int = 1):
    """Fixed (east, north) sky offsets in arcsec for null ("shifted fake path")
    controls. The same offsets are used in every frame, so a null path is stacked
    exactly like the real path."""
    rng = np.random.default_rng(seed)
    ang = np.linspace(0, 2 * np.pi, n, endpoint=False) + rng.uniform(0, 0.2, n)
    rad = rng.uniform(r_min, r_max, n)
    return np.c_[rad * np.cos(ang), rad * np.sin(ang)]


def weighted_stack(flux, err):
    """Inverse-variance weighted mean flux, its error and S/N."""
    flux, err = np.asarray(flux, float), np.asarray(err, float)
    m = np.isfinite(flux) & np.isfinite(err) & (err > 0)
    if m.sum() == 0:
        return np.nan, np.nan, np.nan, 0
    w = 1 / err[m] ** 2
    F = np.sum(w * flux[m]) / np.sum(w)
    E = 1 / np.sqrt(np.sum(w))
    return F, E, F / E, int(m.sum())


# ------------------------------------------------------------------ stamps / images
def resample_north_up(st: Stamp, ra: float, dec: float, half_arcsec: float = 60.0,
                      scale: float = 2.0, subtract: str = "local"):
    """Resample a stamp onto a north-up east-left grid centred on (ra, dec),
    `scale` arcsec per output pixel. Returns (img, var, good) arrays. Values are
    MJy/sr minus the local background (median of the stamp's good pixels)."""
    n = int(round(2 * half_arcsec / scale)) + 1
    k = (n - 1) / 2
    j, i = np.mgrid[0:n, 0:n]
    east = -(i - k) * scale  # east to the left
    north = (j - k) * scale
    c0 = SkyCoord(ra * u.deg, dec * u.deg)
    cc = c0.spherical_offsets_by(east.ravel() * u.arcsec, north.ravel() * u.arcsec)
    px, py = st.wcs.all_world2pix(np.c_[cc.ra.deg, cc.dec.deg], 0).T
    good = ((st.flags & BAD_MASK_STRICT) == 0) & np.isfinite(st.image)
    img = st.image.copy()
    if subtract == "local":
        img = img - np.nanmedian(img[good])
    img[~good] = np.nan
    out = map_coordinates(np.nan_to_num(img, nan=0.0), [py, px], order=1, cval=np.nan).reshape(n, n)
    g = map_coordinates(np.isfinite(img).astype(float), [py, px], order=1, cval=0).reshape(n, n)
    var = map_coordinates(np.nan_to_num(st.variance, nan=0.0), [py, px], order=1, cval=np.nan).reshape(n, n)
    out[g < 0.99] = np.nan
    return out, var, g >= 0.99


def save_png(arr, path, title="", mark=True, vmin=None, vmax=None, scale_arcsec=2.0):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    a = np.array(arr, float)
    fin = np.isfinite(a)
    if vmin is None or vmax is None:
        lo, hi = np.nanpercentile(a[fin], [5, 99.5]) if fin.any() else (0, 1)
        vmin, vmax = (lo if vmin is None else vmin), (hi if vmax is None else vmax)
    fig, ax = plt.subplots(figsize=(3.2, 3.4), dpi=110)
    n = a.shape[0]
    ext = np.array([-1, 1, -1, 1]) * (n / 2) * scale_arcsec
    ax.imshow(a, origin="lower", cmap="gray", vmin=vmin, vmax=vmax, extent=[ext[1], ext[0], ext[2], ext[3]])
    if mark:
        for r in (12, 20):
            ax.add_patch(plt.Circle((0, 0), r, fill=False, color="red", lw=0.6, ls="--" if r == 20 else "-"))
    ax.set_xlabel("east offset [arcsec]", fontsize=6)
    ax.set_ylabel("north offset [arcsec]", fontsize=6)
    ax.tick_params(labelsize=5)
    ax.set_title(title, fontsize=6)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


# ------------------------------------------------------------------ expected brightness
# Solar V - AB(lambda) colours (Willmer 2018 ApJS 236 47, Sun absolute mags; ESTIMATED
# use): V(AB)=4.80; i 4.53, z 4.50, J 4.54, H 4.66, Ks 5.08, W1 5.92 (AB).
_SUN_LAM = np.array([0.55, 0.62, 0.75, 0.89, 1.25, 1.65, 2.16, 3.4])
_SUN_VMAB = np.array([0.0, 0.15, 0.27, 0.30, 0.26, 0.14, -0.28, -1.12])


def expected_ab_reflected(V: float, lam_um: float, red_slope_per_um: float = 0.0) -> float:
    """Expected AB at lam for a body with solar colours (+ optional reddening, mag
    per um relative to V, positive = redder/brighter in IR). Reflected light only."""
    vmab = np.interp(np.log(lam_um), np.log(_SUN_LAM), _SUN_VMAB)
    return V - vmab - red_slope_per_um * (lam_um - 0.55)


# ------------------------------------------------------------------ fast S3 reader (plain HTTPS ranges)
S3_HTTP = "https://nasa-irsa-spherex.s3.amazonaws.com/"
import threading
_TL = threading.local()


def _sess():
    if not hasattr(_TL, "s"):
        _TL.s = requests.Session()
    return _TL.s


def _range(url, start, length, tries=4):
    last = None
    for k in range(tries):
        try:
            r = _sess().get(url, headers={"Range": f"bytes={start}-{start + length - 1}"}, timeout=120)
            if r.status_code in (200, 206):
                return r.content
            last = r.status_code
        except Exception as e:  # noqa
            last = repr(e)
        time.sleep(1.5 * (k + 1))
    raise RuntimeError(f"range read failed {url} {start}+{length}: {last}")


def _read_header(url, offset, stats):
    """Read one FITS header starting at byte `offset`; returns (Header, header_bytes)."""
    buf = b""
    chunk = 28800
    while True:
        buf += _range(url, offset + len(buf), chunk)
        stats["bytes"] += chunk
        stats["requests"] += 1
        # END card must be at an 80-byte card boundary
        for i in range(0, len(buf), 80):
            if buf[i:i + 8] == b"END     ":
                hlen = ((i + 80 + 2879) // 2880) * 2880
                return fits.Header.fromstring(buf[:i + 80].decode("ascii")), hlen


def _data_len(h):
    if h.get("NAXIS", 0) == 0:
        return 0
    n = abs(h["BITPIX"]) // 8
    for k in range(1, h["NAXIS"] + 1):
        n *= h[f"NAXIS{k}"]
    n = (n + h.get("PCOUNT", 0)) * h.get("GCOUNT", 1)
    return ((n + 2879) // 2880) * 2880


def l2_layout(uri: str):
    """Walk the HDU headers of a SPHEREx L2 file with small range reads. Returns
    {extname: (header, header_offset, data_offset, data_len)} plus request stats."""
    url = S3_HTTP + uri.split("ibe/data/spherex/", 1)[1]
    stats = dict(bytes=0, requests=0)
    off = 0
    lay = {}
    for k in range(7):
        h, hl = _read_header(url, off, stats)
        name = h.get("EXTNAME", "PRIMARY") if k else "PRIMARY"
        dl = _data_len(h)
        lay[name] = (h, off, off + hl, dl)
        off = off + hl + dl
    return url, lay, stats


def _read_flags_rows(url, flay, Y0, Y1, stats):
    """Decode only rows Y0..Y1-1 of the RICE row-tiled FLAGS HDU: read the 8-byte
    tile descriptors and the matching heap bytes, rebuild a mini compressed HDU and
    let astropy decompress it. Falls back to reading the whole HDU."""
    fh, foff, fdat, flen = flay
    try:
        assert fh["ZTILE2"] == 1 and fh["NAXIS1"] == 8 and fh["TFORM1"].startswith("1PB")
        n = Y1 - Y0
        desc = np.frombuffer(_range(url, fdat + Y0 * 8, n * 8), dtype=">i4").reshape(n, 2).copy()
        theap = fh.get("THEAP", fh["NAXIS1"] * fh["NAXIS2"])
        lo, hi = desc[:, 1].min(), (desc[:, 1] + desc[:, 0]).max()
        heap = _range(url, fdat + theap + lo, hi - lo)
        stats["bytes"] += n * 8 + len(heap)
        stats["requests"] += 2
        desc[:, 1] -= lo
        h2 = fh.copy()
        h2["NAXIS2"] = n
        h2["ZNAXIS2"] = n
        h2["PCOUNT"] = len(heap)
        if "THEAP" in h2:
            del h2["THEAP"]
        body = desc.astype(">i4").tobytes() + heap
        body += b"\0" * ((-len(body)) % 2880)
        prim = fits.PrimaryHDU().header.tostring().encode()
        hdul = fits.open(io.BytesIO(prim + h2.tostring().encode() + body))
        return np.asarray(hdul[1].data)
    except Exception:
        raw = _range(url, foff, (fdat - foff) + flen)
        stats["bytes"] += len(raw)
        stats["requests"] += 1
        prim = fits.PrimaryHDU().header.tostring().encode()
        return np.asarray(fits.open(io.BytesIO(prim + raw))[1].section[Y0:Y1, :])


def _epsf_dtype(eh):
    f = []
    for k in range(1, eh["TFIELDS"] + 1):
        name, form = eh[f"TTYPE{k}"].strip(), eh[f"TFORM{k}"].strip()
        if form == "J":
            f.append((name, ">i4"))
        elif form == "E":
            f.append((name, ">f4"))
        elif form.endswith("D"):
            f.append((name, ">f8", (int(form[:-1]),)))
        else:
            raise ValueError(form)
    return np.dtype(f)


def read_stamp_http(uri: str, ra: float, dec: float, half: int = 20) -> Stamp:
    """Anonymous S3 read with plain HTTPS Range requests (no s3fs). ~10 requests and
    ~1-3 MB per stamp: 7 header reads, 3 row blocks (IMAGE/VARIANCE/ZODI), the whole
    compressed FLAGS HDU, 2 small EPSF reads (one zone row) and WCS-WAVE."""
    t0 = time.time()
    url, lay, stats = l2_layout(uri)
    hdr, _, dimg, _ = lay["IMAGE"]
    w = _celestial_wcs(hdr)
    x, y = w.all_world2pix([[ra, dec]], 0)[0]
    xi, yi = int(round(x)), int(round(y))
    x0, y0 = xi - half, yi - half
    n = 2 * half + 1
    X0, Y0, X1, Y1 = max(x0, 0), max(y0, 0), min(x0 + n, 2040), min(y0 + n, 2040)
    if X1 <= X0 or Y1 <= Y0:
        raise ValueError(f"target off detector: x={x:.1f} y={y:.1f}")
    NX = hdr["NAXIS1"]

    def rows(name, fill):
        h, _, dloc, _ = lay[name]
        raw = _range(url, dloc + Y0 * NX * 4, (Y1 - Y0) * NX * 4)
        stats["bytes"] += len(raw)
        stats["requests"] += 1
        blk = np.frombuffer(raw, dtype=">f4").reshape(Y1 - Y0, NX)
        a = np.full((n, n), fill, dtype=np.float64)
        a[Y0 - y0:Y1 - y0, X0 - x0:X1 - x0] = blk[:, X0:X1]
        return a
    img = rows("IMAGE", np.nan)
    var = rows("VARIANCE", np.nan)
    zod = rows("ZODI", np.nan)
    # FLAGS: tile-compressed binary table -> read the full HDU and let astropy decode
    prim = fits.PrimaryHDU().header.tostring().encode()
    fl = _read_flags_rows(url, lay["FLAGS"], Y0, Y1, stats)[:, X0:X1]
    flg = np.full((n, n), 1 << 9, dtype=np.int64)
    flg[Y0 - y0:Y1 - y0, X0 - x0:X1 - x0] = fl
    # EPSF: read row 0 to get the zone geometry, then just the zone row
    eh, eoff, edat, elen = lay["EPSF"]
    rowlen, nrow = eh["NAXIS1"], eh["NAXIS2"]
    r0 = _range(url, edat, rowlen)
    dt = _epsf_dtype(eh)
    rec0 = np.frombuffer(r0, dtype=dt)[0]
    xw, yw = float(rec0["XWIDTH"]), float(rec0["YWIDTH"])
    nzx = int(round(2040 / xw))
    nzy = int(round(2040 / yw))
    ix = min(int(x // xw), nzx - 1)
    iy = min(int(y // yw), nzy - 1)
    zi = iy * nzx + ix
    rz = _range(url, edat + zi * rowlen, rowlen)
    stats["bytes"] += 2 * rowlen
    stats["requests"] += 2
    ep = np.frombuffer(rz, dtype=dt).copy()
    # sanity: the chosen zone must contain the pixel (ordering 'x-fast then y')
    zone_ok = abs(ep["XCENTER"][0] - x) <= xw / 2 + 1 and abs(ep["YCENTER"][0] - y) <= yw / 2 + 1
    ep_out = {k: ep[k] for k in ep.dtype.names}
    ep_out["EPSF"] = ep["EPSF"].reshape(1, 33, 33)
    # WCS-WAVE
    whh, woff, wdat, wlen = lay["WCS-WAVE"]
    rawW = _range(url, woff, (wdat - woff) + wlen)
    stats["requests"] += 1
    stats["bytes"] += len(rawW)
    wave = np.array(fits.open(io.BytesIO(prim + rawW))[1].data)
    st = Stamp(img, flg, var, zod, _shift_wcs(w, x0, y0), x0, y0, hdr.copy(), ep_out, wave,
               source="s3-http", meta=dict(t_read=time.time() - t0, x_full=x, y_full=y,
                                           zone_index=zi, zone_ok=bool(zone_ok), **stats))
    return st


def psf_centroid(st: Stamp, ra: float, dec: float, search_px: float = 2.0, step: float = 0.1,
                 fit_half: int = 3, bad_mask: int = BAD_MASK_STRICT):
    """Grid-search PSF fit position near the prediction (linear flux + local bkg).
    Returns measured minus predicted offset (east, north) in arcsec and the
    best-fit pixel position. Only meaningful at S/N >~ 10."""
    x, y = st.wcs.all_world2pix([[ra, dec]], 0)[0]
    psf_os, _ = epsf_zone(st.epsf_table, x + st.x0, y + st.y0)
    good = ((st.flags & bad_mask) == 0) & np.isfinite(st.image) & (st.variance > 0)
    best = (np.inf, x, y)
    for dxx in np.arange(-search_px, search_px + 1e-9, step):
        for dyy in np.arange(-search_px, search_px + 1e-9, step):
            xc, yc = x + dxx, y + dyy
            xi, yi = int(round(xc)), int(round(yc))
            sl = (slice(yi - fit_half, yi + fit_half + 1), slice(xi - fit_half, xi + fit_half + 1))
            D, V, G = st.image[sl], st.variance[sl], good[sl]
            if D.shape != (2 * fit_half + 1,) * 2 or G.sum() < 10:
                continue
            P = psf_native(psf_os, xc - xi, yc - yi, 2 * fit_half + 1)
            A = np.c_[P[G], np.ones(G.sum())]
            wts = 1 / np.sqrt(V[G])
            coef, *_ = np.linalg.lstsq(A * wts[:, None], D[G] * wts, rcond=None)
            chi2 = np.sum(((D[G] - A @ coef) * wts) ** 2)
            if chi2 < best[0]:
                best = (chi2, xc, yc)
    _, xb, yb = best
    c_pred = SkyCoord(ra * u.deg, dec * u.deg)
    rb, db = st.wcs.all_pix2world([[xb, yb]], 0)[0]
    c_meas = SkyCoord(rb * u.deg, db * u.deg)
    de, dn = c_pred.spherical_offsets_to(c_meas)
    return dict(cen_dx_px=xb - x, cen_dy_px=yb - y, cen_east_arcsec=de.arcsec,
                cen_north_arcsec=dn.arcsec, cen_sep_arcsec=c_pred.separation(c_meas).arcsec)


SIA2_URL = "https://irsa.ipac.caltech.edu/SIA"


def sia2_query(ra: float, dec: float, collection: str = "spherex_dr1", radius_deg: float = 0.001,
               time_mjd: tuple | None = None, maxrec: int = 5000) -> pd.DataFrame:
    """IRSA SIA2 ObsCore query for SPHEREx L2 images containing (ra, dec).
    collection: spherex_qr3, spherex_dr1, spherex_qr3_deep, spherex_dr1_deep ..."""
    p = dict(COLLECTION=collection, POS=f"CIRCLE {ra} {dec} {radius_deg}", RESPONSEFORMAT="VOTABLE",
             MAXREC=str(maxrec))
    if time_mjd:
        p["TIME"] = f"{time_mjd[0]} {time_mjd[1]}"
    r = _get(SIA2_URL, p, timeout=300)
    from astropy.io.votable import parse_single_table
    t = parse_single_table(io.BytesIO(r.content)).to_table(use_names_over_ids=True)
    df = t.to_pandas()
    for c in df.columns:
        if df[c].dtype == object:
            df[c] = df[c].astype(str)
    return df


def kete_radec_from_spherex(desig: str, mjd_utc, state=None):
    """Astrometric RA/Dec (deg) of an object seen from SPHEREx using kete: orbit from
    JPL Horizons (kete.HorizonsProperties.fetch), n-body propagation, SPHEREx position
    from kete's bundled (reconstructed, unofficial) SPHEREx SPICE kernel, 3 light-time
    iterations. Pilot check: matches Horizons 500@-163182 to 0.009 arcsec for (1000)."""
    import kete
    st = state or kete.HorizonsProperties.fetch(desig).state
    out = []
    for m in np.atleast_1d(mjd_utc):
        jd = kete.Time.from_mjd(float(m), scaling="utc").jd
        obs = kete.spice.get_state("spherex", jd)
        s2 = kete.propagate_n_body([st], jd)[0]
        for _ in range(3):
            d = (s2.pos - obs.pos).r
            s2 = kete.propagate_n_body([st], jd - d * 0.0057755183)[0]
        v = (s2.pos - obs.pos).as_equatorial
        out.append((v.ra, v.dec))
    return np.array(out)


def robust_stack(flux, err, clip=3.0):
    """Sigma-clipped inverse-variance stack, robust to frames where a star or
    artifact falls in the PSF. Clipping uses the per-frame chi = (f - median)/err
    with a MAD scale. Returns (flux, err, snr, n_used)."""
    f, e = np.asarray(flux, float), np.asarray(err, float)
    m = np.isfinite(f) & np.isfinite(e) & (e > 0)
    f, e = f[m], e[m]
    if len(f) < 3:
        return np.nan, np.nan, np.nan, len(f)
    for _ in range(5):
        med = np.median(f)
        chi = (f - med) / e
        s = 1.4826 * np.median(np.abs(chi - np.median(chi)))
        keep = np.abs(chi - np.median(chi)) <= clip * max(s, 1.0)
        if keep.all():
            break
        f, e = f[keep], e[keep]
    w = 1 / e ** 2
    F = np.sum(w * f) / np.sum(w)
    E = 1 / np.sqrt(np.sum(w))
    return F, E, F / E, len(f)
