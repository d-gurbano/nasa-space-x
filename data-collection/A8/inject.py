"""A8 fake-object injection kit for SPHEREx patch time series (Rewind "Expected Sky").

Injects point sources with the REAL per-zone ePSF of each frame (5x oversampled 33x33, from the L2 EPSF HDU)
at a given position, flux and SED, evaluated at the per-pixel LVF wavelength of that frame (WCS-WAVE), with
optional trailing during the 113.6 s exposure and source shot noise derived from the frame VARIANCE.
Moving-object tracks are defined on the sky (RA/Dec at t0 + linear rates) and mapped into every epoch with that
frame's own WCS (incl. SIP), so the same object lands at the right pixel in each epoch.

Library use:
    from inject import Patch, inject_point, inject_track, Sed
    P = Patch('NEP-D_11')                     # loads data/08-ai-training/patches/NEP-D_11.npz + frame WCS
    img, var, truth = inject_track(P, ra0, dec0, mjd0, rate_ra_cosdec=0.8, rate_dec=-0.3,  # arcsec/min
                                   sed=Sed(ab_ref=19.0), rng=np.random.default_rng(1))
    al_img = P.to_aligned(img)                # resample native cutouts to the shared 64x64 north-up grid

CLI (frozen injected test set):
    python code/A8/inject.py build_testset     -> data/08-ai-training/injected_test/
    python code/A8/inject.py selftest          -> recovery check of injected fluxes (forced ePSF photometry)

Units: IMAGE is MJy/sr (zodi NOT subtracted). Flux in uJy. Pixel solid angle = header OMEGA_MEDIAN arcsec^2.
AB = 23.9 - 2.5 log10(f_uJy).
"""
from __future__ import annotations
import os, sys, json
from dataclasses import dataclass
import numpy as np, pandas as pd
from astropy.io import fits
from astropy.wcs import WCS
from scipy.ndimage import map_coordinates

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, os.path.join(ROOT, 'code/A0'))
sys.path.insert(0, os.path.join(ROOT, 'code/A8'))
import build_patches as B  # noqa: E402

ARCSEC2_PER_SR = 206264.80624709636 ** 2
H_PLANCK, C_LIGHT, K_B = 6.62607015e-34, 2.99792458e8, 1.380649e-23


def ab_to_ujy(ab):
    return 10 ** (-0.4 * (np.asarray(ab, float) - 23.9))


def ujy_to_ab(f):
    return 23.9 - 2.5 * np.log10(np.asarray(f, float))


@dataclass
class Sed:
    """f_nu(lam) = F_ref * (lam/lam_ref)^alpha  +  thermal blackbody (T_K) normalised to f_th_ref at 4.5 um.
    alpha ~ +0.3..+1.0 mimics reflected sunlight from S/D types in f_nu across 0.75-2.5 um (ESTIMATED);
    T_K ~ 200-300 K with f_th_ref adds an NEO-like thermal excess in D5-D6."""
    ab_ref: float = 19.0
    lam_ref: float = 1.5
    alpha: float = 0.0
    T_K: float = 0.0
    f_th_ref_ujy: float = 0.0

    def __call__(self, lam_um):
        lam = np.asarray(lam_um, float)
        f = ab_to_ujy(self.ab_ref) * (lam / self.lam_ref) ** self.alpha
        if self.T_K > 0 and self.f_th_ref_ujy > 0:
            def bnu(l):
                nu = C_LIGHT / (l * 1e-6)
                return nu ** 3 / np.expm1(H_PLANCK * nu / (K_B * self.T_K))
            f = f + self.f_th_ref_ujy * bnu(lam) / bnu(4.5)
        return f

    def as_dict(self):
        return dict(ab_ref=self.ab_ref, lam_ref=self.lam_ref, alpha=self.alpha, T_K=self.T_K, f_th_ref_ujy=self.f_th_ref_ujy)


