"""
Rewind position engine (agent A2).

predict(obj, times, observer='spherex'|'neowise'|'geocenter'|'<MPC code>', engine='kete'|'horizons')
returns a pandas DataFrame with columns:
    jd_tdb, utc_iso, ra_deg, dec_deg, dra_cosdec_deg_per_day, ddec_deg_per_day, delta_au, r_au, phase_deg,
    vmag, sigma_ra_3s_arcsec, sigma_dec_3s_arcsec, sigma_major_3s_arcsec, sigma_minor_3s_arcsec, pa_major_deg
    (PA east of north; uncertainty: covariance sampling for kete, Horizons 3-sigma for horizons)

Observer states:
  geocenter : kete SPICE (DE440s) Earth
  neowise   : kete bundled WISE SPK (NAIF -163), covers 2009-12-14..2011-02-01 and 2013-12-13..2024-09-12
  spherex   : JPL Horizons SPHEREx (-163182, concatenated Space-Track TLEs) geocentric vectors,
              5-min step, cached at data/02-orbits/horizons/spherex_vectors_geo_5min.parquet and
              Hermite-interpolated. Fallback: kete bundled unofficial spherex.bsp (2025-03-12..2025-12-09).

Times: float JD (TDB), astropy Time, or kete.Time. Use utc_mjd_to_tdb_jd() for SPHEREx MJD-UTC header times.
Usage:
    source env.sh; export KETE_CACHE_DIR=$PWD/data/02-orbits/kete-cache
    from code.A2.positions import predict   (or add code/A2 to sys.path)
"""
from __future__ import annotations
import os, io, time as _time
import numpy as np, pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
ORB = os.path.join(ROOT, 'data/02-orbits')
os.environ.setdefault('KETE_CACHE_DIR', os.path.join(ORB, 'kete-cache'))
import kete  # noqa: E402
import requests  # noqa: E402

C_AU_PER_DAY = 173.1446326846693
AU_KM = 149597870.7
SPHEREX_VEC = os.path.join(ORB, 'horizons/spherex_vectors_geo_5min.parquet')
_spx = None


def utc_mjd_to_tdb_jd(mjd_utc):
    return np.array([kete.Time.from_mjd(float(m), scaling='utc').jd for m in np.atleast_1d(mjd_utc)])


def _jd_list(times):
    try:
        from astropy.time import Time as ATime
        if isinstance(times, ATime):
            return np.atleast_1d(times.tdb.jd).astype(float)
    except Exception:
        pass
    if isinstance(times, kete.Time):
        return np.array([times.jd])
    return np.array([t.jd if isinstance(t, kete.Time) else float(t) for t in np.atleast_1d(times)])


def _spherex_geo(jd):
    """Geocentric equatorial (ICRF) position km, velocity km/s of SPHEREx at TDB jd (cubic Hermite)."""
    global _spx
    if _spx is None:
        if not os.path.exists(SPHEREX_VEC):
            return None
        _spx = pd.read_parquet(SPHEREX_VEC)
    t = _spx.jd_tdb.values
    if jd < t[0] or jd > t[-1]:
        return None
    i = min(max(np.searchsorted(t, jd) - 1, 0), len(t) - 2)
    h = (t[i + 1] - t[i]) * 86400.0
    s = (jd - t[i]) * 86400.0 / h
    p0 = _spx.iloc[i][['x', 'y', 'z']].values.astype(float); p1 = _spx.iloc[i + 1][['x', 'y', 'z']].values.astype(float)
    v0 = _spx.iloc[i][['vx', 'vy', 'vz']].values.astype(float); v1 = _spx.iloc[i + 1][['vx', 'vy', 'vz']].values.astype(float)
    h00 = 2 * s**3 - 3 * s**2 + 1; h10 = s**3 - 2 * s**2 + s; h01 = -2 * s**3 + 3 * s**2; h11 = s**3 - s**2
    pos = h00 * p0 + h10 * h * v0 + h01 * p1 + h11 * h * v1
    dh00 = 6 * s**2 - 6 * s; dh10 = 3 * s**2 - 4 * s + 1; dh01 = -6 * s**2 + 6 * s; dh11 = 3 * s**2 - 2 * s
    vel = (dh00 * p0 + dh10 * h * v0 + dh01 * p1 + dh11 * h * v1) / h
    return pos, vel


