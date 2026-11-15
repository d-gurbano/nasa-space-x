"""Summaries for REPORT.md + manifest entries for derived (non-downloaded) A7 files."""
import os, sys, json, csv, datetime
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(__file__))
from common import OUT, sha256, MAN
S = {}
lf = os.path.join(OUT, 'labeled_set/labels.parquet')
if os.path.exists(lf):
    l = pd.read_parquet(lf)
    if 'snr' in l:
        p = l[l.kind == 'positive']; n = l[l.kind == 'negative']
        ak = pd.read_parquet(os.path.join(OUT, 'answer_key/known_objects_in_frames.parquet'), columns=['key', 'packed', 'position_quality'])
        p = p.merge(ak, left_on=['key', 'object'], right_on=['key', 'packed'], how='left')
        d = p[(p.snr > 5) & (p.wave_um < 2.4)]
        S['labels'] = dict(rows=len(l), positives=len(p), negatives=len(n), frames=int(l.key.nunique()),
                           pos_snr_median=float(p.snr.median()), pos_frac_snr_gt5=float((p.snr > 5).mean()),
                           pos_frac_snr_gt3=float((p.snr > 3).mean()), neg_frac_abs_snr_gt5=float((n.snr.abs() > 5).mean()),
                           neg_snr_median=float(n.snr.median()), neg_snr_std=float(n.snr.std()),
                           swir_dAB_median=float((d.ab_mag - d.AB_pred).median()), swir_dAB_std=float((d.ab_mag - d.AB_pred).std()), swir_n=len(d),
                           pos_quality=p.position_quality.value_counts().to_dict(),
                           errors=int(l.error.notna().sum()) if 'error' in l else 0)
af = os.path.join(OUT, 'junk/artifact_stamps_labels.csv')
if os.path.exists(af):
    a = pd.read_csv(af); S['artifacts'] = a.groupby('label').size().to_dict()
json.dump(S, open(os.path.join(OUT, 'summary_stats.json'), 'w'), indent=1, default=str)
print(json.dumps(S, indent=1, default=str))
# manifest: add derived files not yet listed
have = set(pd.read_csv(MAN).filename) if os.path.exists(MAN) else set()
with open(MAN, 'a', newline='') as f:
    w = csv.writer(f)
    for root, _, files in os.walk(OUT):
        for fn in files:
            p = os.path.join(root, fn); rel = os.path.relpath(p, OUT)
            if rel in have or rel.startswith('logs/') or rel == 'manifest.csv' or fn.endswith('.part'):
                continue
            src = 'derived: code/A7 (S3 stamps from https://nasa-irsa-spherex.s3.amazonaws.com/<key>)' if rel.endswith('.fits') else 'derived: code/A7'
            if rel.startswith('frames/sia2_'):
                src = 'https://irsa.ipac.caltech.edu/SIA (SIA2 query result)'
            w.writerow([rel, src, os.path.getsize(p), sha256(p), datetime.datetime.now().isoformat(timespec='seconds')])
print('manifest rows', sum(1 for _ in open(MAN)) - 1)
