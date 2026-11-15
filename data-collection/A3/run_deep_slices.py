"""Full Deep Survey frame lists via SIA2 in 7-day TIME slices (large single queries hit 502 proxy timeouts).
*_deep collections contain only Deep Survey frames; a wide circle around each pole returns that pole's frames."""
import sys,os,time; sys.path.insert(0,'code/A3')
from sia_frames import sia
import numpy as np
D='data/03-spherex/frames/deep_slices'; os.makedirs(D,exist_ok=True)
P={'NEP':(270.0,66.56,10.0),'SEP':(90.0,-66.56,12.0)}
# SPHEREx science ops from ~2025-04-20 (MJD 60785) to now (MJD 61359 = 2026-11-15)
edges=np.arange(60780,61365,7)
for coll in ['spherex_qr3_deep','spherex_dr1_deep']:
  for pole,(ra,dec,r) in P.items():
    for a,b in zip(edges[:-1],edges[1:]):
        fn=f'{D}/{pole}__{coll}__{a}_{b}.parquet'
        if os.path.exists(fn) or os.path.exists(fn+'.fail'): continue
        if os.path.exists('data/03-spherex/STOP_DEEP'): sys.exit()
        t0=time.time()
        try: df=sia(ra,dec,r,coll,tries=4,time_range=(a,b))
        except Exception: open(fn+'.fail','w').close(); print(pole,coll,a,'FAILED',flush=True); continue
        df['field']=pole; df.to_parquet(fn); print(pole,coll,a,b,len(df),round(time.time()-t0,1),flush=True); time.sleep(1)
