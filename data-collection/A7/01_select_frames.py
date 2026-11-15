"""A7 step 1: choose a representative set of SPHEREx L2 frames (ecliptic, mid-latitude, poles;
QR3 and DR1) with IRSA SIA2, then read each frame's headers + WCS-WAVE table with HTTPS range
reads from the public S3 bucket (no full downloads).

Outputs (data/07-answer-keys/frames/):
  sia2_<field>_<coll>.parquet   raw SIA2 rows per field
  frames_selected.parquet       chosen frames (key, field, ecliptic latitude class, release, det, t_min)
  frames_meta.parquet           header info: MJD-AVG, X_SC.., WCS header string, wave table (json)
"""
import os, sys, json, time, io
import numpy as np, pandas as pd
from concurrent.futures import ThreadPoolExecutor
from astropy.coordinates import SkyCoord, GeocentricTrueEcliptic
import astropy.units as u
from astropy.io import fits

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, os.path.join(ROOT, 'code/A0'))
from rewind import sia2_query, l2_layout, _range  # noqa

OUT = os.path.join(ROOT, 'data/07-answer-keys/frames')
os.makedirs(OUT, exist_ok=True)

# (name, class, ecliptic lon, ecliptic lat)
FIELDS = [
    ('ecl_L000', 'ecliptic', 0, 0), ('ecl_L060', 'ecliptic', 60, 0), ('ecl_L120', 'ecliptic', 120, 0),
    ('ecl_L180', 'ecliptic', 180, 0), ('ecl_L225', 'ecliptic', 225, 0), ('ecl_L330', 'ecliptic', 330, 0),
    ('mid_L090_p30', 'mid', 90, 30), ('mid_L210_p30', 'mid', 210, 30),
    ('mid_L030_m30', 'mid', 30, -30), ('mid_L150_m30', 'mid', 150, -30),
    ('NEP', 'pole', 0, 90), ('SEP', 'pole', 0, -90),
]
COLLS = ['spherex_dr1', 'spherex_qr3']
PER = {'ecliptic': 30, 'mid': 22, 'pole': 30}   # frames per field per release


def radec(lon, lat):
    c = SkyCoord(lon=lon * u.deg, lat=lat * u.deg, frame=GeocentricTrueEcliptic(equinox='J2000'))
    i = c.icrs
    return float(i.ra.deg), float(i.dec.deg)


def select():
    rows = []
    for name, cls, lon, lat in FIELDS:
        ra, dec = radec(lon, lat)
        for coll in COLLS:
            fn = os.path.join(OUT, f'sia2_{name}_{coll}.parquet')
            if os.path.exists(fn):
                df = pd.read_parquet(fn)
            else:
                for k in range(4):
                    try:
                        df = sia2_query(ra, dec, coll, 0.001, maxrec=20000); break
                    except Exception as e:
                        print('retry', name, coll, e); time.sleep(10 * (k + 1))
                df = df[[c for c in df.columns if df[c].dtype != object or c in (
                    'obs_id', 'energy_bandpassname', 'access_url', 'cloud_access', 's_region', 'obs_collection',
                    'dataproduct_subtype', 'proposal_project', 'target_name', 'obs_intent')]]
                df.to_parquet(fn)
                time.sleep(1.5)
            df = df[df.dataproduct_subtype.astype(str).str.contains('level2|l2b|spectral_image|image', case=False) |
                    True]
            print(name, coll, len(df), 'frames at field centre', round(ra, 3), round(dec, 3))
            if len(df) == 0:
                continue
            df = df.sort_values('t_min').reset_index(drop=True)
            n = min(PER[cls], len(df))
            idx = np.unique(np.linspace(0, len(df) - 1, n).round().astype(int))
            s = df.iloc[idx].copy()
            s['field'] = name; s['field_class'] = cls; s['field_ra'] = ra; s['field_dec'] = dec
            s['release'] = coll.replace('spherex_', '')
            s['key'] = s.cloud_access.map(lambda j: json.loads(j)['aws']['key'])
            s['detector'] = s.energy_bandpassname.str[-1].astype(int)
            rows.append(s)
    sel = pd.concat(rows, ignore_index=True).drop_duplicates('key').reset_index(drop=True)
    keep = ['key', 'obs_id', 'detector', 'release', 'field', 'field_class', 'field_ra', 'field_dec', 't_min', 't_max',
            's_ra', 's_dec', 'access_url', 's_region', 'em_min', 'em_max']
    sel = sel[[c for c in keep if c in sel.columns]]
    sel.to_parquet(os.path.join(OUT, 'frames_selected.parquet'))
    print('selected', len(sel), sel.groupby(['field_class', 'release']).size().to_dict())
    return sel


HK = ['OBSID', 'DETECTOR', 'MJD-BEG', 'MJD-AVG', 'MJD-END', 'XPOSURE', 'X_SC', 'Y_SC', 'Z_SC', 'VX_SC', 'VY_SC',
      'VZ_SC', 'PSF_FWHM', 'OMEGA_MEDIAN', 'FINAST', 'L2DQAFLG', 'SPS_FLAGS', 'CRVAL1', 'CRVAL2', 'NAXIS1', 'NAXIS2']


def meta_one(key):
    uri = 'ibe/data/spherex/' + key
    url, lay, stats = l2_layout(uri)
    h0 = lay['PRIMARY'][0]; h = lay['IMAGE'][0]
    d = {'key': key}
    for k in HK:
        d[k] = h.get(k, h0.get(k))
    # spacecraft keywords may live in primary
    for k in list(h0.keys()) + list(h.keys()):
        if ('_SC' in k or k.startswith('SC_') or 'SPACECR' in k) and k not in d:
            d[k] = h.get(k, h0.get(k))
    d['image_header'] = h.tostring()
    d['primary_header'] = h0.tostring()
    whh, woff, wdat, wlen = lay['WCS-WAVE']
    raw = _range(url, woff, (wdat - woff) + wlen)
    prim = fits.PrimaryHDU().header.tostring().encode()
    wt = fits.open(io.BytesIO(prim + raw))[1].data
    d['wave_X'] = json.dumps(np.asarray(wt['X']).ravel().tolist())
    d['wave_Y'] = json.dumps(np.asarray(wt['Y']).ravel().tolist())
    d['wave_V'] = json.dumps(np.asarray(wt['VALUES']).ravel().tolist())
    d['wave_shape'] = json.dumps(list(np.asarray(wt['VALUES']).shape))
    d['flags_hdr'] = lay['FLAGS'][0].tostring()
    d['bytes_read'] = stats['bytes'] + len(raw)
    return d


def meta(sel):
    fn = os.path.join(OUT, 'frames_meta.parquet')
    done = pd.read_parquet(fn) if os.path.exists(fn) else pd.DataFrame(columns=['key'])
    todo = [k for k in sel.key if k not in set(done.key)]
    print('header reads to do', len(todo))
    out = []
    def safe(k):
        for t in range(3):
            try:
                return meta_one(k)
            except Exception as e:
                err = repr(e); time.sleep(3 * (t + 1))
        return {'key': k, 'error': err}
    t0 = time.time()
    with ThreadPoolExecutor(6) as ex:
        for i, r in enumerate(ex.map(safe, todo)):
            out.append(r)
            if i % 50 == 0:
                print(i, round(time.time() - t0), 's', flush=True)
    m = pd.concat([done, pd.DataFrame(out)], ignore_index=True)
    m.to_parquet(fn)
    print('meta rows', len(m), 'errors', m.get('error', pd.Series(dtype=str)).notna().sum(), 'time', round(time.time() - t0))


if __name__ == '__main__':
    sel = select()
    meta(sel)
