"""A2 parent-review: SBDB (cov) + MPC obs for A1 lost-recovery shortlist. Resumable (skips existing files).
Order: lost_tier L1 first if that column exists, else file order (A1 rank). Writes lost_orbit_summary.csv."""
import os, sys, json, time, requests, pandas as pd
root = os.path.join(os.path.dirname(__file__), '../../data/02-orbits')
b = pd.read_csv(os.path.join(root, '../01-targets/lists/b_lost_recovery_shortlist.csv'))
if 'lost_tier' in b.columns:
    b = b.assign(_t=b.lost_tier.astype(str)).sort_values(['_t'] + (['tier_rank'] if 'tier_rank' in b.columns else []), kind='stable')
names = list(dict.fromkeys(b.designation.astype(str)))
def get(url, **kw):
    for k in range(5):
        try:
            r = requests.get(url, timeout=180, **kw)
            if r.status_code in (200, 300) or (r.status_code < 500 and r.status_code != 429): return r
        except Exception as e: print('retry', url, e, flush=True)
        time.sleep(10 * (k + 1))
    return r
summ = []
for n in names:
    fn = n.replace('/', '_').replace(' ', '_'); row = dict(designation=n)
    p = f'{root}/sbdb/{fn}.json'
    if not os.path.exists(p):
        r = get('https://ssd-api.jpl.nasa.gov/sbdb.api', params={'sstr': n, 'cov': 'mat', 'full-prec': 1, 'phys-par': 1, 'discovery': 1})
        open(p, 'w').write(r.text); time.sleep(1.5)
    try: d = json.load(open(p))
    except Exception: d = {}
    if 'orbit' in d:
        o = d['orbit']; row.update(orbit_id=o.get('orbit_id'), n_obs_used=o.get('n_obs_used'), data_arc_days=o.get('data_arc'),
            first_obs=o.get('first_obs'), last_obs=o.get('last_obs'), condition_code=o.get('condition_code'), has_cov='covariance' in o)
    q = f'{root}/obs/{fn}_mpc_ades.csv'
    if not os.path.exists(q):
        key = n if '/' in n else (d['object']['des'] if 'object' in d else n)
        r = get('https://data.minorplanetcenter.net/api/get-obs', json={'desigs': [key], 'output_format': ['ADES_DF']})
        try: pd.DataFrame(r.json()[0]['ADES_DF']).to_csv(q, index=False)
        except Exception: open(q + '.fail', 'w').write(r.text[:2000])
        time.sleep(1.5)
    if os.path.exists(q):
        try: row['mpc_n_obs'] = len(pd.read_csv(q, low_memory=False))
        except pd.errors.EmptyDataError: row['mpc_n_obs'] = 0  # MPC returned no observations
    row['lost_tier'] = b.loc[b.designation.astype(str) == n, 'lost_tier'].iloc[0] if 'lost_tier' in b.columns else ''
    summ.append(row); print(row, flush=True)
    if len(summ) % 20 == 0: pd.DataFrame(summ).to_csv(f'{root}/lost_orbit_summary.csv', index=False)
pd.DataFrame(summ).to_csv(f'{root}/lost_orbit_summary.csv', index=False); print('DONE', len(summ))
