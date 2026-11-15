"""Combine SIA frame lists (test targets, deep fields) and summarise the S3 inventory."""
import glob, os, pandas as pd
F='data/03-spherex/frames'
def load(pat):
    fs=[f for f in glob.glob(pat) if os.path.getsize(f)>0]
    return pd.concat([pd.read_parquet(f) for f in fs],ignore_index=True) if fs else pd.DataFrame()
t=load(f'{F}/test_targets/*.parquet')
if len(t):
    t.to_parquet(f'{F}/test_targets_frames.parquet')
    c=t.groupby(['target','release','detector']).size().unstack(fill_value=0); c['total']=c.sum(axis=1)
    c.to_csv(f'{F}/test_targets_frame_counts.csv'); print(c)
d=load(f'{F}/deep_tslices/*.parquet')
if len(d):
    d=d.drop_duplicates('obs_publisher_did')
    d['week']=d.obs_id.str[:10]
    d.to_parquet(f'{F}/deep_fields_frames.parquet')
    c=d.groupby(['field','release','detector']).size().unstack(fill_value=0); c['total']=c.sum(axis=1)
    c.to_csv(f'{F}/deep_fields_frame_counts.csv'); print(c)
    d.groupby(['field','release','week']).size().rename('n_files').to_csv(f'{F}/deep_fields_counts_per_week.csv')
# S3 inventory summary
I='data/03-spherex/s3_inventory'
fs=[f for f in glob.glob(f'{I}/*__level2__*.parquet') if os.path.getsize(f)>0]
rows=[]
for f in fs:
    x=pd.read_parquet(f); p=x.key.str.split('/')
    rows.append(dict(release=p.str[0].iloc[0],week=p.str[2].iloc[0],n_files=len(x),n_exposures=x.key.str.extract(r'level2_(\w+_\d{4}_\d)D')[0].nunique(),
        tb=x.bytes.sum()/1e12,proc_versions=';'.join(sorted(p.str[3].unique())),exts=';'.join(sorted(x.key.str.rsplit('.',n=1).str[-1].unique()))))
s=pd.DataFrame(rows).sort_values(['release','week']); s.to_csv(f'{I}/level2_per_week_summary.csv',index=False)
print(s.groupby('release').agg(weeks=('week','size'),files=('n_files','sum'),exposures=('n_exposures','sum'),TB=('tb','sum')))
