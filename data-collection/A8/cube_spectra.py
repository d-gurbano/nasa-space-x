"""A8 - SPHEREx DR1 all-sky 102-channel HiPS cube (Norder5) cutouts and source spectra for the A8 clusters.

Reads only the rows of each of the 102 IMAGE planes (and NHITS planes) that cover a cluster, with HTTPS range
requests to the public S3 bucket (no full 321 MB tile download). Saves per-cluster cube cutouts plus the
SPECTRAL_CHANNELS and WCS-WAVE tables, then extracts spectra at sources detected in the band-summed cube.

  python code/A8/cube_spectra.py
Outputs: data/08-ai-training/cube/<cluster>_cube.npz, cube/source_spectra.parquet
"""
import os, sys, io, json, time
import numpy as np, pandas as pd
from astropy.io import fits
from astropy.wcs import WCS
from astropy_healpix import HEALPix
import astropy.units as u
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, os.path.join(ROOT, 'code/A0'))
sys.path.insert(0, os.path.join(ROOT, 'code/A8'))
import rewind as R  # noqa
import build_patches as B  # noqa

HIPS = 'https://nasa-irsa-spherex.s3.amazonaws.com/dr1/hips5_cube/hips_20261026/Norder5/'
OUT = os.path.join(ROOT, 'data/08-ai-training/cube')
HALF_DEG = 0.30   # half-size of the cluster box to cut (cluster patches span +/-0.16 deg + 96 px cutouts)


def tile_url(npix):
    return f'{HIPS}Dir{(npix // 10000) * 10000}/Npix{npix}_cube.fits'


def layout(url):
    stats = dict(bytes=0, requests=0)
    off, lay = 0, {}
    for k in range(6):
        h, hl = R._read_header(url, off, stats)
        name = h.get('EXTNAME', 'PRIMARY') if k else 'PRIMARY'
        dl = R._data_len(h)
        lay[name] = (h, off, off + hl, dl)
        off += hl + dl
    return lay


def read_tile_box(npix, pts, half_deg=0.10):
    url = tile_url(npix)
    lay = layout(url)
    h = lay['IMAGE'][0]
    h2 = h.copy()
    for k in list(h2.keys()):
        if k.endswith('3') and (k[:-1] in ('CTYPE', 'CUNIT', 'CRPIX', 'CDELT', 'CRVAL', 'CNAME', 'NAXIS') or k.startswith(('PS3_', 'PV3_', 'PC3_', 'PC1_3', 'PC2_3'))):
            del h2[k]
    for k in ['PS3_0', 'PS3_1', 'PS3_2', 'PV3_3', 'PC3_3']:
        h2.remove(k, ignore_missing=True)
    h2['NAXIS'] = 2
    h2['WCSAXES'] = 2
    w = WCS(h2)
    # box corners in tile pixel coordinates
    dd = half_deg
    cr = [(ra + dx / np.cos(np.radians(dec)), dec + dy) for ra, dec in pts for dx in (-dd, 0, dd) for dy in (-dd, 0, dd)]
    xy = np.array(w.all_world2pix(cr, 0))
    good = np.isfinite(xy).all(1)
    xy = xy[good]
    x0, x1 = int(max(np.floor(xy[:, 0].min()), 0)), int(min(np.ceil(xy[:, 0].max()) + 1, 512))
    y0, y1 = int(max(np.floor(xy[:, 1].min()), 0)), int(min(np.ceil(xy[:, 1].max()) + 1, 512))
    if x1 <= x0 or y1 <= y0:
        return None
    plane = 512 * 512 * 4

    def rd(args):
        ext, c = args
        _, _, dloc, _ = lay[ext]
        raw = R._range(url, dloc + c * plane + y0 * 512 * 4, (y1 - y0) * 512 * 4)
        dt = '>f4' if ext == 'IMAGE' else '>i4'
        return np.frombuffer(raw, dtype=dt).reshape(y1 - y0, 512)[:, x0:x1]
    with ThreadPoolExecutor(6) as ex:
        img = np.array(list(ex.map(rd, [('IMAGE', c) for c in range(102)])), np.float32)
        nh = np.array(list(ex.map(rd, [('NHITS', c) for c in range(102)])), np.int16)
    prim = fits.PrimaryHDU().header.tostring().encode()
    tabs = {}
    for ext in ['SPECTRAL_CHANNELS', 'WCS-WAVE']:
        hh, hoff, dloc, dl = lay[ext]
        raw = R._range(url, hoff, (dloc - hoff) + dl)
        t = fits.open(io.BytesIO(prim + raw))[1].data
        tabs[ext] = t
    wsub = w.deepcopy()
    wsub.wcs.crpix = w.wcs.crpix - np.array([x0, y0])
    return dict(img=img, nhits=nh, wcs=wsub.to_header().tostring(), box=(y0, y1, x0, x1), npix=npix,
                prim=lay['PRIMARY'][0], chan=tabs['SPECTRAL_CHANNELS'], wave=tabs['WCS-WAVE'], url=url)


