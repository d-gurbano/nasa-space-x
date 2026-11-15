"""site/detectives/rounds.json v2: "is there a moving dot?" rounds built from 4-6 real SPHEREx exposures of the SAME
fixed patch of sky (north up, east left, nearest-neighbour pixels, one shared stretch per round), spread over hours.

known   : a catalogued asteroid (benchmark set, true JPL Horizons positions) visibly moves >= ~3 px.
planted : a fake source added with the real ePSF along a straight track (revealed after answering).
empty   : the same kind of frames with nothing moving (grid placed 80" off an undetected object's path).
real    : a Rewind FOUND object, only if it is visible on a fixed grid (our finds are stack-only, so none qualify).
v1 fields (id, images, truth, answer_xy, explain) are kept."""
from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd

from . import config as C
from . import fetch as FE
from . import images as IM
from . import phot as PH
from .pilot import R

OUT = os.path.join(C.SITE, "detectives")
TOL_PX = 30  # answer tolerance in PNG pixels (= 11 arcsec, about 2 SPHEREx pixels)


def _frames(slug):
    f = pd.read_csv(os.path.join(C.WORK, "objects", slug, "frames.csv"))
    f = f[[os.path.exists(FE.stamp_path(slug, x)) for x in f.file]].sort_values("mjd_avg").reset_index(drop=True)
    if "true_ra" not in f:
        f["true_ra"], f["true_dec"] = f.pred_ra, f.pred_dec
    return f


def pick_window(f, min_px=4.0, max_px=14.0, n=5, max_span_d=1.5):
    """4-6 exposures (one detector per exposure time) within <= 1.5 days whose first-to-last object motion is
    min_px..max_px, spread evenly in time and covering >= 2 epochs at least 20 min apart. Returns (rows, motion_px)."""
    det = f.det.value_counts().index[0]
    ex = f.assign(pref=(f.det != det).astype(int)).sort_values(["mjd_avg", "pref"]).drop_duplicates("mjd_avg")
    ex = ex.reset_index(drop=True)
    t = ex.mjd_avg.values
    pos = np.c_[ex.true_ra.values, ex.true_dec.values]
    best = None
    for i in range(len(ex)):
        for j in range(i + 3, len(ex)):
            if t[j] - t[i] > max_span_d:
                break
            mot = np.hypot((pos[j, 0] - pos[i, 0]) * np.cos(np.radians(pos[i, 1])), pos[j, 1] - pos[i, 1]) * 3600 / C.PIX_ARCSEC
            if not (min_px <= mot <= max_px):
                continue
            idx = np.unique(np.round(np.linspace(i, j, min(n, j - i + 1))).astype(int))
            gaps = np.diff(t[idx]) * 24 * 60
            if len(idx) < 4 or (gaps >= 20).sum() < 1:
                continue
            score = (len(idx), (gaps >= 20).sum(), -abs(mot - 10))
            if best is None or score > best[2]:
                best = ([r for r in ex.iloc[idx].itertuples()], mot, score)
    return (best[0], best[1]) if best else None


def _offset(ra, dec, ra0, dec0):
    return ((ra - ra0 + 180) % 360 - 180) * np.cos(np.radians(dec0)) * 3600, (dec - dec0) * 3600


def build_round(slug, sel, center, track=None, plant_snr=None, name=""):
    """Images on the fixed grid centred at `center`; track = list of (ra, dec) per frame (None: no mover).
    plant_snr: inject a fake ePSF source with that single-frame S/N at the track positions."""
    ra0, dec0 = center
    imgs, info, snrs = [], [], []
    for k, r in enumerate(sel):
        st = R.load_stamp_fits(FE.stamp_path(slug, r.file))
        image = None
        if plant_snr is not None and track is not None:
            q = PH.phot(st, *track[k])
            f_in = plant_snr * q["err"] if q.get("status") == "ok" else 0.0
            image = PH.plant(st, *track[k], f_in)
        if track is not None:
            q = PH.phot(st, *track[k], image=image)
            snrs.append(q.get("snr", np.nan) if q.get("status") == "ok" else np.nan)
        imgs.append(IM.north_up(st, ra0, dec0, image=image))
        lam, _ = PH.wavelength(st, ra0, dec0)
        info.append(dict(iso=r.iso[:19], wavelength_um=round(float(lam), 3) if np.isfinite(lam) else None,
                         detector=r.det, key=r.uri.split("ibe/data/spherex/")[-1]))
    if any(np.isnan(a).mean() > 0.3 for a in imgs):
        return None  # the fixed patch is not covered by every exposure (flagged pixels also count; they show black)
    lo, hi = IM.stretch_from(imgs, 5, 99.7)
    xy = [IM.xy_in_png(*_offset(ra, dec, ra0, dec0)) for ra, dec in track] if track is not None else None
    return imgs, info, xy, (lo, hi), snrs


