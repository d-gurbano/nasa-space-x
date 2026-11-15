"""A8 - known asteroids and comets inside every A8 patch-epoch (kete, observer = SPHEREx from the frame header).

Population: MPCORB.DAT (data/02-orbits/mpc, parsed by code/A7/mpcorb.py, cached by A7) + MPC CometEls.txt.
Observer: Earth (kete DE440s SPICE) + the frame header geocentric spacecraft vector X_SC/Y_SC/Z_SC (km, ICRF
equatorial, at MJD-AVG). Times: header MJD-AVG (UTC) -> TDB. Light-time handled by kete.fov_state_check.
Cone FOV of radius CONE_DEG around each cluster centre (covers all 9 patches + margin); then every hit is mapped
to native-cutout and aligned-grid pixel coordinates of each patch with the frame WCS.

  python code/A8/known_movers.py      -> data/08-ai-training/index/known_movers.parquet
"""
import os, sys, json, glob, time
import numpy as np, pandas as pd
from astropy.io import fits
from astropy.wcs import WCS
from astropy.time import Time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, os.path.join(ROOT, 'code/A7'))
sys.path.insert(0, os.path.join(ROOT, 'code/A8'))
from mpcorb import load_mpcorb, load_comets, to_states, kete  # noqa: E402  (A7 helper, read-only use)
import build_patches as B  # noqa: E402

AU_KM = 149597870.7
CONE_DEG = 0.40
IDX = B.IDX


def frame_table():
    """Consolidated frames of the current dataset version (index/frames.parquet + patch_epochs.parquet)."""
    fr = pd.read_parquet(os.path.join(IDX, 'frames.parquet'))
    pe = pd.read_parquet(os.path.join(IDX, 'patch_epochs.parquet'))
    pp = {k: g[['patch', 'x0_full', 'y0_full']].to_dict('records') for k, g in pe.groupby('frame_id')}
    rows = []
    for r in fr.to_dict('records'):
        r['patches'] = pp.get(r['frame_id'], [])
        r['det'] = int(r['det'])
        rows.append(r)
    return rows


def observer(fm):
    jd = Time(fm['MJD-AVG'], format='mjd', scale='utc').tdb.jd
    e = kete.spice.get_state('earth', jd)
    p = kete.Vector([fm['X_SC'] / AU_KM, fm['Y_SC'] / AU_KM, fm['Z_SC'] / AU_KM], kete.Frames.Equatorial).as_ecliptic
    v = kete.Vector([fm['VX_SC'] * 86400 / AU_KM, fm['VY_SC'] * 86400 / AU_KM, fm['VZ_SC'] * 86400 / AU_KM],
                    kete.Frames.Equatorial).as_ecliptic
    return kete.State('SPHEREx', jd, e.pos + p, e.vel + v, kete.Frames.Ecliptic, 10), jd


def hg_mag(H, G, r, d, ph):
    t = np.tan(ph / 2)
    p1 = np.exp(-3.33 * t ** 0.63)
    p2 = np.exp(-1.87 * t ** 1.22)
    return H + 5 * np.log10(r * d) - 2.5 * np.log10((1 - G) * p1 + G * p2)


