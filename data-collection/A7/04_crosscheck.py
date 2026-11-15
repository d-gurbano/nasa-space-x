"""A7 step 4: cross-check the kete answer key against JPL.
 (a) JPL Horizons, observer 500@-163182 (SPHEREx), one call per object at the frame MJD-AVG.
 (b) JPL sb_ident with the SPHEREx geocentric state from the frame header (xobs), a central box of the
     frame, two-pass (numerically integrated) - compare which objects are found and positions.
"""
import os, sys, json, time, requests
import numpy as np, pandas as pd
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, os.path.join(ROOT, 'code/A2'))
import positions as A2pos
from astropy.coordinates import SkyCoord
import astropy.units as u

OUT = os.path.join(ROOT, 'data/07-answer-keys/answer_key/crosscheck'); os.makedirs(OUT, exist_ok=True)
ak = pd.read_parquet(os.path.join(ROOT, 'data/07-answer-keys/answer_key/known_objects_in_frames.parquet'))
meta = pd.read_parquet(os.path.join(ROOT, 'data/07-answer-keys/frames/frames_meta.parquet')).set_index('key')
ak = ak[ak.on_detector]


def unpack(p):
    """MPC packed -> Horizons command."""
    if p.startswith('C_'):
        import re
        s = p[2:].replace('_', ' ')
        if re.match(r'^\d+[PI]/', s):
            s = s.split('/')[0]
        return 'DES=' + s + ';CAP;NOFRAG'
    if p.isdigit():
        return f'{int(p)};'
    if p[0].isalpha() and p[1:].isdigit() and len(p) == 5:   # A0001 style numbered >= 100000
        return f'{(ord(p[0]) - 55 if p[0].isupper() else ord(p[0]) - 61) * 10000 + int(p[1:])};'
    if p[0] == '~':
        import string
        al = string.digits + string.ascii_uppercase + string.ascii_lowercase
        n = 0
        for c in p[1:]:
            n = n * 62 + al.index(c)
        return f'{620000 + n};'
    # provisional packed e.g. K26R39B -> 2026 RB39
    cent = {'I': 18, 'J': 19, 'K': 20}[p[0]]
    yr = f'{cent}{p[1:3]}'
    num = p[4:6]; c = num[0]
    n = (int(c) if c.isdigit() else (ord(c) - 55 if c.isupper() else ord(c) - 61)) * 10 + int(num[1])
    return f'DES={yr} {p[3]}{p[6]}{n if n else ""};'


def horizons_check(nobj=60, seed=3):
    rng = np.random.default_rng(seed)
    # stratified: bright MBAs, faint MBAs, NEO-like fast movers, comets
    ak2 = ak.copy()
    picks = []
    for mask, n in [((ak2.V_pred < 17) & (ak2.kind == 'asteroid'), 15), ((ak2.V_pred > 19) & (ak2.V_pred < 21), 15),
                    ((ak2.rate_arcsec_min > 3) & (ak2.kind == 'asteroid'), 15), (ak2.kind == 'comet', 10),
                    ((ak2.field_class != 'ecliptic') & (ak2.kind == 'asteroid'), 5)]:
        c = ak2[mask]
        if len(c):
            picks.append(c.iloc[rng.choice(len(c), min(n, len(c)), replace=False)])
    S = pd.concat(picks).drop_duplicates(['key', 'packed'])
    rows = []
    for r in S.itertuples():
        cmd = unpack(r.packed)
        jd = A2pos.utc_mjd_to_tdb_jd([getattr(r, '_19') if False else meta.loc[r.key, 'MJD-AVG']])[0]
        try:
            h = A2pos._predict_horizons(cmd, np.array([jd]), 'spherex').iloc[0]
            c1 = SkyCoord(r.ra_deg * u.deg, r.dec_deg * u.deg); c2 = SkyCoord(float(h.ra_deg) * u.deg, float(h.dec_deg) * u.deg)
            rows.append(dict(key=r.key, packed=r.packed, name=r.name, kind=r.kind, cmd=cmd, V_kete=r.V_pred,
                             V_horizons=pd.to_numeric(h.get('vmag'), errors='coerce'), rate_arcsec_min=r.rate_arcsec_min,
                             delta_au=r.delta_au, sep_arcsec=c1.separation(c2).arcsec,
                             sigma3_ra=pd.to_numeric(h.get('sigma_ra_3s_arcsec'), errors='coerce'),
                             sigma3_dec=pd.to_numeric(h.get('sigma_dec_3s_arcsec'), errors='coerce')))
        except Exception as e:
            rows.append(dict(key=r.key, packed=r.packed, name=r.name, kind=r.kind, cmd=cmd, error=str(e)[:300]))
        time.sleep(0.5)
    df = pd.DataFrame(rows); df.to_csv(os.path.join(OUT, 'kete_vs_horizons.csv'), index=False)
    ok = df[df.sep_arcsec.notna()] if 'sep_arcsec' in df else df.iloc[:0]
    print('horizons checked', len(df), 'ok', len(ok))
    if len(ok):
        print(ok.groupby('kind').sep_arcsec.describe())
        print('dV', (ok.V_kete - ok.V_horizons).describe())
    return df


