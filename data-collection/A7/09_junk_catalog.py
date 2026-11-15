"""A7 step 9: junk / artifact catalog.
 a) per-frame artifact statistics from IMAGE headers of the 610 selected frames (pipeline counts of
    persist, ghost, crosstalk, snowball, halo, streak pixels, satellite streak count, airglow/aurora flags)
 b) match selected frames against the SPHEREx team anomalous-image list and the Borlaff 2026 trail catalog
 c) labeled artifact stamps: read the full FLAGS HDU (~11 MB, RICE) of frames rich in each artifact type,
    find connected regions of that flag bit, cut 41x41 stamps at the largest regions (read_stamp_http)
 d) Borlaff 2026 trail stamps: SIA2 lookup of trail position + time, stamp at the trail centre.
Output: data/07-answer-keys/junk/
"""
import os, sys, io, json, time
import numpy as np, pandas as pd
from concurrent.futures import ThreadPoolExecutor
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, os.path.join(ROOT, 'code/A0'))
from rewind import read_stamp_http, save_stamp_fits, l2_layout, _range, decode_flags, sia2_query, FLAG_BITS
from astropy.io import fits
from astropy.wcs import WCS
from scipy import ndimage

J = os.path.join(ROOT, 'data/07-answer-keys/junk'); os.makedirs(os.path.join(J, 'stamps'), exist_ok=True)
KW = ['L2 N_PERSIST', 'L2 N_GHOST', 'L2 N_GHOST_FPA', 'L2 N_GHOST_EXT', 'L2 N_XTALK', 'L2 N_SNOWBALL', 'NSNOWSRC',
      'L2 N_HALO', 'L2 N_SAT_HALO', 'L2 N_BLOOM', 'NBLMSRCS', 'L2 SATSTRKS', 'L2 SATSTRKS_PXS', 'SNWSTRK', 'L2 N_OUTLIER',
      'L2 N_TRANSIENT', 'L2 N_HOT', 'L2 N_COLD', 'L2 N_NONFUNC', 'PXSRCMSK', 'HE_AIRGLOW_CONT', 'AURORA_CONT',
      'SHUTTLE_GLOW_CONT', 'AURORA_CORR', 'SHUTTLE_GLOW_CORR', 'OBS_IN_SBAND', 'FINAST', 'L2DQAFLG', 'SGT_MIN_GCD2SAA', 'PSF_FWHM']
TYPES = {  # artifact label -> (flag bit, header count keyword)
    'persistence': (17, 'L2 N_PERSIST'), 'ghost': (22, 'L2 N_GHOST'), 'ghost_ext': (24, 'L2 N_GHOST_EXT'),
    'crosstalk': (20, 'L2 N_XTALK'), 'snowball': (27, 'L2 N_SNOWBALL'), 'halo': (28, 'L2 N_HALO'),
    'satellite_streak': (25, 'L2 SATSTRKS_PXS'), 'satellite_halo': (29, 'L2 N_SAT_HALO'), 'bloom': (26, 'L2 N_BLOOM'),
    'transient_cosmic_ray': (0, 'L2 N_TRANSIENT'),
}


def header_stats():
    meta = pd.read_parquet(os.path.join(ROOT, 'data/07-answer-keys/frames/frames_meta.parquet'))
    sel = pd.read_parquet(os.path.join(ROOT, 'data/07-answer-keys/frames/frames_selected.parquet'))
    rows = []
    for r in meta.merge(sel[['key', 'release', 'field', 'field_class']], on='key').to_dict('records'):
        h = fits.Header.fromstring(r['image_header'])
        d = dict(key=r['key'], OBSID=r['OBSID'], det=int(r['DETECTOR']), mjd_avg=r['MJD-AVG'], release=r['release'],
                 field=r['field'], field_class=r['field_class'])
        for k in KW:
            d[k.replace('L2 ', '').replace(' ', '_')] = h.get(k)
        rows.append(d)
    df = pd.DataFrame(rows)
    an = pd.read_csv(os.path.join(J, 'anomaly_list/SPHEREX_exposure_anomaly_log_20250810.csv'))
    an.columns = [c.strip() for c in an.columns]
    df['team_anomaly'] = ''
    for r in an.itertuples():
        m = df.OBSID == r.OBSID
        if m.any():
            for i in df.index[m]:
                aff = getattr(r, f'BAND_{df.at[i, "det"]}_AFFECTED')
                if aff:
                    df.at[i, 'team_anomaly'] += f'{r.ANOMALY_NAME}({"affected" if aff == 1 else "possibly"});'
    tr = pd.read_csv(os.path.join(J, 'trails_borlaff2026/SPHEREx_trails_database.csv'))
    df['borlaff_trails_in_exposure'] = df.OBSID.map(tr.groupby('OBSID').size()).fillna(0).astype(int)
    df.to_csv(os.path.join(J, 'frame_artifact_stats.csv'), index=False)
    print('frames', len(df), 'with team anomaly', int((df.team_anomaly != '').sum()), 'with borlaff trails',
          int((df.borlaff_trails_in_exposure > 0).sum()), 'with SATSTRKS>0', int((df.SATSTRKS.fillna(0) > 0).sum()))
    return df, meta.set_index('key'), an, tr


