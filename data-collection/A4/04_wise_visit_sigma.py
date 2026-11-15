"""A4 step 4: for every MOST WISE/NEOWISE frame match, group into visits (gap > 3 d) and compute kete 3-sigma
position uncertainty (SBDB covariance, 100 draws, observer = WISE spacecraft) and V mag at the visit mid-time.
Output wise/wise_visits.parquet; a visit is 'searchable' when sigma_major_3s <= 300" and V <= 21.5 (ESTIMATED limits)."""
import pandas as pd, numpy as np, os, sys, time, json
sys.path.insert(0, os.path.dirname(__file__)); sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../A2'))
from common import *
from positions import predict, utc_mjd_to_tdb_jd
D = f'{O}/wise'
f = pd.read_parquet(f'{D}/most_wise_frames.parquet')
outp = f'{D}/wise_visits.parquet'
prev = pd.read_parquet(outp) if os.path.exists(outp) else pd.DataFrame()
donev = set(prev.designation) if len(prev) else set()
rows = []
for des, g in f.groupby('designation'):
    if des in donev: continue
    u = g.drop_duplicates(['scan_id', 'frame_num']).sort_values('mjd_obs')
    vis = (u.mjd_obs.diff() > 3).cumsum().values
    u = u.assign(visit=vis)
    t0 = time.time()
    agg = u.groupby('visit').agg(mjd_first=('mjd_obs', 'min'), mjd_last=('mjd_obs', 'max'), n_frames=('mjd_obs', 'size'),
        most_vmag_min=('vmag', 'min'), most_vmag_med=('vmag', 'median'), ra_mid=('ra_obj', 'median'), dec_mid=('dec_obj', 'median'),
        sun_dist=('sun_dist', 'median'), geo_dist=('geo_dist', 'median')).reset_index()
    agg['mjd_mid'] = (agg.mjd_first + agg.mjd_last) / 2
    err = ''
    try:
        p = predict(des, utc_mjd_to_tdb_jd(agg.mjd_mid.values), observer='neowise', n_samples=100)
        for c in ['ra_deg', 'dec_deg', 'vmag', 'sigma_major_3s_arcsec', 'sigma_minor_3s_arcsec', 'pa_major_deg', 'delta_au', 'r_au', 'phase_deg']:
            agg['kete_' + c] = p[c].values if c in p else np.nan
    except Exception as e:
        err = repr(e)[:200]
    agg.insert(0, 'designation', des); agg['kete_error'] = err
    rows.append(agg)
    print(des, len(agg), round(time.time() - t0, 1), err[:80], flush=True)
new = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
allv = pd.concat([prev, new], ignore_index=True)
# comets: kete gives no magnitude and MOST comet mags are useless (pilot lesson); use total mag T = M1 + 5 log10(delta) + K1 log10(r)
tg = pd.read_parquet(f'{O}/targets_A4.parquet')
a = pd.read_parquet(f'{R}/data/01-targets/lists/a_spherex_precovery_shortlist.parquet')[['designation', 'K1']]
tg = tg.merge(a, on='designation', how='left')
allv = allv.drop(columns=[c for c in ['is_comet', 'M1', 'K1', 'comet_tmag'] if c in allv]).merge(tg[['designation', 'is_comet', 'M1', 'K1']], on='designation', how='left')
k1 = allv.K1.fillna(10.0)
allv['comet_tmag'] = np.where(allv.is_comet, allv.M1 + 5 * np.log10(allv.kete_delta_au.fillna(allv.geo_dist)) + k1 * np.log10(allv.kete_r_au.fillna(allv.sun_dist)), np.nan)
v = allv.kete_vmag.where(~allv.is_comet, allv.comet_tmag).fillna(allv.most_vmag_min)
allv['vmag_used'] = v
allv['searchable'] = (allv.kete_sigma_major_3s_arcsec <= 300) & (v <= 21.5)
allv['searchable_loose'] = (allv.kete_sigma_major_3s_arcsec <= 3600) & (v <= 22.5)
allv.to_parquet(outp, index=False)
print('loose', int(allv.searchable_loose.sum()), allv[allv.searchable_loose].designation.nunique()); print('visits', len(allv), 'objects', allv.designation.nunique(), 'searchable visits', int(allv.searchable.sum()), 'objects w/ searchable', allv[allv.searchable].designation.nunique())
