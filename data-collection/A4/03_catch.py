"""A4 step 3: CATCH (PDS SBN Comet Asteroid Telescopic Catalog Hub, Univ. Maryland) image lists for all A4 targets.
Read-only GETs. 2 jobs in flight max, polite pacing. Stop by creating data/04-other-archives/catch/STOP."""
import pandas as pd, os, sys, time, json
from concurrent.futures import ThreadPoolExecutor, as_completed
sys.path.insert(0, os.path.dirname(__file__)); from common import *
API = 'https://catch-api.astro.umd.edu'
D = f'{O}/catch'; os.makedirs(f'{D}/parts', exist_ok=True)
t = pd.read_parquet(f'{O}/targets_A4.parquet')
order = sys.argv[1] if len(sys.argv) > 1 else 'rank'
# interleave A and B by rank so the top of both lists finishes first
t = t.sort_values(['rank_in_list', 'list']).reset_index(drop=True)
log = f'{D}/catch_status.jsonl'
done = set()
if os.path.exists(log):
    done = {json.loads(l)['designation'] for l in open(log) if json.loads(l)['status'] == 'ok'}
def job(row):
    if os.path.exists(f'{D}/STOP'): return dict(designation=row.designation, status='stopped')
    t0 = time.time(); des = row.designation
    try:
        r = get(f'{API}/catch', params={'target': des, 'cached': 'true'}, timeout=120).json()
        jid = r.get('job_id')
        if jid is None: return dict(designation=des, status='submit error: ' + json.dumps(r)[:300])
        if r.get('queued'):
            for k in range(90):
                time.sleep(10)
                st = get(f'{API}/status/{jid}', timeout=60).json()
                stat = [x.get('status') for x in st.get('status', [])]
                if stat and all(s in ('success', 'finished', 'failed', 'error') for s in stat): break
        res = get(f'{API}/caught/{jid}', timeout=600).json()
        data = res.get('data', [])
        n = len(data)
        if n:
            df = pd.DataFrame(data); df.insert(0, 'designation', des); df.insert(1, 'list', row.list)
            df.insert(2, 'job_id', jid)
            df.to_parquet(f'{D}/parts/{safe(des)}.parquet', index=False)
            bysrc = df.groupby('source').size().to_dict()
        else: bysrc = {}
        return dict(designation=des, status='ok', job_id=jid, n_images=n, by_source=bysrc, sec=round(time.time()-t0, 1),
                    msg=str(res.get('message', ''))[:200])
    except Exception as e:
        return dict(designation=des, status=f'error {e!r}'[:300], sec=round(time.time()-t0, 1))
rows = [r for r in t.itertuples() if r.designation not in done]
print('todo', len(rows), flush=True)
with ThreadPoolExecutor(2) as ex, open(log, 'a') as f:
    futs = []
    for r in rows:
        futs.append(ex.submit(job, r)); time.sleep(0.5)
    for fu in as_completed(futs):
        res = fu.result(); f.write(json.dumps(res) + '\n'); f.flush(); print(res, flush=True)
