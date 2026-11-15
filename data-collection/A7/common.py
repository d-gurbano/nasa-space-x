import os, hashlib, time, csv, datetime, requests
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
OUT = os.path.join(ROOT, 'data/07-answer-keys')
MAN = os.path.join(OUT, 'manifest.csv')

def sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()

def log_manifest(path, url):
    new = not os.path.exists(MAN)
    with open(MAN, 'a', newline='') as f:
        w = csv.writer(f)
        if new:
            w.writerow(['filename', 'url', 'bytes', 'sha256', 'date'])
        w.writerow([os.path.relpath(path, OUT), url, os.path.getsize(path), sha256(path),
                    datetime.datetime.now().isoformat(timespec='seconds')])

def download(url, path, tries=5, timeout=300, headers=None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    last = None
    for k in range(tries):
        try:
            with requests.get(url, stream=True, timeout=timeout, headers=headers or {}) as r:
                if r.status_code == 200:
                    tmp = path + '.part'
                    with open(tmp, 'wb') as f:
                        for c in r.iter_content(1 << 20):
                            f.write(c)
                    os.replace(tmp, path)
                    log_manifest(path, url)
                    return path
                last = f'HTTP {r.status_code} {r.text[:200]}'
        except Exception as e:
            last = repr(e)
        time.sleep(3 * (k + 1) ** 2)
    raise RuntimeError(f'{url}: {last}')