def main():
    t0 = time.time()
    frames = frame_table()
    print('frames', len(frames), flush=True)
    cl = {c['name']: c for c in B.CLUSTERS}
    df = load_mpcorb()
    com = load_comets()
    # pole cones only see objects that can reach |ecliptic latitude| > 70 deg from near Earth (upper bound,
    # z <= r sin i, lateral distance >= sqrt(r^2 - z^2) - 1.017 AU); NEOs (q < 1.3) are always kept.
    rr = df.q.values[:, None] + (np.clip(df.a.values * (1 + df.ecc.values), 0, 60) - df.q.values)[:, None] * np.linspace(0, 1, 60)[None, :]
    z = rr * np.sin(np.radians(df.incl.values))[:, None]
    lat = np.degrees(np.arctan2(z, np.clip(np.sqrt(np.clip(rr ** 2 - z ** 2, 0, None)) - 1.017, 1e-6, None))).max(1)
    pole_pop = df[(lat > 70) | (df.q < 1.3)]
    print('population all', len(df), 'pole subset', len(pole_pop), 'comets', len(com), flush=True)
    Hmap = dict(zip(df.packed, df.H)); Gmap = dict(zip(df.packed, df.G.fillna(0.15)))
    Hmap.update(dict(zip(com.packed, com.H)))
    out = []
    for role, pop in [('pole', pole_pop), ('other', df)]:
        fr = [f for f in frames if (cl[f['cluster']]['role'] == 'pole') == (role == 'pole')]
        if not fr:
            continue
        fovs, fmap = [], {}
        for f in fr:
            obs, jd = observer(f)
            c = cl[f['cluster']]
            fov = kete.ConeFOV(kete.Vector.from_ra_dec(c['ra'], c['dec']), CONE_DEG, obs)
            fovs.append(fov)
            fmap[round(jd, 9), f['cluster']] = f
        t1 = time.time()
        sts = to_states(pop) + to_states(com)
        jref = min(fv.observer.jd for fv in fovs)
        sts = kete.propagate_n_body(sts, jref)
        # comets: no non-grav model available from CometEls (positions may be off by arcsec-arcmin for active comets)
        sims = kete.fov_state_check(sts, fovs)
        print(role, 'states', len(sts), 'fovs', len(fovs), 'visible sets', len(sims), f'{time.time()-t1:.0f}s', flush=True)
        for s in sims:
            jd = round(s.fov.observer.jd, 9)
            # identify the cluster by the cone pointing
            pv = s.fov.pointing.as_equatorial
            cname = min(cl, key=lambda k: (cl[k]['ra'] - pv.ra) ** 2 * np.cos(np.radians(pv.dec)) ** 2 + (cl[k]['dec'] - pv.dec) ** 2)
            f = fmap.get((jd, cname))
            if f is None:
                continue
            w = WCS(fits.Header.fromstring(f['wcs_header']), relax=True)
            cw = B.cluster_wcs(cl[cname])
            rd = np.array(s.ra_dec_with_rates)
            for i, st in enumerate(s.states):
                ra, dec, dra, ddec = rd[i]
                v = s.obs_vecs[i]
                delta = v.r
                r = st.pos.r
                ph = np.radians(s.phase_angles[i])
                H = Hmap.get(st.desig, np.nan)
                G = Gmap.get(st.desig, 0.15)
                V = hg_mag(H, G, r, delta, ph) if np.isfinite(H) else np.nan
                xf, yf = w.all_world2pix([[ra, dec]], 0)[0]
                cx, cy = cw.all_world2pix([[ra, dec]], 0)[0]
                for p in f['patches']:
                    xn, yn = xf - p['x0_full'], yf - p['y0_full']
                    j, ii = int(p['patch'][-2]), int(p['patch'][-1])
                    xa = cx - (ii - 1) * B.SPACING + (B.NP_AL - 1) / 2
                    ya = cy - (j - 1) * B.SPACING + (B.NP_AL - 1) / 2
                    if -10 <= xn < B.NP_NAT + 10 and -10 <= yn < B.NP_NAT + 10:
                        out.append(dict(patch=p['patch'], cluster=cname, frame_id=f['frame_id'], mjd_avg=f['MJD-AVG'],
                                        det=f['det'], desig=st.desig, kind='comet' if st.desig.startswith('C_') else 'asteroid',
                                        ra=ra, dec=dec, rate_ra_cosdec_arcsec_min=dra * 3600 / 1440,
                                        rate_dec_arcsec_min=ddec * 3600 / 1440, delta_au=delta, r_au=r,
                                        phase_deg=np.degrees(ph), H=H, vmag=V, x_nat=xn, y_nat=yn, x_al=xa, y_al=ya,
                                        in_native=bool(0 <= xn < B.NP_NAT and 0 <= yn < B.NP_NAT),
                                        in_aligned=bool(0 <= xa < B.NP_AL and 0 <= ya < B.NP_AL)))
    km = pd.DataFrame(out)
    km.to_parquet(os.path.join(IDX, 'known_movers.parquet'))
    print('hits', len(km), 'in aligned', int(km.in_aligned.sum()) if len(km) else 0, f'{time.time()-t0:.0f}s')
    if len(km):
        print(km.groupby('cluster').agg(n=('desig', 'size'), nobj=('desig', 'nunique'), vmin=('vmag', 'min')))


if __name__ == '__main__':
    main()
