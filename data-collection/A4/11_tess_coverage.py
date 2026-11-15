"""A4 step 11: TESS full-frame-image coverage before discovery (tess-point v0.9+, NASA TESS pointing table, offline).
For each target and each TESS sector whose mid-time lies in [discovery - 3 yr, discovery): kete geocentric daily track over
sector mid +-13 d (TESS orbits at ~60 R_E, so a nearby NEO can shift by up to ~1-3 deg: ESTIMATED; coverage is approximate),
tess_stars2px with trySector -> days on silicon, camera/ccd, mean column/row, V and 3-sigma at sector mid.
Also writes TESScut astrocut URLs for the best day (cutouts are per fixed position, so a moving target needs one per day)."""
import pandas as pd, numpy as np, os, sys, time, json
sys.path.insert(0, os.path.dirname(__file__)); sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../A2'))
from common import *
from positions import predict
from astropy.time import Time
import tess_stars2px as tp
D = f'{O}/tess'
sc = tp.TESS_Spacecraft_Pointing_Data()
secs = pd.DataFrame(dict(sector=sc.sectors, mid=sc.midtimes)); secs = secs[secs.sector < 1000]
t = pd.read_parquet(f'{O}/targets_A4.parquet')
a = pd.read_parquet(f'{R}/data/01-targets/lists/a_spherex_precovery_shortlist.parquet')[['designation', 'K1']]; t = t.merge(a, on='designation', how='left')
rows = []; stat = []
for row in t.itertuples():
    try:
        disc = Time(str(row.disc_date)).jd
        ss = secs[(secs.mid > disc - 3 * 365.25) & (secs.mid + 13 < disc)]
        n_on = 0
        for s in ss.itertuples():
            jd = s.mid + np.arange(-13, 13.01, 1.0)
            tr = predict(row.designation, jd, observer='geocenter', n_samples=0)
            if row.is_comet:
                k1 = row.K1 if np.isfinite(row.K1) else 10.0
                tr['vmag'] = row.M1 + 5 * np.log10(tr.delta_au) + k1 * np.log10(tr.r_au)
            ok = tr.ra_deg.notna().values
            res = tp.tess_stars2px_function_entry(np.arange(len(tr))[ok], tr.ra_deg.values[ok], tr.dec_deg.values[ok], trySector=int(s.sector), scInfo=sc)
            ids, sec_out, cam, ccd, col, rowp = res[0], res[3], res[4], res[5], res[6], res[7]
            good = (np.asarray(sec_out) == s.sector)
            if good.any():
                idx = np.asarray(ids)[good]; sub = tr.iloc[idx]
                sg = predict(row.designation, [s.mid], observer='geocenter', n_samples=30)
                best = sub.vmag.idxmin() if sub.vmag.notna().any() else sub.index[0]
                rows.append(dict(designation=row.designation, list=row.list, sector=int(s.sector), days_on_silicon=int(good.sum()),
                    camera=int(np.asarray(cam)[good][0]), ccd=int(np.asarray(ccd)[good][0]), first_utc=Time(sub.jd_tdb.min(), format='jd').iso, last_utc=Time(sub.jd_tdb.max(), format='jd').iso,
                    vmag_min=sub.vmag.min(), sigma3_arcsec_mid=float(sg.sigma_major_3s_arcsec.iloc[0]) if 'sigma_major_3s_arcsec' in sg else np.nan,
                    best_utc=Time(tr.loc[best, 'jd_tdb'], format='jd').iso, best_ra=tr.loc[best, 'ra_deg'], best_dec=tr.loc[best, 'dec_deg'],
                    tesscut_url=f"https://mast.stsci.edu/tesscut/api/v0.1/astrocut?ra={tr.loc[best, 'ra_deg']:.5f}&dec={tr.loc[best, 'dec_deg']:.5f}&y=30&x=30&sector={int(s.sector)}"))
                n_on += 1
        stat.append(dict(designation=row.designation, n_sectors_window=len(ss), n_sectors_on=n_on, status='ok'))
    except Exception as e:
        stat.append(dict(designation=row.designation, status=f'error {e!r}'[:200]))
    print(stat[-1], flush=True)
pd.DataFrame(rows).to_csv(f'{D}/tess_predisc_coverage.csv', index=False); pd.DataFrame(stat).to_csv(f'{D}/tess_status.csv', index=False)
print('TESS_DONE', len(rows))