def psf_native(psf_os, dx, dy, n, ovs=5):
    """Point-sample the 5x oversampled ePSF at native pixel centres of an n x n grid whose centre pixel is offset
    (dx, dy) native px from the source. The ePSF already includes the pixel response, so point sampling is right
    (same convention as code/A0/rewind.py psf_native). Normalised to sum 1."""
    c = (psf_os.shape[0] - 1) / 2.0
    j, i = np.mgrid[0:n, 0:n]
    k = (n - 1) / 2.0
    p = map_coordinates(psf_os, [c + (j - k - dy) * ovs, c + (i - k - dx) * ovs], order=3, mode='constant', cval=0.0)
    p[p < 0] = 0
    s = p.sum()
    return p / s if s > 0 else p


class Patch:
    """One sky patch, all epochs. Native arrays: (E, 96, 96); aligned arrays: (E, 64, 64)."""

    def __init__(self, patch, pat_dir=None, idx_dir=None):
        pat_dir, idx_dir = pat_dir or B.PAT, idx_dir or B.IDX
        self.name = patch
        z = np.load(os.path.join(pat_dir, patch + '.npz'))
        self.a = {k: z[k] for k in z.files}
        self.E = len(self.a['mjd_avg'])
        pe = pd.read_parquet(os.path.join(idx_dir, 'patch_epochs.parquet'))
        self.pe = pe[pe.patch == patch].sort_values('epoch_index').reset_index(drop=True)
        fr = pd.read_parquet(os.path.join(idx_dir, 'frames.parquet')).set_index('frame_id')
        self.fr = fr.loc[list(self.a['frame_id'])]
        self._wcs = {}

    def wcs(self, e):
        if e not in self._wcs:
            self._wcs[e] = WCS(fits.Header.fromstring(self.fr.iloc[e]['wcs_header']), relax=True)
        return self._wcs[e]

    def sky_to_native(self, e, ra, dec):
        x, y = self.wcs(e).all_world2pix([[ra, dec]], 0)[0]
        return x - self.a['x0_full'][e], y - self.a['y0_full'][e]

    def omega_sr(self, e):
        return float(self.fr.iloc[e]['OMEGA_MEDIAN']) / ARCSEC2_PER_SR

    def psf_at(self, e, x, y):
        """ePSF zone (oversampled 33x33) covering native pixel (x, y) of epoch e."""
        zi, zj = int(np.clip(round(y), 0, B.NP_NAT - 1)), int(np.clip(round(x), 0, B.NP_NAT - 1))
        zone = self.a['zone'][e][zi, zj]
        k = np.where(self.a['epsf_zone'][e] == zone)[0]
        k = int(k[0]) if len(k) else 0
        return self.a['epsf'][e][k]

    def shot_gain(self, e):
        """k in VARIANCE ~ a + k * IMAGE (MJy/sr), robust fit over unflagged pixels; source shot noise variance
        for an injected signal S is then k * S. Falls back to 0 (background-limited) if the fit is unphysical."""
        im, va = self.a['img'][e].ravel(), self.a['var'][e].ravel()
        m = np.isfinite(im) & np.isfinite(va) & (va > 0)
        if m.sum() < 100:
            return 0.0
        im, va = im[m], va[m]
        hi = im > np.percentile(im, 99)
        lo = im < np.percentile(im, 50)
        if hi.sum() < 5:
            return 0.0
        k = (np.median(va[hi]) - np.median(va[lo])) / max(np.median(im[hi]) - np.median(im[lo]), 1e-9)
        return float(k) if np.isfinite(k) and k > 0 else 0.0

    def to_aligned(self, native):
        """Resample native (E,96,96) arrays to the aligned (E,64,64) grid with the stored mapping."""
        out = np.empty((native.shape[0], B.NP_AL, B.NP_AL), np.float32)
        for e in range(native.shape[0]):
            out[e] = map_coordinates(native[e], [self.a['al_y'][e], self.a['al_x'][e]], order=1, cval=np.nan)
        return out


