"""Kaggle kernel K1 (rewind-c2-engine-all-*): run the Rewind engine on one shard of objects.

Per object: prepare (IRSA MOST + JPL Horizons) -> stamps + static-sky references (anonymous HTTPS range
reads from the public S3 bucket nasa-irsa-spherex) -> measure (photometry, controls, verdict) -> site files.
Downloads run in LANES threads; measuring is one object at a time. IRSA and JPL calls are throttled
per kernel and a circuit breaker opens after repeated 5xx answers.

Outputs (/kaggle/working): site/objects/<slug>/..., work/objects/<slug>/... (tables), run_log.txt,
run_log.jsonl (one line per object), status.json. Resumable: objects with a saved entry.json in this
output or in any attached input (e.g. an earlier version's output) are skipped.
Pixels stay in a temp folder and are not saved."""
SHARD = "__SHARD__"  # replaced by kaggle/build_inputs.py
LANES = 2
WORKERS = 12          # S3 reader threads per lane
BUDGET_H = 11.0       # stop starting new objects after this

import glob
import gzip
import json
import os
import queue
import shutil
import subprocess
import sys
import threading
import time
import traceback
from urllib.parse import urlparse

T0 = time.time()
OUT = "/kaggle/working" if os.path.isdir("/kaggle/working") else os.path.abspath("k1_out")
TMP = os.environ.get("K1_TMP") or ("/kaggle/temp" if os.path.isdir("/kaggle/temp") else "/tmp")
os.makedirs(OUT, exist_ok=True)
_LOG = open(os.path.join(OUT, "run_log.txt"), "a")
_LL = threading.Lock()


def log(msg):
    line = f"[{time.strftime('%H:%M:%S')} +{(time.time() - T0) / 60:.1f}m] {msg}"
    with _LL:
        print(line, flush=True)
        _LOG.write(line + "\n")
        _LOG.flush()


def jlog(rec):
    with _LL:
        with open(os.path.join(OUT, "run_log.jsonl"), "a") as f:
            f.write(json.dumps(rec, default=str) + "\n")


# ------------------------------------------------------------------ setup
def pip_setup():
    want = [("kete", "kete==3.3.0"), ("photutils", "photutils>=2.0"), ("astroquery", "astroquery"), ("pyarrow", "pyarrow")]
    need = []
    for mod, pkg in want:
        try:
            __import__(mod)
        except ImportError:
            need.append(pkg)
    import astropy
    if int(astropy.__version__.split(".")[0]) < 7:
        need.append("astropy>=7")
    if need:
        log(f"pip install {need}")
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", *need], check=True)


def _walk(top, depth=6):
    top = top.rstrip(os.sep)
    for d, dirs, files in os.walk(top, followlinks=True):
        if d[len(top):].count(os.sep) >= depth:
            dirs[:] = []
        yield d, dirs, files


def find_inputs():
    """The input root is the folder with MARKER next to rewind_engine/ (Kaggle may or may not keep the zip's top folder)."""
    for top in ("/kaggle/input", "."):
        for d, dirs, files in _walk(top):
            if "MARKER" in files and "rewind_engine" in dirs and "data" in dirs:
                return d
    for d, _, files in _walk("/kaggle/input"):
        for f in files:
            if f.startswith("rewind_inputs") and f.endswith((".zip", ".tar", ".tar.gz")):
                dst = os.path.join(TMP, "inputs")
                shutil.unpack_archive(os.path.join(d, f), dst)
                for d2, dirs2, files2 in _walk(dst):
                    if "MARKER" in files2 and "rewind_engine" in dirs2 and "data" in dirs2:
                        return d2
    for d, dirs, files in _walk("/kaggle/input", 3):
        log(f"input tree: {d} dirs={dirs[:10]} files={files[:10]}")
    raise SystemExit("rewind_inputs not found under /kaggle/input")


GAP_S = {"irsa.ipac.caltech.edu": 1.5, "ssd.jpl.nasa.gov": 0.5, "ssd-api.jpl.nasa.gov": 0.5}
_last, _bad, _open_until = {}, {}, {}
_TL = threading.Lock()


def polite_requests():
    """At most one call per GAP_S seconds per host (this kernel), and a circuit breaker per host+service:
    5 consecutive 5xx answers -> refuse calls to that service for 10 minutes."""
    import requests
    orig = requests.sessions.Session.request

    def request(self, method, url, *a, **k):
        u = urlparse(url)
        host = u.hostname or ""
        gap = next((g for h, g in GAP_S.items() if host == h), 0)
        if not gap:
            return orig(self, method, url, *a, **k)
        key = host + "/" + u.path.strip("/").split("/")[0]
        with _TL:
            if time.time() < _open_until.get(key, 0):
                raise requests.ConnectionError(f"circuit open for {key}")
            w = _last.get(host, 0) + gap - time.time()
            if w > 0:
                time.sleep(w)
            _last[host] = time.time()
        r = orig(self, method, url, *a, **k)
        with _TL:
            if r.status_code >= 500:
                _bad[key] = _bad.get(key, 0) + 1
                if _bad[key] >= 5:
                    _open_until[key] = time.time() + 600
                    _bad[key] = 0
                    log(f"circuit open 10 min: {key} (HTTP {r.status_code})")
            else:
                _bad[key] = 0
        return r
    requests.sessions.Session.request = request


