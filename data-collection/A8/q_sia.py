import sys, time, pandas as pd
sys.path.insert(0, 'code/A0')
from rewind import sia2_query
out = 'data/08-ai-training/index/'
fields = {'NEP': (270.0, 66.56), 'SEP': (90.0, -66.56)}
for f, (ra, dec) in fields.items():
    for coll in ['spherex_qr3_deep', 'spherex_dr1_deep', 'spherex_qr3', 'spherex_dr1']:
        t = time.time()
        try:
            df = sia2_query(ra, dec, coll, radius_deg=0.001, maxrec=20000)
        except Exception as e:
            print(f, coll, 'ERR', e); continue
        df.to_parquet(f'{out}sia_{f}_{coll}.parquet')
        print(f, coll, len(df), f'{time.time()-t:.1f}s', df['t_min'].min() if len(df) else '', df['t_min'].max() if len(df) else '')
        time.sleep(1)
print(list(df.columns))
