"""A2 test: kete vs JPL Horizons astrometric RA/Dec for 3 asteroids at SPHEREx (and NEOWISE) epochs.
Reports separations in arcsec: kete-vs-Horizons for each observer, and geocentric-vs-spacecraft parallax."""
import os, sys, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(__file__))
import positions as P, kete
out = os.path.join(P.ORB, 'tests')
def sep(r1, d1, r2, d2):
    r1, d1, r2, d2 = map(np.radians, (r1, d1, r2, d2))
    c = np.sin(d1) * np.sin(d2) + np.cos(d1) * np.cos(d2) * np.cos(r1 - r2)
    return np.degrees(np.arccos(np.clip(c, -1, 1))) * 3600
# SPHEREx epochs (MJD UTC): 2025-08-15 12:00, 2025-11-01 03:17, 2026-06-09 07:30 ; NEOWISE: 2020-07-15 00:00
spx = P.utc_mjd_to_tdb_jd([60902.5, 60980.137, 61200.3125])
wise = P.utc_mjd_to_tdb_jd([59045.0])
rows = []
for obj in ['433', '3200', '1566']:
    for obsr, jds in [('spherex', spx), ('neowise', wise)]:
        kk = P.predict(obj, jds, obsr, n_samples=0)
        kg = P.predict(obj, jds, 'geocenter', n_samples=0)
        hh = P.predict(obj, jds, obsr, engine='horizons')
        hg = P.predict(obj, jds, 'geocenter', engine='horizons')
        for i, jd in enumerate(np.sort(jds)):
            r = dict(object=obj, observer=obsr, jd_tdb=jd, utc=kete.Time(jd).iso, delta_au=kk.delta_au[i], vmag_kete=kk.vmag[i], vmag_hz=hh.vmag[i],
                     kete_vs_horizons_sc_arcsec=sep(kk.ra_deg[i], kk.dec_deg[i], hh.ra_deg[i], hh.dec_deg[i]),
                     kete_vs_horizons_geo_arcsec=sep(kg.ra_deg[i], kg.dec_deg[i], hg.ra_deg[i], hg.dec_deg[i]),
                     geo_vs_sc_parallax_arcsec_horizons=sep(hg.ra_deg[i], hg.dec_deg[i], hh.ra_deg[i], hh.dec_deg[i]),
                     hz_sigma_ra_3s=hh.sigma_ra_3s_arcsec[i], hz_sigma_dec_3s=hh.sigma_dec_3s_arcsec[i])
            if obsr == 'spherex' and jd < 2461018.9:  # kete bundled unofficial SPHEREx kernel
                fov = kete.OmniDirectionalFOV(kete.spice.get_state('spherex', jd))
                props = P._fetch_props(obj)
                s = kete.fov_state_check([props.state], [fov], include_asteroids=True)[0]
                ra, dec = s.ra_dec_with_rates[0][:2]
                r['kete_bundled_kernel_vs_horizons_arcsec'] = sep(ra, dec, hh.ra_deg[i], hh.dec_deg[i])
                g = P._spherex_geo(jd); e = kete.spice.get_state('earth', jd); k = kete.spice.get_state('spherex', jd)
                dk = np.array(list(k.pos)) - np.array(list(e.pos))
                gv = np.array(list(kete.Vector(list(g[0] / P.AU_KM), kete.Frames.Equatorial).as_ecliptic))
                r['bundled_kernel_vs_horizons_sc_pos_km'] = np.linalg.norm(dk - gv) * P.AU_KM
            rows.append(r); print(r, flush=True)
df = pd.DataFrame(rows); df.to_csv(f'{out}/kete_vs_horizons.csv', index=False)
print(df.round(4).to_string())
