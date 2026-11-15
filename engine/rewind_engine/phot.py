"""Forced photometry on saved stamps: the pilot ePSF fit, generalised to a trailed (streak) PSF.

For a point source (trail < ~1.5 px) `phot` gives the same numbers as the pilot `forced_phot`
(tested). For a trail it averages the ePSF along the predicted motion during the exposure and
widens the fit box and the background annulus accordingly."""
from __future__ import annotations

import numpy as np
from astropy.stats import sigma_clipped_stats

from . import config as C
from .pilot import R

TRAIL_MIN_PX = 1.5


def trail_vector_px(st, ra, dec, rate_ra, rate_dec):
    """Pixel displacement (dx, dy) over one exposure for sky rates in arcsec/hour (rate_ra = dRA*cosDec)."""
    h = C.EXPTIME_S / 3600.0 / 2.0
    r0, d0 = R.offset_radec(ra, dec, -rate_ra * h, -rate_dec * h)
    r1, d1 = R.offset_radec(ra, dec, rate_ra * h, rate_dec * h)
    p = st.wcs.all_world2pix([[r0, d0], [r1, d1]], 0)
    return float(p[1, 0] - p[0, 0]), float(p[1, 1] - p[0, 1])


def psf_model(psf_os, dx, dy, n, trail=(0.0, 0.0)):
    """n x n native-pixel model centred (dx, dy) from the box centre, normalised to sum 1.
    trail = total (tx, ty) motion in pixels during the exposure (uniform along the segment)."""
    L = float(np.hypot(*trail))
    if L < TRAIL_MIN_PX:
        return R.psf_native(psf_os, dx, dy, n)
    k = int(np.ceil(L / 0.25)) + 1
    m = np.zeros((n, n))
    for t in np.linspace(-0.5, 0.5, k):
        m += R.psf_native(psf_os, dx + t * trail[0], dy + t * trail[1], n)
    s = m.sum()
    return m / s if s > 0 else m


def phot(st, ra, dec, trail=(0.0, 0.0), bad_mask=R.BAD_MASK_STRICT, image=None, r_in=6.0, r_out=12.0):
    """ePSF (or trailed ePSF) weighted linear flux fit with an annulus background.
    `image` overrides st.image (used by injection tests). Returns flux/err in uJy and S/N."""
    img = st.image if image is None else image
    x, y = st.wcs.all_world2pix([[ra, dec]], 0)[0]
    L = float(np.hypot(*trail))
    trailed = L >= TRAIL_MIN_PX
    fit_half = 3 + (int(np.ceil(L / 2)) if trailed else 0)
    r_in2, r_out2 = (r_in + L / 2, r_out + L / 2) if trailed else (r_in, r_out)
    ny, nx = img.shape
    res = dict(x=x, y=y, trailed=trailed)
    if not (fit_half <= x < nx - fit_half - 1 and fit_half <= y < ny - fit_half - 1):
        res["status"] = "edge"
        return res
    jj, ii = np.mgrid[0:ny, 0:nx]
    if trailed:  # distance to the trail segment
        tx, ty = trail[0] / L, trail[1] / L
        u = np.clip((ii - x) * tx + (jj - y) * ty, -L / 2, L / 2)
        rr = np.hypot(ii - x - u * tx, jj - y - u * ty)
    else:
        rr = np.hypot(ii - x, jj - y)
    good = ((st.flags & bad_mask) == 0) & np.isfinite(img) & np.isfinite(st.variance) & (st.variance > 0)
    ann = good & (rr >= r_in2) & (rr <= r_out2)
    if ann.sum() < 20:
        res["status"] = "no_background"
        return res
    _, bkg, bstd = sigma_clipped_stats(img[ann], sigma=3.0, maxiters=5)
    xi, yi = int(round(x)), int(round(y))
    sl = (slice(yi - fit_half, yi + fit_half + 1), slice(xi - fit_half, xi + fit_half + 1))
    n = 2 * fit_half + 1
    psf_os, _ = R.epsf_zone(st.epsf_table, x + st.x0, y + st.y0)
    P = psf_model(psf_os, x - xi, y - yi, n, trail)
    D, V, G = img[sl] - bkg, st.variance[sl], good[sl]
    if P[G].sum() < 0.5:
        res["status"] = "masked"
        return res
    to_uJy = R.pixel_sr(st) * 1e12
    w = P[G] / V[G]
    F = np.sum(w * D[G]) / np.sum(w * P[G])
    E = 1.0 / np.sqrt(np.sum(P[G] ** 2 / V[G]))
    chi2 = float(np.sum((D[G] - F * P[G]) ** 2 / V[G]) / max(G.sum() - 1, 1))
    fv = int(st.flags[min(max(yi, 0), ny - 1), min(max(xi, 0), nx - 1)])
    res.update(status="ok", flux=F * to_uJy, err=E * to_uJy, snr=F / E, bkg=bkg, bkg_std=bstd, chi2=chi2,
               flag_center=fv, flag_or=int(np.bitwise_or.reduce(st.flags[sl].ravel())),
               psf_frac_good=float(P[G].sum()))
    return res


def wavelength(st, ra, dec):
    x, y = st.wcs.all_world2pix([[ra, dec]], 0)[0]
    if st.wave_table is None:
        return np.nan, np.nan
    wt = st.wave_table[0] if np.ndim(st.wave_table) else st.wave_table
    return R.wavelength_at(wt, x + st.x0, y + st.y0)


def plant(st, ra, dec, flux_uJy, trail=(0.0, 0.0), image=None):
    """Return a copy of the image with a (trailed) ePSF source of flux_uJy added at (ra, dec)."""
    img = (st.image if image is None else image).copy()
    x, y = st.wcs.all_world2pix([[ra, dec]], 0)[0]
    L = float(np.hypot(*trail))
    h = 4 + int(np.ceil(L / 2))
    xi, yi = int(round(x)), int(round(y))
    ny, nx = img.shape
    if not (h <= xi < nx - h and h <= yi < ny - h):
        return img
    psf_os, _ = R.epsf_zone(st.epsf_table, x + st.x0, y + st.y0)
    P = psf_model(psf_os, x - xi, y - yi, 2 * h + 1, trail)
    img[yi - h:yi + h + 1, xi - h:xi + h + 1] += P * flux_uJy / (R.pixel_sr(st) * 1e12)
    return img
