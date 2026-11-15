"""A8 - write NUMBERS-<version>.md (auto-generated counts and checks) after a freeze/build.
  A8_VERSION=v1 python code/A8/report_numbers.py
"""
import os, sys, json, subprocess, datetime
import numpy as np, pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, os.path.join(ROOT, 'code/A8'))
import build_patches as B  # noqa: E402
import splits_baselines as SB  # noqa: E402

V = B.VERSION


def _md(df, index=True):
    d = df.reset_index() if index else df
    cols = [str(c) for c in d.columns]
    out = ['| ' + ' | '.join(cols) + ' |', '|' + '-|' * len(cols)]
    for r in d.itertuples(index=False):
        out.append('| ' + ' | '.join(str(x) for x in r) + ' |')
    return '\n'.join(out)


pd.DataFrame.to_markdown = _md
sfx = '' if V == 'v1' else f'_{V}'
L = []
w = L.append


def du(p):
    try:
        return subprocess.run(['du', '-sh', p], capture_output=True, text=True).stdout.split()[0]
    except Exception:
        return '?'


w(f'# A8 dataset {V} - auto-generated numbers ({datetime.datetime.now().isoformat(timespec="minutes")})\n')
w('All counts MEASURED from the files at generation time.\n')
st_f = os.path.join(SB.TAB, 'dataset_stats.json')
if os.path.exists(st_f):
    st = json.load(open(st_f))
    w('## Dataset\n')
    for k, v in st.items():
        w(f'- {k}: {v}')
    w('')
pe_f = os.path.join(B.IDX, 'patch_epochs_split.parquet')
if os.path.exists(pe_f):
    pe = pd.read_parquet(pe_f)
    w('## Patch-epochs per split and cluster\n')
    w(pe.groupby(['split', 'test_kind']).size().rename('patch_epochs').reset_index().to_markdown(index=False))
    w('')
    w(pe.groupby('cluster').agg(patch_epochs=('patch', 'size'), frames=('frame_id', 'nunique'),
                                epochs_per_patch=('patch', lambda s: round(s.value_counts().median(), 1)),
                                mjd_min=('mjd_avg', 'min'), mjd_max=('mjd_avg', 'max')).round(2).to_markdown())
    w('')
for name, f in [('Static-sky reference (per-cluster medians)', os.path.join(SB.TAB, 'staticref_summary.csv'))]:
    if os.path.exists(f):
        s = pd.read_csv(f)
        s['cluster'] = s.patch.str.rsplit('_', n=1).str[0]
        w(f'## {name}\n')
        w(s.groupby('cluster')[[c for c in ['epochs', 'frac_pix_with_ref', 'frac_narrow', 'median_nref', 'chi_mad'] if c in s]].median().round(3).to_markdown())
        w('')
f = os.path.join(SB.TAB, 'known_mover_check.csv')
if os.path.exists(f):
    k = pd.read_csv(f)
    w('## Known-mover check (V < 18 in aligned grid; residual 3x3 sum vs 24 off positions)\n')
    if len(k):
        w(k[['patch', 'desig', 'vmag', 'det', 'rate_arcsec_min', 'z_vs_off', 'z_var']].round(2).to_markdown(index=False))
    w('')
f = os.path.join(B.IDX, 'known_movers.parquet')
if os.path.exists(f):
    km = pd.read_parquet(f)
    w('## Known movers (kete)\n')
    w(km.groupby('cluster').agg(rows=('desig', 'size'), objects=('desig', 'nunique'), in_aligned=('in_aligned', 'sum'),
                                vmin=('vmag', 'min'), n_V_lt_20=('vmag', lambda s: int((s < 20).sum()))).round(2).to_markdown())
    w('')
f = os.path.join(B.OUT, 'injected_test' + sfx, 'truth.parquet')
if os.path.exists(f):
    t = pd.read_parquet(f)
    w('## Frozen injected test set\n')
    w(t.groupby('kind').agg(injections=('ab', 'size'), tracks=('track_id', 'size'), ab_median=('ab', 'median'),
                            snr_pred_median=('snr_pred_psf', 'median'), frac_snr_gt5=('snr_pred_psf', lambda s: float((s > 5).mean()))).round(2).to_markdown())
    w(f"\nTracks (patch, track_id): {t.groupby(['patch', 'track_id']).ngroups}; patches: {t.patch.nunique()}\n")
f = os.path.join(B.OUT, 'labeled' + sfx, 'label_counts.csv')
if os.path.exists(f):
    w('## Labeled real-or-fake stamps\n')
    w(pd.read_csv(f).to_markdown(index=False))
    w('')
f = os.path.join(SB.TAB, 'inject_selftest.csv')
if os.path.exists(f):
    s = pd.read_csv(f)
    w(f'## Injection closure test\n\nflux ratio (fit/true) median {s.ratio_diff.median():.6f}, std {s.ratio_diff.std():.2e}, n={len(s)}\n')
w('## Sizes\n')
for p in ['raw', 'patches' + ('' if V == 'v1' else f'_{V}'), 'baselines' + sfx, 'injected_test' + sfx, 'labeled' + sfx, 'cube', 'index']:
    if os.path.exists(os.path.join(B.OUT, p)):
        w(f'- {p}: {du(os.path.join(B.OUT, p))}')
w(f'- total data/08-ai-training: {du(B.OUT)}')
open(os.path.join(B.OUT, f'NUMBERS-{V}.md'), 'w').write('\n'.join(L) + '\n')
print('\n'.join(L))
