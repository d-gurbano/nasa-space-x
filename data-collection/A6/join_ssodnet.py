"""A6: add SsODNet best-estimate taxonomy (partner, France) to derived/spherex_validation_spectra.csv.
Run after build_templates.py and ssodnet_bft.py."""
import pandas as pd
d = pd.read_parquet('data/06-composition/raw/ssodnet/ssoBFT_Asteroid_selected_columns.parquet')
v = pd.read_csv('data/06-composition/derived/spherex_validation_spectra.csv', dtype={'number': str})
s = d[['number', 'taxonomy.class', 'taxonomy.complex', 'taxonomy.technique']].dropna(subset=['number']).copy()
s['number'] = s.number.astype('Int64').astype(str)
v = v.drop(columns=[c for c in v.columns if c.startswith('ssodnet_')], errors='ignore').merge(
    s.rename(columns={'taxonomy.class': 'ssodnet_class', 'taxonomy.complex': 'ssodnet_complex',
                      'taxonomy.technique': 'ssodnet_tax_technique'}), on='number', how='left')
cols = [c for c in v.columns if not c.startswith('ch')] + [c for c in v.columns if c.startswith('ch')]
v[cols].to_csv('data/06-composition/derived/spherex_validation_spectra.csv', index=False, float_format='%.5f')
print('with ssodnet class:', v.ssodnet_class.notna().sum(), 'of', len(v))
