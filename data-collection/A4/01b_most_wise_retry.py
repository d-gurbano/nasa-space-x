"""A4: retry MOST WISE for objects whose name lookup failed, using the JPL SPK ID as NAIF ID (naifid_input)."""
import pandas as pd, os, sys, gzip
sys.path.insert(0, os.path.dirname(__file__)); from common import *
D = f'{O}/wise'
t = pd.read_parquet(f'{O}/targets_A4.parquet').set_index('designation')
s = pd.read_csv(f'{D}/most_wise_summary.csv')
for des in s[s.most_status != 'ok'].designation:
    sp = int(t.loc[des, 'spkid'])
    r = get(MOST, dict(catalog='wise_merge', input_type='naifid_input', obj_naifid=sp, obs_begin='2010-01-07', obs_end='2024-08-02', output_mode='Brief'))
    print(des, sp, r.status_code, len(r.text), r.text.count('\n'))
    if r.status_code == 200 and '|' in r.text[:20000]:
        with gzip.open(f'{D}/most_raw/{safe(des)}.tbl.gz', 'wt') as f: f.write(r.text)