def difficulty(snr):
    return "easy" if snr >= 12 else ("medium" if snr >= 6 else "hard")


def write_rounds_v2(seed=15):
    rng = np.random.default_rng(seed)
    os.makedirs(os.path.join(OUT, "v2"), exist_ok=True)
    rounds = []

    def save(rid, imgs, stretch):
        names = []
        for k, a in enumerate(imgs):
            p = f"v2/{rid}_{k}.png"
            IM.save(a, os.path.join(OUT, p), *stretch, upscale=UP if a.shape[0] == 64 else IM.UPSCALE)
            names.append(p)
        return names

    # known asteroids: grid centred on the middle of the visible track
    for slug, nm in [("bench-2525", "(2525) O'Steen"), ("bench-1542", "(1542) Schalen"), ("bench-2037", "(2037) Tripaxeptalis"),
                     ("bench-7556", "(7556) Perinaldo"), ("bench-9450", "(9450) Akikoizumo"), ("bench-12141", "(12141) Chushayashi"),
                     ("bench-2699", "(2699) Kalinin"), ("bench-22015", "(22015) 1999 XM100")]:
        f = _frames(slug)
        b = None
        for max_px in (14.0, 9.0, 6.0):  # shorter tracks keep the fixed patch inside every stamp
            w = pick_window(f, min_px=3.0, max_px=max_px)
            if not w:
                continue
            sel, mot = w
            track = [(r.true_ra, r.true_dec) for r in sel]
            c = ((track[0][0] + track[-1][0]) / 2, (track[0][1] + track[-1][1]) / 2)
            b = build_round(slug, sel, c, track)
            if b:
                break
        if not b:
            print("skip", slug, "patch not covered by every exposure")
            continue
        imgs, info, xy, st, snrs = b
        med = float(np.nanmedian(snrs))
        if med < 3:
            print("skip", slug, f"not visible in single frames (S/N {med:.1f})")
            continue
        rid = f"k_{slug.split('-')[1]}"
        rounds.append(dict(id=rid, truth="known", imgs=imgs, info=info, track_xy=xy, stretch=st, snr=med, motion_px=mot,
                           explain=f"The dot that moves is the known asteroid {nm}: it crossed about {mot:.0f} SPHEREx pixels "
                                   f"({mot * C.PIX_ARCSEC:.0f} arcsec) in {(sel[-1].mjd_avg - sel[0].mjd_avg) * 24:.1f} hours "
                                   f"while the stars stayed put."))
    # empty, planted and more known rounds from the fixed-grid AI-training patches
    rounds += patch_rounds(rng)
    # difficulty and order
    for r in rounds:
        if r["truth"] == "empty":
            r["difficulty"] = "medium"
        elif r["truth"] == "planted":
            r["difficulty"] = r["level"]
        elif r.get("vmag") is not None:  # patch movers: by catalogue brightness
            r["difficulty"] = "easy" if r["vmag"] <= 17.5 else ("medium" if r["vmag"] <= 18.7 else "hard")
        else:
            r["difficulty"] = difficulty(r["snr"]) if r["motion_px"] >= 3 else "hard"
    order = {"easy": 0, "medium": 1, "hard": 2}
    rounds.sort(key=lambda r: (order[r["difficulty"]], -(r["snr"] or 0)))
    out = []
    for n, r in enumerate(rounds):
        rid = f"r{n + 1:02d}"
        names = save(rid, r["imgs"], r["stretch"])
        frames = [dict(png=p, **inf) for p, inf in zip(names, r["info"])]
        snr_out = r["snr"] if r.get("vmag") is None else None
        out.append(dict(id=rid, images=names, truth=r["truth"], answer_xy=r["track_xy"][-1] if r["track_xy"] else None,
                        explain=r["explain"], frames=frames, track_xy=r["track_xy"], tolerance_px=TOL_PX,
                        difficulty=r["difficulty"], motion_px=round(float(r["motion_px"]), 1),
                        single_frame_snr=round(float(snr_out), 1) if snr_out is not None else None, vmag=r.get("vmag"),
                        reveal_after_answer=r["truth"] == "planted"))
    meta = dict(schema="rewind-detectives-v2", version=2, sample=False,
                note=("Each round: 4-6 SPHEREx exposures of the SAME fixed patch of sky (north up, east left), hours apart, "
                      "one shared brightness stretch per round. Benchmark rounds: 1.5 arcsec per pixel, 4x nearest-neighbour "
                      "upscaling (324 px); patch rounds (AI-training patches): native 6.15 arcsec pixels on a fixed north-up grid, "
                      "5x nearest-neighbour upscaling (320 px). track_xy = the mover's PNG position (x right, y down) in each frame; tolerance_px = how close "
                      "a click must be. Planted rounds are labelled only after answering."),
                real_rounds_note=("No 'real' rounds: every Rewind find is visible only in stacks of many photos, and on a fixed "
                                  "patch of sky its daily stacks do not overlap, so a person could not see it move."),
                rounds=out)
    from .site import dump
    dump(meta, os.path.join(OUT, "rounds.json"))
    return meta


