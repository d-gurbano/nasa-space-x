"""A4 step 7b: DECam instcal exposures whose centre is within 1.1 deg of each test target (NOIRLab adv_search, read-only POST),
plus IRSA SIA2 retry for targets that got HTTP 502 in step 7."""
import pandas as pd, numpy as np, os, sys, io, time, requests
sys.path.insert(0, os.path.dirname(__file__)); from common import *
from astropy.io.votable import parse
D = f'{O}/test_targets'
T = pd.read_csv(f'{D}/test_targets_coords.csv')
API = 'https://astroarchive.noirlab.edu/api/adv_search/find/?limit=50000&format=json'
OUTF = ["md5sum", "archive_filename", "instrument", "proc_type", "obs_type", "caldat", "dateobs_center", "ra_center", "dec_center", "exposure", "ifilter", "url", "proposal"]
rows = []
for r in T.itertuples():
    key = safe(r.target.replace("'", ''))
    cd = max(np.cos(np.radians(r.dec_deg)), 0.05)
    body = {"outfields": OUTF, "search": [["instrument", "decam"], ["proc_type", "instcal"], ["ra_center", r.ra_deg - 1.2 / cd, r.ra_deg + 1.2 / cd], ["dec_center", r.dec_deg - 1.2, r.dec_deg + 1.2]]}
    try:
        res = requests.post(API, json=body, timeout=600, headers=UA); df = pd.DataFrame(res.json()[1:])
        if len(df):
            sep = np.degrees(np.arccos(np.clip(np.sin(np.radians(r.dec_deg)) * np.sin(np.radians(df.dec_center)) + np.cos(np.radians(r.dec_deg)) * np.cos(np.radians(df.dec_center)) * np.cos(np.radians(df.ra_center - r.ra_deg)), -1, 1)))
            df['sep_deg'] = sep; df = df[df.sep_deg <= 1.1]; df.insert(0, 'target', r.target)
        df.to_csv(f'{D}/{key}_decam_instcal.csv', index=False)
        rows.append(dict(target=r.target, archive='NOIRLab adv_search', collection='DECam instcal (centre <= 1.1 deg)', n=len(df), note=f"{df.caldat.min() if len(df) else ''} .. {df.caldat.max() if len(df) else ''}"))
    except Exception as e: rows.append(dict(target=r.target, archive='NOIRLab adv_search', collection='ERROR', n=0, note=repr(e)[:200]))
    print(rows[-1], flush=True); time.sleep(2)
    if not os.path.exists(f'{D}/{key}_irsa_sia.parquet'):
        try:
            res = get('https://irsa.ipac.caltech.edu/SIA', dict(POS=f'CIRCLE {r.ra_deg} {r.dec_deg} 0.01', RESPONSEFORMAT='VOTABLE'), timeout=900)
            tb = parse(io.BytesIO(res.content)).get_first_table().to_table(use_names_over_ids=True).to_pandas(); tb.insert(0, 'target', r.target)
            tb.to_parquet(f'{D}/{key}_irsa_sia.parquet', index=False)
            for c, n in tb.groupby('obs_collection').size().items(): rows.append(dict(target=r.target, archive='IRSA SIA2', collection=c, n=n))
        except Exception as e: rows.append(dict(target=r.target, archive='IRSA SIA2', collection='ERROR (retry)', n=0, note=repr(e)[:200]))
        print(rows[-1], flush=True)
pd.DataFrame(rows).to_csv(f'{D}/coverage_summary_decam_retry.csv', index=False); print('DONE7B')