def observer_state(observer: str, jd: float) -> kete.State:
    """Heliocentric ecliptic kete.State of the observer at TDB jd."""
    o = observer.lower()
    if o in ('geocenter', 'earth', '500'):
        return kete.spice.get_state('earth', jd)
    if o in ('neowise', 'wise', 'c51', '-163'):
        return kete.spice.get_state('wise', jd)
    if o in ('spherex', '-163182'):
        g = _spherex_geo(jd)
        if g is None:  # fallback to kete's unofficial reconstructed kernel
            return kete.spice.get_state('spherex', jd)
        earth = kete.spice.get_state('earth', jd)
        dp = kete.Vector(list(g[0] / AU_KM), kete.Frames.Equatorial).as_ecliptic
        dv = kete.Vector(list(g[1] * 86400.0 / AU_KM), kete.Frames.Equatorial).as_ecliptic
        pos = [earth.pos[k] + dp[k] for k in range(3)]
        vel = [earth.vel[k] + dv[k] for k in range(3)]
        return kete.State('spherex', jd, pos, vel, kete.Frames.Ecliptic, 10)
    # MPC ground observatory code
    lat, lon, elev, name = kete.mpc.find_obs_code(observer)[:4]
    return kete.spice.earth_pos_to_ecliptic(jd, lat, lon, elev, name)


def _hg_mag(H, G, r, delta, phase_rad):
    if H is None or not np.isfinite(H):
        return np.nan
    G = 0.15 if (G is None or not np.isfinite(G)) else G
    phi1 = np.exp(-3.33 * np.tan(phase_rad / 2) ** 0.63)
    phi2 = np.exp(-1.87 * np.tan(phase_rad / 2) ** 1.22)
    return H + 5 * np.log10(r * delta) - 2.5 * np.log10((1 - G) * phi1 + G * phi2)


def _comet_m1k1(props):
    try:
        pp = {x['name']: x['value'] for x in props.json.get('phys_par', [])}
        if pp.get('M1') is not None:
            return float(pp['M1']), float(pp.get('K1') or 10.0)
    except Exception:
        pass
    return None


def _fetch_props(obj, update_cache=False):
    for k in range(5):
        try:
            return kete.HorizonsProperties.fetch(obj, update_cache=update_cache)
        except ValueError as e:
            if k == 4:
                raise
            _time.sleep(5 * (k + 1))


def predict(obj: str, times, observer: str = 'spherex', engine: str = 'kete', n_samples: int = 200,
            include_asteroids: bool = True, update_cache: bool = False, props=None, state=None,
            return_samples: bool = False) -> pd.DataFrame:
    """Predict astrometric (light-time corrected) RA/Dec of obj as seen from observer at TDB times.
    engine='kete': SBDB orbit via kete.HorizonsProperties (cached), n-body propagation; uncertainty from
                   n_samples covariance draws (3-sigma = 3 x sample std, arcsec). Pass state= to use a custom
                   fitted kete.State (e.g. a precovery-improved orbit), then no samples are drawn.
    engine='horizons': JPL Horizons observer table (quantities 1,9,36), center SPHEREx (-163182), WISE (-163),
                   geocenter (500@399) or MPC code."""
    jds = _jd_list(times)
    if engine == 'horizons':
        return _predict_horizons(obj, jds, observer)
    if state is None:
        props = props or _fetch_props(obj, update_cache)
        states = [props.state]
        ngs = [props.non_grav]
        if n_samples:
            try:
                ss, nn = props.sample(n_samples, seed=42)
                states += list(ss); ngs += list(nn)
            except Exception:
                pass
        H = props.h_mag; G = props.g_phase
        M1K1 = _comet_m1k1(props)
    else:
        M1K1 = None
        states = [state]; ngs = [None]; H = props.h_mag if props else np.nan; G = props.g_phase if props else np.nan
    non_gravs = ngs if any(n is not None for n in ngs) else None
    ep = states[0].jd
    if any(abs(st.jd - ep) > 1e-9 for st in states):  # samples may sit at the covariance epoch
        states = [st if abs(st.jd - ep) < 1e-9 else kete.propagate_n_body([st], ep, include_asteroids=include_asteroids,
                  non_gravs=[ngs[i]] if ngs[i] is not None else None)[0] for i, st in enumerate(states)]
    for i, st in enumerate(states):  # unique names keep sample order traceable
        states[i] = kete.State(f'{st.desig}__{i}', st.jd, st.pos, st.vel, st.frame, st.center_id)
    fovs = [kete.OmniDirectionalFOV(observer_state(observer, jd)) for jd in jds]
    sims = kete.fov_state_check(states, fovs, include_asteroids=include_asteroids, non_gravs=non_gravs)
    by_jd = {round(s.fov.observer.jd, 8): s for s in sims}
    rows = []
    samples = {}
    for jd in jds:
        s = by_jd.get(round(jd, 8))
        if s is None:
            rows.append(dict(jd_tdb=jd)); continue
        rd = np.array(s.ra_dec_with_rates)
        obs = s.fov.observer
        order = np.argsort([int(x.desig.split('__')[-1]) for x in s.states])
        rd = rd[order]
        nom = s.states[order[0]]
        v = s.obs_vecs[order[0]]
        delta = v.r
        rr = np.linalg.norm(list(nom.pos))
        phase = s.phase_angles[order[0]]
        row = dict(jd_tdb=jd, utc_iso=kete.Time(jd).iso, ra_deg=rd[0, 0], dec_deg=rd[0, 1],
                   dra_cosdec_deg_per_day=rd[0, 2], ddec_deg_per_day=rd[0, 3], delta_au=delta, r_au=rr,
                   phase_deg=phase, vmag=(_hg_mag(H, G, rr, delta, np.radians(phase)) if M1K1 is None or (H is not None and np.isfinite(H))
                   else M1K1[0] + 5 * np.log10(delta) + 2.5 * M1K1[1] * np.log10(rr)),  # comets: SBDB M1/K1 total mag
                   n_samples=len(rd) - 1)
        if len(rd) > 2:
            dra = ((rd[1:, 0] - rd[0, 0] + 180) % 360 - 180) * np.cos(np.radians(rd[0, 1])) * 3600
            ddec = (rd[1:, 1] - rd[0, 1]) * 3600
            row.update(sigma_ra_3s_arcsec=3 * np.std(dra), sigma_dec_3s_arcsec=3 * np.std(ddec))
            cov = np.cov(np.vstack([dra, ddec]))
            w, vec = np.linalg.eigh(cov)
            major = vec[:, 1]  # (east, north) components of the major axis
            row.update(sigma_major_3s_arcsec=3 * np.sqrt(max(w[1], 0)), sigma_minor_3s_arcsec=3 * np.sqrt(max(w[0], 0)),
                       pa_major_deg=float(np.degrees(np.arctan2(major[0], major[1])) % 180))  # east of north
            if return_samples:
                samples[jd] = (rd[1:, 0].copy(), rd[1:, 1].copy())
        rows.append(row)
    df = pd.DataFrame(rows)
    if return_samples:
        df.attrs['samples'] = samples  # {jd: (ra_array_deg, dec_array_deg)} of covariance draws
    return df


