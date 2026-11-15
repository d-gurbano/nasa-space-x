"""A4: manifest.csv for data/04-other-archives (every file: path, source url or 'derived', bytes, sha256, date)."""
import os, hashlib, time, pandas as pd, sys
sys.path.insert(0, os.path.dirname(__file__)); from common import O
SRC = {'wise/most_raw': 'https://irsa.ipac.caltech.edu/cgi-bin/MOST/nph-most?catalog=wise_merge (Brief)', 'ztf/most_raw': 'https://irsa.ipac.caltech.edu/cgi-bin/MOST/nph-most?catalog=ztf (Brief)',
       'spitzer/most_raw': 'https://irsa.ipac.caltech.edu/cgi-bin/MOST/nph-most?catalog=spitzer_bcd (Brief)', 'wise/gator_raw': 'https://irsa.ipac.caltech.edu/cgi-bin/Gator/nph-query (searchForm=MO)',
       'catch/parts': 'https://catch-api.astro.umd.edu/caught/<job_id>', 'ztf/parts': 'MOST ztf parsed', 'decam': 'https://astroarchive.noirlab.edu/api/adv_search/find/',
       'test_targets': 'IRSA SIA2 / MAST TESScut / NOIRLab', 'tess': 'derived (tess-point)'}
cm = f'{O}/cutouts/cutouts_manifest_part.csv'; cmap = dict(zip(*[pd.read_csv(cm)[c] for c in ('filename', 'url')])) if os.path.exists(cm) else {}
rows = []
for root, _, files in os.walk(O):
    if '/tmp' in root: continue
    for f in files:
        p = os.path.join(root, f); rel = os.path.relpath(p, O)
        if rel == 'manifest.csv': continue
        h = hashlib.sha256(open(p, 'rb').read()).hexdigest()
        url = cmap.get(rel) or next((v for k, v in SRC.items() if rel.startswith(k)), 'derived (code/A4)')
        rows.append(dict(filename=rel, url=url, bytes=os.path.getsize(p), sha256=h, date=time.strftime('%Y-%m-%d', time.localtime(os.path.getmtime(p)))))
m = pd.DataFrame(rows).sort_values('filename'); m.to_csv(f'{O}/manifest.csv', index=False); print(len(m), 'files', round(m.bytes.sum() / 1e6, 1), 'MB')
