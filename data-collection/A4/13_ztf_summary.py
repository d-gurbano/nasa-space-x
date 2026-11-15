"""A4: summarize MOST ZTF results (1 yr before discovery). Per object-night: kete geocentric 3-sigma and V (comets: T-mag);
useful = 3-sigma <= 300" and V <= 20.5 (ZTF single-exposure 5-sigma limit ~20.5 r, VERIFIED order of magnitude; used as ESTIMATED cut).
Image URLs built from ZTF IBE convention (sci/YYYY/MMDD/fracday/ztf_<filefracday>_<field:06d>_<filter>_c<ccd:02d>_o_q<qid>_sciimg.fits)."""
import pandas as pd, numpy as np, os, sys, glob, json
sys.path.insert(0, os.path.dirname(__file__)); sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../A2'))
from common import *
from positions import predict, utc_mjd_to_tdb_jd
D = f'{O}/ztf'
t = pd.read_parquet(f'{O}/targets_A4.parquet')
a = pd.read_parquet(f'{R}/data/01-targets/lists/a_spherex_precovery_shortlist.parquet')[['designation', 'K1']]; t = t.merge(a, on='designation', how='left').set_index('designation')
st = pd.DataFrame([json.loads(l) for l in open(f'{D}/most_ztf_status.jsonl')]).drop_duplicates('designation', keep='last')
parts = []
for f in glob.glob(f'{D}/parts/*.parquet'):
    df = pd.read_parquet(f)
    if not len(df): continue
    des = df.designation.iloc[0]
    df['mjd'] = df.obsjd - 2400000.5
    if False:
        ffd = df.filefracday.astype(str); mj = pd.to_datetime(ffd.str[:8]).map(lambda x: x.to_julian_date() - 2400000.5) + ffd.str[8:].astype(float) / 1e6
        df['mjd'] = mj.values
    df['night'] = np.floor(df.mjd).astype(int)
    nights = df.groupby('night').mjd.median()
    try:
        p = predict(des, utc_mjd_to_tdb_jd(nights.values), observer='geocenter', n_samples=50)
        sig = dict(zip(nights.index, p.sigma_major_3s_arcsec)); vm = p.vmag.values
        if t.loc[des, 'is_comet']:
            k1 = t.loc[des, 'K1'] if np.isfinite(t.loc[des, 'K1']) else 10.0
            vm = t.loc[des, 'M1'] + 5 * np.log10(p.delta_au) + k1 * np.log10(p.r_au)
        vmd = dict(zip(nights.index, vm))
        df['sigma3_arcsec'] = df.night.map(sig); df['vmag_pred'] = df.night.map(vmd)
    except Exception as e:
        df['sigma3_arcsec'] = np.nan; df['vmag_pred'] = np.nan; print(des, e)
    ffd = df.filefracday.astype(str)
    fcode = df.filtercode.astype(str)
    df['sci_url'] = ('https://irsa.ipac.caltech.edu/ibe/data/ztf/products/sci/' + ffd.str[:4] + '/' + ffd.str[4:8] + '/' + ffd.str[8:] + '/ztf_' + ffd + '_' +
                     df.field.astype(int).map('{:06d}'.format) + '_' + fcode + '_c' + df.ccdid.astype(int).map('{:02d}'.format) + '_o_q' + df.qid.astype(int).astype(str) + '_sciimg.fits')
    df['cutout_url'] = df.sci_url + '?center=' + df.ra_obj.round(5).astype(str) + ',' + df.dec_obj.round(5).astype(str) + '&size=120arcsec&gzip=false'
    df['useful'] = (df.sigma3_arcsec <= 300) & (df.vmag_pred <= 20.5)
    parts.append(df)
im = pd.concat(parts, ignore_index=True)
im.to_parquet(f'{D}/ztf_predisc_frames.parquet', index=False)
im[im.useful].to_csv(f'{D}/ztf_predisc_useful.csv', index=False)
g = im.groupby('designation').agg(n_frames=('mjd', 'size'), n_nights=('night', 'nunique'), n_useful=('useful', 'sum'),
    min_sigma3=('sigma3_arcsec', 'min'), min_vmag=('vmag_pred', 'min'), earliest_useful_mjd=('mjd', lambda s: s[im.loc[s.index, 'useful']].min() if im.loc[s.index, 'useful'].any() else np.nan)).reset_index()
g = st.rename(columns={'n_frames': 'n_frames_most'}).merge(g, on='designation', how='left'); g.to_csv(f'{D}/ztf_summary.csv', index=False)
print('queried', len(st), 'ok', (st.status == 'ok').sum(), 'objects with frames', int((g.n_frames > 0).sum()), 'frames', len(im), 'useful frames', int(im.useful.sum()), 'objects useful', int((g.n_useful > 0).sum()))
print(g.sort_values('n_useful', ascending=False).head(12).to_string())
