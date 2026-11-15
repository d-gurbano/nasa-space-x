"""SIA2 frame lists for the 5 challenge targets. Checkpoint per target x collection."""
import sys,os,time; sys.path.insert(0,'code/A3')
from sia_frames import sia
import pandas as pd
# 2026.0 positions: J2000 catalog coords propagated with proper motion (ESTIMATED, see REPORT)
T={'barnards_star':(269.4482,4.7682),'wise0855-0714':(133.760,-7.242),'eps_indi_b':(331.096,-56.8005),'rw_aurigae':(76.9564,30.4014),'r_draconis':(248.1674,66.7550)}
D='data/03-spherex/frames/test_targets'; os.makedirs(D,exist_ok=True)
for name,(ra,dec) in T.items():
    for coll in ['spherex_dr1','spherex_qr3','spherex_dr1_deep','spherex_qr3_deep']:
        fn=f'{D}/{name}__{coll}.parquet'
        if os.path.exists(fn): continue
        t0=time.time()
        try: df=sia(ra,dec,0.01,coll,tries=8)
        except Exception as e: print(name,coll,'FAILED',flush=True); continue
        df['target']=name; df['query_ra']=ra; df['query_dec']=dec; df['collection_queried']=coll
        df.to_parquet(fn); print(name,coll,len(df),round(time.time()-t0,1),flush=True); time.sleep(2)
