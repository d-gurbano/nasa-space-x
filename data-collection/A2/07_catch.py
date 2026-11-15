"""A2: query CATCH (PDS SBN, Univ. Maryland) for archival survey images of moving targets (read-only GET).
API: GET https://catch-api.astro.umd.edu/catch?target=<des>&cached=true -> {job_id, queued, results:url}
     poll GET /status/<job_id>, then GET /caught/<job_id>."""
import requests, time, json, os, sys, pandas as pd
API = 'https://catch-api.astro.umd.edu'
out = os.path.join(os.path.dirname(__file__), '../../data/02-orbits/catch'); os.makedirs(out, exist_ok=True)
targets = sys.argv[1:] or ['2024 YR4', '2026 MM', '2026 KC3']
summary = []
for t in targets:
    r = requests.get(f'{API}/catch', params={'target': t, 'cached': 'true'}, timeout=120).json()
    print(t, r, flush=True)
    jid = r.get('job_id')
    if r.get('queued'):
        for k in range(60):
            time.sleep(10)
            st = requests.get(f'{API}/status/{jid}', timeout=60).json()
            stat = [x.get('status') for x in st.get('status', [])]
            if stat and all(s in ('success', 'finished', 'failed', 'error') for s in stat): break
    res = requests.get(f'{API}/caught/{jid}', timeout=300).json()
    fn = t.replace('/', '_').replace(' ', '_')
    json.dump(res, open(f'{out}/{fn}_caught.json', 'w'), indent=1)
    data = res.get('data', [])
    if data:
        df = pd.DataFrame(data); df.to_csv(f'{out}/{fn}_caught.csv', index=False)
        bysrc = df.groupby('source').size().to_dict()
    else: bysrc = {}
    summary.append(dict(target=t, job_id=jid, n_images=len(data), by_source=json.dumps(bysrc)))
    print(summary[-1], flush=True); time.sleep(3)
pd.DataFrame(summary).to_csv(f'{out}/catch_summary.csv', index=False)
