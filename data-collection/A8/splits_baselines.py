"""A8 - frozen splits, static-sky baseline and known-mover checks.

  python code/A8/splits_baselines.py splits     -> index/splits_patch.parquet, index/patch_epochs_split.parquet
  python code/A8/splits_baselines.py staticref  -> baselines/<patch>_staticref.npz
  python code/A8/splits_baselines.py km_check   -> tables/known_mover_check.csv (do known asteroids show up?)

Splits (frozen, documented in DATA-CARD.md):
  region (per cluster): train = NEP-A, NEP-B, SEP-A, ECL-1, MID-1; val = NEP-C; test = NEP-D, SEP-B, ECL-2, MID-2
  time (per epoch, header MJD-AVG): early < 61100 (2026-03-09) <= mid < 61200 (2026-06-17) <= late
  split: test  = test region (any time) OR late (any region)
         val   = (train region AND mid) OR (val region AND not late)
         train = train region AND early
"""
import os, sys, json
import numpy as np, pandas as pd
from scipy.ndimage import map_coordinates

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, os.path.join(ROOT, 'code/A8'))
import build_patches as B  # noqa: E402

REGION = {'NEP-A': 'train', 'NEP-B': 'train', 'SEP-A': 'train', 'ECL-1': 'train', 'MID-1': 'train',
          'NEP-C': 'val', 'NEP-D': 'test', 'SEP-B': 'test', 'ECL-2': 'test', 'MID-2': 'test'}
T_MID, T_LATE = 61100.0, 61200.0
SAME_PASS_DAYS = 1.0     # reference epochs must be > 1 day away (a mover in the same pass would self-subtract)
R_LVF = {1: 39, 2: 41, 3: 41, 4: 35, 5: 112, 6: 128}   # ESTIMATED resolving power per detector (ES v2.1 order of magnitude)
BL = os.path.join(B.OUT, 'baselines' if B.VERSION == 'v1' else f'baselines_{B.VERSION}')
TAB = os.path.join(B.OUT, 'tables' if B.VERSION == 'v1' else f'tables_{B.VERSION}')


def cmd_splits():
    pe = pd.read_parquet(os.path.join(B.IDX, 'patch_epochs.parquet'))
    pe['region_split'] = pe.cluster.map(REGION)
    pe['time_bin'] = np.where(pe.mjd_avg < T_MID, 'early', np.where(pe.mjd_avg < T_LATE, 'mid', 'late'))
    r, t = pe.region_split, pe.time_bin
    split = np.where((r == 'test') | (t == 'late'), 'test',
                     np.where(((r == 'train') & (t == 'mid')) | ((r == 'val') & (t != 'late')), 'val', 'train'))
    pe['split'] = split
    pe['test_kind'] = np.where(pe.split != 'test', '', np.where((r == 'test') & (t == 'late'), 'region+time',
                                                                  np.where(r == 'test', 'region', 'time')))
    km_f = os.path.join(B.IDX, 'known_movers.parquet')
    if os.path.exists(km_f):
        km = pd.read_parquet(km_f)
        g = km[km.in_aligned].groupby(['patch', 'frame_id'])
        cnt = g.size().rename('n_known_aligned')
        vmin = g.vmag.min().rename('known_vmin')
        pe = pe.merge(cnt, on=['patch', 'frame_id'], how='left').merge(vmin, on=['patch', 'frame_id'], how='left')
        pe['n_known_aligned'] = pe.n_known_aligned.fillna(0).astype(int)
    # SPHEREx team exposure anomaly log (copied by A7; covers Apr-Aug 2025 only): flag affected patch-epochs
    an_f = os.path.join(ROOT, 'data/07-answer-keys/junk/anomaly_list/SPHEREX_exposure_anomaly_log_20250810.csv')
    pe['anomaly'] = ''
    if os.path.exists(an_f):
        an = pd.read_csv(an_f)
        fr = pd.read_parquet(os.path.join(B.IDX, 'frames.parquet'))[['frame_id', 'OBSID']]
        pe = pe.merge(fr, on='frame_id', how='left')
        amap = {}
        for r in an.itertuples():
            for d in range(1, 7):
                if getattr(r, f'BAND_{d}_AFFECTED', 0):
                    amap[(r.OBSID, d)] = r.ANOMALY_NAME
        pe['anomaly'] = [amap.get((o, int(d)), '') for o, d in zip(pe.OBSID, pe.det)]
        print('patch-epochs on anomaly-log exposures:', int((pe.anomaly != '').sum()))
    pe.to_parquet(os.path.join(B.IDX, 'patch_epochs_split.parquet'))
    sp = pe.groupby('patch').agg(cluster=('cluster', 'first'), region_split=('region_split', 'first'),
                                 n_epochs=('epoch_index', 'size')).reset_index()
    role = {c['name']: c['role'] for c in B.CLUSTERS}
    sp['role'] = sp.cluster.map(role)
    sp.to_parquet(os.path.join(B.IDX, 'splits_patch.parquet'))
    tab = pe.groupby(['split', 'test_kind', 'cluster']).size().unstack(fill_value=0)
    print(tab)
    os.makedirs(TAB, exist_ok=True)
    tab.to_csv(os.path.join(TAB, 'split_counts.csv'))
    print(pe.groupby('time_bin').mjd_avg.agg(['min', 'max', 'size']))