def setup():
    pip_setup()
    root = find_inputs()
    log(f"inputs {root}: {open(os.path.join(root, 'MARKER')).read().strip()}")
    code =os.path.join(TMP, "rw_code")  # writable copy of the code (pycache), data stays in the input
    if not os.path.exists(code):
        shutil.copytree(root, code, ignore=lambda d, names: [n for n in names if n == "data"])
    os.environ["REWIND_MAIN"] = root
    os.environ["REWIND_WORK"] = os.path.join(TMP, "rwork")
    sys.path.insert(0, code)
    polite_requests()
    from rewind_engine import config as C
    C.WORKTREE = code
    C.MIN_FREE_GB = 3
    C.SITE = os.path.join(OUT, "site")
    C.ensure_dirs()
    os.makedirs(os.path.join(C.WORK, "fetch"), exist_ok=True)
    shutil.copytree(os.path.join(root, "kete-cache-seed"), C.KETE_CACHE, dirs_exist_ok=True)
    src = os.path.join(root, "realfake", "models.joblib")
    dst = os.path.join(C.WORK, "realfake", "models.joblib")
    if os.path.exists(src) and not os.path.exists(dst):
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy(src, dst)
    return root, C


# ------------------------------------------------------------------ per object
SMALL = ("frames.csv", "frame_phot.csv", "refs_plan.csv", "result.json", "entry.json", "most_error.txt",
         "crosscheck.json", "crosscheck_median.png")
GZ = ("paths_phot.csv", "most.tbl")


def save_object(C, slug, desig):
    """Copy the object's tables (big ones gzipped) and its SBDB record to OUT/work. Site files are already in OUT/site."""
    from rewind_engine.objects import slugify
    src = os.path.join(C.WORK, "objects", slug)
    dst = os.path.join(OUT, "work", "objects", slug)
    os.makedirs(dst, exist_ok=True)
    sb = os.path.join(C.WORK, "sbdb", slugify(desig) + ".json")
    if os.path.exists(sb):
        os.makedirs(os.path.join(OUT, "work", "sbdb"), exist_ok=True)
        shutil.copy(sb, os.path.join(OUT, "work", "sbdb", os.path.basename(sb)))
    for n in SMALL:
        if os.path.exists(os.path.join(src, n)):
            shutil.copy(os.path.join(src, n), os.path.join(dst, n))
    for n in GZ:
        if os.path.exists(os.path.join(src, n)):
            with open(os.path.join(src, n), "rb") as fi, gzip.open(os.path.join(dst, n + ".gz"), "wb") as fo:
                shutil.copyfileobj(fi, fo)


def done_slugs():
    """Objects already finished: entry.json in this output or in any attached input (earlier versions)."""
    out = set()
    for p in glob.glob(os.path.join(OUT, "work", "objects", "*", "entry.json")):
        out.add(p.split(os.sep)[-2])
    for p in glob.glob("/kaggle/input/**/work/objects/*/entry.json", recursive=True):
        slug = p.split(os.sep)[-2]
        if slug in out:
            continue
        base = p.rsplit(os.sep + "work" + os.sep, 1)[0]
        shutil.copytree(os.path.dirname(p), os.path.join(OUT, "work", "objects", slug), dirs_exist_ok=True)
        if os.path.isdir(os.path.join(base, "site", "objects", slug)):
            shutil.copytree(os.path.join(base, "site", "objects", slug), os.path.join(OUT, "site", "objects", slug), dirs_exist_ok=True)
        out.add(slug)
    return out


def dir_mb(p):
    return sum(os.path.getsize(os.path.join(d, f)) for d, _, fs in os.walk(p) for f in fs) / 1e6 if os.path.isdir(p) else 0.0


