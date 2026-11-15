#!/usr/bin/env python
"""Build a PARTIAL sky index (contract: rewind-skyindex-v1) for the Sky page from the frame
tables we already have: the 5 challenge targets, the 2 deep fields and the shortlist paths.
The full-sky index from the engine replaces it (same format, without "partial").

  MAIN/.venv/bin/python web/scripts/skyindex-partial.py [MAIN] [OUT]

Rows: [compact_key, mjd_avg, detector, ra_c, dec_c, [ra1,dec1,...,ra4,dec4], wl_min_um, wl_max_um, release_code]
compact_key = "<obs_id>|<index into meta.vers>"; the S3 key is rebuilt with meta.key_patterns.
"""
import datetime
import glob
import json
import os
import re
import sys

import numpy as np
import pandas as pd
from astropy.io import fits

MAIN = sys.argv[1] if len(sys.argv) > 1 else '/Users/rahmanbazarov/Data/programming/SpaceApps2026-Rewind'
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(__file__), '..', 'public', 'data', 'skyindex')
FR = os.path.join(MAIN, 'data', '03-spherex', 'frames')
CELL = 5
RELEASES = ['qr3', 'dr1']
KEY = re.compile(r'^(qr3|dr1)/level2/(\w+)/(l2b[\w-]+)/(\d)/level2_(\w+?)D(\d)_spx_(l2b[\w-]+)\.fits$')
PATTERN = '{release}/level2/{week}/{ver}/{det}/level2_{obs}D{det}_spx_{ver}.fits'

tt = pd.read_parquet(os.path.join(FR, 'test_targets_frames.parquet'))
deep = pd.read_parquet(os.path.join(FR, 'deep_fields_frames.parquet'))
short = pd.read_parquet(os.path.join(FR, 'shortlist_frames.parquet'))
cols = ['s3_key', 't_min', 't_max', 's_region']
df = pd.concat([tt[cols], deep[cols], short[cols]]).drop_duplicates('s3_key').reset_index(drop=True)

m = df.s3_key.str.extract(KEY)
ok = m[0].notna() & (m[2] == m[6]) & (m[3] == m[5])
df, m = df[ok].reset_index(drop=True), m[ok].reset_index(drop=True)
vers = sorted(m[2].unique())
ver_ix = m[2].map({v: i for i, v in enumerate(vers)})
# the week is the first two parts of the obs id; check it so the pattern can rebuild every key
assert (m[4].str.split('_').str[:2].str.join('_') == m[1]).all()

poly = np.array([[float(x) for x in s.split()[2:10]] for s in df.s_region])  # ra1 dec1 ... ra4 dec4
ra, dec = np.radians(poly[:, 0::2]), np.radians(poly[:, 1::2])
v = np.stack([np.cos(dec) * np.cos(ra), np.cos(dec) * np.sin(ra), np.sin(dec)], -1).sum(1)
v /= np.linalg.norm(v, axis=1)[:, None]
ra_c = np.degrees(np.arctan2(v[:, 1], v[:, 0])) % 360
dec_c = np.degrees(np.arcsin(v[:, 2]))

bands = pd.read_csv(os.path.join(FR, 'detector_bands.csv')).set_index('detector')
det = m[3].astype(int).to_numpy()
mjd = ((df.t_min + df.t_max) / 2).to_numpy()
rel = m[0].map({r: i for i, r in enumerate(RELEASES)}).to_numpy()

os.makedirs(os.path.join(OUT, 'cells'), exist_ok=True)
os.makedirs(os.path.join(OUT, 'detectors'), exist_ok=True)
for f in glob.glob(os.path.join(OUT, 'cells', '*.json')):
    os.remove(f)
