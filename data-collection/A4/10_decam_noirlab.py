"""A4 step 10: DECam (NOIRLab Astro Data Archive, US) pre-discovery coverage for all A4 targets.
Window: max(2012-09-12, discovery - 3 yr) .. discovery - 1 d. kete geocentric daily track (nominal) and monthly 3-sigma (50 draws).
Months kept when predicted V <= 23.5 (comets: T-mag with K1) and 3-sigma <= 1800". For each kept month: NOIRLab adv_search
(instrument=decam, proc_type=instcal, caldat in month, centre in track box +-1.2 deg), then keep exposures whose centre is within
1.1 deg of the predicted position at dateobs_center. Read-only POST queries (search API), paced 1 s."""
import pandas as pd, numpy as np, os, sys, time, json
sys.path.insert(0, os.path.dirname(__file__)); sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../A2'))
from common import *
from positions import predict
from astropy.time import Time
D = f'{O}/decam'
API = 'https://astroarchive.noirlab.edu/api/adv_search/find/?limit=5000&format=json'
OUTF = ["md5sum", "archive_filename", "instrument", "proc_type", "obs_type", "caldat", "dateobs_center", "ra_center", "dec_center", "exposure", "ifilter", "url", "proposal"]
t = pd.read_parquet(f'{O}/targets_A4.parquet')
a = pd.read_parquet(f'{R}/data/01-targets/lists/a_spherex_precovery_shortlist.parquet')[['designation', 'K1']]; t = t.merge(a, on='designation', how='left')
log = f'{D}/decam_status.jsonl'
done = {json.loads(l)['designation'] for l in open(log)} if os.path.exists(log) else set()
def q(ra0, ra1, de0, de1, c0, c1):
    body = {"outfields": OUTF, "search": [["instrument", "decam"], ["proc_type", "instcal"], ["caldat", c0, c1], ["ra_center", ra0, ra1], ["dec_center", de0, de1]]}
    for k in range(4):
        try:
            r = requests.post(API, json=body, timeout=300, headers=UA)
            if r.status_code == 200: return pd.DataFrame(r.json()[1:])
        except Exception: pass
        time.sleep(5 * 2**k)
    raise RuntimeError('noirlab failed')
for row in t.itertuples():
    if row.designation in done: continue
    t0 = time.time(); rec = dict(designation=row.designation, list=row.list)
    try:
        disc = Time(str(row.disc_date)); start = max(Time('2012-09-12').jd, disc.jd - 3 * 365.25); end = disc.jd - 1
        if end <= start: raise ValueError('discovery before DECam')
        jd = np.arange(start, end, 1.0)
        tr = predict(row.designation, jd, observer='geocenter', n_samples=0)
        mj = np.arange(start + 15, end, 30.0)
        sg = predict(row.designation, mj, observer='geocenter', n_samples=50)
        if row.is_comet:
            k1 = row.K1 if np.isfinite(row.K1) else 10.0
            for d_ in (tr, sg): d_['vmag'] = row.M1 + 5 * np.log10(d_.delta_au) + k1 * np.log10(d_.r_au)
        keep = sg[(sg.vmag <= 23.5) & (sg.sigma_major_3s_arcsec <= 1800)]
        rec.update(n_months=len(sg), n_months_kept=len(keep))
        hits = []
        for m in keep.jd_tdb:
            seg = tr[(tr.jd_tdb >= m - 15) & (tr.jd_tdb < m + 15)]
            if not len(seg): continue
            ra = np.unwrap(np.radians(seg.ra_deg.values)); ra = np.degrees(ra)
            ra0, ra1 = ra.min() - 1.2 / max(np.cos(np.radians(seg.dec_deg.abs().max())), 0.05), ra.max() + 1.2 / max(np.cos(np.radians(seg.dec_deg.abs().max())), 0.05)
            de0, de1 = seg.dec_deg.min() - 1.2, seg.dec_deg.max() + 1.2
            c0 = Time(m - 15, format='jd').strftime('%Y-%m-%d'); c1 = Time(m + 15, format='jd').strftime('%Y-%m-%d')
            boxes = [(ra0 % 360, ra1 % 360)] if (ra0 % 360) < (ra1 % 360) and ra1 - ra0 < 360 else [(ra0 % 360, 360), (0, ra1 % 360)]
            for b0, b1 in boxes:
                df = q(b0, b1, de0, de1, c0, c1); time.sleep(1)
                if len(df): hits.append(df)
        if hits:
            h = pd.concat(hits, ignore_index=True).drop_duplicates('md5sum')
            jdo = Time(pd.to_datetime(h.dateobs_center).dt.tz_localize(None).values.astype('datetime64[ns]')).jd
            pra = np.degrees(np.unwrap(np.radians(tr.ra_deg.values))); prax = np.interp(jdo, tr.jd_tdb, pra) % 360; pdec = np.interp(jdo, tr.jd_tdb, tr.dec_deg)
            sep = np.degrees(np.arccos(np.clip(np.sin(np.radians(pdec)) * np.sin(np.radians(h.dec_center)) + np.cos(np.radians(pdec)) * np.cos(np.radians(h.dec_center)) * np.cos(np.radians(prax - h.ra_center)), -1, 1)))
            h['pred_ra'] = prax; h['pred_dec'] = pdec; h['sep_deg'] = sep
            h['pred_sigma3_arcsec'] = np.interp(jdo, sg.jd_tdb, sg.sigma_major_3s_arcsec); h['pred_vmag'] = np.interp(jdo, tr.jd_tdb, tr.vmag)
            h = h[h.sep_deg <= 1.1].copy(); h.insert(0, 'designation', row.designation); h.insert(1, 'list', row.list)
            if len(h): h.to_parquet(f'{D}/{safe(row.designation)}.parquet', index=False)
            rec['n_exposures'] = len(h)
        else: rec['n_exposures'] = 0
        rec['status'] = 'ok'
    except Exception as e:
        rec['status'] = f'error {e!r}'[:200]
    rec['sec'] = round(time.time() - t0, 1)
    open(log, 'a').write(json.dumps(rec, default=str) + '\n'); print(rec, flush=True)
print('DECAM_DONE')
