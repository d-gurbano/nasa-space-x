"""A2 parent-review step 3: for the top-N lost objects (A1 lost_tier L1 if present, else A1 rank order),
get actual SPHEREx frames from IRSA MOST (catalog=spherex, whole mission), then predict SPHEREx-centric
positions with positions.py (kete, SBDB covariance, 300 samples) at each frame MJD-AVG and record the
3-sigma ellipse (arcsec and SPHEREx pixels, 6.15"/px), predicted V, in-frame (nominal) and fraction of
covariance samples inside the detector footprint. Paced: one MOST query at a time, 10 s gap, cached.
Out: data/02-orbits/lost_spherex/lost_top20_frames.csv, lost_top20_summary.csv, most/<des>.tbl"""
import os, sys, time, requests, numpy as np, pandas as pd
from astropy.io import ascii
sys.path.insert(0, os.path.dirname(__file__))
import positions as P
PX = 6.15
N = int(sys.argv[1]) if len(sys.argv) > 1 else 20
root = P.ORB; od = f'{root}/lost_spherex'; md = f'{od}/most'; os.makedirs(md, exist_ok=True)
b = pd.read_csv(f'{root}/../01-targets/lists/b_lost_recovery_shortlist.csv')
if 'lost_tier' in b.columns:
    l1 = b[b.lost_tier.astype(str).str.startswith('L1')]
    b = l1.sort_values('tier_rank') if 'tier_rank' in b.columns else l1
TAG = 'L1top' if 'lost_tier' in pd.read_csv(f'{root}/../01-targets/lists/b_lost_recovery_shortlist.csv', nrows=1).columns else 'top'
top = list(b.designation.astype(str))[:N]
ALIAS = {'128P': '128P-A'}  # A1 full_name 128P/Shoemaker-Holt 1-A; plain '128P' is ambiguous in MOST and SBDB
MOST = 'https://irsa.ipac.caltech.edu/cgi-bin/MOST/nph-most'

def most(des):
    fn = f"{md}/{des.replace('/', '_').replace(' ', '_')}.tbl"
    if not os.path.exists(fn):
        p = dict(catalog='spherex', input_type='name_input', obj_name=ALIAS.get(des, des), obs_begin='2025-04-01', obs_end='2026-11-14', output_mode='Brief')
        for k in range(5):
            try:
                r = requests.get(MOST, params=p, timeout=900)
                if r.status_code == 200 and ('|' in r.text or 'No' in r.text): break
            except Exception as e: print('retry', des, e, flush=True)
            time.sleep(20 * (k + 1))
        open(fn, 'w').write(r.text); time.sleep(10)
    txt = open(fn).read()
    try:
        df = ascii.read(txt, format='ipac').to_pandas()
    except Exception:
        return pd.DataFrame()
    for c in df.columns:
        if df[c].dtype == object: df[c] = df[c].astype(str).str.strip()
    return df

def tan(ra, dec, ra0, dec0):
    ra, dec, ra0, dec0 = map(np.radians, (ra, dec, ra0, dec0))
    c = np.sin(dec0) * np.sin(dec) + np.cos(dec0) * np.cos(dec) * np.cos(ra - ra0)
    x = np.cos(dec) * np.sin(ra - ra0) / c
    y = (np.cos(dec0) * np.sin(dec) - np.sin(dec0) * np.cos(dec) * np.cos(ra - ra0)) / c
    return x, y

def inside(px, py, poly):
    n = len(poly); ins = np.zeros_like(px, dtype=bool)
    for i in range(n):
        x1, y1 = poly[i]; x2, y2 = poly[(i + 1) % n]
        cond = ((y1 > py) != (y2 > py)) & (px < (x2 - x1) * (py - y1) / (y2 - y1 + 1e-300) + x1)
        ins ^= cond
    return ins

def sep(r1, d1, r2, d2):
    r1, d1, r2, d2 = map(np.radians, (r1, d1, r2, d2))
    c = np.sin(d1) * np.sin(d2) + np.cos(d1) * np.cos(d2) * np.cos(r1 - r2)
    return np.degrees(np.arccos(np.clip(c, -1, 1))) * 3600