def inject_point(P: Patch, img, var, e, x, y, sed: Sed, rng=None, trail_px=(0.0, 0.0), shot=True, n=11):
    """Add one point source to epoch e of native arrays img/var (modified in place). (x, y) native 0-based
    pixel position at mid-exposure; trail_px = total (dx, dy) motion during the exposure. Returns truth dict."""
    lam = float(map_coordinates(P.a['lam'][e], [[y], [x]], order=1, mode='nearest')[0])
    f = float(sed(lam))
    psf_os = P.psf_at(e, x, y)
    tl = float(np.hypot(*trail_px))
    ns = max(1, int(np.ceil(tl / 0.25)))
    offs = np.linspace(-0.5, 0.5, ns) if ns > 1 else np.array([0.0])
    xi, yi = int(round(x)), int(round(y))
    h = n // 2
    stamp = np.zeros((n, n))
    for o in offs:
        xs, ys = x + o * trail_px[0], y + o * trail_px[1]
        # PSF grid is centred on (xi, yi); source offset from that pixel centre
        stamp += psf_native(psf_os, xs - xi, ys - yi, n)
    stamp /= stamp.sum() if stamp.sum() > 0 else 1
    sig = stamp * f * 1e-12 / P.omega_sr(e)        # MJy/sr per pixel
    y0, y1, x0, x1 = yi - h, yi + h + 1, xi - h, xi + h + 1
    sy0, sx0 = max(0, -y0), max(0, -x0)
    Y0, Y1, X0, X1 = max(y0, 0), min(y1, B.NP_NAT), max(x0, 0), min(x1, B.NP_NAT)
    if Y1 <= Y0 or X1 <= X0:
        return None
    s = sig[sy0:sy0 + (Y1 - Y0), sx0:sx0 + (X1 - X0)]
    add = s.copy()
    if shot:
        k = P.shot_gain(e)
        if k > 0:
            rng = rng or np.random.default_rng()
            add = add + rng.normal(0, np.sqrt(np.clip(k * s, 0, None)))
            var[e, Y0:Y1, X0:X1] += (k * s).astype(var.dtype)
    img[e, Y0:Y1, X0:X1] += add.astype(img.dtype)
    v = var[e, yi, xi] if 0 <= yi < B.NP_NAT and 0 <= xi < B.NP_NAT else np.nan
    neff = 1.0 / np.sum(stamp ** 2)
    snr_pred = (f * 1e-12 / P.omega_sr(e)) / np.sqrt(v * neff) if np.isfinite(v) and v > 0 else np.nan
    return dict(epoch_index=int(e), x_nat=float(x), y_nat=float(y), lam_um=lam, flux_ujy=f, ab=float(ujy_to_ab(f)),
                trail_px=tl, peak_mjysr=float(sig.max()), snr_pred_psf=float(snr_pred), shot_k=float(P.shot_gain(e)) if shot else 0.0)


