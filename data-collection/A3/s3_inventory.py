"""Anonymous read-only listing of nasa-irsa-spherex level2 prefixes, per release/week, checkpointed."""
import boto3, os, sys, time, pandas as pd, collections
from botocore import UNSIGNED
from botocore.config import Config
s3=boto3.client('s3',config=Config(signature_version=UNSIGNED,retries={'max_attempts':10,'mode':'adaptive'}),region_name='us-east-1')
B='nasa-irsa-spherex'; OUT='data/03-spherex/s3_inventory'
def prefixes(p):
    r=s3.list_objects_v2(Bucket=B,Prefix=p,Delimiter='/'); return [c['Prefix'] for c in r.get('CommonPrefixes',[])]
for rel in sys.argv[1:] or ['qr3','dr1','qr2']:
    for wk in prefixes(f'{rel}/level2/'):
        name=wk.strip('/').replace('/','__'); fn=f'{OUT}/{name}.parquet'
        if os.path.exists(fn): continue
        rows=[]
        for page in s3.get_paginator('list_objects_v2').paginate(Bucket=B,Prefix=wk):
            for o in page.get('Contents',[]): rows.append((o['Key'],o['Size'],o['LastModified']))
        df=pd.DataFrame(rows,columns=['key','bytes','last_modified']); df.to_parquet(fn)
        ext=collections.Counter(k.rsplit('.',1)[-1] for k in df.key)
        print(rel,wk,len(df),round(df.bytes.sum()/1e9,1),'GB',dict(ext),flush=True)
        time.sleep(0.2)
