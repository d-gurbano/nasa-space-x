"""SIA2 frame metadata (no pixels). Optional TIME slice (MJD)."""
import requests, io, time, json, pandas as pd
from astropy.io.votable import parse
KEEP=['obs_id','obs_collection','energy_bandpassname','t_min','t_max','t_exptime','em_min','em_max','s_ra','s_dec','s_region','access_url','access_estsize','cloud_access','target_name','obs_release_date','obs_publisher_did']
def sia(ra,dec,r,coll,tries=5,time_range=None,timeout=900):
    p={'COLLECTION':coll,'POS':f'CIRCLE {ra} {dec} {r}','RESPONSEFORMAT':'VOTABLE'}
    if time_range: p['TIME']=f'{time_range[0]} {time_range[1]}'
    for i in range(tries):
        try:
            x=requests.get('https://irsa.ipac.caltech.edu/SIA',params=p,timeout=timeout); x.raise_for_status()
            df=parse(io.BytesIO(x.content),verify='ignore').get_first_table().to_table(use_names_over_ids=True).to_pandas()
            break
        except Exception as e:
            print('retry',coll,str(e)[:90],flush=True); time.sleep(20*(i+1))
    else: raise RuntimeError('SIA failed')
    df=df[[c for c in KEEP if c in df.columns]].copy()
    for c in df.columns:
        if df[c].dtype==object: df[c]=df[c].map(lambda v: v.decode() if isinstance(v,bytes) else v)
    df['s3_key']=df.cloud_access.map(lambda s: json.loads(s)['aws']['key'] if isinstance(s,str) and s else None)
    df['detector']=df.energy_bandpassname.str.replace('SPHEREx-','')
    df['release']=df.s3_key.str.split('/').str[0]
    return df
