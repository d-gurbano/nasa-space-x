"""A8 - manifest.csv for data/08-ai-training: every stored file derived from a download, with its source URL,
bytes, sha256 and date. raw/*.npz are range-read subsets of one S3 L2 file each; cube/*.npz of one HiPS tile.
  python code/A8/make_manifest.py
"""
import os, sys, json, glob, hashlib, datetime, csv
import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
OUT = os.path.join(ROOT, 'data/08-ai-training')
S3 = 'https://nasa-irsa-spherex.s3.amazonaws.com/'


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def main():
    rows = []
    old = {}
    mf = os.path.join(OUT, 'manifest.csv')
    if os.path.exists(mf):
        for r in csv.DictReader(open(mf)):
            old[r['filename']] = r
    for p in sorted(glob.glob(os.path.join(OUT, 'raw', '*', '*.npz'))):
        rel = os.path.relpath(p, OUT)
        st = os.stat(p)
        if rel in old and int(old[rel]['bytes']) == st.st_size:
            rows.append(old[rel]); continue
        try:
            m = json.loads(bytes(np.load(p)['meta_json']).decode())['frame']
            url = S3 + m['key']
        except Exception:
            url = 'unreadable'
        rows.append(dict(filename=rel, url=url + ' (HTTPS byte-range subset)', bytes=st.st_size, sha256=sha(p),
                         date=datetime.datetime.fromtimestamp(st.st_mtime).isoformat(timespec='seconds')))
    reads = os.path.join(OUT, 'cube', 'cube_reads.csv')
    urlmap = {}
    if os.path.exists(reads):
        for r in csv.DictReader(open(reads)):
            urlmap[r.get('file', '')] = r['url']
    for p in sorted(glob.glob(os.path.join(OUT, 'cube', '*_cube.npz'))):
        rel = os.path.relpath(p, OUT)
        st = os.stat(p)
        npix = int(os.path.basename(p).split('_tile')[1].split('_')[0])
        url = urlmap.get(os.path.basename(p), f"{S3}dr1/hips5_cube/hips_20261026/Norder5/Dir{(npix // 10000) * 10000}/Npix{npix}_cube.fits")
        rows.append(dict(filename=rel, url=url + ' (HTTPS byte-range subset: IMAGE+NHITS rows, channel tables)', bytes=st.st_size,
                         sha256=sha(p), date=datetime.datetime.fromtimestamp(st.st_mtime).isoformat(timespec='seconds')))
    for p in sorted(glob.glob(os.path.join(OUT, 'index', 'sia_*.parquet'))):
        rel = os.path.relpath(p, OUT)
        st = os.stat(p)
        rows.append(dict(filename=rel, url='https://irsa.ipac.caltech.edu/SIA (SIA2 query, see code/A8/build_patches.py index)',
                         bytes=st.st_size, sha256=sha(p), date=datetime.datetime.fromtimestamp(st.st_mtime).isoformat(timespec='seconds')))
    with open(mf, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['filename', 'url', 'bytes', 'sha256', 'date'])
        w.writeheader()
        w.writerows(rows)
    print('manifest rows', len(rows), 'bytes', sum(int(r['bytes']) for r in rows) / 1e9, 'GB')


if __name__ == '__main__':
    main()
