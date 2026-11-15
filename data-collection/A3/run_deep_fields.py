"""Full deep-survey frame lists via SIA2 (TAP was returning 502). Collections *_deep contain only Deep Survey frames,
so a wide circle around each pole returns the full list for that pole."""
import sys,os,time; sys.path.insert(0,'code/A3')
from sia_frames import sia
import pandas as pd
P={'NEP':(270.0,66.56,10.0),'SEP':(90.0,-66.56,12.0)}
for pole,(ra,dec,r) in P.items():
    for coll in ['spherex_qr3_deep','spherex_dr1_deep']:
        fn=f'data/03-spherex/frames/deep_{pole}_{coll}.parquet'
        if os.path.exists(fn): continue
        t0=time.time()
        try: df=sia(ra,dec,r,coll)
        except Exception as e: print(pole,coll,'FAILED',e,flush=True); continue
        df['field']=pole; df.to_parquet(fn); print(pole,coll,len(df),round(time.time()-t0),'s',flush=True)
