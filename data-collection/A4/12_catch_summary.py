"""A4: summarize CATCH parts -> catch/catch_images_all.parquet, catch/catch_predisc_useful.csv, catch/catch_summary.csv.
pre-discovery = image date < discovery date (A1 disc_date_best; for the lost list, first_obs).
useful = pre-discovery AND CATCH/JPL 3-sigma semi-major unc_a <= 300" AND predicted V <= image maglimit (when maglimit known).
Rerunnable while 03_catch.py is still filling parts."""
import pandas as pd, numpy as np, os, sys, glob, json
sys.path.insert(0, os.path.dirname(__file__)); from common import *
D = f'{O}/catch'
t = pd.read_parquet(f'{O}/targets_A4.parquet')
st = pd.DataFrame([json.loads(l) for l in open(f'{D}/catch_status.jsonl')]).drop_duplicates('designation', keep='last')
parts = [pd.read_parquet(f) for f in glob.glob(f'{D}/parts/*.parquet')]
im = pd.concat(parts, ignore_index=True)
a = pd.read_parquet(f'{R}/data/01-targets/lists/a_spherex_precovery_shortlist.parquet')[['designation', 'K1']]
im = im.merge(t[['designation', 'disc_date', 'is_comet', 'M1']].merge(a, on='designation', how='left'), on='designation', how='left')
# comets: recompute total magnitude T = M1 + 5 log10(delta) + K1 log10(rh) (K1 default 10); CATCH comet vmag kept as vmag_catch
im['vmag_catch'] = im.vmag
im['vmag'] = np.where(im.is_comet, im.M1 + 5 * np.log10(im.delta) + im.K1.fillna(10.0) * np.log10(im.rh.abs()), im.vmag)
im['date_t'] = pd.to_datetime(im.date); im['pre_disc'] = im.date_t < pd.to_datetime(im.disc_date)
# typical single-image limits when CATCH gives no maglimit (ESTIMATED, survey literature-level values)
LIM = {'catalina_bigelow': 20.5, 'catalina_lemmon': 21.5, 'catalina_bokneosurvey': 22.0, 'loneos': 19.5, 'neat_palomar_tricam': 20.0, 'neat_maui_geodss': 19.5,
       'ps1dr2': 22.0, 'skymapper_dr4': 20.5, 'spacewatch': 21.0, 'atlas_haleakela': 19.5, 'atlas_mauna_loa': 19.5, 'atlas_rio_hurtado': 19.5, 'atlas_sutherland': 19.5}
im['maglimit_used'] = im.maglimit.fillna(im.source.map(LIM))
im['bright_enough'] = im.vmag <= im.maglimit_used
im['useful'] = im.pre_disc & (im.unc_a <= 300) & im.bright_enough
keep = ['designation', 'list', 'job_id', 'source', 'date', 'mjd_start', 'ra', 'dec', 'unc_a', 'unc_b', 'unc_theta', 'vmag', 'vmag_catch', 'maglimit', 'maglimit_used', 'filter', 'exposure', 'seeing', 'rh', 'delta', 'product_id', 'archive_url', 'cutout_url', 'preview_url', 'pre_disc', 'useful']
im[keep].to_parquet(f'{D}/catch_images_all.parquet', index=False)
im[im.useful][keep].to_csv(f'{D}/catch_predisc_useful.csv', index=False)
g = im.groupby('designation').agg(n_images=('date', 'size'), n_pre_disc=('pre_disc', 'sum'), n_pre_disc_unc300=('pre_disc', lambda s: int((s & (im.loc[s.index, 'unc_a'] <= 300)).sum())),
    n_useful=('useful', 'sum'), earliest_useful=('date', lambda s: s[im.loc[s.index, 'useful']].min() if im.loc[s.index, 'useful'].any() else None)).reset_index()
src = im[im.useful].groupby('designation').source.apply(lambda s: json.dumps(s.value_counts().to_dict())).rename('useful_by_source').reset_index()
g = st[['designation', 'status', 'job_id']].merge(g, on='designation', how='left').merge(src, on='designation', how='left')
g = t[['designation', 'list', 'disc_date', 'rank_in_list']].merge(g, on='designation', how='right')
g.to_csv(f'{D}/catch_summary.csv', index=False)
print('objects queried', len(g), 'ok', (g.status == 'ok').sum(), 'images', len(im), 'pre-disc', int(im.pre_disc.sum()), 'useful', int(im.useful.sum()))
print('objects with any pre-disc image', int((g.n_pre_disc > 0).sum()), 'with useful', int((g.n_useful > 0).sum()))
print(g.sort_values('n_useful', ascending=False).head(15).to_string())
