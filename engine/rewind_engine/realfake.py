"""Step 4h: a simple, honest real-or-fake score for a blip at a predicted position.

Training data (data/07-answer-keys/labeled_set): REAL = stamps of known asteroids at their predicted
position (S/N >= 5). FAKE = artifacts we plant into truly empty negative stamps (|S/N| <= 5 at the spot; the
5.7% of 'empty' stamps with |S/N| > 5 are probably field stars and are excluded) (cosmic-ray hits, hot-pixel pairs, satellite streaks,
sharp glitches with negative ringing). All samples have S/N >= 5, so the score has to use the SHAPE,
not the brightness.
Features: PSF-fit chi2, sharpness (peak / 3x3 sum), elongation (second moments), light centroid
offset, correlation with the ePSF, flagged-pixel fraction, OUTLIER/TRANSIENT at the centre.
Models: transparent rules + logistic regression + gradient boosting, held-out split by frame (OBSID).
"""
from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd

from . import config as C
from . import phot as PH
from .pilot import R

LAB = os.path.join(C.DATA, "07-answer-keys", "labeled_set")
MODEL = os.path.join(C.WORK, "realfake")
FEATS = ["log_chi2", "sharp", "elong", "cen_off", "psf_corr", "bad_frac", "outlier", "neg_frac"]


def features(st, ra, dec, trail=(0.0, 0.0), image=None):
    img = st.image if image is None else image
    q = PH.phot(st, ra, dec, trail, image=image)
    if q.get("status") != "ok":
        return None
    x, y = q["x"], q["y"]
    xi, yi = int(round(x)), int(round(y))
    if not (3 <= xi < img.shape[1] - 3 and 3 <= yi < img.shape[0] - 3):
        return None
    D = img[yi - 2:yi + 3, xi - 2:xi + 3] - q["bkg"]
    D = np.nan_to_num(D)
    s3 = D[1:4, 1:4].sum()
    pos = np.clip(D, 0, None)
    tot = pos.sum() + 1e-12
    jj, ii = np.mgrid[-2:3, -2:3]
    cx, cy = (pos * ii).sum() / tot, (pos * jj).sum() / tot
    mxx = (pos * (ii - cx) ** 2).sum() / tot
    myy = (pos * (jj - cy) ** 2).sum() / tot
    mxy = (pos * (ii - cx) * (jj - cy)).sum() / tot
    ev = np.linalg.eigvalsh([[mxx, mxy], [mxy, myy]])
    psf_os, _ = R.epsf_zone(st.epsf_table, x + st.x0, y + st.y0)
    P = PH.psf_model(psf_os, x - xi, y - yi, 5, trail)
    pc = np.corrcoef(P.ravel(), D.ravel())[0, 1] if D.std() > 0 else 0.0
    box = st.flags[yi - 3:yi + 4, xi - 3:xi + 4]
    fc = int(st.flags[yi, xi])
    return dict(snr=q["snr"], log_chi2=float(np.log10(max(q["chi2"], 1e-3))), sharp=float(D.max() / s3) if s3 > 0 else 1.0,
                elong=float(np.sqrt(max(ev[1], 1e-6) / max(ev[0], 1e-6))), cen_off=float(np.hypot(cx, cy)),
                psf_corr=float(pc), bad_frac=float(((box & R.BAD_MASK_STRICT) != 0).mean()),
                outlier=int(bool(fc & ((1 << 19) | (1 << 0)))), neg_frac=float((D < -3 * q["bkg_std"]).mean()))


def _plant_artifact(st, ra, dec, kind, rng):
    img = st.image.copy()
    x, y = st.wcs.all_world2pix([[ra, dec]], 0)[0]
    xi, yi = int(round(x)), int(round(y))
    noise = np.nanmedian(np.sqrt(st.variance[np.isfinite(st.variance)]))
    amp = noise * rng.uniform(8, 80)
    if kind == "cosmic":
        img[yi, xi] += amp
        if rng.random() < 0.5:
            img[yi, xi + rng.choice([-1, 1])] += amp * rng.uniform(0.2, 0.8)
    elif kind == "hotpair":
        img[yi:yi + 2, xi:xi + 2] += amp * 0.6
    elif kind == "streak":
        a = rng.uniform(0, np.pi)
        jj, ii = np.mgrid[0:img.shape[0], 0:img.shape[1]]
        d = np.abs((ii - x) * np.sin(a) - (jj - y) * np.cos(a))
        img += amp * 0.4 * np.exp(-0.5 * (d / 0.7) ** 2)
    elif kind == "ringing":
        img[yi, xi] += amp
        img[yi, xi - 1] -= amp * 0.4
        img[yi, xi + 1] -= amp * 0.4
    return img


