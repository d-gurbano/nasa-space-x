"""Parse MPCORB.DAT.gz (data/02-orbits) and CometEls.txt into kete states (A7)."""
import os, gzip
import numpy as np, pandas as pd
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
os.environ.setdefault('KETE_CACHE_DIR', os.path.join(ROOT, 'data/02-orbits/kete-cache'))
import kete

def _unpack_epoch(s):
    c = {'I': 1800, 'J': 1900, 'K': 2000}[s[0]]
    y = c + int(s[1:3])
    def v(ch): return int(ch) if ch.isdigit() else ord(ch) - 55
    return y, v(s[3]), v(s[4])

def load_mpcorb(path=os.path.join(ROOT, 'data/02-orbits/mpc/MPCORB.DAT.gz'), cache=os.path.join(ROOT, 'data/07-answer-keys/orbits/mpcorb_parsed.parquet')):
    if cache and os.path.exists(cache):
        return pd.read_parquet(cache)
    rows = []
    with gzip.open(path, 'rt', errors='replace') as f:
        started = False
        for l in f:
            if not started:
                started = l.startswith('-----'); continue
            if len(l) < 103 or not l[0:7].strip():
                continue
            try:
                rows.append((l[0:7].strip(), float(l[8:13]) if l[8:13].strip() else np.nan,
                             float(l[14:19]) if l[14:19].strip() else np.nan, l[20:25],
                             float(l[26:35]), float(l[37:46]), float(l[48:57]), float(l[59:68]),
                             float(l[70:79]), float(l[80:91]), float(l[92:103]), l[105:106],
                             l[166:194].strip(), l[161:165].strip()))
            except ValueError:
                continue
    df = pd.DataFrame(rows, columns=['packed', 'H', 'G', 'epoch_packed', 'M', 'peri_arg', 'node', 'incl', 'ecc', 'n',
                                     'a', 'U', 'name', 'flags_hex'])
    from astropy.time import Time
    ep = {e: Time('%04d-%02d-%02d' % _unpack_epoch(e), scale='tt').tdb.jd for e in df.epoch_packed.unique()}
    df['epoch_jd'] = df.epoch_packed.map(ep)
    df['peri_time'] = df.epoch_jd - df.M / df.n
    df['q'] = df.a * (1 - df.ecc)
    df['kind'] = 'asteroid'
    if cache:
        os.makedirs(os.path.dirname(cache), exist_ok=True)
        df.to_parquet(cache)
    return df

def load_comets(path=os.path.join(ROOT, 'data/02-orbits/mpc/CometEls.txt')):
    rows = []
    from astropy.time import Time
    for l in open(path, errors='replace'):
        if len(l) < 100:
            continue
        try:
            y, m, d = int(l[14:18]), int(l[19:21]), float(l[22:29])
            q = float(l[30:39]); e = float(l[41:49]); w = float(l[51:59]); node = float(l[61:69]); inc = float(l[71:79])
            epo = l[81:89].strip()
            tp = Time('%04d-%02d-%02d' % (y, m, int(d)), scale='tt').tdb.jd + (d - int(d))
            ep = Time(f'{epo[0:4]}-{epo[4:6]}-{epo[6:8]}', scale='tt').tdb.jd if epo else tp
            H = float(l[91:95]) if l[91:95].strip() else np.nan
            K = float(l[96:100]) if l[96:100].strip() else np.nan
            name = l[102:158].strip()
            rows.append(('C_' + name.split('(')[0].strip().replace(' ', '_'), H, K, ep, tp, q, e, w, node, inc, name))
        except Exception:
            continue
    return pd.DataFrame(rows, columns=['packed', 'H', 'K', 'epoch_jd', 'peri_time', 'q', 'ecc', 'peri_arg', 'node',
                                       'incl', 'name']).assign(kind='comet')

def to_states(df):
    out = []
    for r in df.itertuples():
        try:
            out.append(kete.CometElements(r.packed, r.epoch_jd, r.ecc, r.incl, r.q, r.peri_arg, r.peri_time, r.node).state)
        except Exception:
            pass
    return out