def main():
    os.makedirs(OUT, exist_ok=True)
    hp = HEALPix(nside=32, order='nested', frame='icrs')
    rows, man = [], []
    from scipy.ndimage import maximum_filter
    for c in B.CLUSTERS:
        pl = B.patch_list(c)
        ptile = {p['patch']: int(hp.lonlat_to_healpix(p['ra'] * u.deg, p['dec'] * u.deg)) for p in pl}
        for npix in sorted(set(ptile.values())):
            f = os.path.join(OUT, f"{c['name']}_tile{npix}_cube.npz")
            mine = [p for p in pl if ptile[p['patch']] == npix]
            if not os.path.exists(f):
                t0 = time.time()
                d = read_tile_box(npix, [(p['ra'], p['dec']) for p in mine])
                chan = d['chan']
                cols = {n: np.asarray(chan[n]) for n in chan.columns.names}
                np.savez_compressed(f, img=d['img'], nhits=d['nhits'], wcs_header=np.frombuffer(d['wcs'].encode(), np.uint8),
                                    box=np.array(d['box']), npix=d['npix'], patches=np.array([p['patch'] for p in mine]),
                                    **{f'chan_{k}': v for k, v in cols.items() if v.dtype.kind in 'fiu'},
                                    chan_columns=np.array(chan.columns.names),
                                    primary_header=np.frombuffer(d['prim'].tostring().encode(), np.uint8))
                man.append(dict(cluster=c['name'], file=os.path.basename(f), url=d['url'], npix=npix, box=str(d['box']),
                                sec=round(time.time() - t0, 1)))
                print(c['name'], 'tile', npix, [p['patch'] for p in mine], d['img'].shape, f'{time.time()-t0:.0f}s', flush=True)
            z = np.load(f)
            img = z['img']
            w = WCS(fits.Header.fromstring(bytes(z['wcs_header']).decode()))
            med = np.nanmedian(img, 0)
            bkg = np.nanmedian(med)
            mad = 1.4826 * np.nanmedian(np.abs(med - bkg))
            pk = (med == maximum_filter(np.nan_to_num(med, nan=-1e9), size=5)) & (med > bkg + 8 * mad)
            ys, xs = np.where(pk)
            ras, decs = w.all_pix2world(xs, ys, 0)
            for x, y, r_, d_ in zip(xs, ys, ras, decs):
                inp = [p['patch'] for p in mine if abs((r_ - p['ra'] + 180) % 360 - 180) * np.cos(np.radians(d_)) * 3600 < 32 * B.PIX
                       and abs(d_ - p['dec']) * 3600 < 32 * B.PIX]
                if not inp:
                    continue
                sl = img[:, max(y - 1, 0):y + 2, max(x - 1, 0):x + 2]
                ann = img[:, max(y - 6, 0):y + 7, max(x - 6, 0):x + 7]
                b = np.nanmedian(ann.reshape(102, -1), 1)
                spec = np.nansum(sl - b[:, None, None], (1, 2))
                spec[~np.isfinite(sl).any((1, 2)) | ~np.isfinite(b)] = np.nan   # channel not covered in the DR1 cube
                rows.append(dict(cluster=c['name'], tile=npix, ra=float(r_), dec=float(d_), x=int(x), y=int(y),
                                 peak_med_mjysr=float(med[y, x] - bkg), patches=','.join(inp),
                                 n_channels_valid=int(np.isfinite(spec).sum()), spec_3x3_mjysr=spec.astype(np.float32)))
    df = pd.DataFrame(rows)
    df.to_parquet(os.path.join(OUT, 'source_spectra.parquet'))
    if man:
        mf = os.path.join(OUT, 'cube_reads.csv')
        pd.DataFrame(man).to_csv(mf, index=False, mode='a', header=not os.path.exists(mf))
    print('sources', len(df), df.groupby('cluster').size().to_dict())


if __name__ == '__main__':
    main()
