"""'Tune the Rewind' game data: shift-and-stack by hand.

Each round: 8-24 real SPHEREx exposures of ONE fixed sky patch (64x64 native SPHEREx pixels, north up / east left,
4x nearest-neighbour -> 256x256 PNG, one shared stretch), with the static sky removed (per-pixel median of the
round's own frames, which keeps stars but not the moving object), while a known asteroid or a Rewind find crosses.
Truth: motion in output-PNG pixels per hour and its angle (0 = up/north, clockwise). Verified: the stack at the
truth motion vs random wrong motions (snr_truth, snr_wrong_p95); rounds where the truth does not clearly pop are dropped.

    python -c "from rewind_engine import game; game.build()"
"""
from __future__ import annotations

import glob
import json
import os
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd
from PIL import Image
from scipy.ndimage import shift as nd_shift, uniform_filter

from . import config as C
from . import images as IM
from .pilot import R
from .s3read import read_stamp

N = 64            # grid pixels (native SPHEREx 6.15")
UP = 4            # -> 256 px PNG
OUTS = [os.path.join(C.SITE, "game"),
        "/Users/rahmanbazarov/Data/programming/SpaceApps2026-Rewind-c2-o-game/web/public/data/game"]
CANDIDATES = [  # (slug, object name, frames.csv source, detectors to use)
    ("bench-2525", "(2525) O'Steen", None, None), ("bench-1542", "(1542) Schalen", None, None),
    ("bench-2037", "(2037) Tripaxeptalis", None, None), ("bench-2847", "(2847) Parvati", None, None),
    ("bench-2699", "(2699) Kalinin", None, None), ("b2-152679", "(152679) 1998 KU2 (near-Earth)", None, None),
    ("bench-9450", "(9450) Akikoizumo", None, None), ("bench-7556", "(7556) Perinaldo", None, None),
    ("bench-15905", "(15905) Berthier", None, None), ("b2-11500", "(11500) Tomaiyowit (near-Earth)", None, None),
    ("bench-22015", "(22015) 1999 XM100", None, None), ("bench-12141", "(12141) Chushayashi", None, None),
    # 2025 YH5 shows only in its own thermal glow (D5 per-frame S/N ~7.6, D2 ~0.8): long-wavelength detectors only
    ]


def _frames(slug, src):
    if src == "kaggle":
        p = sorted(glob.glob(os.path.join(C.DATA, "kaggle", "rewind-c2-engine-all-*", "work", "objects", slug, "frames.csv")))[-1]
    else:
        p = os.path.join(C.WORK, "objects", slug, "frames.csv")
    f = pd.read_csv(p).sort_values("mjd_avg").drop_duplicates("mjd_avg").reset_index(drop=True)
    if "true_ra" not in f:
        f["true_ra"], f["true_dec"] = f.pred_ra, f.pred_dec
    return f


def _offsets(ra, dec, ra0, dec0):
    e = ((ra - ra0 + 180) % 360 - 180) * np.cos(np.radians(dec0)) * 3600
    n = (dec - dec0) * 3600
    return e, n


def pick_window(f, min_px=4, max_px=40, nmin=8, nmax=24, max_span_d=6.0):
    """Most frames within max_span_d whose total motion stays inside the patch."""
    t = f.mjd_avg.values
    best = None
    for i in range(len(f)):
        for j in range(i + nmin - 1, len(f)):
            if t[j] - t[i] > max_span_d:
                break
            e, n = _offsets(f.true_ra.values[j], f.true_dec.values[j], f.true_ra.values[i], f.true_dec.values[i])
            mot = np.hypot(e, n) / C.PIX_ARCSEC
            if min_px <= mot <= max_px:
                idx = list(range(i, j + 1))
                if len(idx) > nmax:
                    idx = list(np.unique(np.round(np.linspace(i, j, nmax)).astype(int)))
                if best is None or len(idx) > len(best[0]):
                    best = (idx, mot)
    return best


