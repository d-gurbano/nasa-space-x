"""A4: combine DECam per-object parquet -> decam/decam_predisc_exposures.parquet + decam_summary.csv"""
import pandas as pd, glob, json, os, sys
sys.path.insert(0, os.path.dirname(__file__)); from common import O
st = pd.DataFrame([json.loads(l) for l in open(f'{O}/decam/decam_status.jsonl')])
fs = [pd.read_parquet(f) for f in glob.glob(f'{O}/decam/*.parquet') if not f.endswith('decam_predisc_exposures.parquet')]
if fs:
    e = pd.concat(fs, ignore_index=True); e.to_parquet(f'{O}/decam/decam_predisc_exposures.parquet', index=False)
    e['useful'] = (e.pred_sigma3_arcsec <= 300) & (e.pred_vmag <= 23.5)
    g = e.groupby('designation').agg(n_exp=('md5sum', 'size'), n_useful=('useful', 'sum'), first=('caldat', 'min'), last=('caldat', 'max')).reset_index()
    st = st.merge(g, on='designation', how='left')
st.to_csv(f'{O}/decam/decam_summary.csv', index=False)
print('objects', len(st), 'with exposures', int((st.n_exposures > 0).sum()), 'exposures', int(st.n_exposures.fillna(0).sum()))