def main():
    root, C = setup()
    from rewind_engine import fetch as FE, frames as F, objects as O, report
    shard_csv = os.path.join(root, "kaggle", f"k1_{SHARD}.csv")
    objs = O.load_objects(shard_csv)
    done = done_slugs()
    todo = [o for o in objs.itertuples() if o.slug not in done]
    log(f"shard {SHARD}: {len(objs)} objects, {len(done)} already done, {len(todo)} to run; lanes={LANES} workers={WORKERS}")
    q = queue.Queue()
    for o in todo:
        q.put((o, 0))
    measure_lock = threading.Lock()
    stats = dict(ok=0, fail=0, stamps=0, mb=0.0)

    def lane(name):
        while True:
            try:
                o, tries = q.get_nowait()
            except queue.Empty:
                return
            if (time.time() - T0) / 3600 > BUDGET_H:
                log(f"{name}: time budget reached, not starting {o.slug}")
                jlog(dict(slug=o.slug, status="skipped_budget"))
                continue
            rec = dict(slug=o.slug, name=o.name, lane=name, t_start=time.time())
            try:
                t = time.time()
                fr = F.prepare(o)
                odir = os.path.join(C.WORK, "objects", o.slug)
                err = os.path.join(odir, "most_error.txt")
                if os.path.exists(err) and any(s in open(err).read() for s in ("GET failed", "circuit open")):
                    os.replace(err, err + f".{tries}")  # IRSA trouble, not "no frames": forget it and retry later
                    os.remove(os.path.join(odir, "frames.csv"))
                    raise RuntimeError("MOST query failed (transport/5xx)")
                rec["t_prepare_s"] = round(time.time() - t, 1)
                rec["n_frames_planned"] = int(len(fr))
                t = time.time()
                if len(fr):
                    FE.fetch_object(o, fr, workers=WORKERS)
                rec["t_fetch_s"] = round(time.time() - t, 1)
                rec["stamps_mb"] = round(dir_mb(os.path.join(C.WORK, "stamps", o.slug)) + dir_mb(os.path.join(C.WORK, "refs", o.slug)), 1)
                rec["n_stamps"] = len(glob.glob(os.path.join(C.WORK, "stamps", o.slug, "*.fits")))
                rec["n_refs"] = len(glob.glob(os.path.join(C.WORK, "refs", o.slug, "*.fits")))
                t = time.time()
                with measure_lock:
                    entry, flashes, n_read = report.run_object(o)
                rec["t_measure_s"] = round(time.time() - t, 1)
                if entry["verdict"] in ("FOUND", "HINT"):  # independent simple method while the pixels are here
                    try:
                        from rewind_engine import crosscheck
                        with measure_lock:
                            cc = crosscheck.run(o.slug, "comet" if o.kind == "comet" else "asteroid")
                        rec["crosscheck_snr"] = cc.get("snr")
                    except Exception as e:  # noqa
                        rec["crosscheck_error"] = str(e)[:200]
                save_object(C, o.slug, o.desig)
                rec.update(status="ok", verdict=entry["verdict"], best_snr=entry.get("best_snr"), n_read=n_read,
                           verdict_text=entry.get("verdict_text"))
                stats["ok"] += 1
                stats["stamps"] += rec["n_stamps"] + rec["n_refs"]
                stats["mb"] += rec["stamps_mb"]
                for sub in ("stamps", "refs"):  # pixels are not kept (temp disk)
                    shutil.rmtree(os.path.join(C.WORK, sub, o.slug), ignore_errors=True)
                log(f"{name}: {o.slug} {entry['verdict']} S/N {entry.get('best_snr')} frames {n_read} "
                    f"(prepare {rec['t_prepare_s']}s, fetch {rec['t_fetch_s']}s {rec['n_stamps']}+{rec['n_refs']} stamps "
                    f"{rec['stamps_mb']} MB, measure {rec['t_measure_s']}s)")
            except Exception as e:  # noqa
                rec.update(status="fail", error=str(e)[:500], tb=traceback.format_exc(limit=4)[-1500:], tries=tries + 1)
                log(f"{name}: {o.slug} FAILED (try {tries + 1}): {str(e)[:200]}")
                if tries < 2:  # retry at the end of the queue (IRSA/JPL hiccups)
                    q.put((o, tries + 1))
                else:
                    stats["fail"] += 1
            rec["t_total_s"] = round(time.time() - rec["t_start"], 1)
            jlog(rec)
            n_done = len(glob.glob(os.path.join(OUT, "work", "objects", "*", "entry.json")))
            el = (time.time() - T0) / 3600
            json.dump(dict(shard=SHARD, n_objects=len(objs), n_done=n_done, n_queue=q.qsize(), elapsed_h=round(el, 2),
                           ok=stats["ok"], failed=stats["fail"], stamps_read=stats["stamps"], stamps_mb=round(stats["mb"], 1),
                           updated=time.strftime("%Y-%m-%d %H:%M:%S")), open(os.path.join(OUT, "status.json"), "w"), indent=1)

    ths = [threading.Thread(target=lane, args=(f"lane{i}",), daemon=True) for i in range(LANES)]
    for t in ths:
        t.start()
    for t in ths:
        t.join()
    log(f"shard {SHARD} finished: ok={stats['ok']} failed={stats['fail']} stamps={stats['stamps']} "
        f"({stats['mb']:.0f} MB) in {(time.time() - T0) / 3600:.2f} h")


if __name__ == "__main__":
    main()
