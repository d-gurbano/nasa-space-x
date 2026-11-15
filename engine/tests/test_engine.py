"""Unit tests for the key engine functions (synthetic data, no network)."""
import numpy as np
import pandas as pd
import pytest
from astropy.io import fits
from astropy.wcs import WCS

from rewind_engine import brightness as B
from rewind_engine import frames as F
from rewind_engine import images as IM
from rewind_engine import phot as PH
from rewind_engine import pipeline as PL
from rewind_engine import s3read
from rewind_engine import site as S
from rewind_engine import verdict as V
from rewind_engine.pilot import R


def synthetic_stamp(n=49, flux_ujy=0.0, x=None, y=None, noise=0.01, seed=0, trail=(0, 0), rot_deg=40.0):
    """A SPHEREx-like stamp: TAN WCS (6.15"/px, rotated), Gaussian ePSF, flat background + noise."""
    w = WCS(naxis=2)
    w.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    w.wcs.crval = [150.0, 20.0]
    w.wcs.crpix = [(n + 1) / 2, (n + 1) / 2]
    s = 6.15 / 3600
    c, sn = np.cos(np.radians(rot_deg)), np.sin(np.radians(rot_deg))
    w.wcs.cd = np.array([[-s * c, s * sn], [s * sn, s * c]])
    psf = R.gaussian_epsf(9.0)
    ep = dict(XCENTER=np.array([1020.0]), YCENTER=np.array([1020.0]), XWIDTH=np.array([1e6]), YWIDTH=np.array([1e6]),
              EPSF=psf.reshape(1, 33, 33))
    rng = np.random.default_rng(seed)
    img = 0.5 + rng.normal(0, noise, (n, n))
    var = np.full((n, n), noise ** 2)
    hdr = fits.Header()
    hdr["OMEGA_MEDIAN"] = 37.8
    st = R.Stamp(img, np.zeros((n, n), np.int64), var, np.zeros((n, n)), w, 0, 0, hdr, ep, None)
    if flux_ujy:
        ra, dec = w.all_pix2world([[x if x is not None else (n - 1) / 2, y if y is not None else (n - 1) / 2]], 0)[0]
        st.image = PH.plant(st, ra, dec, flux_ujy, trail)
    return st


def test_phot_point_matches_pilot_and_recovers_flux():
    st = synthetic_stamp(flux_ujy=50.0, x=24.3, y=23.8, noise=0.0005)
    ra, dec = st.wcs.all_pix2world([[24.3, 23.8]], 0)[0]
    a = PH.phot(st, ra, dec)
    b = R.forced_phot(st, ra, dec)
    assert a["status"] == "ok"
    assert a["flux"] == pytest.approx(b["flux_uJy"], rel=1e-9)
    assert a["flux"] == pytest.approx(50.0, rel=0.05)


def test_trailed_model_beats_point_model_on_a_trail():
    trail = (8.0, 3.0)
    st = synthetic_stamp(flux_ujy=200.0, trail=trail, noise=0.002)
    ra, dec = st.wcs.all_pix2world([[24, 24]], 0)[0]
    t = PH.phot(st, ra, dec, trail)
    p = PH.phot(st, ra, dec)
    assert t["trailed"] and not p["trailed"]
    assert t["flux"] == pytest.approx(200.0, rel=0.1)
    assert p["flux"] < 0.8 * t["flux"]  # a point fit loses most of a streak


def test_psf_model_normalised():
    psf = R.gaussian_epsf(9.0)
    for tr in [(0, 0), (5, 0), (3, 4)]:
        assert PH.psf_model(psf, 0.2, -0.1, 15, tr).sum() == pytest.approx(1.0)


def test_robust_amp_colour_weighting():
    rng = np.random.default_rng(1)
    s = rng.uniform(5, 30, 200)       # expected flux per frame
    e = np.full(200, 4.0)
    f = 0.7 * s + rng.normal(0, 4.0, 200)
    f[:5] += 500                       # star passing through 5 frames
    A, E, snr, n = PL.robust_amp(f, e, s)
    assert A == pytest.approx(0.7, abs=0.06)
    assert n < 200


def test_null_offsets_inside_stamp():
    for half, L in [(24, 0), (64, 8)]:
        off = PL.null_offsets_px(half, L)
        r = np.hypot(*off.T)
        assert len(off) == PL.N_NULL
        assert r.min() >= 4 and r.max() <= half - 12


