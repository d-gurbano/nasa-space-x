"""A2: for each candidate (Y1 sample + test objects), fetch
 - JPL SBDB orbit with covariance (sbdb.api?cov=mat&full-prec=1&phys-par=1)
 - MPC observations via MPC get-obs API (ADES_DF), saved as CSV.
Read-only GET requests, paced 1.5 s."""
import requests, json, time, os, pandas as pd, sys
root = os.path.join(os.path.dirname(__file__), '../../data/02-orbits')
cands = pd.read_csv(f'{root}/candidates_Y1.csv')
tests = ['99942', '2024 YR4', '433', '3200', '1566', '3I']  # Apophis, 2024 YR4, Eros, Phaethon, Icarus, 3I/ATLAS
extra = sys.argv[1:]  # optional extra designations (e.g. from A1 lists)
names = list(dict.fromkeys(tests + list(cands.designation) + extra))
os.makedirs(f'{root}/sbdb', exist_ok=True); os.makedirs(f'{root}/obs', exist_ok=True)
summ = []
for n in names:
    fn = n.replace('/', '_').replace(' ', '_')
    row = dict(designation=n)
    p = f'{root}/sbdb/{fn}.json'
    if not os.path.exists(p):
        for k in range(4):
            try:
                r = requests.get('https://ssd-api.jpl.nasa.gov/sbdb.api', params={'sstr': n, 'cov': 'mat', 'full-prec': 1, 'phys-par': 1, 'discovery': 1}, timeout=60)
                if r.status_code in (200, 300): break
            except Exception as e: print('retry', n, e)
            time.sleep(5 * (k + 1))
        open(p, 'w').write(r.text); time.sleep(1.5)
    d = json.load(open(p))
    if 'orbit' in d:
        o = d['orbit']; row.update(sbdb_fullname=d['object']['fullname'], orbit_id=o.get('orbit_id'), n_obs_used=o.get('n_obs_used'),
            data_arc_days=o.get('data_arc'), first_obs=o.get('first_obs'), last_obs=o.get('last_obs'), condition_code=o.get('condition_code'),
            has_cov='covariance' in o, rms=o.get('rms'))
    q = f'{root}/obs/{fn}_mpc_ades.csv'
    if not os.path.exists(q) and not os.path.exists(q + '.fail'):
        key = n if '/' in n else ('C/2025 N1' if n == '3I' else (d['object']['des'] if 'object' in d else n))
        for k in range(4):
            try:
                r = requests.get('https://data.minorplanetcenter.net/api/get-obs', json={'desigs': [key], 'output_format': ['ADES_DF']}, timeout=120)
                if r.status_code == 200: break
            except Exception as e: print('retry obs', n, e)
            time.sleep(5 * (k + 1))
        try:
            js = r.json(); df = pd.DataFrame(js[0]['ADES_DF'])
            df.to_csv(q, index=False)
        except Exception as e:
            print('obs fail', n, r.status_code, r.text[:200]); open(q + '.fail', 'w').write(r.text[:2000])
        time.sleep(1.5)
    if os.path.exists(q): row['mpc_n_obs'] = len(pd.read_csv(q, low_memory=False))
    summ.append(row); print(row, flush=True)
pd.DataFrame(summ).to_csv(f'{root}/candidates_orbit_summary.csv', index=False)