ri = np.minimum((ra_c // CELL).astype(int), 360 // CELL - 1)
di = np.minimum(((dec_c + 90) // CELL).astype(int), 180 // CELL - 1)
cells = {}
order = np.argsort(mjd)
for i in order:
    row = [f'{m[4][i]}|{ver_ix[i]}', round(float(mjd[i]), 4), int(det[i]), round(float(ra_c[i]), 3), round(float(dec_c[i]), 3),
           [round(float(x), 3) for x in poly[i]], round(float(bands.em_min_um[f'D{det[i]}']), 3), round(float(bands.em_max_um[f'D{det[i]}']), 3), int(rel[i])]
    cells.setdefault(f'r{ri[i]}_d{di[i]}', []).append(row)
sizes = []
for name, rows in cells.items():
    p = os.path.join(OUT, 'cells', name + '.json')
    with open(p, 'w') as f:
        json.dump({'f': rows}, f, separators=(',', ':'))
    sizes.append(os.path.getsize(p))

# per-detector central wavelength, 64 x 64 samples of the calibration CWAVE image
N = 64
for d in range(1, 7):
    f = sorted(glob.glob(os.path.join(MAIN, 'data', '03-spherex', 'calibration', 'dr1', 'spectral_wcs', '*', str(d), '*.fits')))[-1]
    cw = fits.getdata(f, 'CWAVE')
    ny, nx = cw.shape
    xs = [round((i + 0.5) * nx / N - 0.5, 2) for i in range(N)]  # 0-based pixel centres
    ys = [round((i + 0.5) * ny / N - 0.5, 2) for i in range(N)]
    grid = [[round(float(cw[int(round(y)), int(round(x))]), 4) for x in xs] for y in ys]
    with open(os.path.join(OUT, 'detectors', f'D{d}_wave.json'), 'w') as fo:
        json.dump({'detector': d, 'nx': N, 'ny': N, 'naxis': [nx, ny], 'xs': xs, 'ys': ys, 'wave_um': grid,
                   'source': os.path.basename(f) + ' (CWAVE), 0-based pixel centres, wave_um[y][x]'}, fo, separators=(',', ':'))

areas = [{'name': n, 'kind': 'challenge target', 'ra': round(float(g.query_ra.iloc[0]), 4), 'dec': round(float(g.query_dec.iloc[0]), 4)} for n, g in tt.groupby('target')]
areas += [{'name': n, 'kind': 'deep field', 'ra': round(float(g.grid_ra.median()), 3), 'dec': round(float(g.grid_dec.median()), 3)} for n, g in deep.groupby('field')]
meta = {
    'schema': 'rewind-skyindex-v1',
    'built_iso': datetime.datetime.now(datetime.UTC).strftime('%Y-%m-%dT%H:%M:%SZ'),
    'partial': True,
    'partial_note': 'Built from the frame tables of the 5 challenge targets, the 2 deep fields and the paths of the '
                    f'{short.designation.nunique()} shortlisted objects. The rest of the sky is not in this index yet.',
    'areas': areas,
    'n_shortlist_paths': int(short.designation.nunique()),
    'releases': RELEASES,
    'n_frames': int(len(df)),
    'mjd_range': [round(float(mjd.min()), 2), round(float(mjd.max()), 2)],
    'cell_deg': CELL,
    'fields': ['key', 'mjd_avg', 'detector', 'ra_c', 'dec_c', 'polygon', 'wl_min_um', 'wl_max_um', 'release_code'],
    'key_patterns': {'compact': '<obs>|<index into vers>', 'level2': PATTERN, 'week': 'first two _ parts of obs'},
    'vers': vers,
    'cells': sorted(cells),
    'bucket': 'nasa-irsa-spherex',
}
with open(os.path.join(OUT, 'meta.json'), 'w') as f:
    json.dump(meta, f, separators=(',', ':'))
print(f'{len(df)} frames, {len(cells)} cells, {sum(sizes) / 1e6:.1f} MB, largest shard {max(sizes) / 1e6:.2f} MB, dropped {int((~ok).sum())} odd keys -> {OUT}')