def grid_images(f, idx, ra0, dec0):
    half_as = C.PIX_ARCSEC * (N - 1) / 2

    def one(k):
        r = f.iloc[k]
        st = read_stamp(r.uri, ra0, dec0, half=48)
        return IM.north_up(st, ra0, dec0, half_arcsec=half_as, scale=C.PIX_ARCSEC, order=1)
    with ThreadPoolExecutor(8) as ex:
        return list(ex.map(one, idx))


_REF_CACHE = {}


def ref_images(f, idx, ra0, dec0, n_ref=2, min_px=50.0):
    """Static-sky references for each frame (as the engine): other exposures of the same detector that cover the patch
    while the object is >= min_px from the patch centre, the n_ref closest in wavelength at the centre; their median
    on the same grid. Returns a list of images (None where no reference)."""
    from . import fetch as FE
    half_as = C.PIX_ARCSEC * (N - 1) / 2
    e, n = _offsets(f.true_ra.values, f.true_dec.values, ra0, dec0)
    away = np.hypot(e, n) / C.PIX_ARCSEC >= min_px
    lam = {}

    def lam_at(k):
        if k not in lam:
            r = f.iloc[k]
            try:
                w, _ = FE.cached_wcs(r.uri)
                x, y = w.all_world2pix([[ra0, dec0]], 0)[0]
                wt = FE.det_wave_table(r.det)
                lam[k] = R.wavelength_at(wt[0] if wt.ndim else wt, x, y)[0] if 40 <= x < 2000 and 40 <= y < 2000 else np.nan
            except Exception:  # noqa
                lam[k] = np.nan
        return lam[k]

    def img(k):
        key = (f.uri.values[k], round(ra0, 6), round(dec0, 6))
        if key not in _REF_CACHE:
            st = read_stamp(f.uri.values[k], ra0, dec0, half=48)
            _REF_CACHE[key] = IM.north_up(st, ra0, dec0, half_arcsec=half_as, scale=C.PIX_ARCSEC, order=1)
        return _REF_CACHE[key]
    out = []
    for i in idx:
        li = lam_at(i)
        cand = [k for k in range(len(f)) if away[k] and f.det.values[k] == f.det.values[i] and k != i]
        sc = sorted(((abs(lam_at(k) - li), k) for k in cand if np.isfinite(lam_at(k))), key=lambda x: x[0])[:n_ref]
        refs = []
        for _, k in sc:
            try:
                a = img(k)
                if np.isnan(a).mean() < 0.15:
                    refs.append(a)
            except Exception:  # noqa
                pass
        out.append(np.nanmedian(refs, 0) if refs else None)
    return out


def truth_motion(f, idx, ra0, dec0):
    """Positions in output-PNG pixels (x right, y down) and a linear fit: rate (px/hr) and angle (0 = up, clockwise)."""
    t0 = f.mjd_avg.values[idx[0]]
    dt = (f.mjd_avg.values[idx] - t0) * 24
    e, n = _offsets(f.true_ra.values[idx], f.true_dec.values[idx], ra0, dec0)
    k = (N - 1) / 2
    x = (k - e / C.PIX_ARCSEC + 0.5) * UP
    y = (k - n / C.PIX_ARCSEC + 0.5) * UP
    vx, x0 = np.polyfit(dt, x, 1)
    vy, y0 = np.polyfit(dt, y, 1)
    rate = float(np.hypot(vx, vy))
    ang = float(np.degrees(np.arctan2(vx, -vy)) % 360)
    return dt, x, y, rate, ang, (x0, y0)


def stack_at(res, dt, rate, ang, how="clipped"):
    """Shift frame i by -rate*dt along ang (PNG px -> grid px) and average."""
    vx, vy = rate * np.sin(np.radians(ang)) / UP, -rate * np.cos(np.radians(ang)) / UP  # grid px per hr, y down
    out = []
    for a, t in zip(res, dt):
        b = np.nan_to_num(a[::-1], nan=0.0)  # array row 0 = north after the flip (PNG orientation)
        out.append(nd_shift(b, (-vy * t, -vx * t), order=1, mode="constant", cval=np.nan))
    a = np.array(out)
    med = np.nanmedian(a, 0)
    if how == "median":  # verification: a dot seen in only one frame (wrong motion) does not survive a median
        return np.nan_to_num(med)
    mad = 1.4826 * np.nanmedian(np.abs(a - med), 0)
    keep = np.abs(a - med) <= 3 * np.where(mad > 0, mad, np.inf)  # per-pixel clip: one-frame star leftovers drop out
    with np.errstate(invalid="ignore"):
        return np.nan_to_num(np.nanmean(np.where(keep, a, np.nan), 0))


