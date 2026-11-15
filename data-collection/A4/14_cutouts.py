"""A4 step 14: small cutouts for the best cases (read-only GETs).
WISE/NEOWISE L1b W1+W2 120" cutouts (IRSA IBE) at NEOWISE candidate rows (within uncertainty, not static, not SSO-tagged), max 40;
CATCH FITS cutouts (CATCH cutout_url, 0.16 deg) for up to 3 useful pre-discovery images per object, top 15 objects;
ZTF science-image 120" cutouts (IRSA IBE) for up to 3 useful frames per object, top 10 objects."""
import pandas as pd, numpy as np, os, sys, time, hashlib
sys.path.insert(0, os.path.dirname(__file__)); from common import *
C = f'{O}/cutouts'; os.makedirs(C, exist_ok=True)
man = []
def fetch(url, fn):
    if os.path.exists(fn): return
    try:
        r = get(url, timeout=300, tries=3)
        if r.status_code == 200 and len(r.content) > 500:
            open(fn, 'wb').write(r.content); man.append(dict(filename=os.path.relpath(fn, O), url=url, bytes=len(r.content), sha256=hashlib.sha256(r.content).hexdigest(), date=time.strftime('%Y-%m-%d')))
        else: print('fail', r.status_code, url[:120])
    except Exception as e: print('err', e, url[:120])
    time.sleep(0.5)
w = f'{O}/wise/neowise_candidates_ranked.csv'
if os.path.exists(w):
    c = pd.read_csv(w); c = pd.concat([c[c.strong], c[c.candidate & (c.sigma3_visit_arcsec <= 30) & ~c.strong].sort_values('dist_x').groupby('designation').head(4)]).drop_duplicates('source_id').head(40)
    for r in c.itertuples():
        s = r.scan_id; f = int(r.frame_num)
        if r.table.startswith('neowiser'): base = f'https://irsa.ipac.caltech.edu/ibe/data/wise/neowiser/p1bm_frm/{s[-2:]}/{s}/{f:03d}/{s}{f:03d}'
        else:
            sub = {'allsky_4band_p1bs_psd': 'allsky/4band_p1bm_frm', 'allsky_3band_p1bs_psd': 'cryo_3band/3band_p1bm_frm', 'allsky_2band_p1bs_psd': 'postcryo/2band_p1bm_frm'}[r.table]
            base = f'https://irsa.ipac.caltech.edu/ibe/data/wise/{sub}/{s[-2:]}/{s}/{f:03d}/{s}{f:03d}'
        for b in (1, 2):
            fetch(f'{base}-w{b}-int-1b.fits?center={r.ra_u},{r.dec_u}&size=120arcsec', f'{C}/wise_{safe(r.designation)}_{s}{f:03d}_w{b}.fits.gz')
cu = f'{O}/catch/catch_predisc_useful.csv'
if os.path.exists(cu):
    c = pd.read_csv(cu); top = c.groupby('designation').size().sort_values(ascending=False).head(15).index
    for d in top:
        sub = c[c.designation == d].sort_values('unc_a').drop_duplicates('source').head(3)
        for r in sub.itertuples(): fetch(r.cutout_url, f'{C}/catch_{safe(d)}_{r.source}_{str(r.product_id).split(":")[-1][:40]}.fits')
zu = f'{O}/ztf/ztf_predisc_useful.csv'
if os.path.exists(zu):
    c = pd.read_csv(zu); top = c.groupby('designation').size().sort_values(ascending=False).head(10).index
    for d in top:
        sub = c[c.designation == d].sort_values('vmag_pred').head(3)
        for r in sub.itertuples(): fetch(r.cutout_url, f'{C}/ztf_{safe(d)}_{r.filefracday}_{r.filtercode}.fits')
m = pd.DataFrame(man); fn = f'{C}/cutouts_manifest_part.csv'
if os.path.exists(fn): m = pd.concat([pd.read_csv(fn), m], ignore_index=True)
m.to_csv(fn, index=False); print('CUTOUTS_DONE', len(man), 'new files', m.bytes.sum() if len(m) else 0, 'bytes total')
