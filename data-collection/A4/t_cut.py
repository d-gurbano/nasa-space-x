import requests, pandas as pd, io
from astropy.io import ascii
txt=open('data/04-other-archives/wise/gator_raw/2015_SA__neowiser_p1bs_psd.tbl').read()
d=ascii.read(txt,format='ipac').to_pandas(); print(d[['ra','dec','mjd','w1mpro','w2mpro','w2snr','scan_id','frame_num','dist_x']].to_string())
r0=d.iloc[0]; s=r0.scan_id; f=int(r0.frame_num)
for u in [f"https://irsa.ipac.caltech.edu/ibe/data/wise/neowiser/p1bm_frm/{s[-2:]}/{s}/{f:03d}/{s}{f:03d}-w2-int-1b.fits?center={r0.ra},{r0.dec}&size=120arcsec",
          f"https://irsa.ipac.caltech.edu/ibe/search/wise/neowiser/p1bm_frm?POS={r0.ra},{r0.dec}&where=scan_id='{s}'+and+frame_num={f}"]:
    r=requests.get(u,timeout=200); print(u, r.status_code, len(r.content), r.content[:300])
