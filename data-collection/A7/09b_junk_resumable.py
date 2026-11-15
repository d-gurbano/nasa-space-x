"""A7 step 9b: resumable, chunked version of 09 (the 11 MB single-range FLAGS reads in 09 time out at
~100 KB/s). One frame per artifact type, FLAGS read in 512 KB ranges, regions checkpointed per frame,
stamps checkpointed in artifact_stamps_labels.csv."""
import os, sys, io, json, time
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(__file__))
import importlib.util
spec = importlib.util.spec_from_file_location('j9', os.path.join(os.path.dirname(__file__), '09_junk_catalog.py'))
j9 = importlib.util.module_from_spec(spec); spec.loader.exec_module(j9)
from rewind import l2_layout, _range
from astropy.io import fits
from astropy.wcs import WCS
from scipy import ndimage
J = j9.J; CK = os.path.join(J, 'flag_regions_ckpt'); os.makedirs(CK, exist_ok=True)


def full_flags_chunked(key, chunk=512 * 1024):
    url, lay, st = l2_layout('ibe/data/spherex/' + key)
    fh, foff, fdat, flen = lay['FLAGS']
    n = (fdat - foff) + flen; buf = bytearray()
    while len(buf) < n:
        buf += _range(url, foff + len(buf), min(chunk, n - len(buf)), tries=6)
    prim = fits.PrimaryHDU().header.tostring().encode()
    return np.asarray(fits.open(io.BytesIO(prim + bytes(buf)))[1].data), lay['IMAGE'][0]


def regions():
    stats = pd.read_csv(os.path.join(J, 'frame_artifact_stats.csv'))
    jobs = []
    for lab, (bit, kw) in j9.TYPES.items():
        col = kw.replace('L2 ', '').replace(' ', '_')
        cand = stats[pd.to_numeric(stats[col], errors='coerce').fillna(0) > 0].sort_values(col, ascending=False).drop_duplicates('OBSID')
        if len(cand):
            jobs.append((lab, bit, cand.iloc[0].key))
    out = []
    for lab, bit, key in jobs:
        ck = os.path.join(CK, lab + '.json')
        if os.path.exists(ck):
            out += json.load(open(ck)); continue
        t0 = time.time()
        try:
            fl, hdr = full_flags_chunked(key)
        except Exception as e:
            print('flags fail', lab, e, flush=True); continue
        m = (fl & (1 << bit)) != 0
        if lab == 'transient_cosmic_ray':
            m &= (fl & (1 << 21)) == 0
        lb, n = ndimage.label(m)
        res = []
        if n:
            sizes = ndimage.sum(m, lb, range(1, n + 1)); order = np.argsort(sizes)[::-1][:4]
            w = WCS(hdr, relax=True, key=' ')
            for oi in order:
                ys, xs = np.where(lb == oi + 1); yc, xc = ys.mean(), xs.mean()
                k = np.argmin((ys - yc) ** 2 + (xs - xc) ** 2); x, y = float(xs[k]), float(ys[k])
                ra, dec = w.all_pix2world([[x, y]], 0)[0]
                res.append(dict(label=lab, flag_bit=bit, key=key, x_pix=x, y_pix=y, ra=float(ra), dec=float(dec),
                                region_npix=int(sizes[oi]), n_regions_in_frame=int(n), frac_frame=float(m.mean()), source='pipeline FLAGS'))
        json.dump(res, open(ck, 'w'))
        print(lab, key.split('/')[-1], 'regions', n, round(time.time() - t0), 's', flush=True)
        out += res
    return out


def main():
    lab_fn = os.path.join(J, 'artifact_stamps_labels.csv')
    jobs = regions()
    tf = os.path.join(CK, 'trails_anoms.json')
    if os.path.exists(tf):
        extra = json.load(open(tf))
    else:
        _, _, an, tr = (None, None, pd.read_csv(os.path.join(J, 'anomaly_list/SPHEREX_exposure_anomaly_log_20250810.csv')),
                        pd.read_csv(os.path.join(J, 'trails_borlaff2026/SPHEREx_trails_database.csv')))
        extra = []
        for fn_, kw_ in ((j9.trail_jobs, dict(tr=tr, n=10)), (j9.anomaly_jobs, dict(an=an, n=6))):
            try:
                extra += fn_(**kw_)
            except Exception as e:
                print('lookup failed', fn_.__name__, repr(e)[:200], flush=True)
        json.dump(extra, open(tf, 'w'), default=float)
    jobs += extra
    done = pd.read_csv(lab_fn) if os.path.exists(lab_fn) else pd.DataFrame(columns=['key', 'ra'])
    dk = set(zip(done.key, done.ra.round(6)))
    todo = [j for j in jobs if (j['key'], round(j['ra'], 6)) not in dk]
    print('stamps to cut', len(todo), 'of', len(jobs), flush=True)
    res = []
    for i, j in enumerate(todo):
        res.append(j9.cut(j))
        if i % 5 == 4 or i == len(todo) - 1:
            pd.concat([done, pd.DataFrame(res)], ignore_index=True).to_csv(lab_fn, index=False)
            print(i + 1, 'cut', flush=True)
    print('done', flush=True)


if __name__ == '__main__':
    main()
