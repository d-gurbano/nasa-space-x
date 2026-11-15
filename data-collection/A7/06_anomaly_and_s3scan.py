"""Download the SPHEREx team anomalous-image list and scan the public S3 bucket for any SSO/ancillary files."""
import os, sys, re, time, requests, json
sys.path.insert(0, os.path.dirname(__file__))
from common import download, OUT
D = os.path.join(OUT, 'junk/anomaly_list'); os.makedirs(D, exist_ok=True)
pg = requests.get('https://spherex.caltech.edu/page/anomalyimages', timeout=60).text
open(os.path.join(D, 'anomalyimages_page.html'), 'w').write(pg)
links = sorted(set(re.findall(r'href="([^"]+\.csv[^"]*)"', pg)))
print('csv links', links)
for l in links:
    url = l if l.startswith('http') else 'https://spherex.caltech.edu' + l
    fn = url.split('/')[-1].split('?')[0]
    if not os.path.exists(os.path.join(D, fn)):
        download(url, os.path.join(D, fn))
# S3 listing (anonymous ListObjectsV2), top-level and a few level2 directories
S = os.path.join(OUT, 'sso_pipeline_check'); os.makedirs(S, exist_ok=True)
def ls(prefix, delim='/', maxkeys=1000):
    r = requests.get('https://nasa-irsa-spherex.s3.amazonaws.com/', params={'list-type': '2', 'prefix': prefix, 'delimiter': delim, 'max-keys': maxkeys}, timeout=120)
    pre = re.findall(r'<Prefix>([^<]*)</Prefix>', r.text)
    keys = re.findall(r'<Key>([^<]*)</Key>', r.text)
    return pre, keys, r.text
out = {}
for p in ['', 'qr3/', 'dr1/', 'qr2/', 'qr3/level2/', 'qr3/level2/2026W30_1B/', 'qr3/level2/2026W30_1B/l2b-v27-2026-222/',
          'qr3/level2/2026W30_1B/l2b-v27-2026-222/1/', 'dr1/level2/2025W30_2B/l2b-v27-2026-221/']:
    pre, keys, txt = ls(p)
    out[p] = dict(prefixes=pre[:200], keys=keys[:50], n_prefixes=len(pre), n_keys=len(keys))
    print(p, 'prefixes', pre[:15], 'keys', keys[:5], len(keys))
    time.sleep(1)
json.dump(out, open(os.path.join(S, 's3_listing_sample.json'), 'w'), indent=1)
