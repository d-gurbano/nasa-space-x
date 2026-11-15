"""A4 step 9: IRSA MOST catalog=spitzer_bcd (2003-08-25..2020-01-30) for objects whose WISE-era 3-sigma <= 3600" and V <= 22.5
at some visit (searchable_loose in wise_visits). Other shortlist objects are uncertain by degrees in the Spitzer era. NAIF ID input."""
import pandas as pd, os, sys, time, json, gzip
from astropy.io import ascii
sys.path.insert(0, os.path.dirname(__file__)); from common import *
D = f'{O}/spitzer'
v = pd.read_parquet(f'{O}/wise/wise_visits.parquet'); objs = sorted(v[v.searchable_loose].designation.unique())
t = pd.read_parquet(f'{O}/targets_A4.parquet').set_index('designation')
rows, parts = [], []
for des in objs:
    t0 = time.time(); st = 'ok'; n = 0
    try:
        r = get(MOST, dict(catalog='spitzer_bcd', input_type='naifid_input', obj_naifid=int(t.loc[des, 'spkid']), obs_begin='2003-08-25', obs_end='2020-01-30', output_mode='Brief'), timeout=900)
        with gzip.open(f'{D}/most_raw/{safe(des)}.tbl.gz', 'wt') as f: f.write(r.text)
        if r.status_code != 200: st = f'HTTP{r.status_code} ' + r.text[:200].replace('\n', ' ')
        elif '|' in r.text[:20000]:
            df = ascii.read(r.text, format='ipac').to_pandas(); n = len(df); df.insert(0, 'designation', des); parts.append(df)
        else: st = 'no images'
    except Exception as e: st = f'error {e!r}'[:200]
    rows.append(dict(designation=des, status=st, n_frames=n, sec=round(time.time() - t0, 1))); print(rows[-1], flush=True); time.sleep(2)
pd.DataFrame(rows).to_csv(f'{D}/most_spitzer_status.csv', index=False)
if parts: pd.concat(parts, ignore_index=True).to_parquet(f'{D}/most_spitzer_frames.parquet', index=False)
print('SPITZER_DONE')
