"""Deep Survey frame lists via SIA2 small circles (r=0.05 deg); large circles time out (502).
Step 1: pole point. Step 2: re-centre on median frame centre. Step 3: rings at 2.5 and 5 deg (6 and 12 points);
a ring is kept going outward only while it adds >2% new frames. Checkpoint per point (parquet)."""
import sys,os,time,glob; sys.path.insert(0,'code/A3')
from sia_frames import sia
import numpy as np, pandas as pd
from astropy.coordinates import SkyCoord
import astropy.units as u
D='data/03-spherex/frames/deep_grid'; os.makedirs(D,exist_ok=True)
def q(tag,coll,ra,dec):
    fn=f'{D}/{tag}__{coll}__{ra:.3f}_{dec:.3f}.parquet'
    if os.path.exists(fn): return pd.read_parquet(fn)
    if os.path.exists(fn+'.fail'): return None
    t0=time.time()
    try: df=sia(ra,dec,0.05,coll,tries=6,timeout=1200)
    except Exception: open(fn+'.fail','w').close(); print(tag,coll,ra,dec,'FAILED',flush=True); return None
    df['field']=tag; df['grid_ra']=ra; df['grid_dec']=dec; df.to_parquet(fn)
    print(tag,coll,round(ra,3),round(dec,3),len(df),round(time.time()-t0),'s',flush=True); time.sleep(2); return df
for tag,(ra0,dec0) in {'NEP':(270.0,66.56),'SEP':(90.0,-66.56)}.items():
    for coll in ['spherex_qr3_deep','spherex_dr1_deep']:
        d0=q(tag,coll,ra0,dec0)
        if d0 is None or len(d0)==0: continue
        c=SkyCoord(d0.s_ra.values*u.deg,d0.s_dec.values*u.deg)
        cart=c.cartesian.xyz.value.mean(axis=1); cc=SkyCoord(*cart,representation_type='cartesian')
        ra_c,dec_c=cc.spherical.lon.deg,cc.spherical.lat.deg
        print(tag,coll,'frame-centre mean',round(ra_c,3),round(dec_c,3),flush=True)
        seen=set(d0.obs_publisher_did); dc=q(tag,coll,ra_c,dec_c)
        if dc is not None: seen|=set(dc.obs_publisher_did)
        cen=SkyCoord(ra_c*u.deg,dec_c*u.deg)
        for rad,npt in [(2.5,6),(5.0,12),(7.5,18)]:
            new=0
            for pa in np.arange(npt)*360/npt:
                p=cen.directional_offset_by(pa*u.deg,rad*u.deg)
                d=q(tag,coll,p.ra.deg,p.dec.deg)
                if d is None: continue
                s=set(d.obs_publisher_did); new+=len(s-seen); seen|=s
            print(tag,coll,'ring',rad,'new',new,'total',len(seen),flush=True)
            if new < 0.02*len(seen): break
