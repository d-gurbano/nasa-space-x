"""PNGs for the website: north up, east left, nearest-neighbour sampling (pixels stay honest),
one shared brightness stretch per object, at most 512 px."""
from __future__ import annotations

import numpy as np
from astropy.coordinates import SkyCoord
import astropy.units as u
from PIL import Image
from scipy.ndimage import map_coordinates

from .pilot import R

SCALE = 1.5      # arcsec per output pixel before upscaling
HALF_AS = 60.0   # half box, arcsec
UPSCALE = 4      # 81 px -> 324 px


def north_up(st, ra, dec, half_arcsec=HALF_AS, scale=SCALE, order=0, image=None):
    """Resample a stamp onto a north-up east-left grid centred on (ra, dec); local median removed.
    order=0 keeps the native pixels as blocks."""
    n = int(round(2 * half_arcsec / scale)) + 1
    k = (n - 1) / 2
    j, i = np.mgrid[0:n, 0:n]
    c0 = SkyCoord(ra * u.deg, dec * u.deg)
    cc = c0.spherical_offsets_by((-(i - k) * scale).ravel() * u.arcsec, ((j - k) * scale).ravel() * u.arcsec)
    px, py = st.wcs.all_world2pix(np.c_[cc.ra.deg, cc.dec.deg], 0).T
    img = (st.image if image is None else image).copy()
    good = ((st.flags & R.BAD_MASK_STRICT) == 0) & np.isfinite(img)
    if good.any():
        img = img - np.nanmedian(img[good])
    img[~good] = np.nan
    out = map_coordinates(np.nan_to_num(img, nan=0.0), [py, px], order=order, cval=np.nan).reshape(n, n)
    g = map_coordinates(good.astype(float), [py, px], order=0, cval=0).reshape(n, n)
    out[g < 0.5] = np.nan
    return out


def clipped_mean(cube, clip=3.0):
    a = np.asarray(cube, float)
    med = np.nanmedian(a, 0)
    mad = 1.4826 * np.nanmedian(np.abs(a - med), 0)
    m = np.abs(a - med) <= clip * np.where(mad > 0, mad, np.inf)
    with np.errstate(invalid="ignore"):
        return np.nanmean(np.where(m, a, np.nan), 0)


def stretch_from(arrs, lo=2.0, hi=99.7):
    v = np.concatenate([np.asarray(a, float)[np.isfinite(a)].ravel() for a in arrs if a is not None]) if arrs else np.array([0, 1])
    if v.size == 0:
        return 0.0, 1.0
    a, b = np.percentile(v, [lo, hi])
    return float(a), float(b if b > a else a + 1)


def save(arr, path, vmin, vmax, upscale=UPSCALE):
    a = np.asarray(arr, float)
    x = np.clip((a - vmin) / (vmax - vmin), 0, 1)
    x = np.where(np.isfinite(x), x, 0.0)
    im = (x[::-1] * 255).astype(np.uint8)  # row 0 = south in the array -> flip so north is up
    up = max(1, min(upscale, 512 // max(im.shape)))
    Image.fromarray(im, "L").resize((im.shape[1] * up, im.shape[0] * up), Image.NEAREST).save(path, optimize=True)
    return dict(px=im.shape[0] * up, scale_arcsec_per_px=SCALE / up)


def xy_in_png(east_arcsec, north_arcsec, n=None, upscale=UPSCALE):
    """PNG pixel coordinates (x right, y down) of a sky offset from the image centre."""
    n = n or int(round(2 * HALF_AS / SCALE)) + 1
    k = (n - 1) / 2
    return [round((k - east_arcsec / SCALE + 0.5) * upscale, 1), round((k - north_arcsec / SCALE + 0.5) * upscale, 1)]
