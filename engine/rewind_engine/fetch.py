"""Step 3: pixels. Detached, resumable stamp downloader (pilot S3 byte-range reader).

Two stages per object:
  target : one compact stamp per frame, centred on the predicted position (size from the
           uncertainty ellipse and trail length).
  refs   : static-sky references - the same sky spot in other-epoch frames at the closest
           wavelength (the LVF wavelength at a pixel is fixed per detector, so the reference
           wavelength comes from the reference header WCS + our cached WCS-WAVE table).

Every finished stamp is appended to WORK/fetch/state.jsonl; outputs that exist are skipped,
so the process can be killed and restarted at any time.
Run detached:  nohup python -m rewind_engine fetch --objects first > WORK/fetch/fetch.log 2>&1 &
"""
from __future__ import annotations

import json
import os
import shutil
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np
import pandas as pd
from astropy.io import fits

from . import config as C
from .pilot import R

FETCH_DIR = os.path.join(C.WORK, "fetch")
STATE = os.path.join(FETCH_DIR, "state.jsonl")
STOP_FILE = os.path.join(FETCH_DIR, "STOP")
_lock = threading.Lock()


def free_gb(path=C.WORK) -> float:
    return shutil.disk_usage(path).free / 1e9


def log_state(rec: dict):
    with _lock:
        with open(STATE, "a") as f:
            f.write(json.dumps(rec) + "\n")


def failed_counts() -> dict:
    n = {}
    if os.path.exists(STATE):
        for line in open(STATE):
            try:
                r = json.loads(line)
            except Exception:  # noqa
                continue
            if r.get("status") != "ok":
                n[r["out"]] = n.get(r["out"], 0) + 1
    return n


def stamp_path(slug: str, file: str, kind: str = "target", ref_file: str | None = None) -> str:
    base = file.replace(".fits", "")
    if kind == "target":
        return os.path.join(C.WORK, "stamps", slug, base + ".fits")
    return os.path.join(C.WORK, "refs", slug, base + "__" + ref_file.replace(".fits", "")[-60:] + ".fits")


def read_and_save(uri, ra, dec, half, out, extra):
    from .s3read import read_stamp
    st = read_stamp(uri, ra, dec, half=int(half))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    tmp = out + ".part"
    R.save_stamp_fits(st, tmp, extra=extra)
    os.replace(tmp, out)
    return st.meta.get("bytes", 0)


def _run_jobs(jobs, workers, label):
    """jobs: list of dicts(uri, ra, dec, half, out, extra, slug, kind)."""
    fails = failed_counts()
    todo = [j for j in jobs if not os.path.exists(j["out"]) and fails.get(j["out"], 0) < 2]
    print(f"[{time.strftime('%H:%M:%S')}] {label}: {len(todo)} to read ({len(jobs) - len(todo)} done/skipped)", flush=True)
    t0, nb, nok = time.time(), 0, 0
    for i in range(0, len(todo), 60):
        if os.path.exists(STOP_FILE) or os.path.exists(STOP_FILE + "_" + LANE):
            print("STOP file found, exiting", flush=True)
            raise SystemExit(0)
        if free_gb() < C.MIN_FREE_GB:
            print(f"disk free {free_gb():.1f} GB < {C.MIN_FREE_GB} GB, stopping", flush=True)
            raise SystemExit(2)
        with ThreadPoolExecutor(workers) as ex:
            futs = {ex.submit(read_and_save, j["uri"], j["ra"], j["dec"], j["half"], j["out"], j["extra"]): j
                    for j in todo[i:i + 60]}
            for f in as_completed(futs):
                j = futs[f]
                try:
                    b = f.result()
                    nb += b
                    nok += 1
                    log_state(dict(slug=j["slug"], kind=j["kind"], out=j["out"], status="ok", t=time.time()))
                except Exception as e:  # noqa
                    log_state(dict(slug=j["slug"], kind=j["kind"], out=j["out"], status="fail", err=str(e)[:200],
                                   t=time.time()))
        dt = time.time() - t0
        print(f"[{time.strftime('%H:%M:%S')}] {label}: {min(i + 60, len(todo))}/{len(todo)} ok={nok} "
              f"{nok / dt * 60:.0f}/min {nb / 1e6 / dt:.2f} MB/s free={free_gb():.0f}GB", flush=True)


