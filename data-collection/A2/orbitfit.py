"""
Rewind orbit improvement helper (agent A2): "future path before vs after adding precovery positions".

    from orbitfit import fit, add_precovery, compare_future
    obs   = fetch_obs('2026 MM')                                     # MPC ADES obs as kete Observations (cached)
    f0    = fit(obs)                                                 # (a) fit from MPC observations
    new   = add_precovery(obs, [(jd_tdb, ra_deg, dec_deg, 1.5, 'spherex')])   # (b) add SPHEREx precovery astrometry
    f1    = fit(new)
    table = compare_future(f0, f1, future_jds, observer='geocenter') # (c) sky-plane 3-sigma before/after at future dates

Uses kete (Caltech/IPAC) least-squares fitting (kete.orbit_fitting.fit_orbit), EFCC18 debiasing and
per-station weights, covariance sampling for uncertainty. Observer 'spherex' / 'neowise' states come from
positions.observer_state (Horizons SPHEREx vectors / kete WISE kernel).
SPHEREx pixel = 6.2 arcsec, so a realistic precovery sigma is about 1-2 arcsec per axis (ESTIMATED).
"""
from __future__ import annotations
import os, sys
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(__file__))
import positions as P  # noqa: E402  (sets KETE_CACHE_DIR)
import kete, kete.orbit_fitting as of  # noqa: E402


def fetch_obs(desig, before_jd=None, exclude=None):
    """MPC optical obs as kete Observations; optional cutoff and exclusion window list [(jd0,jd1),...]."""
    obs = of.fetch_mpc_observations(desig)
    if before_jd is not None:
        obs = [o for o in obs if o.epoch.jd < before_jd]
    for lo, hi in (exclude or []):
        obs = [o for o in obs if not (lo < o.epoch.jd < hi)]
    return obs


def fit(obs, initial_state=None, non_grav=None):
    st = initial_state or of.initial_orbit_determination(obs)[0][1]
    return of.fit_orbit(st, obs, non_grav=non_grav) if non_grav is not None else of.fit_orbit(st, obs)


def add_precovery(obs, rows):
    """rows: iterable of (jd_tdb, ra_deg, dec_deg, sigma_arcsec, observer) -> new obs list."""
    extra = [of.Observation.optical(P.observer_state(o, jd), ra, dec, s, s) for jd, ra, dec, s, o in rows]
    return list(obs) + extra


def sky_uncertainty(fitres, jds, observer='geocenter', n=300, seed=1):
    ss, _ = fitres.uncertain_state.sample(n, seed=seed)
    states = [fitres.state] + list(ss)
    out = []
    for jd in np.atleast_1d(jds):
        fov = kete.OmniDirectionalFOV(P.observer_state(observer, jd))
        named = [kete.State(f'x__{i}', s.jd, s.pos, s.vel, s.frame, s.center_id) for i, s in enumerate(states)]
        sim = kete.fov_state_check(named, [fov], include_asteroids=True)[0]
        order = np.argsort([int(x.desig.split('__')[-1]) for x in sim.states])
        rd = np.array(sim.ra_dec_with_rates)[order]
        dra = ((rd[1:, 0] - rd[0, 0] + 180) % 360 - 180) * np.cos(np.radians(rd[0, 1])) * 3600
        ddec = (rd[1:, 1] - rd[0, 1]) * 3600
        cov = np.cov(np.vstack([dra, ddec]))
        smaj = 3 * np.sqrt(np.max(np.linalg.eigvalsh(cov)))
        out.append(dict(jd_tdb=jd, ra_deg=rd[0, 0], dec_deg=rd[0, 1], sigma_ra_3s_arcsec=3 * dra.std(),
                        sigma_dec_3s_arcsec=3 * ddec.std(), semimajor_3s_arcsec=smaj))
    return pd.DataFrame(out)


def compare_future(fit_before, fit_after, jds, observer='geocenter', n=300):
    b = sky_uncertainty(fit_before, jds, observer, n); a = sky_uncertainty(fit_after, jds, observer, n)
    m = b[['jd_tdb', 'semimajor_3s_arcsec']].rename(columns={'semimajor_3s_arcsec': 'before_3s_arcsec'})
    m['after_3s_arcsec'] = a.semimajor_3s_arcsec.values
    m['shrink_factor'] = m.before_3s_arcsec / m.after_3s_arcsec
    m['shift_arcsec'] = np.hypot(((a.ra_deg - b.ra_deg + 180) % 360 - 180) * np.cos(np.radians(b.dec_deg)), a.dec_deg - b.dec_deg) * 3600
    return m
