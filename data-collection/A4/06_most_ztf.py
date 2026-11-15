"""A4 step 6: IRSA MOST catalog=ztf, window [discovery - 365 d, discovery - 0.5 d], NAIF ID input (JPL SPK ID),
for all A4 targets ordered by rank (A and B interleaved). Resumable (status jsonl). Stop: create ztf/STOP."""
import pandas as pd, os, sys, time, json, gzip
from concurrent.futures import ThreadPoolExecutor, as_completed
from astropy.io import ascii
sys.path.insert(0, os.path.dirname(__file__)); from common import *
D = f'{O}/ztf'
t = pd.read_parquet(f'{O}/targets_A4.parquet').sort_values(['rank_in_list', 'list']).reset_index(drop=True)
log = f'{D}/most_ztf_status.jsonl'
done = {json.loads(l)['designation'] for l in open(log)} if os.path.exists(log) else set()
def job(row):
    if os.path.exists(f'{D}/STOP'): return None
    d = pd.Timestamp(row.disc_date); b = (d - pd.Timedelta(days=365)).strftime('%Y-%m-%d'); e = (d - pd.Timedelta(hours=12)).strftime('%Y-%m-%d')
    t0 = time.time()
    try:
        r = get(MOST, dict(catalog='ztf', input_type='naifid_input', obj_naifid=int(row.spkid), obs_begin=b, obs_end=e, output_mode='Brief'), timeout=900)
        txt = r.text
        with gzip.open(f'{D}/most_raw/{safe(row.designation)}.tbl.gz', 'wt') as f: f.write(txt)
        n = 0; st = 'ok'
        if r.status_code != 200: st = f'HTTP{r.status_code} ' + txt[:200].replace('\n', ' ')
        elif '|' in txt[:20000]:
            df = ascii.read(txt, format='ipac').to_pandas(); n = len(df)
            df.insert(0, 'designation', row.designation); df.insert(1, 'list', row.list)
            df.to_parquet(f'{D}/parts/{safe(row.designation)}.parquet', index=False)
        else: st = 'no images' if 'No image' in txt or len(txt) < 20000 else 'unparsed'
    except Exception as ex:
        st, n = f'error {ex!r}'[:200], 0
    return dict(designation=row.designation, list=row.list, begin=b, end=e, status=st, n_frames=n, sec=round(time.time() - t0, 1))
rows = [r for r in t.itertuples() if r.designation not in done]
print('todo', len(rows), flush=True)
with ThreadPoolExecutor(2) as ex, open(log, 'a') as f:
    futs = []
    for r in rows: futs.append(ex.submit(job, r))
    for fu in as_completed(futs):
        res = fu.result()
        if res: f.write(json.dumps(res) + '\n'); f.flush(); print(res, flush=True)