def full_flags(key):
    url, lay, st = l2_layout('ibe/data/spherex/' + key)
    fh, foff, fdat, flen = lay['FLAGS']
    raw = _range(url, foff, (fdat - foff) + flen)
    prim = fits.PrimaryHDU().header.tostring().encode()
    return np.asarray(fits.open(io.BytesIO(prim + raw))[1].data), lay['IMAGE'][0]


def flag_regions(stats, n_frames=3, n_regions=3):
    jobs = []
    for lab, (bit, kw) in TYPES.items():
        col = kw.replace('L2 ', '').replace(' ', '_')
        cand = stats[pd.to_numeric(stats[col], errors='coerce').fillna(0) > 0].sort_values(col, ascending=False)
        # spread over different exposures
        cand = cand.drop_duplicates('OBSID').head(n_frames)
        for r in cand.itertuples():
            jobs.append((lab, bit, r.key))
    print('flag frames to read', len(jobs), 'unique', len({j[2] for j in jobs}), flush=True)
    cache = {}
    def get(k):
        if k not in cache:
            for t in range(3):
                try:
                    cache[k] = full_flags(k); break
                except Exception as e:
                    time.sleep(5)
        return cache.get(k)
    with ThreadPoolExecutor(4) as ex:
        list(ex.map(get, list(dict.fromkeys(j[2] for j in jobs))))
    st_jobs = []
    for lab, bit, key in jobs:
        g = cache.get(key)
        if g is None:
            continue
        fl, hdr = g
        m = (fl & (1 << bit)) != 0
        if lab == 'transient_cosmic_ray':
            m &= (fl & (1 << 21)) == 0     # cosmic rays away from catalogued sources
        lb, n = ndimage.label(m)
        if n == 0:
            continue
        sizes = ndimage.sum(m, lb, range(1, n + 1))
        order = np.argsort(sizes)[::-1][:n_regions]
        com = ndimage.center_of_mass(m, lb, order + 1)
        w = WCS(hdr, relax=True, key=' ')
        for (yc, xc), oi in zip(com, order):
            # use a flagged pixel nearest the centroid (centroid of a ring/halo can be unflagged)
            ys, xs = np.where(lb == oi + 1)
            k = np.argmin((ys - yc) ** 2 + (xs - xc) ** 2)
            x, y = float(xs[k]), float(ys[k])
            ra, dec = w.all_pix2world([[x, y]], 0)[0]
            st_jobs.append(dict(label=lab, flag_bit=bit, key=key, x_pix=x, y_pix=y, ra=ra, dec=dec,
                                region_npix=int(sizes[oi]), source='pipeline FLAGS'))
    # frame-level flag fractions for the frames read
    fr = []
    for key, g in cache.items():
        if g is None:
            continue
        fl = g[0]
        d = {'key': key}
        for b, nme in FLAG_BITS.items():
            d['frac_' + nme] = float(((fl & (1 << b)) != 0).mean())
        fr.append(d)
    pd.DataFrame(fr).to_csv(os.path.join(J, 'flag_fractions_fullframe.csv'), index=False)
    return st_jobs


