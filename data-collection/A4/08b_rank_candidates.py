"""A4: rank NEOWISE catalog candidates. strong = candidate AND dist_x <= max(3-sigma, 5") AND 3-sigma <= 30" AND W1 or W2 SNR >= 4.
Per object/visit table -> wise/neowise_candidates_ranked.csv, wise/neowise_object_summary.csv"""
import pandas as pd, numpy as np, os, sys
sys.path.insert(0, os.path.dirname(__file__)); from common import *
c = pd.read_parquet(f'{O}/wise/neowise_candidates.parquet')
t = pd.read_parquet(f'{O}/targets_A4.parquet')[['designation', 'list', 'disc_date']]
c = c.merge(t, on='designation', how='left')
c['date_utc'] = pd.to_datetime('1858-11-17') + pd.to_timedelta(c.mjd, unit='D')
c['pre_disc'] = c.date_utc < pd.to_datetime(c.disc_date)
snr = np.fmax(pd.to_numeric(c.w1snr, errors='coerce').fillna(0), pd.to_numeric(c.w2snr, errors='coerce').fillna(0))
c['strong'] = c.candidate & (c.dist_x <= np.maximum(c.sigma3_visit_arcsec, 5)) & (c.sigma3_visit_arcsec <= 30) & (snr >= 4)
c = c.sort_values(['strong', 'dist_x'], ascending=[False, True])
c.to_csv(f'{O}/wise/neowise_candidates_ranked.csv', index=False)
g = c.groupby('designation').agg(list=('list', 'first'), disc_date=('disc_date', 'first'), rows=('ra', 'size'), within_unc=('within_unc', 'sum'), candidates=('candidate', 'sum'),
    strong=('strong', 'sum'), strong_frames=('source_id', lambda s: s[c.loc[s.index, 'strong']].str[:9].nunique()), min_sigma3=('sigma3_visit_arcsec', 'min'),
    best_dist=('dist_x', lambda s: s[c.loc[s.index, 'candidate']].min() if c.loc[s.index, 'candidate'].any() else np.nan), pre_disc_strong=('pre_disc', lambda s: int((s & c.loc[s.index, 'strong']).sum()))).reset_index()
g.to_csv(f'{O}/wise/neowise_object_summary.csv', index=False); print(g.to_string())
print(c[c.strong][['designation', 'date_utc', 'table', 'ra', 'dec', 'dist_x', 'sigma3_visit_arcsec', 'w1mpro', 'w2mpro', 'w1snr', 'w2snr', 'source_id', 'pre_disc']].head(25).to_string())
