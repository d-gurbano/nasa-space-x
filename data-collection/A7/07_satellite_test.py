"""A7 step 7: can catalogued satellites (Starlink etc.) cross SPHEREx frames?

Test A (geometry, no orbit errors): for every selected frame, take the SPHEREx position from the header
  (X_SC.. at MJD-AVG, geocentric, km) and the line of sight through the 4 corners and the centre (WCS).
  The lowest altitude any point on that ray reaches is the lowest altitude a satellite must have to
  appear in the frame. Compare with the altitude distribution of the CelesTrak catalogue.
Test B (SGP4 with CelesTrak GP of 2026-11-14/15): for the most recent public frames (QR3, early Oct 2026)
  propagate every object in the snapshot over the exposure (1 s steps) and test whether the line of sight
  from SPHEREx falls inside the frame. Elements are ~40 days newer than the frames, so along-track errors
  are large (ESTIMATED tens to hundreds of km for LEO); test B shows which orbits CAN cross, not exact trails.
Also: fraction of Borlaff 2026 simulated detected trails from satellites below SPHEREx (Zenodo data).
"""
import os, sys, glob, json, time
import numpy as np, pandas as pd
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, os.path.join(ROOT, 'code/A0'))
from astropy.io import fits
from astropy.wcs import WCS
from astropy.time import Time
import astropy.units as u
from astropy.coordinates import TEME, GCRS, CartesianRepresentation
from sgp4.api import Satrec, SatrecArray, jday
from sgp4 import omm

OUT = os.path.join(ROOT, 'data/07-answer-keys/satellites'); RE = 6378.137
GPD = os.path.join(OUT, 'celestrak_2026-11-15')


def radec2vec(ra, dec):
    ra, dec = np.radians(ra), np.radians(dec)
    return np.stack([np.cos(dec) * np.cos(ra), np.cos(dec) * np.sin(ra), np.sin(dec)], -1)


def ray_min_alt(r0, d):
    t = -(r0 @ d)
    if t <= 0:
        return np.linalg.norm(r0) - RE, 0.0
    return np.linalg.norm(r0 + t * d) - RE, t


def load_catalog():
    sats = {}
    for f in sorted(glob.glob(os.path.join(GPD, 'gp_*.csv'))) + [os.path.join(GPD, 'supgp_starlink.csv')]:
        grp = os.path.basename(f)[:-4]
        with open(f) as fh:
            for rec in omm.parse_csv(fh):
                nid = int(rec['NORAD_CAT_ID'])
                if grp == 'supgp_starlink':
                    key = ('sup', nid)
                else:
                    key = ('gp', nid)
                if key in sats:
                    sats[key]['groups'].add(grp); continue
                s = Satrec()
                rec2 = dict(rec)
                if nid > 339999:   # sgp4init Alpha-5 limit; satnum does not affect propagation
                    rec2['NORAD_CAT_ID'] = '0'
                omm.initialize(s, rec2)
                n = float(rec['MEAN_MOTION']); e = float(rec['ECCENTRICITY'])
                a = (398600.4418 / (n * 2 * np.pi / 86400) ** 2) ** (1 / 3)
                sats[key] = dict(sat=s, name=rec['OBJECT_NAME'], norad=nid, groups={grp}, apogee_km=a * (1 + e) - RE,
                                 perigee_km=a * (1 - e) - RE, epoch=rec['EPOCH'], src=key[0])
    return sats


def test_A(meta):
    rows = []
    for r in meta.to_dict('records'):
        w = WCS(fits.Header.fromstring(r['image_header']), relax=True, key=' ')
        r0 = np.array([r['X_SC'], r['Y_SC'], r['Z_SC']], float)
        pts = np.array([[0, 0], [2039, 0], [2039, 2039], [0, 2039], [1019.5, 1019.5]])
        rd = w.all_pix2world(pts, 0)
        d = radec2vec(rd[:, 0], rd[:, 1])
        mins = [ray_min_alt(r0, di) for di in d]
        zen = np.degrees(np.arccos(d @ (r0 / np.linalg.norm(r0))))
        rows.append(dict(key=r['key'], OBSID=r['OBSID'], det=r['DETECTOR'], mjd=r['MJD-AVG'],
                         sc_alt_km=np.linalg.norm(r0) - RE, min_ray_alt_km=min(m[0] for m in mins),
                         max_zenith_angle_deg=zen.max(), min_zenith_angle_deg=zen.min(),
                         centre_zenith_angle_deg=zen[4], range_at_min_km=mins[int(np.argmin([m[0] for m in mins]))][1]))
    return pd.DataFrame(rows)