def static_ref(a, lam, bw, det, mjd, flags=None, win=2.0, min_n=3):
    """Per-pixel static-sky reference for every epoch e, built ONLY from other epochs of the same detector that
    are > SAME_PASS_DAYS away in time and whose wavelength at that pixel is within win x channel width (bw):
    a regularised linear fit of value vs (lambda_o - lambda_e), evaluated at lambda_e, with one 4-sigma MAD
    clip. Needs >= min_n reference epochs per pixel, else NaN. a, lam, bw: (E, H, W).
    Returns ref (E,H,W) float32, nref (E,H,W) uint8."""
    E = a.shape[0]
    ref = np.full(a.shape, np.nan, np.float32)
    nref = np.zeros(a.shape, np.uint8)
    for e in range(E):
        o = np.where((det == det[e]) & (np.abs(mjd - mjd[e]) > SAME_PASS_DAYS))[0]
        if len(o) < min_n:
            continue
        x = lam[o] - lam[e][None]
        y = a[o].astype(np.float64)
        m = (np.abs(x) < win * bw[e][None]) & np.isfinite(y) & np.isfinite(x)
        if flags is not None:
            m &= (flags[o] & BAD) == 0
        eps = (0.3 * bw[e]) ** 2
        for it in range(2):
            w = m.astype(np.float64)
            n = w.sum(0)
            with np.errstate(all='ignore'):
                xm = np.nansum(np.where(m, x, 0), 0) / n
                ym = np.nansum(np.where(m, y, 0), 0) / n
                cxx = np.nansum(np.where(m, (x - xm) ** 2, 0), 0) / n
                cxy = np.nansum(np.where(m, (x - xm) * (y - ym), 0), 0) / n
                slope = cxy / (cxx + eps)
                fit = ym - slope * xm
                if it == 0:
                    r = np.where(m, y - (ym + slope * (x - xm)), np.nan)
                    mad = 1.4826 * np.nanmedian(np.abs(r), 0)
                    m &= ~(np.abs(r) > 4 * np.maximum(mad, 1e-12))
        fit[n < min_n] = np.nan
        ref[e] = fit
        nref[e] = np.clip(n, 0, 255)
    return ref, nref


import rewind as _R  # noqa: E402  (code/A0 is on sys.path via build_patches)
BAD = _R.BAD_MASK_STRICT


