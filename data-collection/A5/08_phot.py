"""A5 step 8: per-exposure measurements on the saved SPHEREx stamps.
For each stamp: predicted position (PM + parallax at MJD-AVG), wavelength at the
target pixel, flags near the target, and three measurements:
  (1) strict ePSF forced photometry at the predicted position (pilot method,
      rewind.forced_phot; pixels with OVERFLOW/NONLINEAR/... dropped);
  (2) "wing" ePSF fit for saturated stars: same, but only drops NaN, NONFUNC,
      MISSING, OVERFLOW, SUR_ERROR and NONLINEAR pixels and accepts any PSF fraction
      >= 2% (the core is gone, the wings carry the flux - ESTIMATED quality);
  (3) free-position ePSF fit (dx, dy, flux, bkg) with scipy least_squares, using
      the same pixel mask as (2): measured minus predicted offset (east, north) arcsec.
Usage: python 08_phot.py [target ...]. Output: results/<key>_phot.csv"""
import os, sys, glob, warnings
import numpy as np, pandas as pd
from astropy.io import fits
from astropy.time import Time
from astropy.coordinates import SkyCoord
import astropy.units as u
from scipy.optimize import least_squares
from a5lib import OUT, radec_at, sky_offset_arcsec, pos
from astrometry import ASTRO
import rewind as R

warnings.filterwarnings("ignore")
SAT_BITS = (1 << 1) | (1 << 2) | (1 << 15) | (1 << 26)  # OVERFLOW, SUR_ERROR, NONLINEAR, BLOOM
WING_DROP = (1 << 1) | (1 << 2) | (1 << 6) | (1 << 9) | (1 << 15)
rd = os.path.join(OUT, "results"); os.makedirs(rd, exist_ok=True)


def wing_fit(st, ra, dec, free=False, half=4):
    x, y = st.wcs.all_world2pix([[ra, dec]], 0)[0]
    ny, nx = st.image.shape
    if not (half <= x < nx - half - 1 and half <= y < ny - half - 1):
        return dict(w_status="edge")
    jj, ii = np.mgrid[0:ny, 0:nx]
    rr = np.hypot(ii - x, jj - y)
    good = ((st.flags & WING_DROP) == 0) & np.isfinite(st.image) & np.isfinite(st.variance) & (st.variance > 0)
    ann = good & (rr >= 6) & (rr <= 9.5) & ((st.flags & SAT_BITS) == 0)
    bkg = np.nanmedian(st.image[ann]) if ann.sum() > 10 else np.nanmedian(st.image[good])
    psf_os, _ = R.epsf_zone(st.epsf_table, x + st.x0, y + st.y0)
    xi, yi = int(round(x)), int(round(y))
    sl = (slice(yi - half, yi + half + 1), slice(xi - half, xi + half + 1))
    n = 2 * half + 1
    D, V, G = st.image[sl] - bkg, st.variance[sl], good[sl]
    sr = R.pixel_sr(st) * 1e12
    out = {}
    P = R.psf_native(psf_os, x - xi, y - yi, n)
    fr = float(P[G].sum())
    out.update(w_psf_frac=fr, w_npix=int(G.sum()))
    if fr < 0.02 or G.sum() < 8:
        out["w_status"] = "masked"
        return out
    w = 1 / V[G]
    F = np.sum(w * P[G] * D[G]) / np.sum(w * P[G] ** 2)
    E = 1 / np.sqrt(np.sum(P[G] ** 2 * w))
    out.update(w_status="ok", w_flux_uJy=F * sr, w_err_uJy=E * sr, w_snr=F / E)
    if free and F / E > 5:
        def resid(p):
            Pm = R.psf_native(psf_os, x - xi + p[0], y - yi + p[1], n)
            return ((D - p[2] * Pm - p[3]) / np.sqrt(V))[G]
        try:
            s = least_squares(resid, [0, 0, F, 0], bounds=([-3, -3, 0, -np.inf], [3, 3, np.inf, np.inf]), x_scale=[0.1, 0.1, abs(F) + 1, 1])
            dx, dy = s.x[:2]
            J = s.jac
            cov = np.linalg.pinv(J.T @ J) * max(np.sum(s.fun ** 2) / max(len(s.fun) - 4, 1), 1)
            rb, db = st.wcs.all_pix2world([[x + dx, y + dy]], 0)[0]
            de, dn = sky_offset_arcsec(ra, dec, rb, db)
            out.update(c_dx_px=dx, c_dy_px=dy, c_east_arcsec=float(de), c_north_arcsec=float(dn),
                       c_err_px=float(np.sqrt((cov[0, 0] + cov[1, 1]) / 2)), c_ra=rb, c_dec=db,
                       c_chi2r=float(np.sum(s.fun ** 2) / max(len(s.fun) - 4, 1)), c_hit_bound=bool(np.any(np.abs(s.x[:2]) > 2.9)))
        except Exception as e:
            out["c_err"] = repr(e)[:80]
    return out


def run(key):
    A = ASTRO[key]
    files = sorted(glob.glob(os.path.join(OUT, "stamps", key, "*.fits")))
    rows = []
    for fn in files:
        base = os.path.basename(fn)[:-5]
        r = dict(file=os.path.relpath(fn, OUT))
        try:
            st = R.load_stamp_fits(fn)
            h = fits.getheader(fn)
        except Exception as e:
            r["status"] = "corrupt " + repr(e)[:80]; rows.append(r); continue
        mjd = float(h["MJD-AVG"])
        ra, dec = pos(A, Time(mjd, format="mjd"))
        ra, dec = float(ra[0]), float(dec[0])
        parts = base.split("_")
        r.update(obs_id="_".join(parts[:4]), detector=int(h["DETECTOR"]) if "DETECTOR" in h else int(parts[4][1]),
                 release=parts[-1], mjd=mjd, date=Time(mjd, format="mjd").isot, pred_ra=ra, pred_dec=dec,
                 x0full=h["X0FULL"], y0full=h["Y0FULL"])
        ph = R.forced_phot(st, ra, dec, r_in=5.0, r_out=9.5)
        for k in ["status", "flux_uJy", "err_uJy", "err_emp_uJy", "snr", "ab_mag", "chi2_psf", "wave_um", "bandwidth_um",
                  "flag_center_names", "flag_or_names", "npix_bad", "psf_frac_good", "x_full", "y_full"]:
            r[k] = ph.get(k)
        x, y = st.wcs.all_world2pix([[ra, dec]], 0)[0]
        jj, ii = np.mgrid[0:st.image.shape[0], 0:st.image.shape[1]]
        near = np.hypot(ii - x, jj - y) <= 2.5
        r["saturated"] = bool(np.any((st.flags[near] & SAT_BITS) != 0))
        r["n_sat_pix"] = int(np.sum((st.flags[near] & SAT_BITS) != 0))
        r["peak_MJysr"] = float(np.nanmax(st.image[near])) if np.isfinite(st.image[near]).any() else np.nan
        r.update(wing_fit(st, ra, dec, free=True))
        rows.append(r)
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(rd, f"{key}_phot.csv"), index=False)
    print(key, len(df), "stamps;", (df.status == "ok").sum(), "strict ok;", (df.get("w_status") == "ok").sum(), "wing ok;",
          int(df.saturated.sum()) if "saturated" in df else 0, "saturated", flush=True)


if __name__ == "__main__":
    for k in (sys.argv[1:] or list(ASTRO)):
        run(k)