def teme_to_gcrs(pos, jd):
    t = Time(jd, format='jd', scale='utc')
    c = TEME(CartesianRepresentation(pos.T * u.km), obstime=t).transform_to(GCRS(obstime=t))
    return c.cartesian.xyz.to(u.km).value.T


def test_B(fr, sats, step_s=1.0):
    """fr: one frame row (with image_header). Returns list of crossing objects."""
    w = WCS(fits.Header.fromstring(fr['image_header']), relax=True, key=' ')
    beg, end = float(fr['MJD-BEG']), float(fr['MJD-END'])
    ts = np.arange(beg, end + 1e-9, step_s / 86400)
    # SPHEREx position: linear-in-time Hermite from START/MID/END header vectors (quadratic fit)
    tt = np.array([beg, float(fr['MJD-AVG']), end])
    P = np.array([[fr[f'{c}_SC_START'] for c in 'XYZ'], [fr[f'{c}_SC'] for c in 'XYZ'], [fr[f'{c}_SC_END'] for c in 'XYZ']], float)
    sc = np.stack([np.polyval(np.polyfit(tt - tt[1], P[:, k], 2), ts - tt[1]) for k in range(3)], -1)
    keys = list(sats.keys())
    arr = SatrecArray([sats[k]['sat'] for k in keys])
    jd = ts + 2400000.5
    jd_i = np.floor(jd); jd_f = jd - jd_i
    e, rr, vv = arr.sgp4(jd_i, jd_f)       # (nsat, nt, 3) TEME
    ok = (e == 0)
    # TEME->GCRS rotation is nearly constant over 2 minutes: compute once at mid-time via 3 basis vectors
    Rm = teme_to_gcrs(np.eye(3) * 7000.0, jd[len(jd) // 2]) / 7000.0   # rows = images of basis vectors
    g = rr @ Rm                               # (nsat, nt, 3) GCRS km
    los = g - sc[None, :, :]
    rng_km = np.linalg.norm(los, axis=-1)
    u_ = los / rng_km[..., None]
    ra = np.degrees(np.arctan2(u_[..., 1], u_[..., 0])) % 360; dec = np.degrees(np.arcsin(np.clip(u_[..., 2], -1, 1)))
    # quick cone prefilter around the frame centre (radius 3 deg), then exact pixel test
    cra, cdec = w.all_pix2world([[1019.5, 1019.5]], 0)[0]
    c0 = radec2vec(cra, cdec)
    cosd = u_ @ c0
    cand = np.where(((cosd > np.cos(np.radians(3.0))) & ok).any(1))[0]
    out = []
    for i in cand:
        m = (cosd[i] > np.cos(np.radians(3.0))) & ok[i]
        px = w.all_world2pix(np.c_[ra[i, m], dec[i, m]], 0)
        inside = (px[:, 0] >= 0) & (px[:, 0] < 2040) & (px[:, 1] >= 0) & (px[:, 1] < 2040)
        if inside.any():
            s = sats[keys[i]]
            j = np.where(m)[0][inside]
            alt = np.linalg.norm(g[i, j], axis=-1) - RE
            out.append(dict(key=fr['key'], OBSID=fr['OBSID'], det=fr['DETECTOR'], norad=s['norad'], name=s['name'],
                            elements=s['src'], groups='|'.join(sorted(s['groups'])), n_samples_inside=int(inside.sum()),
                            sat_alt_km=float(np.median(alt)), range_km=float(np.median(rng_km[i, j])),
                            apogee_km=s['apogee_km'], perigee_km=s['perigee_km'], gp_epoch=s['epoch'],
                            x_first=float(px[inside][0, 0]), y_first=float(px[inside][0, 1]),
                            x_last=float(px[inside][-1, 0]), y_last=float(px[inside][-1, 1])))
    return out, len(cand)


def recent_frames(n_each=3):
    """Most recent public frames: QR3 SIA2 at NEP/SEP deep fields and the ecliptic, Sep 25 - Oct 6 2026."""
    from rewind import sia2_query, l2_layout
    rows = []
    for ra, dec, coll in [(270.0, 66.56, 'spherex_qr3_deep'), (90.0, -66.56, 'spherex_qr3_deep'), (270.0, 66.56, 'spherex_qr3'),
                          (90.0, -66.56, 'spherex_qr3')]:
        try:
            df = sia2_query(ra, dec, coll, 0.01, time_mjd=(61305, 61330))
        except Exception as e:
            print('sia2 fail', e); continue
        df = df.sort_values('t_min', ascending=False)
        df = df[df.energy_bandpassname.isin(['SPHEREx-D1', 'SPHEREx-D2', 'SPHEREx-D3'])].head(n_each)
        for r in df.itertuples():
            rows.append(json.loads(r.cloud_access)['aws']['key'])
        time.sleep(1)
    out = []
    for k in dict.fromkeys(rows):
        url, lay, st = l2_layout('ibe/data/spherex/' + k)
        h = lay['IMAGE'][0]
        d = {kk: h.get(kk) for kk in ['OBSID', 'DETECTOR', 'MJD-BEG', 'MJD-AVG', 'MJD-END', 'X_SC', 'Y_SC', 'Z_SC',
                                       'X_SC_START', 'Y_SC_START', 'Z_SC_START', 'X_SC_END', 'Y_SC_END', 'Z_SC_END']}
        d.update(key=k, image_header=h.tostring(), SATSTRKS=h.get('L2 SATSTRKS', h.get('SATSTRKS')))
        out.append(d)
    return pd.DataFrame(out)


def main():
    meta = pd.read_parquet(os.path.join(ROOT, 'data/07-answer-keys/frames/frames_meta.parquet'))
    A = test_A(meta)
    A.to_csv(os.path.join(OUT, 'testA_frame_min_line_of_sight_altitude.csv'), index=False)
    sats = load_catalog()
    cat = pd.DataFrame([{k: v for k, v in s.items() if k != 'sat'} | {'groups': '|'.join(sorted(s['groups']))} for s in sats.values()])
    cat.to_csv(os.path.join(OUT, 'catalog_orbit_summary.csv'), index=False)
    gp = cat[cat.src == 'gp']
    star = gp[gp.groups.str.contains('starlink')]
    print('Test A: frames', len(A), 'SC alt km', A.sc_alt_km.describe().round(1).to_dict())
    print('min ray alt km', A.min_ray_alt_km.describe().round(1).to_dict())
    print('max zenith angle deg', A.max_zenith_angle_deg.describe().round(1).to_dict())
    print('catalog objects', len(gp), 'starlink', len(star), 'starlink apogee max', star.apogee_km.max(),
          'p99', star.apogee_km.quantile(0.99))
    print('frames whose lowest ray altitude is below the highest Starlink apogee:',
          int((A.min_ray_alt_km < star.apogee_km.max()).sum()))
    B = recent_frames()
    B.drop(columns=['image_header']).to_csv(os.path.join(OUT, 'testB_frames.csv'), index=False)
    res = []; summ = []
    for fr in B.to_dict('records'):
        t0 = time.time()
        o, nc = test_B(fr, sats)
        res += o
        r0 = np.array([fr['X_SC'], fr['Y_SC'], fr['Z_SC']], float)
        summ.append(dict(key=fr['key'], OBSID=fr['OBSID'], det=fr['DETECTOR'], mjd=fr['MJD-AVG'], header_SATSTRKS=fr['SATSTRKS'],
                         n_crossing=len(o), n_starlink=sum('starlink' in x['groups'] for x in o), n_candidates_cone=nc,
                         sc_alt_km=np.linalg.norm(r0) - RE, t_s=round(time.time() - t0, 1)))
        print(summ[-1], flush=True)
    pd.DataFrame(res).to_csv(os.path.join(OUT, 'testB_crossings.csv'), index=False)
    pd.DataFrame(summ).to_csv(os.path.join(OUT, 'testB_summary.csv'), index=False)
    # Borlaff simulation check
    s = pd.read_csv(os.path.join(ROOT, 'data/07-answer-keys/junk/trails_borlaff2026/SPHEREx_per_trail_database.csv'),
                    usecols=['altitude_telescope', 'altitude_satellites', 'bool_detected', 'limb_angle'])
    d = s[s.bool_detected == True]
    below = d.altitude_satellites / 1000 < d.altitude_telescope
    json.dump(dict(sim_detected_trails=int(len(d)), from_below_telescope=int(below.sum()), frac=float(below.mean())),
              open(os.path.join(OUT, 'borlaff_sim_below_altitude.json'), 'w'))


if __name__ == '__main__':
    main()
