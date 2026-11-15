"""Snapshot CelesTrak (US, public, no login) SATCAT and current GP element sets (CSV/OMM)."""
import os, sys, time
sys.path.insert(0, os.path.dirname(__file__))
from common import download, OUT
D = os.path.join(OUT, 'satellites/celestrak_2026-11-15')
GP = 'https://celestrak.org/NORAD/elements/gp.php?GROUP={g}&FORMAT=csv'
files = {'satcat.csv': 'https://celestrak.org/pub/satcat.csv'}
for g in ['active', 'starlink', 'oneweb', 'kuiper', 'last-30-days', 'stations', 'visual', 'analyst',
          'cosmos-1408-debris', 'cosmos-2251-debris', 'iridium-33-debris', 'fengyun-1c-debris']:
    files[f'gp_{g}.csv'] = GP.format(g=g)
files['supgp_starlink.csv'] = 'https://celestrak.org/NORAD/elements/supplemental/sup-gp.php?FILE=starlink&FORMAT=csv'
for fn, url in files.items():
    p = os.path.join(D, fn)
    if os.path.exists(p):
        continue
    try:
        download(url, p, tries=3, timeout=300, headers={'User-Agent': 'Rewind-SpaceApps2026-research'})
        print(fn, os.path.getsize(p))
    except Exception as e:
        print('FAIL', fn, e)
    time.sleep(4)
