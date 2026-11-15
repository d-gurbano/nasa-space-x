"""A4 step 8: catalog-level NEOWISE/WISE precovery. For each object with searchable visits (kete 3-sigma <= 300", V <= 21.5,
see 04), run the IRSA Gator moving-object search (searchForm=MO, Horizons ephemeris by name) on the single-exposure
source tables covering those visits, radius = clip(max 3-sigma, 10", 300"). Keep rows within max(3-sigma_visit, 10")
of the predicted position. Flags: static (AllWISE counterpart < 3" for NEOWISE-R rows, or another frame of the same
visit has a source within 2" of the same sky spot), sso_flg (pipeline already tied it to a known object).
Output wise/neowise_candidates.parquet + wise/gator_status.jsonl. Resumable."""
import pandas as pd, numpy as np, os, sys, time, json, io
sys.path.insert(0, os.path.dirname(__file__)); from common import *
from astropy.io import ascii
D = f'{O}/wise'; os.makedirs(f'{D}/gator_raw', exist_ok=True)
G = 'https://irsa.ipac.caltech.edu/cgi-bin/Gator/nph-query'
TABLES = [('allsky_4band_p1bs_psd', 55203.0, 55414.94), ('allsky_3band_p1bs_psd', 55414.94, 55468.9), ('allsky_2band_p1bs_psd', 55468.9, 55593.6), ('neowiser_p1bs_psd', 56600, 60530)]
BASE = 'ra,dec,sigra,sigdec,mjd,w1mpro,w1sigmpro,w2mpro,w2sigmpro,w1snr,w2snr,scan_id,frame_num,source_id,cc_flags,ph_qual,sso_flg,qual_frame,nb,na'
v = pd.read_parquet(f'{D}/wise_visits.parquet'); sv = v[(v.kete_sigma_major_3s_arcsec <= 300) & (v.vmag_used <= 22.5)].copy()  # strict searchable plus V 21.5-22.5 stretch
log = f'{D}/gator_status.jsonl'
done = {(json.loads(l)['designation'], json.loads(l)['table']) for l in open(log) if json.loads(l)['status'] in ('ok', 'no rows')} if os.path.exists(log) else set()
def mjd2str(m): return pd.Timestamp('1858-11-17') + pd.Timedelta(days=float(m))
out = []
for des, g in sv.groupby('designation'):
    for tb, m0, m1 in TABLES:
        gg = g[(g.mjd_last >= m0) & (g.mjd_first <= m1)]
        if not len(gg) or (des, tb) in done: continue
        rad = float(np.clip(gg.kete_sigma_major_3s_arcsec.max(), 10, 300))
        b = mjd2str(max(gg.mjd_first.min() - 0.5, m0)).strftime('%Y %m %d %H:%M:%S'); e = mjd2str(min(gg.mjd_last.max() + 0.5, m1)).strftime('%Y %m %d %H:%M:%S')
        name = des if not des[0].isdigit() or ' ' in des else des
        cols = BASE + (',allwise_cntr,r_allwise,w1mpro_allwise,w2mpro_allwise' if tb.startswith('neowiser') else '')
        p = dict(searchForm='MO', spatial='cone', catalog=tb, outfmt=1, mobj='smo', mobjstr=name, moradius=rad, selcols=cols)  # btime/etime make Gator MO fail ('key->mobj exceeds the limit'); filter by time below
        t0 = time.time(); st = 'ok'; n = 0
        try:
            r = get(G, p, timeout=900); txt = r.text
            open(f'{D}/gator_raw/{safe(des)}__{tb}.tbl', 'w').write(txt)
            if 'stat="ERROR"' in txt[:500]: st = 'error ' + txt[:300]
            elif '|' in txt[:50000]:
                df = ascii.read(txt, format='ipac').to_pandas(); n = len(df)
                if n:
                    df = df[(df.mjd >= gg.mjd_first.min() - 1) & (df.mjd <= gg.mjd_last.max() + 1)].copy(); n = len(df)
                if n:
                    df.insert(0, 'designation', des); df.insert(1, 'table', tb)
                    # attach visit sigma by nearest visit mid-time
                    idx = np.abs(df.mjd.values[:, None] - gg.mjd_mid.values[None, :]).argmin(1)
                    df['visit'] = gg.visit.values[idx]; df['sigma3_visit_arcsec'] = gg.kete_sigma_major_3s_arcsec.values[idx]
                    df['vmag_pred'] = gg.vmag_used.values[idx]; df['radius_used_arcsec'] = rad
                    df['within_unc'] = df.dist_x <= np.maximum(df.sigma3_visit_arcsec, 10)
                    out.append(df)
            else: st = 'no rows'
        except Exception as ex: st = f'error {ex!r}'[:300]
        rec = dict(designation=des, table=tb, status=st, n_rows=n, radius=rad, btime=b, etime=e, sec=round(time.time() - t0, 1))
        open(log, 'a').write(json.dumps(rec) + '\n'); print(rec, flush=True); time.sleep(1)
if out:
    new = pd.concat(out, ignore_index=True)
    fn = f'{D}/neowise_candidates.parquet'
    allc = pd.concat([pd.read_parquet(fn), new], ignore_index=True) if os.path.exists(fn) else new
    # static flags
    allc['static_allwise'] = allc.get('r_allwise', pd.Series(np.nan, index=allc.index)).fillna(99) < 3
    st = np.zeros(len(allc), bool)
    for (d_, vi), gi in allc.groupby(['designation', 'visit']):
        if len(gi) < 2: continue
        ra = np.radians(gi.ra.values); de = np.radians(gi.dec.values); fr = gi.source_id.str[:9].values
        for k, ii in enumerate(gi.index):
            sep = np.degrees(np.arccos(np.clip(np.sin(de[k]) * np.sin(de) + np.cos(de[k]) * np.cos(de) * np.cos(ra - ra[k]), -1, 1))) * 3600
            st[allc.index.get_loc(ii)] = ((sep < 2) & (fr != fr[k])).any()
    allc['static_repeat'] = st
    allc['candidate'] = allc.within_unc & ~allc.static_allwise & ~allc.static_repeat & (allc.sso_flg.fillna(0) == 0)
    allc.to_parquet(fn, index=False)
    print('rows', len(allc), 'within_unc', int(allc.within_unc.sum()), 'candidates', int(allc.candidate.sum()), 'objects w/ cand', allc[allc.candidate].designation.nunique())
