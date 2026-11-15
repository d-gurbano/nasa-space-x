"""A2: 'path before vs after precovery' test on real history: 99942 Apophis, Dec 2004.
Before: all MPC optical obs up to 2004-12-27 00:00 UTC EXCLUDING the 2004-03-15 Spacewatch (691) precovery.
After : same + the six 2004-03-15 precovery positions (found 2004 Dec 27, which ruled out a 2029 impact).
Fit with kete least squares, sample covariance, propagate to the 2029-04-13 Earth encounter, report
uncertainty of the geocentric close-approach distance and sky-plane uncertainty at a future date."""
import os, sys, json, numpy as np, pandas as pd
os.environ.setdefault('KETE_CACHE_DIR', os.path.join(os.path.dirname(__file__), '../../data/02-orbits/kete-cache'))
import kete, kete.orbit_fitting as of
out = os.path.join(os.path.dirname(__file__), '../../data/02-orbits/tests'); os.makedirs(out, exist_ok=True)
obs = of.fetch_mpc_observations('99942')
cut = kete.Time.from_iso('2004-12-27T00:00:00').jd
pre_lo, pre_hi = kete.Time.from_iso('2004-03-14T00:00:00').jd, kete.Time.from_iso('2004-03-17T00:00:00').jd
early = [o for o in obs if o.epoch.jd < cut]
before = [o for o in early if not (pre_lo < o.epoch.jd < pre_hi)]
after = early
print('n obs before', len(before), 'after', len(after))
res = {}
import logging
class _ImpactCounter(logging.Handler):
    def __init__(self): super().__init__(); self.n = 0
    def emit(self, rec):
        if 'Impact detected' in rec.getMessage() and 'earth' in rec.getMessage(): self.n += 1
counter = _ImpactCounter(); logging.getLogger().addHandler(counter); logging.getLogger('kete').addHandler(counter)
ca_lo, ca_hi = kete.Time.from_iso('2029-04-10T00:00:00').jd, kete.Time.from_iso('2029-04-16T00:00:00').jd
for label, ob in [('before', before), ('after', after)]:
    iod = of.initial_orbit_determination(ob)
    fit = of.fit_orbit(iod[0][1], ob)
    us = fit.uncertain_state
    ss, _ = us.sample(300, seed=1)
    states = [fit.state] + list(ss)
    # geocentric distance at 2029-04-13 encounter (min over 1-hr grid in +-3 d)
    nominal_ca = 2462240.40  # 2029-04-13 ~21:36 TDB, from JPL CAD
    grid = np.arange(nominal_ca - 0.5, nominal_ca + 0.5, 2 / 1440)  # 2-min steps, +-12 h
    counter.n = 0
    st = kete.propagate_n_body(states, grid[0], include_asteroids=True)
    dmin = np.full(len(states), np.inf); tmin = np.zeros(len(states))
    for jd in grid:
        st = kete.propagate_n_body(st, jd, include_asteroids=True)
        e = kete.spice.get_state('earth', jd)
        for i, s in enumerate(st):
            d = np.linalg.norm(np.array(list(s.pos)) - np.array(list(e.pos)))
            if d < dmin[i]: dmin[i] = d; tmin[i] = jd
    km = dmin * 149597870.7
    res[label] = dict(n_obs=len(ob), n_included=int(sum(fit.included)), rms=float(fit.rms), converged=bool(fit.converged),
                      arc_days=float(max(o.epoch.jd for o in ob) - min(o.epoch.jd for o in ob)),
                      ca2029_nominal_km=float(km[0]), ca2029_median_km=float(np.median(km[1:])),
                      ca2029_sigma_km=float(np.std(km[1:])), ca2029_p01_km=float(np.percentile(km[1:], 1)),
                      ca2029_p99_km=float(np.percentile(km[1:], 99)), n_samples=len(km)-1, n_earth_impacts_logged_by_kete=counter.n, impact_prob_estimate=counter.n / (len(km) - 1), n_impact_or_nonfinite=int(np.sum(~np.isfinite(km[1:]) | (km[1:] < 6378.137 * 1.02))),
                      impact_fraction=float(np.mean(~np.isfinite(km[1:]) | (km[1:] < 6378.137 * 1.02))), min_sample_km=float(np.nanmin(km[1:])),
                      ca_time_sigma_hours=float(np.std(tmin[1:]) * 24),
                      state_epoch=fit.state.jd, pos=list(fit.state.pos), vel=list(fit.state.vel))
    print(label, json.dumps({k: v for k, v in res[label].items() if k not in ('pos', 'vel')}, indent=1), flush=True)
import requests
cad = requests.get('https://ssd-api.jpl.nasa.gov/cad.api', params={'des': '99942', 'date-min': '2029-01-01', 'date-max': '2029-12-31', 'dist-max': '0.01'}, timeout=60).json()
res['truth_jpl_cad_2029'] = dict(fields=cad.get('fields'), data=cad.get('data'), dist_km=float(cad['data'][0][4]) * 149597870.7)
print('JPL CAD 2029 (current best orbit):', res['truth_jpl_cad_2029'])
json.dump(res, open(f'{out}/apophis_before_after_precovery.json', 'w'), indent=1)
