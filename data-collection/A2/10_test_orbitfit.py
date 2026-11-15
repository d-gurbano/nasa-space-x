"""A2 test of orbitfit.py: (1) Apophis real Dec-2004 precovery, future sky uncertainty 2029-04-01 and 2029-04-13;
(2) 2026 RD39 (4-day arc) with ONE synthetic SPHEREx precovery point (injected from its own nominal orbit,
1.5 arcsec sigma) 60 days before discovery - demonstrates the SPHEREx-observer path; not a real detection."""
import os, json, numpy as np, pandas as pd, kete
import orbitfit as F, positions as P
out = os.path.join(P.ORB, 'tests')
cut = kete.Time.from_iso('2004-12-27T00:00:00').jd
lo, hi = kete.Time.from_iso('2004-03-14T00:00:00').jd, kete.Time.from_iso('2004-03-17T00:00:00').jd
b = F.fit(F.fetch_obs('99942', cut, [(lo, hi)])); a = F.fit(F.fetch_obs('99942', cut))
fut = [kete.Time.from_iso('2029-04-01T00:00:00').jd, kete.Time.from_iso('2029-04-13T12:00:00').jd]
t1 = F.compare_future(b, a, fut, 'geocenter'); t1.insert(0, 'case', 'Apophis real precovery 2004-03-15 (691)')
obs = F.fetch_obs('2026 RD39')
f0 = F.fit(obs)
first = min(o.epoch.jd for o in obs)
jd_pre = first - 60
truth = P.predict('2026 RD39', [jd_pre], 'spherex', n_samples=0)
f1 = F.fit(F.add_precovery(obs, [(jd_pre, truth.ra_deg[0], truth.dec_deg[0], 1.5, 'spherex')]), initial_state=f0.state)
fut2 = [first + 365, first + 730]
t2 = F.compare_future(f0, f1, fut2, 'geocenter'); t2.insert(0, 'case', '2026 RD39 + 1 synthetic SPHEREx point (-60 d)')
t = pd.concat([t1, t2]); t['utc'] = [kete.Time(j).iso[:10] for j in t.jd_tdb]
t.to_csv(f'{out}/before_after_sky_uncertainty.csv', index=False); print(t.round(2).to_string())