def cmd_staticref():
    os.makedirs(BL, exist_ok=True)
    rows = []
    for f in sorted(os.listdir(B.PAT)):
        patch = f[:-4]
        z = np.load(os.path.join(B.PAT, f))
        a = z['al_img'] - z['al_zodi']
        E = a.shape[0]
        bw = np.stack([map_coordinates(z['bw'][e].astype(np.float32), [z['al_y'][e], z['al_x'][e]], order=1, cval=np.nan)
                       for e in range(E)])
        ref, nref = static_ref(a, z['al_lam'], bw, z['det'], z['mjd_avg'], z['al_flags'], win=2.0)
        # fallback where fewer than 3 epochs match: broader +/-6 channel-width window, same linear fit
        ref6, nref6 = static_ref(a, z['al_lam'], bw, z['det'], z['mjd_avg'], z['al_flags'], win=6.0)
        rq = np.where(np.isfinite(ref), 1, np.where(np.isfinite(ref6), 2, 0)).astype(np.uint8)
        nref = np.where(rq == 2, nref6, nref).astype(np.uint8)
        ref = np.where(rq == 2, ref6, ref).astype(np.float32)
        res = a - ref
        np.savez_compressed(os.path.join(BL, patch + '_staticref.npz'), ref=ref, nref=nref, ref_quality=rq,
                            al_bw=bw.astype(np.float16))
        # robust residual noise vs VARIANCE (per patch)
        with np.errstate(all='ignore'):
            chi = res / np.sqrt(z['al_var'] * (1 + 1.0 / np.maximum(nref, 1)))
        good = np.isfinite(chi)
        rows.append(dict(patch=patch, epochs=E, frac_pix_with_ref=float(good.mean()), frac_narrow=float((rq == 1).mean()),
                         median_nref=float(np.median(nref[nref > 0])) if (nref > 0).any() else 0,
                         chi_mad=float(1.4826 * np.nanmedian(np.abs(chi[good] - np.nanmedian(chi[good])))) if good.any() else np.nan,
                         chi_p999=float(np.nanpercentile(np.abs(chi[good]), 99.9)) if good.any() else np.nan))
        print(rows[-1], flush=True)
    os.makedirs(TAB, exist_ok=True)
    pd.DataFrame(rows).to_csv(os.path.join(TAB, 'staticref_summary.csv'), index=False)


def cmd_km_check():
    """For known movers predicted inside the aligned grid with V < 18: is there a positive static-ref residual
    at the predicted pixel? Compares the 3x3 residual sum at the prediction against 3x3 sums at 24 random
    off positions of the same epoch."""
    km = pd.read_parquet(os.path.join(B.IDX, 'known_movers.parquet'))
    km = km[km.in_aligned & (km.vmag < 18) & (km.x_al > 3) & (km.x_al < 60) & (km.y_al > 3) & (km.y_al < 60)]
    pe = pd.read_parquet(os.path.join(B.IDX, 'patch_epochs.parquet'))
    rng = np.random.default_rng(3)
    out = []
    for patch, g in km.groupby('patch'):
        z = np.load(os.path.join(B.PAT, patch + '.npz'))
        sr = np.load(os.path.join(BL, patch + '_staticref.npz'))
        fid = list(z['frame_id'])
        res = z['al_img'] - z['al_zodi'] - sr['ref']
        for r in g.itertuples():
            if r.frame_id not in fid:
                continue
            e = fid.index(r.frame_id)
            xi, yi = int(round(r.x_al)), int(round(r.y_al))
            S = np.nansum(res[e, yi - 1:yi + 2, xi - 1:xi + 2])
            V = np.nansum(z['al_var'][e, yi - 1:yi + 2, xi - 1:xi + 2])
            offs = []
            for _ in range(24):
                xo, yo = rng.integers(3, 61, 2)
                if np.hypot(xo - xi, yo - yi) > 6:
                    offs.append(np.nansum(res[e, yo - 1:yo + 2, xo - 1:xo + 2]))
            offs = np.array(offs)
            sd = 1.4826 * np.median(np.abs(offs - np.median(offs)))
            out.append(dict(patch=patch, frame_id=r.frame_id, desig=r.desig, vmag=r.vmag, det=r.det,
                            rate_arcsec_min=float(np.hypot(r.rate_ra_cosdec_arcsec_min, r.rate_dec_arcsec_min)),
                            resid_sum3x3=S, off_median=float(np.median(offs)), off_sd=sd,
                            z_vs_off=(S - np.median(offs)) / sd if sd > 0 else np.nan, z_var=S / np.sqrt(V) if V > 0 else np.nan))
    o = pd.DataFrame(out)
    os.makedirs(TAB, exist_ok=True)
    o.to_csv(os.path.join(TAB, 'known_mover_check.csv'), index=False)
    if len(o):
        o['vbin'] = pd.cut(o.vmag, [0, 14, 15, 16, 17, 18])
        print(o.groupby('vbin', observed=True).agg(n=('z_vs_off', 'size'), median_z=('z_vs_off', 'median'),
                                                   frac_z_gt5=('z_vs_off', lambda s: float((s > 5).mean()))))


if __name__ == '__main__':
    {'splits': cmd_splits, 'staticref': cmd_staticref, 'km_check': cmd_km_check}[sys.argv[1]]()