def inject_track(P: Patch, ra0, dec0, mjd0, rate_ra_cosdec, rate_dec, sed: Sed, rng=None, epochs=None,
                 margin=6, shot=True, track_id=0, img=None, var=None):
    """Linear sky track (rates in arcsec/min) injected into every epoch where it falls inside the native cutout
    (with `margin` px). Returns (img, var, truth DataFrame). Positions use each frame's own WCS at MJD-AVG."""
    img = P.a['img'].copy() if img is None else img
    var = P.a['var'].copy() if var is None else var
    rows = []
    pra, pdec = aligned_to_sky(P, (B.NP_AL - 1) / 2, (B.NP_AL - 1) / 2)
    epochs = range(P.E) if epochs is None else epochs
    for e in epochs:
        mjd = float(P.a['mjd_avg'][e])
        dtm = (mjd - mjd0) * 1440.0
        dec = dec0 + rate_dec * dtm / 3600
        ra = ra0 + rate_ra_cosdec * dtm / 3600 / np.cos(np.radians(dec))
        if np.hypot((ra - pra + 180) % 360 - 180, 0) * np.cos(np.radians(dec)) > 0.2 or abs(dec - pdec) > 0.2:
            continue   # far from the patch (also avoids SIP divergence far off the detector)
        try:
            x, y = P.sky_to_native(e, ra, dec)
        except Exception:
            continue
        if not (margin <= x < B.NP_NAT - margin and margin <= y < B.NP_NAT - margin):
            continue
        # trail: motion during XPOSURE in native px, from the WCS at +/- half exposure
        xp = float(P.fr.iloc[e]['XPOSURE']) / 60.0
        d2 = dec + rate_dec * xp / 2 / 3600
        r2 = ra + rate_ra_cosdec * xp / 2 / 3600 / np.cos(np.radians(dec))
        x2, y2 = P.sky_to_native(e, r2, d2)
        tr = (2 * (x2 - x), 2 * (y2 - y))
        t = inject_point(P, img, var, e, x, y, sed, rng=rng, trail_px=tr, shot=shot)
        if t:
            ax, ay = native_to_aligned(P, e, x, y)
            t.update(track_id=track_id, ra=ra, dec=dec, mjd_avg=mjd, det=int(P.a['det'][e]), x_al=ax, y_al=ay)
            rows.append(t)
    return img, var, pd.DataFrame(rows)


def _affine(P, e):
    ax, ay = P.a['al_x'][e], P.a['al_y'][e]
    jj, ii = np.mgrid[0:B.NP_AL, 0:B.NP_AL]
    A = np.c_[ii.ravel(), jj.ravel(), np.ones(ii.size)]
    cx, *_ = np.linalg.lstsq(A, ax.ravel(), rcond=None)
    cy, *_ = np.linalg.lstsq(A, ay.ravel(), rcond=None)
    return cx, cy


def aligned_to_native(P, e, xa, ya):
    """Aligned-grid (x, y) -> native-cutout (x, y) for epoch e (affine fit of the stored mapping)."""
    cx, cy = _affine(P, e)
    return float(cx[0] * xa + cx[1] * ya + cx[2]), float(cy[0] * xa + cy[1] * ya + cy[2])


def native_to_aligned(P, e, x, y):
    """Invert the stored aligned->native mapping locally (it is affine to <0.01 px over a patch)."""
    ax, ay = P.a['al_x'][e], P.a['al_y'][e]
    jj, ii = np.mgrid[0:B.NP_AL, 0:B.NP_AL]
    A = np.c_[ii.ravel(), jj.ravel(), np.ones(ii.size)]
    cx, *_ = np.linalg.lstsq(A, ax.ravel(), rcond=None)
    cy, *_ = np.linalg.lstsq(A, ay.ravel(), rcond=None)
    M = np.array([[cx[0], cx[1]], [cy[0], cy[1]]])
    s = np.linalg.solve(M, np.array([x - cx[2], y - cy[2]]))
    return float(s[0]), float(s[1])


def forced_flux(P, img, var, e, x, y, n=7):
    """Linear ePSF fit (flux + constant background) at native (x, y); returns (flux_uJy, err_uJy)."""
    psf_os = P.psf_at(e, x, y)
    xi, yi = int(round(x)), int(round(y))
    h = n // 2
    D = img[e, yi - h:yi + h + 1, xi - h:xi + h + 1].astype(float)
    V = var[e, yi - h:yi + h + 1, xi - h:xi + h + 1].astype(float)
    fl = P.a['flags'][e, yi - h:yi + h + 1, xi - h:xi + h + 1]
    G = np.isfinite(D) & np.isfinite(V) & (V > 0) & ((fl & B_BAD) == 0)
    if D.shape != (n, n) or G.sum() < 10:
        return np.nan, np.nan
    Pm = psf_native(psf_os, x - xi, y - yi, n)
    A = np.c_[Pm[G], np.ones(G.sum())]
    w = 1 / np.sqrt(V[G])
    coef, *_ = np.linalg.lstsq(A * w[:, None], D[G] * w, rcond=None)
    cov = np.linalg.inv((A * w[:, None]).T @ (A * w[:, None]))
    k = 1e12 * P.omega_sr(e)
    return coef[0] * k, np.sqrt(cov[0, 0]) * k


