"""Download the NASA Ames SPHEREx satellite-trail catalog (Borlaff 2026, Zenodo 17957747/17957748, CC-BY-4.0)."""
import os, sys, json, hashlib, requests, time
sys.path.insert(0, os.path.dirname(__file__))
from common import download, OUT
d = os.path.join(OUT, 'junk/trails_borlaff2026')
j = requests.get('https://zenodo.org/api/records/17957747', timeout=60).json()
json.dump(j, open(os.path.join(d if os.path.isdir(d) else (os.makedirs(d) or d), 'zenodo_record.json'), 'w'), indent=1)
for f in j['files']:
    p = os.path.join(d, f['key'])
    if os.path.exists(p):
        continue
    download(f['links']['self'], p)
    md5 = hashlib.md5(open(p, 'rb').read()).hexdigest()
    print(f['key'], f['size'], 'md5 ok' if 'md5:' + md5 == f['checksum'] else 'MD5 MISMATCH')
    time.sleep(1)
