"""A7 step 3: known-object answer key for the selected SPHEREx frames.

For every frame in frames_meta.parquet:
  observer  = SPHEREx at header MJD-AVG, position from the header X_SC/Y_SC/Z_SC (geocentric ICRF, km,
              VERIFIED keyword comment 'Exposure MID') + kete DE440 Earth. Horizons-TLE vectors
              (code/A2/positions.py) are used only to report the difference.
  objects   = all 1.58 M MPCORB asteroids (data/02-orbits, epoch 2026-06-09 TT) + 973 MPC comets,
              kete n-body (planets only, no asteroid perturbers, no comet non-grav), light-time corrected.
  FOV       = frame corners from the IMAGE WCS (TAN-SIP), expanded 4 px, then exact pixel test.
Outputs: data/07-answer-keys/answer_key/known_objects_in_frames.parquet (+ per-frame summary).
"""
import os, sys, json, time
import numpy as np, pandas as pd
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, os.path.join(ROOT, 'code/A7')); sys.path.insert(0, os.path.join(ROOT, 'code/A0'))
sys.path.insert(0, os.path.join(ROOT, 'code/A2'))
from mpcorb import load_mpcorb, load_comets, kete
from astropy.io import fits
from astropy.wcs import WCS
from rewind import expected_ab_reflected
import positions as A2pos

OUT = os.path.join(ROOT, 'data/07-answer-keys/answer_key'); os.makedirs(OUT, exist_ok=True)
AU_KM = 149597870.7


def frame_wcs(hstr):
    return WCS(fits.Header.fromstring(hstr), relax=True, key=' ')


def observer_from_header(r, jd):
    earth = kete.spice.get_state('earth', jd)
    p = np.array([r['X_SC'], r['Y_SC'], r['Z_SC']], float) / AU_KM
    v = np.array([r['VX_SC'], r['VY_SC'], r['VZ_SC']], float) * 86400 / AU_KM
    dp = kete.Vector(list(p), kete.Frames.Equatorial).as_ecliptic
    dv = kete.Vector(list(v), kete.Frames.Equatorial).as_ecliptic
    return kete.State('spherex', jd, [earth.pos[k] + dp[k] for k in range(3)],
                      [earth.vel[k] + dv[k] for k in range(3)], kete.Frames.Ecliptic, 10)


def wave_at(r, x0, y0):
    X = np.array(json.loads(r['wave_X'])); Y = np.array(json.loads(r['wave_Y']))
    V = np.array(json.loads(r['wave_V'])).reshape(len(Y), len(X), 2)
    from scipy.ndimage import map_coordinates
    fx = np.interp(np.asarray(x0) + 1, X, np.arange(len(X))); fy = np.interp(np.asarray(y0) + 1, Y, np.arange(len(Y)))
    return (map_coordinates(V[:, :, 0], [fy, fx], order=1), map_coordinates(V[:, :, 1], [fy, fx], order=1))


def hg(H, G, r, d, ph):
    G = np.where(np.isfinite(G), G, 0.15)
    t = np.tan(np.radians(ph) / 2)
    return H + 5 * np.log10(r * d) - 2.5 * np.log10((1 - G) * np.exp(-3.33 * t ** 0.63) + G * np.exp(-1.87 * t ** 1.22))


