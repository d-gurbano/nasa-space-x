import sys,time,os; sys.path.insert(0,'code/A2')
import pandas as pd, numpy as np
from positions import predict, utc_mjd_to_tdb_jd
f=pd.read_parquet('data/04-other-archives/wise/most_wise_frames.parquet')
d='2026 AP1'; g=f[f.designation==d].drop_duplicates('mjd_obs').sort_values('vmag').head(10)
jd=utc_mjd_to_tdb_jd(g.mjd_obs.values)
t0=time.time()
for obs in ['neowise','geocenter']:
    p=predict(d, jd, observer=obs, n_samples=100)
    print(obs, time.time()-t0, p.columns.tolist())
p['most_ra']=g.ra_obj.values; p['most_dec']=g.dec_obj.values; p['most_vmag']=g.vmag.values
print(p.to_string())