def target_jobs(slug: str, fr: pd.DataFrame, mag_cut: float = 23.5, min_keep: int = 20):
    """Skip hopeless frames (predicted mag > mag_cut) unless that leaves fewer than min_keep."""
    if len(fr) == 0:
        return []
    use = fr[fr["mag"].fillna(99) <= mag_cut]
    if len(use) < min_keep:
        use = fr.nsmallest(min(min_keep, len(fr)), "mag")
    jobs = []
    for r in use.itertuples():
        jobs.append(dict(slug=slug, kind="target", uri=r.uri, ra=r.pred_ra, dec=r.pred_dec, half=r.half,
                         out=stamp_path(slug, r.file),
                         extra=dict(RAPRED=r.pred_ra, DECPRED=r.pred_dec, MAGPRED=r.mag, SIGPX=r.sigma_px)))
    return jobs


# ------------------------------------------------------------------ static-sky references
_WAVE = {}


def det_wave_table(det: str):
    """WCS-WAVE table of a detector (identical for every frame of that detector: MEASURED)."""
    if det in _WAVE:
        return _WAVE[det]
    p = os.path.join(C.WORK, "cal", f"wcs_wave_{det}.fits")
    if os.path.exists(p):
        _WAVE[det] = np.asarray(fits.open(p)[1].data)
        return _WAVE[det]
    return None


def save_det_wave(det: str, stamp_file: str):
    p = os.path.join(C.WORK, "cal", f"wcs_wave_{det}.fits")
    if os.path.exists(p) or not os.path.exists(stamp_file):
        return
    os.makedirs(os.path.dirname(p), exist_ok=True)
    h = fits.open(stamp_file)
    if "WCS-WAVE" in h:
        fits.BinTableHDU(h["WCS-WAVE"].data, name="WCS-WAVE").writeto(p, overwrite=True)


def image_header(uri: str):
    """IMAGE HDU header with two small range reads (PRIMARY + IMAGE header)."""
    url = R.S3_HTTP + uri.split("ibe/data/spherex/", 1)[1]
    st = dict(bytes=0, requests=0)
    h0, l0 = R._read_header(url, 0, st)
    h1, _ = R._read_header(url, l0 + R._data_len(h0), st)
    return h1


def _hdr_cache_path(file):
    return os.path.join(C.WORK, "hdr", file.replace(".fits", ".hdr"))


def cached_wcs(uri: str):
    from astropy.wcs import WCS
    f = uri.split("/")[-1]
    p = _hdr_cache_path(f)
    if os.path.exists(p):
        h = fits.Header.fromtextfile(p)
    else:
        h = image_header(uri)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        keep = fits.Header([c for c in h.cards if c.keyword not in ("COMMENT", "HISTORY", "")])
        keep.totextfile(p, overwrite=True)
        h = keep
    return R._celestial_wcs(h), h


_SIA = dict(fails=0, until=0.0)


def _sia_once(ra, dec, coll, radius):
    """One SIA2 try (60 s timeout); the pilot helper retries 4x with long timeouts, too slow when IRSA is down."""
    import io
    import requests
    from astropy.io.votable import parse_single_table
    p = dict(COLLECTION=coll, POS=f"CIRCLE {ra} {dec} {radius}", RESPONSEFORMAT="VOTABLE", MAXREC="5000")
    r = requests.get(R.SIA2_URL, params=p, timeout=60)
    if r.status_code != 200:
        raise RuntimeError(f"HTTP {r.status_code}")
    df = parse_single_table(io.BytesIO(r.content)).to_table(use_names_over_ids=True).to_pandas()
    for c in df.columns:
        if df[c].dtype == object:
            df[c] = df[c].astype(str)
    return df


def sia_candidates(ra, dec, radius=0.005):
    """SIA2 fallback with a circuit breaker: after 3 failures in a row, skip SIA2 for 20 minutes."""
    if time.time() < _SIA["until"]:
        return pd.DataFrame()
    rows = []
    for coll in ("spherex_qr3", "spherex_dr1"):
        try:
            rows.append(_sia_once(ra, dec, coll, radius))
            _SIA["fails"] = 0
        except Exception as e:  # noqa
            _SIA["fails"] += 1
            print("SIA2 fail", coll, str(e)[:80], flush=True)
            if _SIA["fails"] >= 3:
                _SIA["until"] = time.time() + 1200
                print("SIA2 circuit open for 20 min", flush=True)
                break
        time.sleep(1.0)
    if not rows:
        return pd.DataFrame()
    s = pd.concat(rows, ignore_index=True)
    s = s[s.access_url.str.contains("spx_l2b")].copy()
    s["uri"] = "ibe/" + s.access_url.str.split("/ibe/", n=1).str[1]
    s["file"] = s.uri.str.split("/").str[-1]
    s["det"] = s.file.str.extract(r"_\d(D\d)_spx")[0]
    return s.drop_duplicates("file")


