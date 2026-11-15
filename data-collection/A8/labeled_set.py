"""A8 - 'real or fake' labeled stamp set from the patch time series (aligned 64x64 grid).

Stamp = 15x15 aligned pixels, 6 channels: [image-zodi, static-sky ref, residual, sigma=sqrt(VARIANCE), wavelength um,
bad-flag mask]. Units MJy/sr (channels 0-3). Every stamp inherits the frozen split of its patch-epoch.
Labels (column `label`, plus `is_mover` 1/0):
  real_known   - known asteroid/comet predicted by kete at the stamp centre (V < 20), is_mover=1
  fake_planted - point source planted with the real ePSF (inject.py), AB 16-20.5, is_mover=1 (truth exact)
  junk_artifact- >5 sigma residual peak on pixels carrying artifact flags (PERSIST, GHOST*, CROSSTALK, STREAK,
                 SATELLITE_HALO, SNOWBALL, BLOOM, HALO), no known mover within 4 px, is_mover=0
  junk_star    - bright static star whose static-ref residual exceeds 5 sigma (PSF/wavelength mismatch), is_mover=0
  empty        - random position, no known mover within 6 px, is_mover=0
Note: real_known fainter than the per-frame depth (~V 19-19.5) are kept but flagged `detectable_pred` False.

  python code/A8/labeled_set.py   -> data/08-ai-training/labeled[_v2]/{labels.parquet, stamps_<split>.npz}
"""
import os, sys, json
import numpy as np, pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, os.path.join(ROOT, 'code/A8'))
import build_patches as B  # noqa: E402
import splits_baselines as SB  # noqa: E402
import inject as I  # noqa: E402

H = 7
OUTD = os.path.join(B.OUT, 'labeled' if B.VERSION == 'v1' else f'labeled_{B.VERSION}')
ART_BITS = [17, 20, 22, 23, 24, 25, 26, 27, 28, 29]
ART_MASK = int(sum(1 << b for b in ART_BITS))


def stamp(a, ref, var, lam, flg, e, x, y):
    xi, yi = int(round(x)), int(round(y))
    if not (H <= xi < B.NP_AL - H and H <= yi < B.NP_AL - H):
        return None
    sl = (e, slice(yi - H, yi + H + 1), slice(xi - H, xi + H + 1))
    im = a[sl]
    rf = ref[sl]
    return np.stack([im, rf, im - rf, np.sqrt(var[sl]), lam[sl], ((flg[sl] & SB.BAD) != 0).astype(np.float32)]).astype(np.float32)