def hms(ra):
    h = ra / 15; H = int(h); m = (h - H) * 60; M = int(m); s = (m - M) * 60
    return f'{H:02d}-{M:02d}-{s:05.2f}'


def dms(d):
    sg = 'M' if d < 0 else ''; d = abs(d); D = int(d); m = (d - D) * 60; M = int(m); s = (m - M) * 60
    return f'{sg}{D:02d}-{M:02d}-{s:04.1f}'


def sbident_check(nframes=8, hw=1.0, vlim=20.5):
    sm = pd.read_csv(os.path.join(ROOT, 'data/07-answer-keys/answer_key/frame_summary.csv'))
    keys = list(sm[sm.field_class == 'ecliptic'].sample(6, random_state=1).key) + \
        list(sm[sm.field_class == 'mid'].sample(2, random_state=1).key)
    rows = []
    for key in keys[:nframes]:
        m = meta.loc[key]
        from astropy.io import fits
        from astropy.wcs import WCS
        w = WCS(fits.Header.fromstring(m['image_header']), relax=True, key=' ')
        rc, dc = w.all_pix2world([[1019.5, 1019.5]], 0)[0]
        jd_utc = float(m['MJD-AVG']) + 2400000.5
        xobs = ','.join(f'{float(m[k]):.6f}' for k in ['X_SC', 'Y_SC', 'Z_SC', 'VX_SC', 'VY_SC', 'VZ_SC'])
        p = {'xobs': xobs, 'obs-time': f'{jd_utc:.6f}', 'fov-ra-center': hms(rc), 'fov-dec-center': dms(dc),
             'fov-ra-hwidth': hw / np.cos(np.radians(dc)), 'fov-dec-hwidth': hw, 'two-pass': 'true',
             'suppress-first-pass': 'true', 'vmag-lim': vlim, 'mag-required': 'true'}
        t0 = time.time(); j = None
        for k in range(3):
            try:
                r = requests.get('https://ssd-api.jpl.nasa.gov/sb_ident.api', params=p, timeout=300)
                if r.status_code == 200:
                    j = r.json(); break
                err = f'HTTP {r.status_code} {r.text[:300]}'
            except Exception as e:
                err = repr(e)
            time.sleep(10 * (k + 1))
        json.dump(j or {'error': err, 'params': p}, open(os.path.join(OUT, f"sbident_{m['OBSID']}_D{int(m['DETECTOR'])}.json"), 'w'))
        if j is None:
            rows.append(dict(key=key, error=err)); continue
        flds = j.get('fields_second', []); data = j.get('data_second_pass', [])
        sb = pd.DataFrame(data, columns=flds) if data else pd.DataFrame(columns=flds)
        # our objects inside the same RA/Dec box and V < vlim
        a = ak[ak.key == key]
        c = SkyCoord(a.ra_deg.values * u.deg, a.dec_deg.values * u.deg)
        c0 = SkyCoord(rc * u.deg, dc * u.deg)
        dra, ddec = c0.spherical_offsets_to(c)
        inbox = (np.abs(ddec.deg) < hw * 0.98) & (np.abs(dra.deg) < hw * 0.98) & (a.V_pred.values < vlim - 0.3)
        ours = a[inbox]
        matched = 0; seps = []
        if len(sb):
            import re as _re
            def _dec(x):
                m_ = _re.match(r"([+-]?)(\d+)\s+(\d+)'([\d.]+)", x.strip())
                v = int(m_.group(2)) + int(m_.group(3)) / 60 + float(m_.group(4)) / 3600
                return -v if m_.group(1) == '-' else v
            def _ra(x):
                a, b, c = x.split(':'); return 15 * (int(a) + int(b) / 60 + float(c) / 3600)
            sc = SkyCoord(np.array([_ra(x) for x in sb.iloc[:, 1]]) * u.deg, np.array([_dec(x) for x in sb.iloc[:, 2]]) * u.deg)
            if len(ours):
                co = SkyCoord(ours.ra_deg.values * u.deg, ours.dec_deg.values * u.deg)
                idx, d2, _ = co.match_to_catalog_sky(sc)
                good = d2.arcsec < 30
                matched = int(good.sum()); seps = d2.arcsec[good]
        rows.append(dict(key=key, obsid=m['OBSID'], det=int(m['DETECTOR']), n_sbident=len(sb), n_kete_box=len(ours),
                         n_matched_30arcsec=matched, median_sep_arcsec=float(np.median(seps)) if len(seps) else np.nan,
                         p95_sep_arcsec=float(np.percentile(seps, 95)) if len(seps) else np.nan, t_s=round(time.time() - t0, 1)))
        print(rows[-1], flush=True)
        time.sleep(3)
    df = pd.DataFrame(rows); df.to_csv(os.path.join(OUT, 'kete_vs_sbident.csv'), index=False)
    return df


if __name__ == '__main__':
    what = sys.argv[1] if len(sys.argv) > 1 else 'both'
    if what in ('both', 'horizons'):
        horizons_check()
    if what in ('both', 'sbident'):
        sbident_check()