def most_candidates(slug):
    """All MOST frames of the object (also the ones not selected): each one covers a 3.5 deg patch
    around the object's position at that time, so it is a static-sky candidate for nearby spots."""
    p = os.path.join(C.WORK, "objects", slug, "most.tbl")
    if not os.path.exists(p):
        return pd.DataFrame()
    m = R.most_query("", "", "", cache=p)
    m["t_min"] = m.mjd_start.astype(float)
    m["det"] = m.productid.astype(str)
    return m[["uri", "file", "det", "t_min", "ra_obj", "dec_obj"]].drop_duplicates("file")


def _sep_deg(ra1, dec1, ra2, dec2):
    r1, d1, r2, d2 = map(np.radians, (ra1, dec1, ra2, dec2))
    c = np.sin(d1) * np.sin(d2) + np.cos(d1) * np.cos(d2) * np.cos(r1 - r2)
    return np.degrees(np.arccos(np.clip(c, -1, 1)))


def plan_refs(slug: str, fr: pd.DataFrame, n_ref: int = 2, max_frames: int = 150, max_cand: int = 16, workers: int = 8):
    """For each target frame: up to n_ref other-epoch frames covering the same spot whose wavelength
    at that spot is closest to the target's. Candidates: the object's own MOST frames within 1.2 deg,
    else IRSA SIA2. Writes WORK/objects/<slug>/refs_plan.csv."""
    d = os.path.join(C.WORK, "objects", slug)
    out = os.path.join(d, "refs_plan.csv")
    if os.path.exists(out) and os.path.getsize(out) > 200:
        return pd.read_csv(out)
    ok = [r for r in fr.itertuples() if os.path.exists(stamp_path(slug, r.file))]
    ok = sorted(ok, key=lambda r: r.score)[:max_frames]
    for r in ok:
        save_det_wave(r.det, stamp_path(slug, r.file))
    most = most_candidates(slug)
    sel = {}
    for r in ok:
        rate_px_day = max(r.rate_arcsec_hr * 24 / C.PIX_ARCSEC, 1e-3)
        comet = slug.startswith(("c20", "p20", "3i")) or "/" in str(getattr(r, "desig", ""))
        dt_min = max((40.0 if comet else 5.0 + r.trail_px) / rate_px_day, 0.25)  # object (comets: coma) moved away
        cc = pd.DataFrame()
        if len(most):
            near = _sep_deg(most.ra_obj.values, most.dec_obj.values, r.pred_ra, r.pred_dec) < 1.2
            cc = most[near & (most.det == r.det) & (np.abs(most.t_min - r.mjd_avg) > dt_min)]
        if len(cc) < 3:
            sc = sia_candidates(r.pred_ra, r.pred_dec)
            if len(sc):
                cc = pd.concat([cc, sc[(sc.det == r.det) & (np.abs(sc.t_min - r.mjd_avg) > dt_min)]]).drop_duplicates("file")
        if len(cc) > max_cand:  # sample evenly in time (wavelength is only known after reading the header)
            cc = cc.sort_values("t_min").iloc[np.linspace(0, len(cc) - 1, max_cand).astype(int)]
        sel[r.file] = (r, cc)
    uris = sorted({u for _, cc in sel.values() for u in cc.uri})
    with ThreadPoolExecutor(workers) as ex:
        wcs = dict(zip(uris, ex.map(lambda u: _safe(cached_wcs, u), uris)))
    plan = []
    for f, (r, cc) in sel.items():
        wt = det_wave_table(r.det)
        if wt is None or not len(cc):
            continue
        wt = wt[0] if wt.ndim else wt
        lam_t = R.wavelength_at(wt, *R_target_xy(fits.getheader(stamp_path(slug, r.file))))[0]
        scored = []
        for q in cc.itertuples():
            w = wcs.get(q.uri)
            if w is None:
                continue
            xf, yf = w[0].all_world2pix([[r.pred_ra, r.pred_dec]], 0)[0]
            if not (8 <= xf < 2032 and 8 <= yf < 2032):
                continue
            lam, bw = R.wavelength_at(wt, xf, yf)
            scored.append((abs(lam - lam_t) / max(bw, 1e-3), q.uri, q.file, q.t_min, lam, bw))
        scored.sort()
        for s in scored[:n_ref]:
            plan.append(dict(file=r.file, det=r.det, ra=r.pred_ra, dec=r.pred_dec, wave_target=lam_t,
                             ref_uri=s[1], ref_file=s[2], ref_mjd=s[3], ref_wave=s[4], ref_bw=s[5],
                             dlam_over_bw=s[0], dt_days=s[3] - r.mjd_avg))
    df = pd.DataFrame(plan)
    df.to_csv(out, index=False)
    return df


