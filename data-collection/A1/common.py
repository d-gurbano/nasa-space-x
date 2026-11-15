"""A1 shared helpers: polite GET with retry, file save + manifest row."""
import hashlib, time, pathlib, csv, requests

ROOT = pathlib.Path(__file__).resolve().parents[2]
D = ROOT / "data/01-targets"
RAW = D / "raw"
MANIFEST = D / "manifest.csv"
UA = {"User-Agent": "Rewind-SpaceApps2026-A1/1.0 (read-only research; contact via NASA Space Apps team)"}


def get(url, params=None, tries=6, timeout=300, pause=1.0, as_json=False, method="GET", json_body=None):
    last = None
    for k in range(tries):
        try:
            if method == "GET":
                r = requests.get(url, params=params, timeout=timeout, headers=UA)
            else:
                r = requests.request(method, url, json=json_body, timeout=timeout, headers=UA)
            if r.status_code == 200:
                time.sleep(pause)
                return r.json() if as_json else r
            last = f"HTTP {r.status_code} {r.text[:200]}"
            if r.status_code in (400, 404):
                break
        except Exception as ex:  # noqa
            last = str(ex)
        time.sleep(4 * 2 ** k)
    raise RuntimeError(f"failed {url} {params}: {last}")


def save(rel, content: bytes, url):
    p = RAW / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(content)
    add_manifest(p, url)
    return p


def add_manifest(p, url):
    p = pathlib.Path(p)
    h = hashlib.sha256(p.read_bytes()).hexdigest()
    new = not MANIFEST.exists()
    with open(MANIFEST, "a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["filename", "url", "bytes", "sha256", "date"])
        w.writerow([str(p.relative_to(D)), url, p.stat().st_size, h, time.strftime("%Y-%m-%dT%H:%M:%S%z")])
