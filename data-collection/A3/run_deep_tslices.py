"""Deep Survey frame lists via SIA2: small circle (r=0.05 deg) x TIME slices, so each response stays ~1-3 MB
(big responses die with 502 proxy timeouts on this link). Pass 1: pole point, 7-day slices. Pass 2: 6 points on a
2.5-deg ring around the mean frame centre, 14-day slices. Checkpoint per (point, slice). Stop: touch data/03-spherex/STOP_TS."""
import sys,os,time,glob; sys.path.insert(0,'code/A3')
from sia_frames import sia
import numpy as np, pandas as pd
from astropy.coordinates import SkyCoord
import astropy.units as u
D='data/03-spherex/frames/deep_tslices'; os.makedirs(D,exist_ok=True)
RANGE={'spherex_qr3_deep':(61170,61330),'spherex_dr1_deep':(60780,61180)}   # MJD windows (QR3 ~2026W20-W40, DR1 2025W17-2026W20), padded
def run_point(tag,coll,ra,dec,step):
    a0,a1=RANGE[coll]; out=[]
    for a in range(a0,a1,step):
        if os.path.exists('data/03-spherex/STOP_TS'): sys.exit()
        fn=f'{D}/{tag}__{coll}__{ra:.3f}_{dec:.3f}__{a}_{a+step}.parquet'
        if os.path.exists(fn): out.append(pd.read_parquet(fn)); continue
        if os.path.exists(fn+'.fail'): continue
        t0=time.time()
        try: df=sia(ra,dec,0.05,coll,tries=4,time_range=(a,a+step),timeout=600)
        except Exception: open(fn+'.fail','w').close(); print(tag,coll,a,'FAILED',flush=True); continue
        df['field']=tag; df['grid_ra']=ra; df['grid_dec']=dec; df.to_parquet(fn); out.append(df)
        print(tag,coll,round(ra,2),round(dec,2),a,len(df),round(time.time()-t0),'s',flush=True); time.sleep(1)
    return pd.concat(out) if out else None
for coll in ['spherex_qr3_deep','spherex_dr1_deep']:
    for tag,(ra0,dec0) in {'NEP':(270.0,66.56),'SEP':(90.0,-66.56)}.items():
        run_point(tag,coll,ra0,dec0,7)
for coll in ['spherex_qr3_deep','spherex_dr1_deep']:
    for tag,(ra0,dec0) in {'NEP':(270.0,66.56),'SEP':(90.0,-66.56)}.items():
        fs=glob.glob(f'{D}/{tag}__{coll}__{ra0:.3f}_{dec0:.3f}__*.parquet')
        if not fs: continue
        d0=pd.concat([pd.read_parquet(f) for f in fs])
        if len(d0)==0: continue
        c=SkyCoord(d0.s_ra.values*u.deg,d0.s_dec.values*u.deg); xyz=c.cartesian.xyz.value.mean(axis=1)
        cen=SkyCoord(*xyz,representation_type='cartesian'); cen=SkyCoord(cen.spherical.lon,cen.spherical.lat)
        print(tag,coll,'mean frame centre',round(cen.ra.deg,3),round(cen.dec.deg,3),flush=True)
        for pa in range(0,360,60):
            p=cen.directional_offset_by(pa*u.deg,2.5*u.deg); run_point(tag,coll,p.ra.deg,p.dec.deg,14)