def peak_snr(img, xy0):
    """3x3-aperture sum at the object's start position (grid px from the PNG position, best of +-1 px) divided by the
    robust spread of 3x3 sums over the whole stack (empirical S/N)."""
    a = uniform_filter(img, 3) * 9
    m = a[4:-4, 4:-4]
    sd = 1.4826 * np.median(np.abs(m - np.median(m)))
    x, y = int(round(xy0[0] / UP - 0.5)), int(round(xy0[1] / UP - 0.5))
    v = a[max(y - 1, 0):y + 2, max(x - 1, 0):x + 2].max() if 0 <= x < N and 0 <= y < N else np.nan
    return float((v - np.median(m)) / sd) if sd > 0 else 0.0


def build(rng_seed=1, n_wrong=200):
    rng = np.random.default_rng(rng_seed)
    rounds, sheet = [], []
    for slug, name, src, dets in CANDIDATES:
        try:
            f = _frames(slug, src)
            if dets:
                f = f[f.det.isin(dets)].reset_index(drop=True)
            w = pick_window(f) or pick_window(f, nmin=6)  # 6-frame windows only when no 8-frame window exists
            if not w:
                print("skip", slug, "no window", flush=True)
                continue
            idx, mot = w
            e, n = f.true_ra.values[[idx[0], idx[-1]]], f.true_dec.values[[idx[0], idx[-1]]]
            ra0, dec0 = float(np.mean(e)), float(np.mean(n))
            imgs = grid_images(f, idx, ra0, dec0)
            ok = [k for k, a in enumerate(imgs) if np.isnan(a).mean() <= 0.15]  # drop exposures that miss the patch
            if len(ok) < 6:
                print("skip", slug, "patch not covered", flush=True)
                continue
            idx, imgs = [idx[k] for k in ok], [imgs[k] for k in ok]
            refs = ref_images(f, idx, ra0, dec0)
            keep = [k for k, r_ in enumerate(refs) if r_ is not None]
            variants = []
            if len(keep) >= 6:  # preferred: engine-style static-sky references at the closest wavelength
                variants.append(("references", [idx[k] for k in keep], [imgs[k] - refs[k] for k in keep]))
            med = np.nanmedian(imgs, 0)  # fallback: the per-pixel median of the round's own frames
            variants.append(("round median", idx, [a - med for a in imgs]))
            best = None
            for how, idx_v, res in variants:
                dt, x, y, rate, ang, p0 = truth_motion(f, idx_v, ra0, dec0)
                xy0 = (x[0], y[0])
                s_true = peak_snr(stack_at(res, dt, rate, ang, "median"), xy0)
                wrong = []
                for _ in range(n_wrong):
                    r2, a2 = rng.uniform(0, 2 * rate + 1), rng.uniform(0, 360)
                    if np.hypot(r2 * np.sin(np.radians(a2)) - rate * np.sin(np.radians(ang)),
                                r2 * np.cos(np.radians(a2)) - rate * np.cos(np.radians(ang))) * dt[-1] < 2 * UP * 2:
                        continue
                    wrong.append(peak_snr(stack_at(res, dt, r2, a2, "median"), xy0))
                p95 = float(np.percentile(wrong, 95))
                print(slug, how, f"n={len(idx_v)} snr_truth={s_true:.1f} wrong_p95={p95:.1f}", flush=True)
                if s_true >= 6 and s_true >= 1.5 * p95:
                    best = (how, idx_v, res, dt, x, y, rate, ang, s_true, p95)
                    break
            if best is None:
                print("drop", slug, "truth does not clearly pop", flush=True)
                continue
            how, idx, res, dt, x, y, rate, ang, s_true, p95 = best
            rounds.append(dict(slug=slug, name=name, res=res, sky=how, dt=dt, rate=rate, ang=ang, s_true=s_true, p95=p95, n=len(idx),
                               mot=mot, xy=list(zip(x, y)), wrong_example=(rng.uniform(0, 2 * rate + 1), (ang + 90) % 360),
                               iso=[f.iso.values[i][:19] if "iso" in f else "" for i in idx]))
        except Exception as ex:  # noqa
            import traceback
            traceback.print_exc()
            print("skip", slug, str(ex)[:150], flush=True)
    try:
        g = guided_yh5()
    except Exception as ex:  # noqa
        print("guided YH5 failed", str(ex)[:150], flush=True)
        g = None
    return write(rounds, g)


