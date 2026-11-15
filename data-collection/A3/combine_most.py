"""Combine MOST raw tables -> frames/shortlist_frames.parquet + per-object counts."""
import glob, gzip, os, pandas as pd, numpy as np
from astropy.io import ascii
# nominal per-detector band edges (um), VERIFIED from SIA em_min/em_max rows (see detector_bands.csv)
lists={}
for f,tag in [('a_spherex_precovery_shortlist','precovery'),('b_lost_recovery_shortlist','lost')]:
    for x in pd.read_parquet(f'data/01-targets/lists/{f}.parquet').designation: lists.setdefault(x,tag)
rows=[];cnt=[]
for name,tag in lists.items():
    fn=f"data/03-spherex/frames/most_raw/{name.replace('/','_').replace(' ','_')}.tbl.gz"
    if not os.path.exists(fn):
        cnt.append(dict(designation=name,list=tag,status='error' if os.path.exists(fn+'.err') else 'pending',n_files=0)); continue
    txt=gzip.open(fn,'rt').read()
    meta={l.split('=')[0].strip('\\ '):l.split('=',1)[1].strip().strip('"') for l in txt.splitlines() if l.startswith('\\') and '=' in l}
    try: t=ascii.read(txt,format='ipac').to_pandas()
    except Exception as e: cnt.append(dict(designation=name,list=tag,status='parse_error',n_files=0)); continue
    if len(t)==0: cnt.append(dict(designation=name,list=tag,status='ok',n_files=0,most_object_name=meta.get('object_name'))); continue
    t['designation']=name; t['list']=tag; t['most_object_name']=meta.get('object_name')
    rows.append(t)
    rel=t.uri.str.split('/').str[3]
    cnt.append(dict(designation=name,list=tag,status='ok',most_object_name=meta.get('object_name'),n_files=len(t),n_exposures=t.observationid.nunique(),
        n_dr1=int((rel=='dr1').sum()),n_qr3=int((rel=='qr3').sum()),n_qr2=int((rel=='qr2').sum()),
        first_mjd=t.mjd_start.min(),last_mjd=t.mjd_start.max(),vmag_min=t.vmag.min(),
        **{f'n_D{i}':int((t.productid.str.strip()==f'D{i}').sum()) for i in range(1,7)}))
d=pd.concat(rows,ignore_index=True)
for c in d.columns:
    if d[c].dtype==object: d[c]=d[c].astype(str).str.strip()
d['detector']=d.productid; d['release']=d.uri.str.split('/').str[3]
d['s3_key']=d.uri.str.split('ibe/data/spherex/',n=1).str[1]
d['obs_id']=d.observationid; d['t_min']=d.mjd_start; d['t_max']=d.mjd_end
d['s_region']=('POLYGON ICRS '+d.ra1.round(6).astype(str)+' '+d.dec1.round(6).astype(str)+' '+d.ra2.round(6).astype(str)+' '+d.dec2.round(6).astype(str)+' '
               +d.ra3.round(6).astype(str)+' '+d.dec3.round(6).astype(str)+' '+d.ra4.round(6).astype(str)+' '+d.dec4.round(6).astype(str))
bands='data/03-spherex/frames/detector_bands.csv'
if os.path.exists(bands):
    b=pd.read_csv(bands); d=d.merge(b[['detector','em_min_um','em_max_um']],on='detector',how='left')
keep=['designation','list','most_object_name','obs_id','detector','release','s3_key','t_min','t_max','exposure_time','s_region','em_min_um','em_max_um',
      'ra_obj','dec_obj','vmag','sun_dist','geo_dist','dist_ctr','phase','target_name','planeid','ra','dec']
d=d[[c for c in keep if c in d.columns]]
d.to_parquet('data/03-spherex/frames/shortlist_frames.parquet')
c=pd.DataFrame(cnt); c.to_csv('data/03-spherex/frames/shortlist_frame_counts.csv',index=False)
print(len(d),'rows',d.designation.nunique(),'objects'); print(c.status.value_counts()); print(c.groupby('list').n_files.describe())
