"""A4 shared helpers: polite GET with retry, MOST query + IPAC parse."""
import requests, time, io, os, gzip
import pandas as pd
from astropy.io import ascii
R = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
O = f'{R}/data/04-other-archives'
MOST = 'https://irsa.ipac.caltech.edu/cgi-bin/MOST/nph-most'
UA = {'User-Agent': 'Rewind-SpaceApps2026-A4 (read-only research)'}

def get(url, params=None, timeout=600, tries=5, **kw):
    last = None
    for k in range(tries):
        try:
            r = requests.get(url, params=params, timeout=timeout, headers=UA, **kw)
            if r.status_code in (429, 500, 502, 503, 504):
                last = f'HTTP {r.status_code}'; time.sleep(5 * 2**k); continue
            return r
        except Exception as e:
            last = repr(e); time.sleep(5 * 2**k)
    raise RuntimeError(last)

def safe(des): return des.replace('/', '_').replace(' ', '_')

def most(catalog, des, begin, end, is_comet=False, rawdir=None):
    p = dict(catalog=catalog, input_type='name_input', obj_name=des, obs_begin=begin, obs_end=end, output_mode='Brief')
    if is_comet: p['obj_type'] = 'Comet'
    r = get(MOST, p)
    txt = r.text
    if rawdir:
        os.makedirs(rawdir, exist_ok=True)
        with gzip.open(f'{rawdir}/{safe(des)}.tbl.gz', 'wt') as f: f.write(txt)
    if r.status_code != 200 or '|' not in txt[:20000]:
        msg = txt[:400].replace('\n', ' ')
        return None, f'HTTP{r.status_code}: {msg}'
    hdr = [l for l in txt.splitlines() if l.startswith('\\')]
    if 'No image' in txt[:5000] and txt.count('\n') < 40:
        return pd.DataFrame(), 'no images'
    try:
        t = ascii.read(txt, format='ipac')
        df = t.to_pandas()
    except Exception as e:
        return None, f'parse error {e!r}: {txt[:300]!r}'
    return df, 'ok'