def main():
    meta = pd.read_parquet(os.path.join(ROOT, 'data/07-answer-keys/frames/frames_meta.parquet'))
    sel = pd.read_parquet(os.path.join(ROOT, 'data/07-answer-keys/frames/frames_selected.parquet'))
    meta = meta.merge(sel[['key', 'release', 'field', 'field_class']], on='key')
    fovs, info, sc_diff = [], {}, []
    for r in meta.to_dict('records'):
        jd = kete.Time.from_mjd(float(r['MJD-AVG']), scaling='utc').jd
        obs = observer_from_header(r, jd)
        w = frame_wcs(r['image_header'])
        cpx = np.array([[-4, -4], [2043, -4], [2043, 2043], [-4, 2043]])
        cw = w.all_pix2world(cpx, 0)
        corners = [kete.Vector.from_ra_dec(float(a), float(b)) for a, b in cw]
        fovs.append(kete.SpherexCmos(corners, obs, r['key'], str(r['DETECTOR'])))
        info[r['key']] = (r, w)
        try:
            hz = A2pos._spherex_geo(jd)
            if hz is not None:
                sc_diff.append(dict(key=r['key'], mjd_avg=r['MJD-AVG'], dpos_km=float(np.linalg.norm(
                    hz[0] - np.array([r['X_SC'], r['Y_SC'], r['Z_SC']])))))
        except Exception:
            pass
    pd.DataFrame(sc_diff).to_csv(os.path.join(OUT, 'header_vs_horizons_spacecraft_km.csv'), index=False)
    print('frames', len(fovs), 'header-vs-Horizons sc pos km median', pd.DataFrame(sc_diff).dpos_km.median())
    dupe = len(info) != len(fovs)
    if dupe:
        print('WARNING duplicate jd keys', len(info), len(fovs))

    ast = load_mpcorb(); com = load_comets()
    cat = pd.concat([ast[['packed', 'name', 'kind', 'H', 'G', 'U', 'epoch_jd', 'peri_time', 'q', 'ecc', 'peri_arg', 'node',
                          'incl', 'a']], com[['packed', 'name', 'kind', 'H', 'K', 'epoch_jd', 'peri_time', 'q', 'ecc',
                                              'peri_arg', 'node', 'incl']]], ignore_index=True)
    cat = cat.drop_duplicates('packed').set_index('packed')
    rows = []
    t0 = time.time()
    CH = 200000
    chunks = []
    for ep, g in cat.groupby('epoch_jd'):
        for j in range(0, len(g), CH):
            chunks.append(g.iloc[j:j + CH])
    print('epochs', cat.epoch_jd.nunique(), 'chunks', len(chunks))
    i = 0
    for sub in chunks:
        i += 0
        sts = []
        for pk, r in zip(sub.index, sub.itertuples()):
            try:
                sts.append(kete.CometElements(pk, r.epoch_jd, r.ecc, r.incl, r.q, r.peri_arg, r.peri_time, r.node).state)
            except Exception:
                pass
        res = kete.fov_state_check(sts, fovs)
        for s in res:
            fr, w = info[s.fov.uri]
            rd = np.array(s.ra_dec_with_rates)
            ph = np.array(s.phase_angles)
            dl = np.array([v.r for v in s.obs_vecs])
            rr = np.array([np.linalg.norm(list(x.pos)) for x in s.states])
            names = [x.desig for x in s.states]
            px = w.all_world2pix(rd[:, :2], 0)
            for k in range(len(names)):
                rows.append((fr['key'], names[k], rd[k, 0], rd[k, 1], px[k, 0], px[k, 1], rd[k, 2], rd[k, 3], dl[k], rr[k], ph[k]))
        i += len(sub)
        print(i, 'objects done', len(rows), 'hits', round(time.time() - t0), 's', flush=True)
    df = pd.DataFrame(rows, columns=['key', 'packed', 'ra_deg', 'dec_deg', 'x_pix', 'y_pix', 'dra_cosdec_deg_day',
                                     'ddec_deg_day', 'delta_au', 'r_au', 'phase_deg'])
    df = df.join(cat[['name', 'kind', 'H', 'G', 'K', 'U']], on='packed')
    df['on_detector'] = (df.x_pix >= -0.5) & (df.x_pix <= 2039.5) & (df.y_pix >= -0.5) & (df.y_pix <= 2039.5)
    df = df[df.on_detector | ((df.x_pix > -20) & (df.x_pix < 2060) & (df.y_pix > -20) & (df.y_pix < 2060))].copy()
    ast_m = df.kind == 'asteroid'
    df['V_pred'] = np.nan
    df.loc[ast_m, 'V_pred'] = hg(df.H[ast_m], df.G[ast_m], df.r_au[ast_m], df.delta_au[ast_m], df.phase_deg[ast_m])
    cm = ~ast_m
    df.loc[cm, 'V_pred'] = df.H[cm] + 5 * np.log10(df.delta_au[cm]) + 2.5 * df.K[cm] * np.log10(df.r_au[cm])
    df['rate_arcsec_min'] = np.hypot(df.dra_cosdec_deg_day, df.ddec_deg_day) * 3600 / 1440
    df['trail_px_in_exposure'] = df.rate_arcsec_min * 113.58 / 60 / 6.15
    mm = meta.set_index('key')
    lam, bw = np.full(len(df), np.nan), np.full(len(df), np.nan)
    for key, g in df.groupby('key'):
        l, b = wave_at(mm.loc[key], g.x_pix.clip(0, 2039).values, g.y_pix.clip(0, 2039).values)
        lam[df.index.get_indexer(g.index)] = l; bw[df.index.get_indexer(g.index)] = b
    df['wave_um'] = lam; df['bandwidth_um'] = bw
    df['AB_reflected_est'] = [expected_ab_reflected(v, l) if np.isfinite(v) and np.isfinite(l) else np.nan
                              for v, l in zip(df.V_pred, df.wave_um)]
    df = df.merge(meta[['key', 'OBSID', 'DETECTOR', 'MJD-AVG', 'release', 'field', 'field_class']], on='key', how='left')
    df.to_parquet(os.path.join(OUT, 'known_objects_in_frames.parquet'))
    on = df[df.on_detector]
    summ = on.groupby('key').agg(n_known=('packed', 'size'), n_V_lt_18=('V_pred', lambda v: int((v < 18).sum())),
                                 n_V_lt_20=('V_pred', lambda v: int((v < 20).sum())), brightest_V=('V_pred', 'min'),
                                 n_comets=('kind', lambda k: int((k == 'comet').sum())))
    summ = meta[['key', 'OBSID', 'DETECTOR', 'MJD-AVG', 'release', 'field', 'field_class']].merge(
        summ, left_on='key', right_index=True, how='left').fillna({'n_known': 0})
    summ.to_csv(os.path.join(OUT, 'frame_summary.csv'), index=False)
    print('rows', len(df), 'on detector', len(on), 'time', round(time.time() - t0))
    print(summ.groupby('field_class')[['n_known', 'n_V_lt_18', 'n_V_lt_20']].median())


if __name__ == '__main__':
    main()
