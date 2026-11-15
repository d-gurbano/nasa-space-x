"""Reverse check: how many JPL sb_ident objects are in the kete answer key (any V) within 30 arcsec."""
import os, json, glob, re
import numpy as np, pandas as pd
from astropy.coordinates import SkyCoord
import astropy.units as u
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
D = os.path.join(ROOT, 'data/07-answer-keys/answer_key/crosscheck')
ak = pd.read_parquet(os.path.join(ROOT, 'data/07-answer-keys/answer_key/known_objects_in_frames.parquet'))
s = pd.read_csv(os.path.join(D, 'kete_vs_sbident.csv'))
def _dec(x):
    m = re.match(r"([+-]?)(\d+)\s+(\d+)'([\d.]+)", x.strip()); v = int(m.group(2)) + int(m.group(3)) / 60 + float(m.group(4)) / 3600
    return -v if m.group(1) == '-' else v
def _ra(x):
    a, b, c = x.split(':'); return 15 * (int(a) + int(b) / 60 + float(c) / 3600)
rows = []
for r in s.itertuples():
    j = json.load(open(os.path.join(D, f'sbident_{r.obsid}_D{r.det}.json')))
    data = j.get('data_second_pass', [])
    a = ak[ak.key == r.key]
    if not data:
        continue
    sc = SkyCoord([_ra(d[1]) for d in data] * u.deg, [_dec(d[2]) for d in data] * u.deg)
    ca = SkyCoord(a.ra_deg.values * u.deg, a.dec_deg.values * u.deg)
    idx, d2, _ = sc.match_to_catalog_sky(ca)
    for k, d in enumerate(data):
        rows.append(dict(obsid=r.obsid, det=r.det, sb_name=d[0], sb_V=float(d[6]), sep_arcsec=d2[k].arcsec,
                         kete_name=a.name.values[idx[k]], kete_V=a.V_pred.values[idx[k]], kete_on_detector=bool(a.on_detector.values[idx[k]])))
df = pd.DataFrame(rows); df.to_csv(os.path.join(D, 'sbident_reverse_match.csv'), index=False)
m = df.sep_arcsec < 30
print('sb_ident objects', len(df), 'found in kete key <30"', int(m.sum()), 'median sep', df.sep_arcsec[m].median())
print(df[~m].to_string())