def build_training(seed=3, n_art_per=1):
    rng = np.random.default_rng(seed)
    lab = pd.read_parquet(os.path.join(LAB, "labels.parquet"))
    rows = []
    for r in lab.itertuples():
        p = os.path.join(LAB, r.file)
        if not os.path.exists(p) or r.status != "ok":
            continue
        try:
            st = R.load_stamp_fits(p)
        except Exception:  # noqa
            continue
        f = features(st, r.ra, r.dec)
        if r.kind == "negative" and abs(r.snr) > 5:
            continue  # 'empty sky' stamp with a source at the spot: probably a field star, not junk (A7 caution)
        if f and f["snr"] >= 5 and r.kind == "positive":
            rows.append(dict(f, label=1, group=str(r.OBSID), source=r.kind))
        if r.kind == "negative":
            for _ in range(n_art_per):
                kind = rng.choice(["cosmic", "hotpair", "streak", "ringing"])
                img = _plant_artifact(st, r.ra, r.dec, kind, rng)
                f = features(st, r.ra, r.dec, image=img)
                if f and f["snr"] >= 5:
                    rows.append(dict(f, label=0, group=str(r.OBSID), source="planted_" + kind))
    return pd.DataFrame(rows)


def rule_score(df):
    """Transparent rules: real point sources fit the ePSF, are not too sharp, round and centred."""
    ok = (df.psf_corr > 0.6) & (df.sharp < 0.6) & (df.elong < 2.5) & (df.cen_off < 0.8) & (df.bad_frac < 0.3)
    return ok.astype(float)


def train():
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import GroupShuffleSplit
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    import joblib
    os.makedirs(MODEL, exist_ok=True)
    df = build_training()
    df.to_csv(os.path.join(MODEL, "training_features.csv"), index=False)
    gss = GroupShuffleSplit(n_splits=1, test_size=0.3, random_state=0)
    tr, te = next(gss.split(df, df.label, df.group))
    X, y = df[FEATS].values, df.label.values
    lr = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000)).fit(X[tr], y[tr])
    gb = HistGradientBoostingClassifier(max_depth=3, max_iter=200, learning_rate=0.05).fit(X[tr], y[tr])
    acc = lambda p: float(np.mean((p >= 0.5) == y[te]))  # noqa
    rep = dict(n_train=int(len(tr)), n_test=int(len(te)), n_real=int(y.sum()), n_fake=int((1 - y).sum()),
               fake_sources=df[df.label == 0].source.value_counts().to_dict(),
               test_accuracy=dict(rules=acc(rule_score(df.iloc[te]).values), logistic=acc(lr.predict_proba(X[te])[:, 1]),
                                  gradient_boosting=acc(gb.predict_proba(X[te])[:, 1])),
               baseline_majority=float(max(y[te].mean(), 1 - y[te].mean())),
               split="GroupShuffleSplit by OBSID (frames in the test set never appear in training), 30% test",
               features=FEATS, label="MEASURED on held-out frames")
    joblib.dump(dict(lr=lr, gb=gb), os.path.join(MODEL, "models.joblib"))
    json.dump(rep, open(os.path.join(MODEL, "report.json"), "w"), indent=1)
    print(json.dumps(rep, indent=1))
    return rep


_M = None


def score_features(f: dict) -> float | None:
    global _M
    p = os.path.join(MODEL, "models.joblib")
    if _M is None:
        if not os.path.exists(p):
            return None
        import joblib
        _M = joblib.load(p)  # our own model file, written by train() in WORK (not downloaded data)
    X = np.array([[f[k] for k in FEATS]])
    return float(_M["gb"].predict_proba(X)[0, 1])


def score_object(obj, out, res):
    """Mean model probability over frames where the object itself is bright (S/N >= 5); None if the
    object is too faint per frame (the model is trained on single frames, not on stacks)."""
    from . import fetch as FE
    rows, ph = out["rows"], out["ph"]
    t_all = ph[(ph.path == "target") & (ph.status == "ok")]
    if not len(t_all) or np.median(t_all.flux / t_all.err) < 3:
        return None  # too faint in single frames: frames with S/N >= 5 would be noise or star hits, not the object
    tg = t_all[t_all.flux / t_all.err >= 5]
    if not len(tg) or not os.path.exists(os.path.join(MODEL, "models.joblib")):
        return None
    fr = pd.read_csv(os.path.join(C.WORK, "objects", obj.slug, "frames.csv")).set_index("file")
    sc = []
    for f in tg.file.head(40):
        st = R.load_stamp_fits(FE.stamp_path(obj.slug, f))
        r = fr.loc[f]
        trail = PH.trail_vector_px(st, r.pred_ra, r.pred_dec, r.rate_ra, r.rate_dec)
        ft = features(st, r.pred_ra, r.pred_dec, trail)
        if ft:
            s = score_features(ft)
            if s is not None:
                sc.append(s)
    return round(float(np.mean(sc)), 3) if sc else None