def test_brightness_units_and_thermal():
    assert B.ujy_to_ab(B.ab_to_ujy(20.0)) == pytest.approx(20.0)
    near = B.neatm_ujy(4.5, 20.0, 1.0, 0.1, 60)
    far = B.neatm_ujy(4.5, 20.0, 2.0, 0.1, 30)
    assert near > far > 0
    # solar-colour reflected light at 0.55 um equals V (V-AB = 0 there in the pilot table)
    assert B.ujy_to_ab(B.reflected_ujy(18.0, np.array([0.55]), None))[0] == pytest.approx(18.0, abs=0.01)


def test_verdict_rules():
    obj = type("O", (), dict(name="X", role="precovery"))()
    good = dict(snr_scaled=7.0, null_exceed=0, null_n=24, shift_peak_at_zero=True, days_positive=3, recovered_at_pred=0.9,
                n=100, limit_mag=21.0,
                frac_positive=dict(target=0.7, null_mean=0.5, null_std=0.04, null_max=0.6), snr_without_best_day=6.0)
    v, s, _ = V.decide(obj, dict(n_frames_measured=100, cleaned=True, main=good), {"ok": True})
    assert v == "FOUND"
    v, _, _ = V.decide(obj, dict(n_frames_measured=100, cleaned=True, main=good), {"ok": False})
    assert v == "HINT"   # orbit fit blew up -> downgrade
    one_day = dict(good, snr_without_best_day=2.0)
    assert V.decide(obj, dict(n_frames_measured=100, cleaned=True, main=one_day), {"ok": True})[0] == "HINT"
    weak_sign = dict(good, frac_positive=dict(target=0.61, null_mean=0.5, null_std=0.05, null_max=0.609))
    assert V.decide(obj, dict(n_frames_measured=100, cleaned=True, main=weak_sign), {"ok": True})[0] == "HINT"
    faint = dict(good, snr_scaled=0.3, shift_peak_at_zero=False, days_positive=0, recovered_at_pred=0.0)
    assert V.decide(obj, dict(n_frames_measured=50, cleaned=True, main=faint), None)[0] == "TOO_FAINT"
    assert V.decide(obj, None)[0] == "NO_PHOTOS"


def test_extname_parser():
    h = fits.Header()
    h["XTENSION"] = "IMAGE"
    h["EXTNAME"] = "VARIANCE"
    raw = h.tostring().encode()
    assert s3read._extname(raw) == "VARIANCE"


def test_north_up_east_left():
    st = synthetic_stamp(flux_ujy=300.0, noise=0.001)
    ra0, dec0 = st.wcs.all_pix2world([[24, 24]], 0)[0]
    # source 20" east of the centre must land left of the image centre, north must be up
    ra_e, dec_e = R.offset_radec(ra0, dec0, -20, 0)  # centre 20" WEST of the source -> source is east
    a = IM.north_up(st, ra_e, dec_e, order=1)
    j, i = np.unravel_index(np.nanargmax(a), a.shape)
    k = (a.shape[0] - 1) / 2
    assert i < k - 5 and abs(j - k) <= 2
    ra_n, dec_n = R.offset_radec(ra0, dec0, 0, -20)  # source north of the centre
    a = IM.north_up(st, ra_n, dec_n, order=1)
    j, i = np.unravel_index(np.nanargmax(a), a.shape)
    assert j > k + 5  # array row grows to the north (flipped when saved)
    assert IM.xy_in_png(20, 0)[0] < IM.xy_in_png(0, 0)[0]


def test_json_clean_and_stamp_half():
    assert S.clean({"a": np.float64("nan"), "b": [np.int64(3)], "_x": 1}) == {"a": None, "b": [3]}
    assert F.stamp_half(0, 0) == 24 and F.stamp_half(300, 0) == 64 and F.stamp_half(30, 10) == 44


def test_rank_frames_prefers_close_and_bright():
    obj = type("O", (), dict(role="precovery", disc_iso="2026-01-10"))()
    fr = pd.DataFrame(dict(mjd_avg=[61040.0, 61049.0, 61049.5], mag=[18.0, 20.0, 25.0], file=list("abc")))
    out = F.rank_frames(fr, obj, cap=2)
    assert set(out.file) == {"a", "b"}
