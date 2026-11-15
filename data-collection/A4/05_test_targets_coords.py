"""A4: coordinates + proper motions of the 5 challenge test targets (SIMBAD/CDS, partner France: standard name resolver, no US equivalent with PMs for all 5)."""
import pandas as pd, os, sys
sys.path.insert(0, os.path.dirname(__file__)); from common import *
from astroquery.simbad import Simbad
s = Simbad(); s.add_votable_fields('pmra', 'pmdec', 'plx_value', 'otype')
names = {"Barnard's Star": "Barnard's star", 'WISE 0855-0714': 'WISE J085510.83-071442.5', 'Epsilon Indi B': 'eps Ind B', 'RW Aurigae': 'RW Aur', 'R Draconis': 'R Dra'}
rows = []
for k, v in names.items():
    r = s.query_object(v).to_pandas().iloc[0]
    rows.append(dict(target=k, simbad_id=v, ra_j2000=r['ra'], dec_j2000=r['dec'], pmra_mas_yr=r['pmra'], pmdec_mas_yr=r['pmdec'], plx_mas=r['plx_value'], otype=r['otype']))
d = pd.DataFrame(rows); print(d.to_string())
os.makedirs(f'{O}/test_targets', exist_ok=True); d.to_csv(f'{O}/test_targets/test_targets_coords.csv', index=False)