import rewind as _R  # noqa: E402
B_BAD = _R.BAD_MASK_STRICT


# ------------------------------------------------------------------ frozen test set
def bright_sources(P, nsig=30, min_sep=4):
    """Static bright-source positions on the aligned grid: peaks of the median zodi-subtracted aligned stack."""
    from scipy.ndimage import maximum_filter
    a = P.a['al_img'] - P.a['al_zodi']
    med = np.nanmedian(a, 0)
    bk = np.nanmedian(med)
    mad = 1.4826 * np.nanmedian(np.abs(med - bk))
    pk = (med == maximum_filter(np.nan_to_num(med, nan=-1e9), size=2 * min_sep + 1)) & (med > bk + nsig * mad)
    ys, xs = np.where(pk)
    keep = (xs > 4) & (xs < B.NP_AL - 5) & (ys > 4) & (ys < B.NP_AL - 5)
    return xs[keep], ys[keep], med[ys[keep], xs[keep]] - bk


def aligned_to_sky(P, xa, ya):
    """Aligned-grid pixel -> RA/Dec through the cluster TAN grid."""
    c = next(c for c in B.CLUSTERS if c['name'] == P.name.rsplit('_', 1)[0])
    j, i = int(P.name[-2]), int(P.name[-1])
    cw = B.cluster_wcs(c)
    h = (B.NP_AL - 1) / 2
    ra, dec = cw.all_pix2world([[xa - h + (i - 1) * B.SPACING, ya - h + (j - 1) * B.SPACING]], 0)[0]
    return float(ra), float(dec)


