import numpy as np
from astropy.wcs import WCS

from rewind_engine import neowise as N


def _frame(flux=0.0, trail=(0.0, 0.0), seed=1):
    w = WCS(naxis=2)
    w.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    w.wcs.crval = [80.0, -16.0]
    w.wcs.crpix = [41, 41]
    w.wcs.cd = np.array([[-N.PIX / 3600, 0], [0, N.PIX / 3600]])
    rng = np.random.default_rng(seed)
    img = 40 + rng.normal(0, 5, (81, 81))
    Y, X = np.mgrid[0:81, 0:81]
    sig = N.FWHM[2] / 2.3548 / N.PIX
    img += flux * N._gauss_pix(40.0, 40.0, sig, X, Y)
    return dict(img=img, unc=np.full_like(img, 5.0), bad=np.zeros(img.shape, bool), wcs=w, band=2)


def test_phot_recovers_flux_and_unit_null_scatter():
    p = N.phot(_frame(500.0), 80.0, -16.0)
    assert p["ok"] and abs(p["flux_dn"] - 500) < 4 * p["err_dn"]
    snr = [N.phot(_frame(0.0, seed=s), 80.0, -16.0)["snr"] for s in range(200)]
    assert 0.8 < np.std(snr) < 1.25 and abs(np.mean(snr)) < 0.25


def test_robust_stack_clips_outlier():
    f = np.r_[np.ones(10), 50.0]
    F, E, S, n, keep = N.robust_stack(f, np.ones(11))
    assert n == 10 and not keep[-1] and abs(F - 1) < 1e-9