rows, summ = [], []
_ff, _sf = f'{od}/lost_{TAG}{N}_frames.csv', f'{od}/lost_{TAG}{N}_summary.csv'
if os.path.exists(_sf):  # resume: keep finished objects
    summ = pd.read_csv(_sf).to_dict('records'); rows = pd.read_csv(_ff).to_dict('records') if os.path.exists(_ff) else []
done_objs = {x['object'] for x in summ}
for des in top:
    if des in done_objs: continue
    m = most(des)
    if m.empty or 'mjd_start' not in m:
        summ.append(dict(object=des, n_files=0, note='no MOST frames')); print(des, 'no frames', flush=True); continue
    m['mjd_avg'] = (m.mjd_start.astype(float) + m.mjd_end.astype(float)) / 2
    m['file'] = m.uri.str.split('/').str[-1]
    ut = np.sort(m.mjd_avg.unique())
    jds = P.utc_mjd_to_tdb_jd(ut)
    try:
        pr = P.predict(ALIAS.get(des, des), jds, 'spherex', n_samples=300, return_samples=True)
    except Exception as e:
        summ.append(dict(object=des, n_files=len(m), note=f'predict failed: {e}')); print(des, e); continue
    smp = pr.attrs['samples']; pr['mjd_avg'] = ut
    pr = pr.rename(columns={'vmag': 'vmag_pred'})
    m = m.merge(pr, on='mjd_avg', how='left')
    for r in m.itertuples():
        poly = [tan(getattr(r, f'ra{k}'), getattr(r, f'dec{k}'), r.ra_deg, r.dec_deg) for k in range(1, 5)]
        nom_in = bool(inside(np.array([0.0]), np.array([0.0]), poly)[0])
        s = smp.get(r.jd_tdb)
        frac = np.nan
        if s is not None:
            sx, sy = tan(s[0], s[1], r.ra_deg, r.dec_deg); frac = float(inside(sx, sy, poly).mean())
        rows.append(dict(object=des, frame_key=r.file, observationid=r.observationid, detector=r.productid if 'productid' in m else '',
                         mjd_avg_utc=r.mjd_avg, ra_deg=r.ra_deg, dec_deg=r.dec_deg,
                         sigma_major_3s_arcsec=getattr(r, 'sigma_major_3s_arcsec', np.nan), sigma_minor_3s_arcsec=getattr(r, 'sigma_minor_3s_arcsec', np.nan), pa_major_deg=getattr(r, 'pa_major_deg', np.nan),
                         sigma_major_3s_px=getattr(r, 'sigma_major_3s_arcsec', np.nan) / PX, sigma_minor_3s_px=getattr(r, 'sigma_minor_3s_arcsec', np.nan) / PX,
                         rate_arcsec_per_hr=np.hypot(r.dra_cosdec_deg_per_day, r.ddec_deg_per_day) * 150,
                         delta_au=r.delta_au, vmag_pred=r.vmag_pred, vmag_most=r.vmag,
                         in_frame=nom_in, frac_3s_samples_in_frame=frac,
                         sep_kete_vs_most_arcsec=sep(r.ra_deg, r.dec_deg, r.ra_obj, r.dec_obj)))
    d = pd.DataFrame([x for x in rows if x['object'] == des])
    summ.append(dict(object=des, n_files=len(d), n_exposures=d.observationid.nunique(), n_in_frame=int(d.in_frame.sum()),
                     first_mjd=d.mjd_avg_utc.min(), last_mjd=d.mjd_avg_utc.max(), min_major_3s_px=d.sigma_major_3s_px.min(),
                     median_major_3s_px=d.sigma_major_3s_px.median(), max_major_3s_px=d.sigma_major_3s_px.max(),
                     brightest_vmag=d.vmag_pred.min(), major_3s_px_at_brightest=(d.loc[d.vmag_pred.idxmin(), 'sigma_major_3s_px'] if d.vmag_pred.notna().any() else np.nan),
                     median_sep_vs_most_arcsec=d.sep_kete_vs_most_arcsec.median()))
    print(summ[-1], flush=True)
    pd.DataFrame(rows).to_csv(f'{od}/lost_{TAG}{N}_frames.csv', index=False); pd.DataFrame(summ).to_csv(f'{od}/lost_{TAG}{N}_summary.csv', index=False)
print('DONE')