def build_testset(n_tracks_per_patch=40, seed=20261115):
    out = os.path.join(B.OUT, 'injected_test' if B.VERSION == 'v1' else f'injected_test_{B.VERSION}')
    os.makedirs(out, exist_ok=True)
    sp = pd.read_parquet(os.path.join(B.IDX, 'splits_patch.parquet'))
    pe = pd.read_parquet(os.path.join(B.IDX, 'patch_epochs.parquet'))
    test_patches = sorted(sp[sp.region_split == 'test'].patch)
    rng = np.random.default_rng(seed)
    truth_all = []
    for patch in test_patches:
        P = Patch(patch)
        if P.E < 5:
            continue
        img, var = P.a['img'].copy(), P.a['var'].copy()
        bx, by, bf = bright_sources(P)
        t_lo, t_hi = P.a['mjd_avg'].min(), P.a['mjd_avg'].max()
        for k in range(n_tracks_per_patch):
            kind = rng.choice(['isolated', 'near_bright', 'fast'], p=[0.45, 0.35, 0.20])
            e_anchor = int(rng.integers(P.E))
            mjd0 = float(P.a['mjd_avg'][e_anchor])
            if kind == 'near_bright' and len(bx):
                q = rng.integers(len(bx))
                r_, th = rng.uniform(1.0, 4.0), rng.uniform(0, 2 * np.pi)
                xa, ya = bx[q] + r_ * np.cos(th), by[q] + r_ * np.sin(th)
                dist = r_
            else:
                xa, ya = rng.uniform(8, B.NP_AL - 8, 2)
                dist = float(np.min(np.hypot(bx - xa, by - ya))) if len(bx) else np.inf
                kind = 'isolated' if kind == 'near_bright' else kind
            ra0, dec0 = aligned_to_sky(P, xa, ya)
            if kind == 'fast':   # NEO-like, trailed by ~1-10 px per exposure
                rate = rng.uniform(5, 60)
            else:               # main-belt / distant: 0.05-1.5 arcsec/min
                rate = rng.uniform(0.05, 1.5)
            pa = rng.uniform(0, 2 * np.pi)
            sed = Sed(ab_ref=float(rng.uniform(16.0, 21.0)), lam_ref=1.5, alpha=float(rng.choice([0.0, 0.4, 0.8])),
                      T_K=float(rng.choice([0, 0, 250])), f_th_ref_ujy=0.0)
            if sed.T_K > 0:
                sed.f_th_ref_ujy = float(ab_to_ujy(sed.ab_ref) * rng.uniform(1, 10))
            img, var, tr = inject_track(P, ra0, dec0, mjd0, rate * np.sin(pa), rate * np.cos(pa), sed, rng=rng,
                                        track_id=k, img=img, var=var)
            if len(tr):
                tr['patch'] = patch
                tr['kind'] = kind
                tr['dist_to_bright_px'] = dist
                tr['rate_arcsec_min'] = rate
                tr['pa_deg'] = np.degrees(pa)
                tr['mjd0'] = mjd0
                tr['sed_json'] = json.dumps(sed.as_dict())
                tr['frame_id'] = [P.a['frame_id'][e] for e in tr.epoch_index]
                truth_all.append(tr)
        np.savez_compressed(os.path.join(out, patch + '_injected.npz'), img=img, var=var,
                            al_img=P.to_aligned(img), al_var=P.to_aligned(var), frame_id=P.a['frame_id'],
                            mjd_avg=P.a['mjd_avg'])
        print(patch, 'epochs', P.E, 'injections', sum(len(t) for t in truth_all if t.patch.iloc[0] == patch), flush=True)
    T = pd.concat(truth_all, ignore_index=True)
    T.to_parquet(os.path.join(out, 'truth.parquet'))
    json.dump(dict(seed=seed, n_tracks_per_patch=n_tracks_per_patch, patches=test_patches,
                   ab_range=[16, 21], kinds={'isolated': 0.45, 'near_bright': 0.35, 'fast': 0.20},
                   note='frozen; regenerate only with the same seed and code version'),
              open(os.path.join(out, 'config.json'), 'w'), indent=1)
    print('truth rows', len(T), 'tracks', T.groupby(['patch', 'track_id']).ngroups)


def selftest(npatch=3, ninj=60, seed=7):
    """Inject isolated fakes at AB 15-17 (high S/N) into real epochs, then measure them back with forced ePSF
    photometry on (injected - original) and on the injected image; report ratio statistics."""
    rng = np.random.default_rng(seed)
    pats = sorted(pd.read_parquet(os.path.join(B.IDX, 'patch_epochs.parquet')).patch.unique())[:npatch]
    res = []
    for patch in pats:
        P = Patch(patch)
        for _ in range(ninj):
            e = int(rng.integers(P.E))
            x, y = rng.uniform(15, 80, 2)
            img, var = P.a['img'].copy(), P.a['var'].copy()
            t = inject_point(P, img, var, e, x, y, Sed(ab_ref=float(rng.uniform(15, 17))), rng=rng, shot=False)
            diff = img - P.a['img']
            f1, e1 = forced_flux(P, diff, var, e, x, y)
            f2, e2 = forced_flux(P, img, var, e, x, y)
            f0, e0 = forced_flux(P, P.a['img'], P.a['var'], e, x, y)
            res.append(dict(patch=patch, e=e, true=t['flux_ujy'], diff_fit=f1, inj_fit_minus_orig=f2 - f0, err=e2,
                            snr_pred=t['snr_pred_psf']))
    r = pd.DataFrame(res)
    r['ratio_diff'] = r.diff_fit / r.true
    r['ratio_inj'] = r.inj_fit_minus_orig / r.true
    print(r[['ratio_diff', 'ratio_inj']].describe())
    r.to_csv(os.path.join(B.OUT, 'tables', 'inject_selftest.csv'), index=False)


if __name__ == '__main__':
    if sys.argv[1] == 'build_testset':
        build_testset()
    elif sys.argv[1] == 'selftest':
        selftest()
