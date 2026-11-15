"""A2: summarize lost_{TAG}_frames.csv for Phase B: frames outside the observed arc (before first_obs or after
last_obs, i.e. frames that would add arc) and with predicted V <= 20.5 (about S/N>=3 single frame, ESTIMATED from Y1 depth AB 19 + V-0.3 colour)."""
import pandas as pd, numpy as np, os, sys
TAG = sys.argv[1] if len(sys.argv) > 1 else 'top20'
root = os.path.join(os.path.dirname(__file__), '../../data/02-orbits')
f = pd.read_csv(f'{root}/lost_spherex/lost_{TAG}_frames.csv')
f = f.drop(columns=['designation', 'first_mjd', 'last_mjd', 'H', 'first_obs', 'last_obs', 'condition_code', 'outside_arc', 'bright', 'unconstrained', 'search_class'], errors='ignore')
b = pd.read_csv(f'{root}/../01-targets/lists/b_lost_recovery_shortlist.csv')[['designation', 'H', 'first_obs', 'last_obs', 'condition_code']]
from astropy.time import Time
b = b[b.designation.isin(f.object)].copy()
fix = lambda x: str(x).replace('??', '01')
b['first_mjd'] = Time([fix(x) for x in b.first_obs]).mjd; b['last_mjd'] = Time([fix(x) for x in b.last_obs]).mjd + 1
f = f.merge(b, left_on='object', right_on='designation')
f['outside_arc'] = (f.mjd_avg_utc < f.first_mjd) | (f.mjd_avg_utc > f.last_mjd)
f['bright'] = f.vmag_pred <= 20.5
# 3-sigma major > 10 deg: linear covariance no longer meaningful, object effectively unconstrained on the sky
f['unconstrained'] = f.sigma_major_3s_arcsec > 36000
f['search_class'] = np.select([f.sigma_major_3s_px <= 3, f.sigma_major_3s_px <= 50, ~f.unconstrained], ['<=3px', '3-50px', '50px-10deg'], 'unconstrained>10deg')
u = f[f.outside_arc & f.bright & f.in_frame]
s = f.groupby('object', sort=False).agg(H=('H', 'first'), U=('condition_code', 'first'), first_obs=('first_obs', 'first'), last_obs=('last_obs', 'first'),
        n_files=('frame_key', 'size'), n_in_frame=('in_frame', 'sum'), n_outside_arc=('outside_arc', 'sum'), n_bright=('bright', 'sum'), n_unconstrained=('unconstrained', 'sum'), median_major_3s_deg=('sigma_major_3s_arcsec', lambda x: np.nanmedian(x) / 3600)).reset_index()
g = u.groupby('object').agg(n_useful_files=('frame_key', 'size'), n_useful_exposures=('observationid', 'nunique'), useful_first_mjd=('mjd_avg_utc', 'min'),
        useful_last_mjd=('mjd_avg_utc', 'max'), useful_best_vmag=('vmag_pred', 'min'), useful_median_major_3s_px=('sigma_major_3s_px', 'median'),
        useful_max_major_3s_px=('sigma_major_3s_px', 'max'), useful_median_rate_arcsec_hr=('rate_arcsec_per_hr', 'median')).reset_index()
s = s.merge(g, on='object', how='left').fillna({'n_useful_files': 0, 'n_useful_exposures': 0})
s.to_csv(f'{root}/lost_spherex/lost_{TAG}_phaseB_summary.csv', index=False)
f.drop(columns=['designation', 'first_mjd', 'last_mjd', 'H', 'first_obs', 'last_obs', 'condition_code'], errors='ignore').to_csv(f'{root}/lost_spherex/lost_{TAG}_frames.csv', index=False)
pd.set_option('display.width', 250); print(s.round(2).to_string())
