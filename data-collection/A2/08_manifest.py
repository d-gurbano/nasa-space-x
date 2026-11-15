"""A2: write data/02-orbits/manifest.csv (filename, url, bytes, sha256, date) for downloaded/derived files."""
import os, hashlib, csv, datetime as dt
root = os.path.join(os.path.dirname(__file__), '../../data/02-orbits')
URL = {
 'mpc/MPCORB.DAT.gz': 'https://minorplanetcenter.net/iau/MPCORB/MPCORB.DAT.gz',
 'mpc/NEA.txt': 'https://minorplanetcenter.net/iau/MPCORB/NEA.txt',
 'mpc/CometEls.txt': 'https://minorplanetcenter.net/iau/MPCORB/CometEls.txt',
 'mpc/ObsCodes.html': 'https://minorplanetcenter.net/iau/lists/ObsCodes.html',
 'mpc/mpcorb_extended.json.gz': 'https://minorplanetcenter.net/Extended_Files/mpcorb_extended.json.gz',
 'mpc/obscodes_api.json': 'https://data.minorplanetcenter.net/api/obscodes',
}
def url_for(rel):
    if rel in URL: return URL[rel]
    if rel.startswith('sbdb/'): return 'https://ssd-api.jpl.nasa.gov/sbdb.api?sstr=<des>&cov=mat&full-prec=1&phys-par=1&discovery=1'
    if rel.startswith('obs/') and rel.endswith('.csv'): return 'https://data.minorplanetcenter.net/api/get-obs (ADES_DF)'
    if rel.startswith('findorb/apophis'): return 'https://data.minorplanetcenter.net/api/get-obs (OBS80)'
    if rel.startswith('horizons/'): return 'https://ssd.jpl.nasa.gov/api/horizons.api (COMMAND=-163182 VECTORS)'
    if rel.startswith('catch/'): return 'https://catch-api.astro.umd.edu/'
    if rel.startswith('kete-cache/kernels'): return 'kete 3.3.0 bundled/auto-downloaded kernels (NAIF de440s, kete reconstructed spherex.bsp, wise.bsp)'
    if rel.startswith('kete-cache/'): return 'kete auto-download (JPL Horizons SBDB / MPC / JPL debias_2018)'
    return 'derived (A2 code)'
rows = []
for dp, dn, fn in os.walk(root):
    if '/findorb/' in dp + '/' and any(x in dp for x in ['/find_orb', '/lunar', '/jpl_eph', '/sat_code', '/miscell', '/home', '/install']): continue
    for f in fn:
        p = os.path.join(dp, f); rel = os.path.relpath(p, root)
        if rel in ('manifest.csv',) or rel.endswith('.log'): continue
        h = hashlib.sha256(open(p, 'rb').read()).hexdigest()
        rows.append([rel, url_for(rel), os.path.getsize(p), h, dt.datetime.fromtimestamp(os.path.getmtime(p)).strftime('%Y-%m-%d')])
rows.sort()
with open(os.path.join(root, 'manifest.csv'), 'w', newline='') as f:
    w = csv.writer(f); w.writerow(['filename', 'url', 'bytes', 'sha256', 'date']); w.writerows(rows)
print(len(rows), 'files', sum(r[2] for r in rows) / 1e6, 'MB')
