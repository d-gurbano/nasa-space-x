"""A7 step 8: labeled positives (known asteroids) and empty-sky negatives from ~100 frames.
Uses the pilot fast S3 reader (code/A0 read_stamp_http) and ePSF forced photometry (forced_phot).
Output: data/07-answer-keys/labeled_set/{positives,negatives}/<OBSID>_D<d>_<label>.fits + labels.parquet
"""
import os, sys, time
import numpy as np, pandas as pd
from concurrent.futures import ThreadPoolExecutor
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, os.path.join(ROOT, 'code/A0'))
from rewind import read_stamp_http, forced_phot, save_stamp_fits, decode_flags
from astropy.io import fits
from astropy.wcs import WCS

OUT = os.path.join(ROOT, 'data/07-answer-keys/labeled_set')
for d in ('positives', 'negatives'):
    os.makedirs(os.path.join(OUT, d), exist_ok=True)
N_FRAMES, N_POS, N_NEG, VMAX = 100, 8, 3, 19.0


def plan():
    ak = pd.read_parquet(os.path.join(ROOT, 'data/07-answer-keys/answer_key/known_objects_in_frames.parquet'))
    meta = pd.read_parquet(os.path.join(ROOT, 'data/07-answer-keys/frames/frames_meta.parquet')).set_index('key')
    ak = ak[ak.on_detector]
    inner = ak[(ak.x_pix > 25) & (ak.x_pix < 2014) & (ak.y_pix > 25) & (ak.y_pix < 2014) & (ak.V_pred < VMAX)]
    cnt = inner.groupby('key').size()
    fr = pd.read_csv(os.path.join(ROOT, 'data/07-answer-keys/answer_key/frame_summary.csv')).set_index('key')
    fr = fr.loc[cnt.index].assign(n_bright=cnt)
    rng = np.random.default_rng(7)
    ecl = fr[fr.field_class == 'ecliptic']; mid = fr[fr.field_class != 'ecliptic']
    pick = list(ecl.sample(min(75, len(ecl)), random_state=7).index) + list(mid.sample(min(N_FRAMES - 75, len(mid)), random_state=7).index)
    if len(pick) < N_FRAMES:
        rest = [k for k in ecl.index if k not in pick]
        pick += rest[:N_FRAMES - len(pick)]
    jobs = []
    for key in pick:
        g = inner[inner.key == key].sort_values('V_pred').head(N_POS)
        for r in g.itertuples():
            jobs.append(dict(kind='positive', key=key, ra=r.ra_deg, dec=r.dec_deg, object=r.packed, name=r.name,
                             V_pred=r.V_pred, AB_pred=r.AB_reflected_est, wave_pred=r.wave_um, rate_arcsec_min=r.rate_arcsec_min,
                             x_pix=r.x_pix, y_pix=r.y_pix))
        # negatives: random pixels > 60" (10 px) from any known object with V < 23 (all of them, any V)
        allk = ak[ak.key == key]
        w = WCS(fits.Header.fromstring(meta.loc[key, 'image_header']), relax=True, key=' ')
        n = 0; tries = 0
        while n < N_NEG and tries < 200:
            tries += 1
            x, y = rng.uniform(40, 2000, 2)
            if len(allk) and np.min(np.hypot(allk.x_pix - x, allk.y_pix - y)) < 10:
                continue
            ra, dec = w.all_pix2world([[x, y]], 0)[0]
            jobs.append(dict(kind='negative', key=key, ra=ra, dec=dec, object='none', name='empty_sky_no_known_SSO',
                             x_pix=x, y_pix=y))
            n += 1
    return pd.DataFrame(jobs), meta


def run_one(j):
    for t in range(3):
        try:
            st = read_stamp_http('ibe/data/spherex/' + j['key'], j['ra'], j['dec'], half=20)
            ph = forced_phot(st, j['ra'], j['dec'])
            obs = st.header.get('OBSID'); det = st.header.get('DETECTOR')
            lab = j['object'] if j['kind'] == 'positive' else f"neg{int(j['x_pix'])}_{int(j['y_pix'])}"
            fn = os.path.join(OUT, j['kind'] + 's', f"{obs}_D{det}_{lab}.fits".replace('/', '-'))
            save_stamp_fits(st, fn, extra=dict(LABEL=j['kind'], OBJECT=str(j['object'])[:60], VPRED=j.get('V_pred'),
                                               RA_TGT=j['ra'], DEC_TGT=j['dec'], SNR=ph.get('snr'), WAVEUM=ph.get('wave_um')))
            out = dict(j); out.update({k: v for k, v in ph.items() if not isinstance(v, (np.ndarray,))})
            out.update(file=os.path.relpath(fn, OUT), bytes_read=st.meta.get('bytes'), t_read=st.meta.get('t_read'))
            return out
        except Exception as e:
            err = repr(e)[:300]; time.sleep(3 * (t + 1))
    out = dict(j); out['error'] = err
    return out


def main():
    jobs, meta = plan()
    lab_fn = os.path.join(OUT, 'labels.parquet')
    done = pd.read_parquet(lab_fn) if os.path.exists(lab_fn) else None
    if done is not None:
        k = set(zip(done.key, done.ra.round(7)))
        jobs = jobs[[(a, b) not in k for a, b in zip(jobs.key, jobs.ra.round(7))]]
    print('jobs', len(jobs), jobs.kind.value_counts().to_dict(), 'frames', jobs.key.nunique(), flush=True)
    res = []; t0 = time.time()
    with ThreadPoolExecutor(6) as ex:
        for i, r in enumerate(ex.map(run_one, jobs.to_dict('records'))):
            res.append(r)
            if i % 50 == 0:
                print(i, round(time.time() - t0), 's', flush=True)
                pd.concat([done, pd.DataFrame(res)] if done is not None else [pd.DataFrame(res)]).to_parquet(lab_fn)
    df = pd.concat([done, pd.DataFrame(res)] if done is not None else [pd.DataFrame(res)], ignore_index=True)
    df = df.merge(meta[['OBSID', 'DETECTOR', 'MJD-AVG']], left_on='key', right_index=True, how='left')
    df['detected_snr5'] = df.snr > 5
    df.to_parquet(lab_fn)
    df.drop(columns=[c for c in df.columns if df[c].dtype == object and c not in ('kind', 'key', 'object', 'name', 'file', 'status', 'flag_center_names', 'flag_or_names', 'error')]).to_csv(os.path.join(OUT, 'labels.csv'), index=False)
    p = df[df.kind == 'positive']; n = df[df.kind == 'negative']
    print('positives', len(p), 'detected S/N>5', int((p.snr > 5).sum()), 'negatives', len(n), 'neg S/N>5', int((n.snr > 5).sum()),
          'time', round(time.time() - t0))


if __name__ == '__main__':
    main()