def trail_jobs(tr, n=12):
    out = []
    s = tr.sample(n * 2, random_state=5)
    for r in s.itertuples():
        if len(out) >= n:
            break
        try:
            df = sia2_query(r.ra, r.dec, 'spherex_dr1', 0.001, time_mjd=(r.MJDOBS - 0.003, r.MJDOBS + 0.003))
        except Exception as e:
            print('sia2 fail', e); continue
        df = df[df.obs_id == r.OBSID]
        if not len(df):
            continue
        k = json.loads(df.iloc[0].cloud_access)['aws']['key']
        out.append(dict(label='satellite_trail_borlaff2026', flag_bit=25, key=k, ra=r.ra, dec=r.dec, pa_deg=r.pa,
                        source=f'Borlaff 2026 trail row {r[0]}', band=df.iloc[0].energy_bandpassname))
        time.sleep(1)
    return out


def anomaly_jobs(an, n=8):
    out = []
    a = an[an.ANOMALY_TYPE.isin([1, 2, 3, 10])].groupby('ANOMALY_NAME').head(2)
    for r in a.head(n).itertuples():
        band = next((b for b in range(1, 7) if getattr(r, f'BAND_{b}_AFFECTED') == 1), None)
        if band is None:
            continue
        # find the file: DR1 SIA2 has obs_id; query by time window around DATE-OBS at any position is not possible,
        # so use TAP on obscore by obs_id (indexed)
        import requests
        q = f"select access_url, energy_bandpassname, s_ra, s_dec, obs_collection from spherex.obscore where obs_id='{r.OBSID}'"
        try:
            t = requests.get('https://irsa.ipac.caltech.edu/TAP/sync', params=dict(QUERY=q, FORMAT='csv'), timeout=120).text
            df = pd.read_csv(io.StringIO(t))
        except Exception as e:
            print('tap fail', e); continue
        df = df[(df.energy_bandpassname == f'SPHEREx-D{band}') & df.obs_collection.str.contains('dr1')]
        if not len(df):
            continue
        k = df.iloc[0].access_url.split('ibe/data/spherex/')[1]
        out.append(dict(label='team_anomaly_' + r.ANOMALY_NAME, flag_bit=-1, key=k, ra=df.iloc[0].s_ra, dec=df.iloc[0].s_dec,
                        source='SPHEREx team anomalous-image list 2025-08-10 (frame centre stamp; anomaly is diffuse)'))
        time.sleep(1)
    return out


def cut(j):
    for t in range(3):
        try:
            st = read_stamp_http('ibe/data/spherex/' + j['key'], j['ra'], j['dec'], half=20)
            obs, det = st.header.get('OBSID'), st.header.get('DETECTOR')
            fn = os.path.join(J, 'stamps', j['label'], f"{obs}_D{det}_{int(st.meta['x_full'])}_{int(st.meta['y_full'])}.fits")
            os.makedirs(os.path.dirname(fn), exist_ok=True)
            save_stamp_fits(st, fn, extra=dict(LABEL=j['label'][:60], FLAGBIT=j['flag_bit'], RA_TGT=j['ra'], DEC_TGT=j['dec']))
            c = st.flags[20, 20]
            fb = j['flag_bit']
            frac = float(((st.flags & (1 << fb)) != 0).mean()) if fb >= 0 else np.nan
            return dict(j, file=os.path.relpath(fn, J), OBSID=obs, det=det, flags_centre=decode_flags(c),
                        frac_stamp_with_flag=frac)
        except Exception as e:
            err = repr(e)[:200]; time.sleep(3)
    return dict(j, error=err)


def main():
    stats, meta, an, tr = header_stats()
    jobs = flag_regions(stats)
    print('flag stamps', len(jobs), flush=True)
    jobs += trail_jobs(tr); print('with trails', len(jobs), flush=True)
    jobs += anomaly_jobs(an); print('with anomalies', len(jobs), flush=True)
    with ThreadPoolExecutor(6) as ex:
        res = list(ex.map(cut, jobs))
    df = pd.DataFrame(res)
    df.to_csv(os.path.join(J, 'artifact_stamps_labels.csv'), index=False)
    print(df.groupby('label').size(), 'errors', df.get('error', pd.Series(dtype=str)).notna().sum())


if __name__ == '__main__':
    main()
