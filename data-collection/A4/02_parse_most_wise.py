"""A4: parse MOST WISE raw tables (gz IPAC) -> wise/most_wise_frames.parquet + per-object summary."""
import pandas as pd, os, sys, gzip, glob, re
sys.path.insert(0, os.path.dirname(__file__)); from common import *
from astropy.io import ascii
D = f'{O}/wise'
t = pd.read_parquet(f'{O}/targets_A4.parquet'); bysafe = {safe(d): d for d in t.designation}
frames, summ = [], []
for fn in sorted(glob.glob(f'{D}/most_raw/*.tbl.gz')):
    key = os.path.basename(fn)[:-7]; des = bysafe.get(key, key)
    txt = gzip.open(fn, 'rt').read()
    st, n = 'ok', 0
    if '|' not in txt[:20000]:
        st = 'error: ' + re.sub(r'<[^>]+>', ' ', txt[:600]).replace('\n', ' ')[:250]
    else:
        try:
            df = ascii.read(txt, format='ipac').to_pandas(); n = len(df)
            df.insert(0, 'designation', des); frames.append(df)
        except Exception as e:
            if 'No image' in txt or txt.count('\n') < 40: st = 'no images'
            else: st = f'parse error {e!r}'[:200]
    summ.append(dict(designation=des, most_status=st, n_frame_rows=n))
f = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
s = pd.DataFrame(summ)
if len(f):
    f['phase_name'] = pd.cut(f.mjd_obs, [55200, 55414.9, 55468.9, 55593.5, 56600, 60600], labels=['allsky_4band', 'cryo_3band', 'postcryo_2band', 'gap', 'neowise_reactivation'])
    g = f.groupby('designation').agg(n_frames=('mjd_obs', 'size'), n_w1=('band', lambda b: (b == 1).sum()), n_w2=('band', lambda b: (b == 2).sum()),
        first_mjd=('mjd_obs', 'min'), last_mjd=('mjd_obs', 'max'), min_vmag=('vmag', 'min'), n_epochs=('mjd_obs', lambda m: (pd.Series(sorted(m)).diff() > 30).sum() + 1)).reset_index()
    s = s.merge(g, on='designation', how='left')
    f.to_parquet(f'{D}/most_wise_frames.parquet', index=False)
s = t[['designation', 'list', 'is_comet', 'H', 'disc_date', 'rank_in_list', 'spkid']].merge(s, on='designation', how='left')
s.to_csv(f'{D}/most_wise_summary.csv', index=False)
print(s.most_status.fillna('not run').str[:40].value_counts().to_string()); print(len(f), 'frame rows')
if len(f): print(s.describe().to_string())
