"""A4 step 1: IRSA MOST WISE/NEOWISE single-exposure frame coverage (catalog=wise_merge, 2010-01-07..2024-08-02) for all A4 targets."""
import pandas as pd, os, sys, time, json
from concurrent.futures import ThreadPoolExecutor, as_completed
sys.path.insert(0, os.path.dirname(__file__)); from common import *
D = f'{O}/wise'; os.makedirs(D, exist_ok=True)
t = pd.read_parquet(f'{O}/targets_A4.parquet')
done = set()
log = f'{D}/most_wise_status.jsonl'
if os.path.exists(log):
    done = {json.loads(l)['designation'] for l in open(log) if json.loads(l)['status'] in ('ok', 'no images')}
def job(row):
    time.sleep(1)
    t0 = time.time()
    try:
        df, st = most('wise_merge', row.designation, '2010-01-07', '2024-08-02', row.is_comet, rawdir=f'{D}/most_raw')
    except Exception as e:
        df, st = None, f'error {e}'
    n = 0
    if df is not None and len(df):
        df.insert(0, 'designation', row.designation); df.insert(1, 'list', row.list)
        df.to_parquet(f'{D}/most_parts/{safe(row.designation)}.parquet', index=False); n = len(df)
    return dict(designation=row.designation, status=st if st == 'ok' or st == 'no images' else st[:300], n_frames=n, sec=round(time.time()-t0, 1))
os.makedirs(f'{D}/most_parts', exist_ok=True)
rows = [r for r in t.itertuples() if r.designation not in done]
print('todo', len(rows), flush=True)
with ThreadPoolExecutor(3) as ex, open(log, 'a') as f:
    for fu in as_completed([ex.submit(job, r) for r in rows]):
        res = fu.result(); f.write(json.dumps(res) + '\n'); f.flush(); print(res, flush=True)