def write(rounds, guided=None):
    yh5 = [r for r in rounds if r["slug"] == "2025yh5"]
    rest = sorted([r for r in rounds if r["slug"] != "2025yh5"], key=lambda r: -r["s_true"] / np.sqrt(r["n"]))
    rounds = rest[:7] + yh5
    out, sheet = [], []
    for i, r in enumerate(rounds):
        rid = f"g{i + 1:02d}"
        per_frame = r["s_true"] / np.sqrt(r["n"])
        diff = "easy" if per_frame >= 5 else ("medium" if per_frame >= 2.5 else "hard")
        if r["slug"] == "2025yh5":
            diff = "hard"
        v = np.concatenate([a[np.isfinite(a)].ravel() for a in r["res"]])
        sd = 1.4826 * np.median(np.abs(v - np.median(v)))
        lo, hi = np.median(v) - 2.5 * sd, np.median(v) + 8 * sd
        frames = []
        for k, (a, t) in enumerate(zip(r["res"], r["dt"])):
            p = f"{rid}/f{k:02d}.png"
            for o in OUTS:
                os.makedirs(os.path.join(o, rid), exist_ok=True)
                IM.save(a, os.path.join(o, p), lo, hi, upscale=UP)
            frames.append(dict(png=p, dt_hr=round(float(t), 4), iso=r["iso"][k]))
        is_find = r["slug"] == "2025yh5"
        explain = (f"{r['name']} moves {r['rate']:.1f} pixels per hour on this picture. Slide each photo back by its time and the "
                   f"faint dot lines up: SPHEREx saw it in {r['n']} photos over {r['dt'][-1]:.1f} hours.")
        if is_find:
            explain = (f"This is a real Rewind find: 2025 YH5, a potentially hazardous asteroid, in SPHEREx photos taken before "
                       f"anyone had seen it. In a single photo it is lost in the noise; lined up correctly, {r['n']} photos make it pop.")
        out.append(dict(id=rid, title=("A real Rewind find" if is_find else f"Round {i + 1}: {r['name'].split(' (')[0]}"),
                        object=r["name"], truth=dict(angle_deg=round(r["ang"], 1), rate_px_per_hr=round(r["rate"], 3)),
                        frames=frames, explain=explain, difficulty=diff, snr_truth=round(r["s_true"], 1),
                        snr_wrong_p95=round(r["p95"], 1), track_xy=[[round(float(x), 1), round(float(y), 1)] for x, y in r["xy"]],
                        motion_px_grid=round(float(r["mot"]), 1), static_sky=r["sky"]))
        sheet.append((rid, r))
    order = {"easy": 0, "medium": 1, "hard": 2}
    last = [o for o in out if o["object"].startswith("2025 YH5")]
    out = sorted([o for o in out if not o["object"].startswith("2025 YH5")], key=lambda o: (order[o["difficulty"]], -o["snr_truth"])) + last
    for i, o in enumerate(out):  # ids follow the easy-to-hard order (PNG folders keep their build ids)
        o["title"] = o["title"].replace(o["title"].split(":")[0], f"Round {i + 1}") if o["title"].startswith("Round") else o["title"]
    if guided:
        rid = "g_yh5"
        stacks = []
        allv = np.concatenate([a[np.isfinite(a)].ravel() for _, a, _ in guided["stacks"]])
        sd = 1.4826 * np.median(np.abs(allv - np.median(allv)))
        lo, hi = np.median(allv) - 2.5 * sd, np.median(allv) + 10 * sd
        for name, a, snr in guided["stacks"]:
            p = f"{rid}/{name}.png"
            for o in OUTS:
                os.makedirs(os.path.join(o, rid), exist_ok=True)
                IM.save(a, os.path.join(o, p), lo, hi, upscale=4)
            stacks.append(dict(label=name, png=p, snr=round(float(snr), 1)))
        ex = {s_["label"]: s_["snr"] for s_ in stacks}
        out.append(dict(id=rid, mode="guided", title="A real Rewind find", object="2025 YH5 (Rewind find, potentially hazardous)",
                        truth=dict(angle_deg=round(guided["angle"], 1), rate_arcsec_per_hr=round(guided["rate_arcsec_hr"], 1)),
                        frames=[], stacks=stacks, difficulty="hard", snr_truth=ex.get("exact"), snr_wrong_p95=None,
                        snr_wrong=ex.get("wrong"), snr_close=ex.get("close"),
                        explain=(f"2025 YH5, a potentially hazardous asteroid, moves about {guided['rate_arcsec_hr'] / C.PIX_ARCSEC:.0f} "
                                 f"SPHEREx pixels per hour, too fast to stay in one patch, so here Rewind does the shifting for you. "
                                 f"These are {guided['n']} real sky-cleaned SPHEREx photos from before anyone had seen it, stacked with a "
                                 f"wrong motion, a close one and the exact one: it pops only when the motion is right."),
                        note=("guided: stacks of the real cleaned frames (target minus static-sky references, long-wavelength "
                              "detectors where its thermal glow shows), centred on the predicted track; wrong/close = the median frame "
                              "drifts ~4 px / ~1 px off the track. S/N = 3x3-aperture sum at the centre vs the robust spread (MEASURED).")))
    doc = dict(schema="rewind-game-v1", sample=False,
               note=("Frames: real SPHEREx exposures of one fixed 64x64-pixel patch (6.15 arcsec pixels, north up, east left), "
                     "static sky removed (other-epoch SPHEREx exposures of the same patch at the closest wavelength, as in the engine), 4x nearest-neighbour to 256x256, one stretch per round. "
                     "truth: shift frame i by -rate_px_per_hr*dt_hr along angle_deg (0 = up, clockwise) and sum. snr_truth / "
                     "snr_wrong_p95: empirical S/N at the object's start position in the MEDIAN stack at the truth motion vs 100 random wrong motions (MEASURED)."),
               rounds=out)
    for o in OUTS:
        os.makedirs(o, exist_ok=True)
        json.dump(doc, open(os.path.join(o, "rounds.json"), "w"), indent=1)
    contact_sheet(sheet, guided)
    return doc