def _safe(fn, *a):
    try:
        return fn(*a)
    except Exception:  # noqa
        return None


def R_target_xy(hdr):
    """Full-frame position of the predicted target in a saved stamp (centre pixel)."""
    n = hdr["NAXIS1"]
    return hdr["X0FULL"] + (n - 1) / 2, hdr["Y0FULL"] + (n - 1) / 2


def ref_jobs(slug: str, plan: pd.DataFrame):
    jobs = []
    for p in plan.itertuples():
        jobs.append(dict(slug=slug, kind="ref", uri=p.ref_uri, ra=p.ra, dec=p.dec, half=20,
                         out=stamp_path(slug, p.file, "ref", p.ref_file), extra=dict(RAPRED=p.ra, DECPRED=p.dec)))
    return jobs


LANE = os.environ.get("REWIND_LANE", "A")
LOCK = os.path.join(FETCH_DIR, "lock" if LANE == "A" else f"lock_{LANE}")
CAP_Y1, CAP_OTHER = 300, 120  # frames per object: Y1 candidates and S1 keep 300, others the 120 most useful


def frame_cap(o) -> tuple[int, int]:
    """(max frames, static-sky references per frame) for an object."""
    big = bool(getattr(o, "y1", False)) or o.slug == "c2026s1"
    return (CAP_Y1, 2) if big else (CAP_OTHER, 1)


def _heartbeat():
    while True:
        with open(LOCK, "w") as f:
            f.write(f"{os.getpid()} {time.time()}")
        time.sleep(30)


def run(objs, workers: int = 8, refs: bool = True):
    """One fetch process per lane (env REWIND_LANE, default A): a lock file with a 30 s heartbeat; a second
    process in the same lane exits. Stop one lane with WORK/fetch/STOP_<lane>, all lanes with STOP."""
    from . import frames as F
    os.makedirs(FETCH_DIR, exist_ok=True)
    if os.path.exists(LOCK) and time.time() - os.path.getmtime(LOCK) < 120:
        print("another fetch process is running (fresh lock), exiting", flush=True)
        return
    threading.Thread(target=_heartbeat, daemon=True).start()
    first = ["c2026s1", "eros", "2025oz"]
    objs = objs.assign(_o=[0 if s in first else (1 if getattr(o, "y1", False) else 2) for s, o in zip(objs.slug, objs.itertuples())])
    for o in objs.sort_values("_o", kind="stable").itertuples():
        try:  # each object complete (stamps, then static-sky references) before the next
            fr = F.prepare(o)
        except Exception as e:  # noqa
            print("prepare failed", o.slug, str(e)[:300], flush=True)
            continue
        fetch_object(o, fr, workers, refs)
    print(f"[{time.strftime('%H:%M:%S')}] fetch done", flush=True)


def fetch_object(o, fr: pd.DataFrame, workers: int = 8, refs: bool = True):
    """Stamps, then static-sky references, of one prepared object (no lock: callers own the lane)."""
    cap, nref = frame_cap(o)
    if len(fr) > cap:
        fr = fr.nsmallest(cap, "score")
    _run_jobs(target_jobs(o.slug, fr), workers, f"{o.slug} target")
    if refs and len(fr):
        try:
            plan = plan_refs(o.slug, fr, n_ref=nref, max_frames=min(150, cap))
            _run_jobs(ref_jobs(o.slug, plan), workers, f"{o.slug} refs")
        except Exception as e:  # noqa
            print("refs failed", o.slug, str(e)[:300], flush=True)