# ------------------------------------------------------------------ rounds from the AI-training patches (A8)
# Each patch = one fixed 64x64 north-up TAN grid (6.15"/px) resampled for every epoch (data/08-ai-training).
A8 = os.path.join(C.DATA, "08-ai-training")
UP = 5  # 64 px -> 320 px


def _patch(name):
    return np.load(os.path.join(A8, "patches", name + ".npz"), allow_pickle=False)


def _epoch_windows(mjd, n=5, max_span_d=1.0, min_gap_min=20):
    """Index sets of n epochs within max_span_d with >= 2 gaps of >= min_gap_min (hours of motion)."""
    o = np.argsort(mjd)
    t = mjd[o]
    out = []
    for i in range(len(t)):
        j = np.searchsorted(t, t[i] + max_span_d)
        if j - i < n:
            continue
        idx = o[i + np.unique(np.round(np.linspace(0, j - i - 1, n)).astype(int))]
        g = np.diff(np.sort(mjd[idx])) * 1440
        if len(idx) == n and (g >= min_gap_min).sum() >= 2:
            out.append(idx)
    return out


def _png_xy(x_al, y_al, n=64):
    return [round((float(x_al) + 0.5) * UP, 1), round((n - 1 - float(y_al) + 0.5) * UP, 1)]


def _patch_imgs(z, idx, image=None):
    out = []
    for k, e in enumerate(idx):
        a = (z["al_img"][e] if image is None else image[k]).astype(float)
        bad = (z["al_flags"][e] & R.BAD_MASK_STRICT) != 0
        a = a - np.nanmedian(a[~bad]) if (~bad).any() else a
        a[bad] = np.nan
        out.append(a)
    return out


def _patch_info(z, idx):
    from .frames import mjd_to_iso
    return [dict(iso=mjd_to_iso(z["mjd_avg"][e], True), wavelength_um=round(float(np.nanmedian(z["al_lam"][e])), 3),
                 detector=f"D{int(z['det'][e])}", key=str(z["frame_id"][e])) for e in idx]