_HZ_CENTER = {'spherex': '500@-163182', 'neowise': '500@-163', 'wise': '500@-163', 'geocenter': '500@399'}


def _predict_horizons(obj, jds, observer):
    center = _HZ_CENTER.get(observer.lower(), observer)
    out = []
    cmd = obj if obj.endswith(';') else (f"DES={obj};" if any(c.isalpha() for c in obj) and '/' not in obj else f"{obj};")
    jds = np.sort(jds)
    for i in range(0, len(jds), 40):
        tl = ' '.join(f"'{j:.8f}'" for j in jds[i:i + 40])
        p = dict(format='text', COMMAND=f"'{cmd}'", EPHEM_TYPE='OBSERVER', CENTER=f"'{center}'", TLIST=tl,
                 TLIST_TYPE='JD', TIME_TYPE='TT', QUANTITIES="'1,9,19,20,36'", CSV_FORMAT='YES', EXTRA_PREC='YES',
                 ANG_FORMAT='DEG', CAL_FORMAT='JD', OBJ_DATA='NO')
        for k in range(5):
            r = requests.get('https://ssd.jpl.nasa.gov/api/horizons.api', params=p, timeout=120)
            if r.status_code == 200 and '$$SOE' in r.text:
                break
            _time.sleep(5 * (k + 1))
        t = r.text
        if '$$SOE' not in t:
            raise RuntimeError(t[-2000:])
        hdr = [h.strip() for h in t[:t.find('$$SOE')].strip().splitlines()[-2].split(',')]
        hdr = [h if h else f'_blank{j}' for j, h in enumerate(hdr)]
        body = t[t.find('$$SOE') + 5:t.find('$$EOE')]
        df = pd.read_csv(io.StringIO(body), header=None, names=hdr, index_col=False)
        out.append(df)
        _time.sleep(1)
    df = pd.concat(out, ignore_index=True)
    ren = {'Date_________JDTT': 'jd_tdb', 'R.A.___(ICRF)': 'ra_deg', 'DEC____(ICRF)': 'dec_deg', 'APmag': 'vmag', 'T-mag': 'vmag',
           'r': 'r_au', 'delta': 'delta_au', '3sigma_RA': 'sigma_ra_3s_arcsec', '3sigma_DEC': 'sigma_dec_3s_arcsec',
           'RA_3sigma': 'sigma_ra_3s_arcsec', 'DEC_3sigma': 'sigma_dec_3s_arcsec'}
    df = df.rename(columns={k: v for k, v in ren.items() if k in df.columns})
    # Horizons returns rows sorted by time; TT and TDB differ by < 2 ms
    df = df[[c for c in df.columns if not c.startswith('_blank')]]
    return df.sort_values('jd_tdb').reset_index(drop=True)


if __name__ == '__main__':
    import sys
    o = sys.argv[1] if len(sys.argv) > 1 else '433'
    print(predict(o, [2461000.5], 'spherex', n_samples=50).T)