def contact_sheet(items, guided=None, path="/tmp/c2/shots/game-rounds.png"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    S = 256
    canvas = Image.new("L", (S * 3, S * (len(items) + (1 if guided else 0))), 0)
    for i, (rid, r) in enumerate(items):
        for j, (rate, ang) in enumerate([(r["rate"], r["ang"]), r["wrong_example"]]):
            a = stack_at(r["res"], r["dt"], rate, ang)
            v = a[np.isfinite(a)]
            sd = 1.4826 * np.median(np.abs(v - np.median(v)))
            x = np.clip((a - np.median(v) + 2 * sd) / (10 * sd), 0, 1)
            im = Image.fromarray((x * 255).astype(np.uint8)).resize((S, S), Image.NEAREST)  # already north-up (flipped)
            canvas.paste(im, (j * S, i * S))
    if guided:  # last row: wrong, close, exact
        for j, (_, a, _) in enumerate(guided["stacks"]):
            v = a[np.isfinite(a)]
            sd = 1.4826 * np.median(np.abs(v - np.median(v)))
            x = np.clip((np.nan_to_num(a) - np.median(v) + 2 * sd) / (12 * sd), 0, 1)[::-1]
            canvas.paste(Image.fromarray((x * 255).astype(np.uint8)).resize((S, S), Image.NEAREST), (j * S, len(items) * S))
    canvas.save(path)


def guided_yh5(slug="2025yh5", dets=("D4", "D5", "D6")):
    """2025 YH5 cannot cross one fixed patch in >= 8 exposures (it moves 23-33 px/hr and its long-wavelength exposures come
    in bursts hours apart), so the final round is a guided reveal: its real sky-cleaned frames (target minus the engine's
    static-sky references) of one day, stacked three ways: a wrong motion, a close motion and the exact motion."""
    from . import fetch as FE
    from .pipeline import load_refs
    f = pd.read_csv(os.path.join(C.WORK, "objects", slug, "frames.csv"))
    f = f[f.det.isin(dets) & np.array([os.path.exists(FE.stamp_path(slug, x)) for x in f.file])].sort_values("mjd_avg")
    day = int(f.mjd_avg.astype(int).min())  # all fetched days (bursts hours to days apart)
    f = f.reset_index(drop=True)
    ts = np.unique(np.round(f.mjd_avg.values, 4))
    # reference time between two exposure times: under a wrong motion every frame is displaced (no frame sits at dt = 0)
    tmid = float((ts[len(ts) // 2 - 1] + ts[len(ts) // 2]) / 2) if len(ts) > 1 else float(ts[0])
    stamps = [R.load_stamp_fits(FE.stamp_path(slug, r.file)) for r in f.itertuples()]
    refs = [load_refs(slug, r.file, r.rate_arcsec_hr, False, r.trail_px) for r in f.itertuples()]
    v = np.c_[f.rate_ra.values, f.rate_dec.values].mean(0)  # arcsec/hr (east, north)

    def stack(dv):
        imgs = []
        for st, rf, r in zip(stamps, refs, f.itertuples()):
            t = (r.mjd_avg - tmid) * 24
            ra, dec = R.offset_radec(r.pred_ra, r.pred_dec, dv[0] * t, dv[1] * t)
            a = IM.north_up(st, ra, dec, half_arcsec=48, scale=1.5, order=1)
            if rf:
                a = a - np.nanmedian([IM.north_up(s2, ra, dec, half_arcsec=48, scale=1.5, order=1) for s2 in rf], 0)
            imgs.append(a)
        return np.nanmedian(imgs, 0)  # median: a dot seen in one frame only (the reference-time frame) does not survive

    def rot(vec, deg, scale):
        c, s_ = np.cos(np.radians(deg)), np.sin(np.radians(deg))
        return np.array([c * vec[0] - s_ * vec[1], s_ * vec[0] + c * vec[1]]) * scale
    tmax = float(np.median(np.abs((f.mjd_avg.values - tmid) * 24)))  # sized on the median frame
    unit = rot(v, 60, 1.0) / np.hypot(*v)  # a direction off the motion
    # wrong: the median frame drifts ~4 px (25"); close: ~1 px (6")
    variants = [("wrong", unit * 4 * C.PIX_ARCSEC / tmax), ("close", unit * 1.0 * C.PIX_ARCSEC / tmax), ("exact", np.zeros(2))]
    out = []
    k = None
    for name, dv in variants:
        a = stack(dv)
        k = (a.shape[0] - 1) // 2
        b = np.nan_to_num(a)
        s3 = uniform_filter(b, 3) * 9
        m = s3[4:-4, 4:-4]
        sd = 1.4826 * np.median(np.abs(m - np.median(m)))
        snr = float((s3[k - 1:k + 2, k - 1:k + 2].max() - np.median(m)) / sd)
        out.append((name, a, snr))
    span = (f.mjd_avg.max() - f.mjd_avg.min()) * 24
    rate_png = float(np.hypot(*v) / 1.5 * 4 * (256 / (4 * 65)))
    return dict(f=f, stacks=out, n=len(f), span_h=span, rate_arcsec_hr=float(np.hypot(*v)),
                angle=float(np.degrees(np.arctan2(v[0], v[1])) % 360), day=int(day))