def main(seed=11):
    os.makedirs(OUTD, exist_ok=True)
    rng = np.random.default_rng(seed)
    pe = pd.read_parquet(os.path.join(B.IDX, 'patch_epochs_split.parquet'))
    km = pd.read_parquet(os.path.join(B.IDX, 'known_movers.parquet'))
    km = km[km.in_aligned]
    rows, X = [], []
    for patch in sorted(pe.patch.unique()):
        P = I.Patch(patch)
        sr = np.load(os.path.join(SB.BL, patch + '_staticref.npz'))
        ref = sr['ref']
        a = P.a['al_img'] - P.a['al_zodi']
        var, lam, flg = P.a['al_var'], P.a['al_lam'], P.a['al_flags']
        fid = list(P.a['frame_id'])
        sp = pe[pe.patch == patch].set_index('frame_id')
        kmp = km[km.patch == patch]
        bx, by, bf = I.bright_sources(P)

        def add(label, e, x, y, extra, arr=None):
            s = stamp(a if arr is None else arr, ref, var, lam, flg, e, x, y)
            if s is None:
                return
            r = sp.loc[fid[e]]
            rows.append(dict(label=label, is_mover=int(label in ('real_known', 'fake_planted')), patch=patch,
                             cluster=r.cluster, frame_id=fid[e], epoch_index=e, det=int(P.a['det'][e]),
                             mjd_avg=float(P.a['mjd_avg'][e]), split=r.split, test_kind=r.test_kind,
                             x_al=float(x), y_al=float(y), has_ref=bool(np.isfinite(s[1, H, H])),
                             ref_quality=int(sr['ref_quality'][e, int(round(y)), int(round(x))]), lam_um=float(lam[e, int(round(y)), int(round(x))]), **extra))
            X.append(s)
        # real known movers
        for q in kmp.itertuples():
            if q.frame_id in fid and np.isfinite(q.vmag) and q.vmag < 20:
                add('real_known', fid.index(q.frame_id), q.x_al, q.y_al,
                    dict(desig=q.desig, vmag=float(q.vmag), detectable_pred=bool(q.vmag < 19.3),
                         rate_arcsec_min=float(np.hypot(q.rate_ra_cosdec_arcsec_min, q.rate_dec_arcsec_min))))
        n_ep = P.E
        for e in range(n_ep):
            if not np.isfinite(ref[e]).mean() > 0.3:
                continue
            kme = kmp[kmp.frame_id == fid[e]]
            res = a[e] - ref[e]
            sig = np.sqrt(var[e] * (1 + 1.0 / np.maximum(sr['nref'][e], 1)))
            chi = res / sig

            def far(x, y, r):
                return len(kme) == 0 or np.min(np.hypot(kme.x_al - x, kme.y_al - y)) > r
            # planted fakes: 1 per epoch with valid ref (inject into a copy of this epoch only)
            x, y = rng.uniform(H + 2, B.NP_AL - H - 2, 2)
            if rng.random() < 0.35 and len(bx):
                k = rng.integers(len(bx)); r_, th = rng.uniform(1, 4), rng.uniform(0, 2 * np.pi)
                x, y = np.clip(bx[k] + r_ * np.cos(th), H + 1, B.NP_AL - H - 2), np.clip(by[k] + r_ * np.sin(th), H + 1, B.NP_AL - H - 2)
            ab = float(rng.uniform(16.0, 20.5))
            img_n, var_n = P.a['img'].copy()[e:e + 1], P.a['var'].copy()[e:e + 1]
            xn, yn = I.aligned_to_native(P, e, x, y)
            t = I.inject_point(_EpochView(P, e), img_n, var_n, 0, xn, yn, I.Sed(ab_ref=ab), rng=rng, shot=True)
            if t:
                al = I.map_coordinates(img_n[0], [P.a['al_y'][e], P.a['al_x'][e]], order=1, cval=np.nan) - P.a['al_zodi'][e]
                arr = a.copy(); arr[e] = al
                dist = float(np.min(np.hypot(bx - x, by - y))) if len(bx) else np.inf
                add('fake_planted', e, x, y, dict(ab_true=t['ab'], flux_ujy=t['flux_ujy'], snr_pred=t['snr_pred_psf'],
                                                   dist_to_bright_px=dist, detectable_pred=bool(t['snr_pred_psf'] > 5)), arr=arr)
            # junk artifacts: flagged, >5 sigma residual peaks
            art = ((flg[e] & ART_MASK) != 0) & (chi > 5) & ((flg[e] & (1 << 9)) == 0)
            ys, xs = np.where(art)
            if len(xs):
                for k in rng.choice(len(xs), min(2, len(xs)), replace=False):
                    if far(xs[k], ys[k], 4):
                        add('junk_artifact', e, xs[k], ys[k], dict(flags=int(flg[e, ys[k], xs[k]]), chi=float(chi[ys[k], xs[k]])))
            # junk star residuals
            for k in range(len(bx)):
                if np.isfinite(chi[by[k], bx[k]]) and abs(chi[by[k], bx[k]]) > 5 and rng.random() < 0.3 and far(bx[k], by[k], 4):
                    add('junk_star', e, bx[k], by[k], dict(chi=float(chi[by[k], bx[k]]), star_peak_mjysr=float(bf[k])))
            # empty
            x, y = rng.uniform(H, B.NP_AL - H - 1, 2)
            if far(x, y, 6):
                add('empty', e, x, y, dict(chi=float(chi[int(round(y)), int(round(x))])))
        print(patch, len(rows), flush=True)
    L = pd.DataFrame(rows)
    X = np.array(X)
    L['stamp_index'] = -1
    for s in L.split.unique():
        idx = np.where(L.split == s)[0]
        L.loc[idx, 'stamp_index'] = np.arange(len(idx))
        np.savez_compressed(os.path.join(OUTD, f'stamps_{s}.npz'), X=X[idx], channels=np.array(
            ['image_minus_zodi', 'static_ref', 'residual', 'sigma', 'wavelength_um', 'bad_flag']))
    L.to_parquet(os.path.join(OUTD, 'labels.parquet'))
    t = L.groupby(['split', 'label']).size().unstack(fill_value=0)
    print(t)
    t.to_csv(os.path.join(OUTD, 'label_counts.csv'))


class _EpochView:
    """Minimal Patch-like view of one epoch so inject_point can work on 1-epoch arrays."""

    def __init__(self, P, e):
        self.P, self.e = P, e
        self.a = {k: P.a[k][e:e + 1] for k in ('lam', 'zone', 'epsf', 'epsf_zone', 'img', 'var')}
        self.fr = P.fr.iloc[e:e + 1]

    def omega_sr(self, e):
        return self.P.omega_sr(self.e)

    def psf_at(self, e, x, y):
        return self.P.psf_at(self.e, x, y)

    def shot_gain(self, e):
        return self.P.shot_gain(self.e)


if __name__ == '__main__':
    main()