def patch_rounds(rng, n_known=4, n_planted=5, n_empty=4):
    km = pd.read_parquet(os.path.join(A8, "index", "known_movers.parquet"))
    rounds = []
    # known movers on the fixed grid
    good = km[km.in_aligned & (km.vmag <= 19.5) & km.x_al.between(4, 59) & km.y_al.between(4, 59)]
    for (patch, desig), g in good.groupby(["patch", "desig"]):
        if len([r for r in rounds if r["truth"] == "known"]) >= n_known:
            break
        z = _patch(patch)
        fid = {f: i for i, f in enumerate(z["frame_id"])}
        g = g[g.frame_id.isin(fid)].sort_values("mjd_avg").drop_duplicates("mjd_avg")
        idx_all = np.array([fid[f] for f in g.frame_id])
        for idx in _epoch_windows(z["mjd_avg"][idx_all], n=min(5, len(idx_all)), max_span_d=1.5):
            sel = g.iloc[idx]
            mot = float(np.hypot(sel.x_al.iloc[-1] - sel.x_al.iloc[0], sel.y_al.iloc[-1] - sel.y_al.iloc[0]))
            if not 3 <= mot <= 40 or len(sel) < 4:
                continue
            ep = idx_all[idx]
            imgs = _patch_imgs(z, ep)
            if any(np.isnan(a).mean() > 0.2 for a in imgs):
                continue
            rounds.append(dict(id=f"pk_{patch}", truth="known", imgs=imgs, info=_patch_info(z, ep), stretch=IM.stretch_from(imgs, 5, 99.3),
                               track_xy=[_png_xy(x, y) for x, y in zip(sel.x_al, sel.y_al)], snr=float(30 - sel.vmag.median()),
                               motion_px=mot, vmag=float(sel.vmag.median()),
                               explain=f"The dot that moves is the known asteroid {desig} (V about {sel.vmag.median():.1f}): it "
                                       f"crossed {mot:.0f} SPHEREx pixels in {(sel.mjd_avg.iloc[-1] - sel.mjd_avg.iloc[0]) * 24:.1f} "
                                       f"hours while the stars stayed put."))
            break
    # empty / planted: windows of a patch where no catalogued mover is on the grid
    patches = sorted({os.path.basename(p)[:-4] for p in __import__("glob").glob(os.path.join(A8, "patches", "NEP-*.npz"))})
    rng.shuffle(patches)
    levels = [("easy", 30.0), ("easy", 25.0), ("medium", 15.0), ("medium", 12.0), ("hard", 8.0)]
    n_p = n_e = 0
    for patch in patches:
        if n_p >= n_planted and n_e >= n_empty:
            break
        z = _patch(patch)
        busy = set(km[(km.patch == patch) & km.in_aligned].frame_id)
        ok = np.array([f not in busy for f in z["frame_id"]])
        cand = np.where(ok)[0]
        wins = _epoch_windows(z["mjd_avg"][cand], n=5, max_span_d=1.0)
        if not wins:
            continue
        ep = cand[wins[len(wins) // 2]]
        ep = ep[np.argsort(z["mjd_avg"][ep])]
        imgs = _patch_imgs(z, ep)
        if any(np.isnan(a).mean() > 0.2 for a in imgs):
            continue
        if n_p < n_planted:
            lvl, snr = levels[n_p]
            L, a2 = rng.uniform(5, 10), rng.uniform(0, 2 * np.pi)
            x0, y0 = rng.uniform(22, 42, 2)
            t = np.linspace(-0.5, 0.5, len(ep))
            xs, ys = x0 + L * t * np.cos(a2), y0 + L * t * np.sin(a2)
            planted = []
            for k, e in enumerate(ep):
                psf = z["epsf"][e, 0].astype(float)
                xi, yi = int(round(xs[k])), int(round(ys[k]))
                P = PH.psf_model(psf, xs[k] - xi, ys[k] - yi, 9)
                V = z["al_var"][e][yi - 4:yi + 5, xi - 4:xi + 5].astype(float)
                amp = snr / np.sqrt(np.nansum(P ** 2 / V))  # MJy/sr total so that the PSF-fit S/N is about `snr`
                img = z["al_img"][e].astype(float).copy()
                img[yi - 4:yi + 5, xi - 4:xi + 5] += amp * P
                planted.append(img)
            imgs = _patch_imgs(z, ep, image=planted)
            rounds.append(dict(id=f"pp_{patch}", truth="planted", imgs=imgs, info=_patch_info(z, ep),
                               stretch=IM.stretch_from(imgs, 5, 99.3), track_xy=[_png_xy(x, y) for x, y in zip(xs, ys)],
                               snr=snr, motion_px=L, level=lvl,
                               explain="A trick: we added a fake moving dot (made with SPHEREx's real blur pattern for each "
                                       "photo) to real photos. Rewind plants fakes like this to measure how faint it can see."))
            n_p += 1
        elif n_e < n_empty:
            rounds.append(dict(id=f"pe_{patch}", truth="empty", imgs=imgs, info=_patch_info(z, ep),
                               stretch=IM.stretch_from(imgs, 5, 99.3), track_xy=None, snr=None, motion_px=0.0,
                               explain="Nothing moves here: the dots are stars and galaxies that stay put (no catalogued "
                                       "asteroid crosses this patch at these times). 'Nothing' is the right answer."))
            n_e += 1
    return rounds
