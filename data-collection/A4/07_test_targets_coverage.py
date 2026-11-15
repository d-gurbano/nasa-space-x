"""A4 step 7: archive coverage for the 5 challenge test targets (fixed positions; proper motion small vs search radius).
Coordinates: NASA/IPAC NED name resolver (RW Aur, R Dra, WISE 0855, eps Ind B via 2MASS J22041052-5646577);
Barnard's Star from A5 query centre (2MASS epoch). Services: IRSA SIA2 (all collections), MAST TESScut sector API,
NOIRLab Astro Data Archive SIA (voimg), ESA Euclid archive TAP (partner)."""
import pandas as pd, os, sys, io, json, time
sys.path.insert(0, os.path.dirname(__file__)); from common import *
from astropy.io.votable import parse
D = f'{O}/test_targets'; os.makedirs(D, exist_ok=True)
T = [("Barnard's Star", 269.452204, 4.693276, '2MASS fp_psc (A5 query centre), epoch ~1999'),
     ('WISE 0855-0714', 133.7947597, -7.2451456, 'NED WISEA J085510.74-071442.5'),
     ('Epsilon Indi B', 331.043836, -56.782707, 'NED 2MASS J22041052-5646577'),
     ('RW Aurigae', 76.9564535, 30.4013327, 'NED RW Aur'),
     ('R Draconis', 248.167472, 66.7549882, 'NED R Dra')]
pd.DataFrame(T, columns=['target', 'ra_deg', 'dec_deg', 'coord_source']).to_csv(f'{D}/test_targets_coords.csv', index=False)
summ = []
which = sys.argv[1:] or ['irsa', 'tess', 'noirlab', 'euclid']
for name, ra, dec, _ in T:
    key = safe(name.replace("'", ''))
    if 'irsa' in which:
        try:
            r = get('https://irsa.ipac.caltech.edu/SIA', dict(POS=f'CIRCLE {ra} {dec} 0.01', RESPONSEFORMAT='VOTABLE'), timeout=900)
            tb = parse(io.BytesIO(r.content)).get_first_table().to_table(use_names_over_ids=True).to_pandas()
            tb.insert(0, 'target', name); tb.to_parquet(f'{D}/{key}_irsa_sia.parquet', index=False)
            for c, n in tb.groupby('obs_collection').size().items(): summ.append(dict(target=name, archive='IRSA SIA2', collection=c, n=n))
            print(name, 'irsa', len(tb), flush=True)
        except Exception as e: summ.append(dict(target=name, archive='IRSA SIA2', collection='ERROR', n=0, note=repr(e)[:200])); print(name, 'irsa err', e, flush=True)
    if 'tess' in which:
        try:
            r = get('https://mast.stsci.edu/tesscut/api/v0.1/sector', dict(ra=ra, dec=dec, radius='1m'), timeout=300).json()
            res = pd.DataFrame(r.get('results', [])); res.insert(0, 'target', name)
            res['tesscut_url'] = [f'https://mast.stsci.edu/tesscut/api/v0.1/astrocut?ra={ra}&dec={dec}&y=20&x=20&sector={int(s)}' for s in res.get('sector', [])] if len(res) else []
            res.to_csv(f'{D}/{key}_tess_sectors.csv', index=False)
            summ.append(dict(target=name, archive='MAST TESScut', collection='TESS FFI sectors', n=len(res), note=','.join(res.get('sector', pd.Series(dtype=str)).astype(str))))
            print(name, 'tess', len(res), flush=True)
        except Exception as e: summ.append(dict(target=name, archive='MAST TESScut', collection='ERROR', n=0, note=repr(e)[:200]))
    if 'noirlab' in which:
        try:
            r = get('https://astroarchive.noirlab.edu/api/sia/voimg', dict(POS=f'{ra},{dec}', SIZE=0.02, format='json', limit=20000), timeout=600).json()
            res = pd.DataFrame(r[1:]); res.insert(0, 'target', name); res.to_csv(f'{D}/{key}_noirlab_sia.csv', index=False)
            for c, n in res.groupby('instrument').size().items(): summ.append(dict(target=name, archive='NOIRLab SIA', collection=c, n=n))
            print(name, 'noirlab', len(res), flush=True)
        except Exception as e: summ.append(dict(target=name, archive='NOIRLab SIA', collection='ERROR', n=0, note=repr(e)[:200]))
    if 'euclid' in which:
        try:
            q = f"SELECT observation_id, instrument_name, filter_name, release_name FROM sedm.mosaic_product WHERE 1=CONTAINS(POINT('ICRS',ra,dec), CIRCLE('ICRS',{ra},{dec},0.5))"
            r = get('https://easidr.esac.esa.int/tap-server/tap/sync', dict(REQUEST='doQuery', LANG='ADQL', FORMAT='csv', QUERY=q), timeout=120, tries=2)
            open(f'{D}/{key}_euclid.csv', 'w').write(r.text)
            summ.append(dict(target=name, archive='ESA Euclid TAP', collection='mosaic_product', n=max(r.text.count('\n') - 1, 0), note=f'HTTP {r.status_code}'))
        except Exception as e: summ.append(dict(target=name, archive='ESA Euclid TAP', collection='ERROR', n=0, note=repr(e)[:200]))
    time.sleep(2)
s = pd.DataFrame(summ); out = f'{D}/coverage_summary_{"_".join(which)}.csv'; s.to_csv(out, index=False); print(s.to_string())
