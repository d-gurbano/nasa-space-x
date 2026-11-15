"""K2 kernel "rewind-c2-ai" (Rewind, Team SpaceX, NASA Space Apps 2026).

Stages (each time-boxed, each writes metrics.json + report.md when it ends, so a late crash keeps earlier results):
  realfake  real-or-fake: small CNN on stamps vs the engine's gradient boosting (same features, same hyper-
            parameters) vs majority / rules, identical test splits by FRAME (OBSID) and by SKY REGION (10 deg cells)
  download  A8 dataset v2 frame list (index/frames_selected_v2.parquet, 8,792 L2 frames) re-read from the public
            S3 bucket nasa-irsa-spherex with anonymous HTTPS range reads (A8 fetch_frame; no IRSA queries)
  build     A8 consolidate -> per-patch time series (patches_v2k/) + patch-epoch index
  staticref A8 static-sky reference baseline (splits_baselines.static_ref) for val + test patches
  es_train  "Expected Sky" U-Net: K other-epoch patches + wavelength offsets -> this epoch, region-held-out
  es_eval   residual noise, injected-source recovery and false positives near bright stars vs baselines
  report    report.md / metrics.json in the work dir

Pixels stay under --tmp (not saved as Kaggle output). Usage:
  python k2_main.py                       # on Kaggle (inputs found by globbing */rewind_inputs/MARKER)
  python k2_main.py --smoke --inputs-root <dir with data/, code/, rewind_engine/> --work W --tmp T
Labels: MEASURED (from data in this run), COMPUTED (derived from measured numbers), ESTIMATED (assumption).
"""
import argparse
import glob
import json
import os
import shutil
import subprocess
import sys
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed

sys.dont_write_bytecode = True   # never write __pycache__ into the (read-only) inputs

T0 = time.time()
A = None          # parsed args
LOGF = None
MET = {}          # metrics.json content


# ------------------------------------------------------------------ setup
def ensure_packages():
    need = dict(astropy="astropy", pyarrow="pyarrow", sklearn="scikit-learn", scipy="scipy", pandas="pandas",
                requests="requests", matplotlib="matplotlib", joblib="joblib")
    miss = []
    for mod, pkg in need.items():
        try:
            __import__(mod)
        except ImportError:
            miss.append(pkg)
    if miss:
        subprocess.run([sys.executable, "-m", "pip", "install", "-q"] + miss, check=False)


def log(*a):
    s = f"[{time.strftime('%H:%M:%S')} +{(time.time() - T0) / 60:6.1f} min] " + " ".join(str(x) for x in a)
    print(s, flush=True)
    if LOGF:
        with open(LOGF, "a") as f:
            f.write(s + "\n")


def find_inputs(arg):
    if arg:
        return os.path.abspath(arg)
    # Kaggle mounts the dataset as /kaggle/input/datasets/<owner>/<slug>/ without the zip's top folder:
    # the root is the folder with MARKER next to rewind_engine/
    for d, dirs, files in os.walk("/kaggle/input", followlinks=True):
        if "MARKER" in files and "rewind_engine" in dirs and "data" in dirs:
            return d
        if d.count(os.sep) > 8:
            dirs[:] = []
    raise SystemExit("inputs not found: no MARKER next to rewind_engine/ under /kaggle/input (use --inputs-root)")


def setup_root():
    """Writable copy of the A8 code + v2 frame list under TMP, so the unchanged A8 functions write there."""
    root = os.path.join(A.tmp, "k2root")
    for rel in ["code/A0/rewind.py", "code/A8/build_patches.py", "code/A8/inject.py", "code/A8/splits_baselines.py",
                "data/08-ai-training/index/frames_selected_v2.parquet"]:
        dst = os.path.join(root, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy(os.path.join(A.inputs, rel), dst)
    os.environ["A8_VERSION"] = "v2k"          # -> index/v2k, patches_v2k (never the shipped v1/v2 names)
    os.environ["REWIND_MAIN"] = A.inputs       # engine config: data/07-answer-keys/labeled_set under inputs
    os.environ["REWIND_WORK"] = os.path.join(A.tmp, "engine_work")
    for p in [os.path.join(root, "code/A0"), os.path.join(root, "code/A8"), A.inputs]:
        if p not in sys.path:
            sys.path.insert(0, p)
    return root


def save_metrics():
    MET["updated"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    MET["elapsed_min"] = round((time.time() - T0) / 60, 1)
    p = os.path.join(A.work, "metrics.json")
    txt = json.dumps(MET, indent=1, default=_js)   # serialise first: a failure never leaves a half-written file
    with open(p + ".tmp", "w") as f:
        f.write(txt)
    os.replace(p + ".tmp", p)


def _js(o):
    import numpy as np
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return None if not np.isfinite(o) else float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    return str(o)


def run_stage(name, fn, budget_min):
    st = MET.setdefault("stages", {})
    if st.get(name, {}).get("status") == "ok" and not A.force:
        log(f"== {name}: already ok, skipped")
        return True
    deadline = min(time.time() + budget_min * 60, T0 + A.max_hours * 3600)
    log(f"== {name}: start (budget {budget_min:.0f} min)")
    t = time.time()
    try:
        fn(deadline)
        status = "ok"
    except Exception as e:  # keep going: later stages may still work, earlier outputs are kept
        log(f"!! {name} FAILED: {e!r}\n{traceback.format_exc()}")
        status = "failed: " + repr(e)[:300]
    st[name] = dict(status=status, minutes=round((time.time() - t) / 60, 2), label="MEASURED")
    save_metrics()
    try:
        write_report()
    except Exception as e:
        log("report failed", repr(e))
    log(f"== {name}: {status} in {st[name]['minutes']} min")
    return status == "ok"


# ------------------------------------------------------------------ helpers
def bootstrap(fn, n_items, n_boot, seed=0):
    """Percentile 95% CI of a statistic fn(index_array) over bootstrap resamples."""
    import numpy as np
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(n_boot):
        v = fn(rng.integers(0, n_items, n_items))
        if v is not None and np.isfinite(v):
            vals.append(v)
    if len(vals) < 10:
        return [None, None]
    return [float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))]


def torch_device():
    import torch
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


# ================================================================== stage: realfake
H_CNN = 7   # 15x15 stamp


def cnn_input(R, st, img, ra, dec):
    """3 x 15 x 15: asinh-scaled (image - background) / noise, bad-flag mask, ePSF model at the sub-pixel position."""
    import numpy as np
    x, y = st.wcs.all_world2pix([[ra, dec]], 0)[0]
    xi, yi = int(round(x)), int(round(y))
    pad = H_CNN + 1
    im = np.pad(np.asarray(img, float), pad, constant_values=np.nan)
    fl = np.pad(st.flags, pad, constant_values=1 << 9)
    sl = (slice(yi - H_CNN + pad, yi + H_CNN + 1 + pad), slice(xi - H_CNN + pad, xi + H_CNN + 1 + pad))
    bkg = np.nanmedian(img)
    noise = np.sqrt(np.nanmedian(st.variance[np.isfinite(st.variance)]))
    z = np.nan_to_num((im[sl] - bkg) / max(noise, 1e-12))
    bad = ((fl[sl] & R.BAD_MASK_STRICT) != 0).astype(np.float32)
    psf_os, _ = R.epsf_zone(st.epsf_table, x + st.x0, y + st.y0)
    p = R.psf_native(psf_os, x - xi, y - yi, 2 * H_CNN + 1)
    p = p / max(p.max(), 1e-12)
    return np.stack([np.arcsinh(z / 3.0), bad, p]).astype(np.float32)


def build_realfake_set(deadline):
    """Engine training set (rewind_engine.realfake.build_training) plus CNN stamps of exactly the same samples."""
    import numpy as np
    import pandas as pd
    from rewind_engine import realfake as RF
    from rewind_engine.pilot import R
    lab = pd.read_parquet(os.path.join(RF.LAB, "labels.parquet"))
    if A.smoke:
        lab = pd.concat([lab[lab.kind == "positive"].head(70), lab[lab.kind == "negative"].head(40)])
    rng = np.random.default_rng(3)
    rows, X = [], []
    for r in lab.itertuples():
        if time.time() > deadline:
            log("realfake: build time box reached")
            break
        p = os.path.join(RF.LAB, r.file)
        if not os.path.exists(p) or r.status != "ok":
            continue
        try:
            st = R.load_stamp_fits(p)
        except Exception:  # noqa
            continue
        base = dict(group=str(r.OBSID), ra=float(r.ra), dec=float(r.dec), file=r.file)
        if r.kind == "positive":
            f = RF.features(st, r.ra, r.dec)
            if f and f["snr"] >= 5:
                rows.append(dict(f, label=1, source="positive", **base))
                X.append(cnn_input(R, st, st.image, r.ra, r.dec))
        elif abs(r.snr) <= 5:   # same exclusion as the engine (|S/N| > 5 'empty' stamps are probably stars)
            for _ in range(A.n_art_per):
                kind = rng.choice(["cosmic", "hotpair", "streak", "ringing"])
                img = RF._plant_artifact(st, r.ra, r.dec, kind, rng)
                f = RF.features(st, r.ra, r.dec, image=img)
                if f and f["snr"] >= 5:
                    rows.append(dict(f, label=0, source="planted_" + kind, **base))
                    X.append(cnn_input(R, st, img, r.ra, r.dec))
    df = pd.DataFrame(rows)
    # sky region: 10 x 10 deg cells (RA scaled by cos Dec) of each frame's median stamp position
    g = df.groupby("group")[["ra", "dec"]].median()
    cell = (np.floor(g.dec / 10).astype(int).astype(str) + "_" +
            np.floor(g.ra * np.cos(np.radians(g.dec)) / 10).astype(int).astype(str))
    df["sky_cell"] = df.group.map(cell)
    return df, np.array(X)


def make_cnn():
    import torch.nn as nn
    return nn.Sequential(nn.Conv2d(3, 16, 3, padding=1), nn.ReLU(), nn.Conv2d(16, 32, 3, padding=1), nn.ReLU(),
                         nn.MaxPool2d(2), nn.Conv2d(32, 64, 3, padding=1), nn.ReLU(), nn.AdaptiveAvgPool2d(1),
                         nn.Flatten(), nn.Dropout(0.3), nn.Linear(64, 1))


def _aug(x, torch):
    k = int(torch.randint(0, 4, (1,)))
    x = torch.rot90(x, k, (2, 3))
    return torch.flip(x, (3,)) if torch.rand(1) < 0.5 else x


def train_cnn(X, y, n_epochs, seed, Xv=None, yv=None):
    """Train the stamp CNN; with a validation set, returns (model, best_epoch) by validation loss."""
    import numpy as np
    import torch
    torch.manual_seed(seed)
    dev = torch_device()
    net = make_cnn().to(dev)
    opt = torch.optim.AdamW(net.parameters(), lr=2e-3, weight_decay=1e-3)
    lossf = torch.nn.BCEWithLogitsLoss()
    Xt, yt = torch.tensor(X, device=dev), torch.tensor(y, dtype=torch.float32, device=dev)
    best, best_ep, best_state, bad = np.inf, n_epochs, None, 0
    for ep in range(n_epochs):
        net.train()
        perm = torch.randperm(len(Xt), device=dev)
        for i in range(0, len(Xt), 64):
            b = perm[i:i + 64]
            opt.zero_grad()
            loss = lossf(net(_aug(Xt[b], torch)).squeeze(1), yt[b])
            loss.backward()
            opt.step()
        if Xv is not None:
            pv = predict_cnn(net, Xv)
            vl = float(-np.mean(yv * np.log(np.clip(pv, 1e-6, 1)) + (1 - yv) * np.log(np.clip(1 - pv, 1e-6, 1))))
            if vl < best - 1e-4:
                best, best_ep, bad = vl, ep + 1, 0
                best_state = {k: v.detach().clone() for k, v in net.state_dict().items()}
            else:
                bad += 1
                if bad >= 20:
                    break
    if best_state is not None:
        net.load_state_dict(best_state)
    return net, best_ep


def predict_cnn(net, X):
    import numpy as np
    import torch
    net.eval()
    dev = next(net.parameters()).device
    out = []
    with torch.no_grad():
        for i in range(0, len(X), 512):
            xb = torch.tensor(X[i:i + 512], device=dev)
            # test-time average over the 8 flips/rotations
            p = sum(torch.sigmoid(net(torch.flip(torch.rot90(xb, k, (2, 3)), (3,)) if f else torch.rot90(xb, k, (2, 3))))
                    for k in range(4) for f in (0, 1)) / 8
            out.append(p.squeeze(1).cpu().numpy())
    return np.concatenate(out) if out else np.zeros(0)


def clf_metrics(y, p, src):
    import numpy as np
    from sklearn.metrics import roc_auc_score
    pred = (p >= 0.5).astype(int)
    m = dict(n=int(len(y)), accuracy=float(np.mean(pred == y)),
             roc_auc=float(roc_auc_score(y, p)) if len(set(y)) == 2 else None,
             recall_real=float(np.mean(pred[y == 1] == 1)) if (y == 1).any() else None,
             recall_fake=float(np.mean(pred[y == 0] == 0)) if (y == 0).any() else None,
             precision_real=float(np.mean(y[pred == 1] == 1)) if (pred == 1).any() else None)
    m["per_source_correct"] = {s: dict(n=int((src == s).sum()), frac_correct=float(np.mean(pred[src == s] == y[src == s])))
                               for s in sorted(set(src))}
    return m


def stage_realfake(deadline):
    import numpy as np
    import pandas as pd
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.model_selection import GroupShuffleSplit
    from sklearn.metrics import roc_auc_score
    from rewind_engine import realfake as RF
    df, X = build_realfake_set(deadline - 0.6 * (deadline - time.time()))
    y, src = df.label.values.astype(int), df.source.values
    log(f"realfake set: {len(df)} samples, real {int(y.sum())}, fake {int((1 - y).sum())}, frames {df.group.nunique()}, "
        f"sky cells {df.sky_cell.nunique()}")
    df.drop(columns=["file"]).to_csv(os.path.join(A.work, "realfake_samples.csv"), index=False)
    out = dict(label="MEASURED on held-out test groups; CIs COMPUTED (paired bootstrap over test samples)",
               n_samples=int(len(df)), n_real=int(y.sum()), n_fake=int((1 - y).sum()), n_frames=int(df.group.nunique()),
               n_sky_cells=int(df.sky_cell.nunique()), fake_sources=df[df.label == 0].source.value_counts().to_dict(),
               n_art_per_negative=A.n_art_per, features=RF.FEATS,
               gb="HistGradientBoostingClassifier(max_depth=3, max_iter=200, learning_rate=0.05) = engine settings, "
                  "retrained on each training split (the shipped models.joblib used a different split)",
               cnn="3x15x15 stamps (asinh image/noise, bad-flag mask, ePSF model); 3 conv layers, ~23k params; "
                   "epochs chosen on an inner group split, then refit on the whole training split; 8-fold flip/rot TTA",
               splits={})
    n_ep = 3 if A.smoke else 150
    seeds = [0] if A.smoke else list(range(5))
    for split_kind, gcol in [("by_frame", "group"), ("by_sky_region", "sky_cell")]:
        runs = []
        for seed in seeds:
            if time.time() > deadline:
                log("realfake: time box reached")
                break
            gss = GroupShuffleSplit(n_splits=1, test_size=0.3, random_state=seed)
            tr, te = next(gss.split(df, y, df[gcol]))
            if len(set(y[te])) < 2 or len(set(y[tr])) < 2:
                continue
            Xf = df[RF.FEATS].values
            gb = HistGradientBoostingClassifier(max_depth=3, max_iter=200, learning_rate=0.05).fit(Xf[tr], y[tr])
            p_gb = gb.predict_proba(Xf[te])[:, 1]
            p_rule = RF.rule_score(df.iloc[te]).values
            maj = int(y[tr].mean() >= 0.5)
            p_maj = np.full(len(te), float(maj))
            # CNN: choose epochs on an inner group split of the training set, then refit on all of it
            itr, iva = next(GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=100 + seed).split(
                np.zeros((len(tr), 1)), y[tr], df[gcol].values[tr]))
            _, best_ep = train_cnn(X[tr][itr], y[tr][itr], n_ep, seed, X[tr][iva], y[tr][iva])
            net, _ = train_cnn(X[tr], y[tr], max(best_ep, 1), seed)
            p_cnn = predict_cnn(net, X[te])
            res = dict(seed=seed, n_train=int(len(tr)), n_test=int(len(te)), cnn_epochs=int(best_ep),
                       test_groups=int(df[gcol].iloc[te].nunique()),
                       cnn=clf_metrics(y[te], p_cnn, src[te]), gradient_boosting=clf_metrics(y[te], p_gb, src[te]),
                       rules=clf_metrics(y[te], p_rule, src[te]),
                       majority=dict(n=int(len(te)), accuracy=float(np.mean(p_maj == y[te])), roc_auc=0.5, predicts=maj))
            if seed == 0:
                nb = 100 if A.smoke else 1000
                yt = y[te]

                def acc(p):
                    return lambda i: float(np.mean((p[i] >= 0.5) == yt[i]))

                def auc(p):
                    return lambda i: float(roc_auc_score(yt[i], p[i])) if len(set(yt[i])) == 2 else None
                res["ci95"] = dict(
                    cnn_accuracy=bootstrap(acc(p_cnn), len(te), nb), gb_accuracy=bootstrap(acc(p_gb), len(te), nb),
                    cnn_auc=bootstrap(auc(p_cnn), len(te), nb), gb_auc=bootstrap(auc(p_gb), len(te), nb),
                    cnn_minus_gb_accuracy=bootstrap(lambda i: acc(p_cnn)(i) - acc(p_gb)(i), len(te), nb),
                    cnn_minus_gb_auc=bootstrap(lambda i: (auc(p_cnn)(i) or np.nan) - (auc(p_gb)(i) or np.nan), len(te), nb))
                pd.DataFrame(dict(idx=te, label=y[te], source=src[te], p_cnn=p_cnn, p_gb=p_gb)).to_csv(
                    os.path.join(A.work, f"realfake_test_{split_kind}_seed0.csv"), index=False)
                if split_kind == "by_sky_region":
                    import torch
                    torch.save(net.state_dict(), os.path.join(A.work, "realfake_cnn.pt"))
                    roc_figure(y[te], dict(CNN=p_cnn, GB=p_gb), os.path.join(A.work, "fig_realfake_roc.png"))
            runs.append(res)
            log(f"realfake {split_kind} seed {seed}: CNN acc {res['cnn']['accuracy']:.3f} auc {res['cnn']['roc_auc']}, "
                f"GB acc {res['gradient_boosting']['accuracy']:.3f} auc {res['gradient_boosting']['roc_auc']}, "
                f"majority {res['majority']['accuracy']:.3f}")
        summ = {}
        for mname in ["cnn", "gradient_boosting", "rules", "majority"]:
            for k in ["accuracy", "roc_auc"]:
                v = [r[mname][k] for r in runs if r[mname].get(k) is not None]
                if v:
                    summ[f"{mname}_{k}_mean"] = float(np.mean(v))
                    summ[f"{mname}_{k}_std"] = float(np.std(v))
        out["splits"][split_kind] = dict(runs=runs, summary_over_seeds=summ, n_seeds=len(runs),
                                         group_column=gcol, test_size=0.3)
        MET["realfake"] = out
        save_metrics()


def roc_figure(y, probs, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from sklearn.metrics import roc_curve
    fig, ax = plt.subplots(figsize=(4, 4))
    for name, p in probs.items():
        fpr, tpr, _ = roc_curve(y, p)
        ax.plot(fpr, tpr, label=name)
    ax.plot([0, 1], [0, 1], ":", color="gray")
    ax.set_xlabel("false positive rate (fakes called real)")
    ax.set_ylabel("true positive rate (real kept)")
    ax.set_title("real-or-fake, held-out sky region (seed 0)", fontsize=9)
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


# ================================================================== stage: download
def smoke_selection(sel):
    """Tiny frame list: 6 ECL-1 (train), 5 NEP-C (val), 8 ECL-2 (test, 4 with frozen injections); all detector 4."""
    import pandas as pd
    T = pd.read_parquet(os.path.join(A.inputs, "data/08-ai-training/injected_test_v2/truth.parquet"))
    det = 4
    out = []
    for cl, n in [("ECL-1", 6), ("NEP-C", 5), ("ECL-2", 4)]:
        d = sel[(sel.cluster == cl) & (sel.det == det)].sort_values("t_min")
        out.append(d.iloc[[int(round(i * (len(d) - 1) / max(n - 1, 1))) for i in range(n)]])
    tf = set(T[T.patch.str.startswith("ECL-2") & (T.det == det)].frame_id)
    out.append(sel[(sel.cluster == "ECL-2") & sel.frame_id.isin(tf)].head(4))
    return pd.concat(out).drop_duplicates(["cluster", "frame_id"])


def stage_download(deadline):
    import numpy as np
    import pandas as pd
    import build_patches as B
    sel = pd.read_parquet(os.path.join(B.IDX_BASE, "frames_selected_v2.parquet"))
    if A.smoke:
        sel = smoke_selection(sel)
    elif A.max_frames:
        sel = pd.concat([d.sort_values("t_min").iloc[np.unique(np.linspace(0, len(d) - 1, A.max_frames).round().astype(int))]
                         for _, d in sel.groupby("cluster")])
    plists = {c["name"]: B.patch_list(c) for c in B.CLUSTERS}
    # interleave clusters (rank within cluster / cluster size) so a time stop leaves every cluster partly filled
    sel = sel.sort_values("t_min").copy()
    sel["rank"] = sel.groupby("cluster").cumcount() / sel.groupby("cluster").frame_id.transform("size")
    todo = [fr for fr in sel.sort_values("rank").itertuples()
            if not os.path.exists(os.path.join(B.RAW, fr.cluster, fr.frame_id + ".npz"))
            and not os.path.exists(os.path.join(B.RAW, fr.cluster, fr.frame_id + ".npz.skip"))]
    log(f"download: {len(sel)} frames selected (v2 list), {len(todo)} to fetch, threads {A.threads}")
    lock = threading.Lock()
    S = dict(ok=0, err=0, skip=0, bytes_read=0, bytes_stored=0, consec_err=0, pauses=0, stop=None)
    t0 = time.time()
    last = [t0]
    raw_gb0 = sum(os.path.getsize(p) for p in glob.glob(os.path.join(B.RAW, "*", "*.npz"))) / 1e9

    def free_gb():
        return shutil.disk_usage(A.tmp).free / 1e9

    def work(fr):
        if S["stop"]:
            return
        if time.time() > deadline:
            S["stop"] = "time box"
            return
        # disk guard: consolidation needs about as much again as the raw files (COMPUTED from the v1 build)
        if free_gb() < raw_gb0 + S["bytes_stored"] / 1e9 + A.disk_reserve_gb:
            S["stop"] = "disk guard"
            return
        # circuit breaker: many consecutive failures -> pause, then give up after 3 pauses
        if S["consec_err"] >= 25:
            with lock:
                if S["consec_err"] >= 25:
                    S["pauses"] += 1
                    log(f"download: {S['consec_err']} consecutive errors, pause {S['pauses']} (120 s)")
                    if S["pauses"] > 3:
                        S["stop"] = "circuit breaker (S3 errors)"
                        return
                    time.sleep(120)
                    S["consec_err"] = 0
        d = os.path.join(B.RAW, fr.cluster)
        os.makedirs(d, exist_ok=True)
        f = os.path.join(d, fr.frame_id + ".npz")
        err = None
        for k in range(3):
            try:
                out, meta = B.fetch_frame(fr, plists[fr.cluster])
                break
            except Exception as e:  # noqa
                err = repr(e)
                time.sleep(3 * (k + 1))
        else:
            with open(f + ".err", "w") as fh:
                fh.write(str(err))
            with lock:
                S["err"] += 1
                S["consec_err"] += 1
            return
        if out is None:
            open(f + ".skip", "w").write(meta["reason"])
            with lock:
                S["skip"] += 1
            return
        np.savez_compressed(f + ".tmp.npz", **out)
        os.replace(f + ".tmp.npz", f)
        with lock:
            S["ok"] += 1
            S["consec_err"] = 0
            S["bytes_read"] += meta["bytes_read"]
            S["bytes_stored"] += os.path.getsize(f)
            n = S["ok"] + S["err"] + S["skip"]
            if time.time() - last[0] > (20 if A.smoke else 60):
                last[0] = time.time()
                el = time.time() - t0
                rate = S["ok"] / el
                eta = (len(todo) - n) / rate / 60 if rate > 0 else float("nan")
                log(f"download {n}/{len(todo)} ok {S['ok']} err {S['err']} skip {S['skip']} | "
                    f"{S['bytes_read'] / 1e6:.0f} MB read, {S['bytes_read'] / 1e6 / el:.1f} MB/s, {rate:.2f} frames/s, "
                    f"ETA {eta:.0f} min, stored {S['bytes_stored'] / 1e9:.2f} GB, free {free_gb():.1f} GB")
    with ThreadPoolExecutor(A.threads) as ex:
        list(ex.map(work, todo))
    el = time.time() - t0
    have = len(glob.glob(os.path.join(B.RAW, "*", "*.npz"))) - len(glob.glob(os.path.join(B.RAW, "*", "*.tmp.npz")))
    MET["download"] = dict(label="MEASURED", frames_selected_v2=int(len(sel)), frames_to_fetch=len(todo),
                           fetched_ok=S["ok"], errors=S["err"], skipped_no_patch=S["skip"], frames_on_disk=have,
                           mb_read=round(S["bytes_read"] / 1e6, 1), gb_stored_compressed=round(S["bytes_stored"] / 1e9, 2),
                           minutes=round(el / 60, 1), mb_per_s=round(S["bytes_read"] / 1e6 / max(el, 1), 2),
                           frames_per_s=round(S["ok"] / max(el, 1), 3), stop_reason=S["stop"] or "completed",
                           breaker_pauses=S["pauses"], irsa_queries=0, threads=A.threads,
                           source="s3://nasa-irsa-spherex via anonymous HTTPS Range (A8 build_patches.fetch_frame)")
    log("download done", json.dumps(MET["download"]))
    if have == 0:
        raise RuntimeError("no frames downloaded")


# ================================================================== stage: build
def stage_build(deadline):
    import numpy as np
    import pandas as pd
    import build_patches as B
    import splits_baselines as SB
    B.cmd_consolidate()
    pe = pd.read_parquet(os.path.join(B.IDX, "patch_epochs.parquet"))
    pe["region_split"] = pe.cluster.map(SB.REGION)
    pe["time_bin"] = np.where(pe.mjd_avg < SB.T_MID, "early", np.where(pe.mjd_avg < SB.T_LATE, "mid", "late"))
    pe.to_parquet(os.path.join(B.IDX, "patch_epochs_k2.parquet"))
    MET["dataset_v2k"] = dict(
        label="MEASURED", frames=int(pe.frame_id.nunique()), patch_epochs=int(len(pe)), patches=int(pe.patch.nunique()),
        by_cluster=pe.groupby("cluster").size().to_dict(), by_region_split=pe.groupby("region_split").size().to_dict(),
        by_region_and_time={f"{a}/{b}": int(n) for (a, b), n in pe.groupby(["region_split", "time_bin"]).size().items()},
        mjd_range=[float(pe.mjd_avg.min()), float(pe.mjd_avg.max())],
        patches_gb=round(sum(os.path.getsize(p) for p in glob.glob(os.path.join(B.PAT, "*.npz"))) / 1e9, 2))
    log("dataset", json.dumps(MET["dataset_v2k"]))
    if not A.keep_raw:
        shutil.rmtree(B.RAW, ignore_errors=True)
        log("raw per-frame files deleted (patches_v2k keeps everything needed)")


# ================================================================== stage: staticref (A8 baseline)
def _staticref_one(args):
    """Worker: A8 static-sky reference for one patch (same code and windows as splits_baselines.cmd_staticref)."""
    root, pat_path, out_path = args
    for p in [os.path.join(root, "code/A0"), os.path.join(root, "code/A8")]:
        if p not in sys.path:
            sys.path.insert(0, p)
    import numpy as np
    from scipy.ndimage import map_coordinates
    import splits_baselines as SB
    z = np.load(pat_path)
    a = z["al_img"] - z["al_zodi"]
    E = a.shape[0]
    bw = np.stack([map_coordinates(z["bw"][e].astype(np.float32), [z["al_y"][e], z["al_x"][e]], order=1, cval=np.nan)
                   for e in range(E)])
    ref, nref = SB.static_ref(a, z["al_lam"], bw, z["det"], z["mjd_avg"], z["al_flags"], win=2.0)
    ref6, nref6 = SB.static_ref(a, z["al_lam"], bw, z["det"], z["mjd_avg"], z["al_flags"], win=6.0)
    rq = np.where(np.isfinite(ref), 1, np.where(np.isfinite(ref6), 2, 0)).astype(np.uint8)
    nref = np.where(rq == 2, nref6, nref).astype(np.uint8)
    ref = np.where(rq == 2, ref6, ref).astype(np.float32)
    np.savez_compressed(out_path + ".tmp.npz", ref=ref, nref=nref, ref_quality=rq)
    os.replace(out_path + ".tmp.npz", out_path)
    return os.path.basename(pat_path), E


def eval_patches():
    import pandas as pd
    import build_patches as B
    pe = pd.read_parquet(os.path.join(B.IDX, "patch_epochs_k2.parquet"))
    sp = pe.groupby("patch").region_split.first()
    return sorted(sp[sp == "val"].index), sorted(sp[sp == "test"].index), sorted(sp[sp == "train"].index)


def stage_staticref(deadline):
    import build_patches as B
    val, test, _ = eval_patches()
    od = os.path.join(A.tmp, "staticref_v2k")
    os.makedirs(od, exist_ok=True)
    jobs = [(A.root, os.path.join(B.PAT, p + ".npz"), os.path.join(od, p + "_staticref.npz")) for p in val + test]
    jobs = [j for j in jobs if not os.path.exists(j[2])]
    # biggest patches first so the time box cuts small ones
    jobs.sort(key=lambda j: -os.path.getsize(j[1]))
    done, n_ep = 0, 0
    nproc = max(1, min(os.cpu_count() or 1, 4))
    try:
        ex = ProcessPoolExecutor(nproc)
    except OSError as e:   # e.g. sandboxed laptop without POSIX semaphores: run serially
        log("staticref: no process pool", repr(e), "-> serial")
        ex = None
    futs = [ex.submit(_staticref_one, j) for j in jobs] if ex else jobs
    for fu in (as_completed(futs) if ex else futs):
        try:
            name, E = fu.result() if ex else _staticref_one(fu)
            done += 1
            n_ep += E
            log(f"staticref {name}: {E} epochs ({done}/{len(jobs)})")
        except Exception as e:
            log("staticref failed for one patch", repr(e))
        if time.time() > deadline:
            log("staticref: time box reached, cancelling the rest")
            if ex:
                for f in futs:
                    f.cancel()
            break
    if ex:
        ex.shutdown(cancel_futures=True)
    MET["staticref"] = dict(label="MEASURED", patches_done=done, patches_requested=len(jobs), epochs=n_ep,
                            method="A8 splits_baselines.static_ref: per-pixel linear fit vs wavelength offset of other "
                                   "same-detector epochs > 1 day away within +/-2 channel widths (fallback +/-6), 4-sigma clip")


# ================================================================== Expected Sky data + model
K_REF = 6


def candidates(det, mjd, lamc, K):
    """Per epoch: the K other epochs of the same detector, > 1 day away, closest in centre wavelength (-1 = none)."""
    import numpy as np
    import splits_baselines as SB
    E = len(det)
    out = -np.ones((E, K), np.int64)
    for e in range(E):
        o = np.where((det == det[e]) & (np.abs(mjd - mjd[e]) > SB.SAME_PASS_DAYS) & np.isfinite(lamc))[0]
        if len(o):
            o = o[np.argsort(np.abs(lamc[o] - lamc[e]), kind="stable")][:K]
            out[e, :len(o)] = o
    return out


def load_patch(patch):
    import numpy as np
    import build_patches as B
    import splits_baselines as SB
    z = np.load(os.path.join(B.PAT, patch + ".npz"))
    img = (z["al_img"] - z["al_zodi"]).astype(np.float32)
    var = z["al_var"].astype(np.float32)
    lam = z["al_lam"].astype(np.float32)
    good = np.isfinite(img) & np.isfinite(var) & (var > 0) & ((z["al_flags"] & SB.BAD) == 0)
    E = img.shape[0]
    lamc = np.nanmedian(lam[:, 28:36, 28:36].reshape(E, -1), 1)
    bwc = z["bw"][:, 48, 48].astype(np.float32)
    bwc = np.where(np.isfinite(bwc) & (bwc > 0), bwc, lamc / 40.0).astype(np.float32)
    mjd, det = z["mjd_avg"], z["det"]
    return dict(patch=patch, img=img, var=var, lam=lam, good=good, bwc=bwc, mjd=mjd, det=det, lamc=lamc,
                frame_id=np.array(z["frame_id"]), cand=candidates(det, mjd, lamc, K_REF))


def to_store(parts, dev):
    """Concatenate patch dicts into one device store with global candidate indices."""
    import numpy as np
    import torch
    off, cands = 0, []
    for p in parts:
        c = p["cand"].copy()
        c[c >= 0] += off
        cands.append(c)
        off += len(p["img"])
    cat = lambda k: np.concatenate([p[k] for p in parts])  # noqa
    S = {k: torch.tensor(cat(k), device=dev) for k in ["img", "var", "lam", "good", "bwc"]}
    S["cand"] = torch.tensor(np.concatenate(cands), device=dev)
    return S


def make_batch(S, idx):
    """Inputs for target epochs idx: K refs (asinh-scaled, normalised by the target noise), their wavelength offsets
    in target channel widths, ref masks, the engine-style base (mean of the 2 closest-wavelength refs) and its mask."""
    import torch
    nan = float("nan")
    c = S["cand"][idx]
    ok = c >= 0
    cc = c.clamp(min=0)
    G = S["good"][cc] & ok[:, :, None, None]
    R = S["img"][cc]
    R = torch.where(G, R, torch.full_like(R, nan))
    base = torch.nanmean(R[:, :2], 1)
    med = R.nanmedian(dim=1).values
    base = torch.where(torch.isnan(base), med, base)
    bv = torch.isfinite(base)
    T, V, Gt = S["img"][idx], S["var"][idx], S["good"][idx]
    off = torch.nan_to_num(base.flatten(1).nanmedian(dim=1).values, nan=0.0)
    sc = torch.where(Gt, V.clamp(min=0).sqrt(), torch.full_like(V, nan)).flatten(1).nanmedian(dim=1).values
    sc = torch.nan_to_num(sc, nan=1.0).clamp(min=1e-6)
    o3, s3 = off[:, None, None], sc[:, None, None]
    bn = torch.nan_to_num((base - o3) / s3, nan=0.0)
    Rn = torch.where(G, (R - o3[:, None]) / s3[:, None], bn[:, None].expand_as(R))
    dl = (S["lam"][cc] - S["lam"][idx][:, None]) / S["bwc"][idx][:, None, None, None]
    dl = torch.nan_to_num(torch.where(G, dl, torch.zeros_like(dl)), nan=0.0).clamp(-10, 10) / 5
    x = torch.cat([torch.asinh(Rn / 5), dl, G.float(), torch.asinh(bn / 5)[:, None], bv.float()[:, None]], 1)
    tn = torch.nan_to_num((T - o3) / s3, nan=0.0)
    sn = torch.nan_to_num(V.clamp(min=0).sqrt() / s3, nan=1.0).clamp(min=1e-3)
    w = Gt & bv
    return x, bn, tn, sn, w, o3, s3, bv


def make_unet(cin, w=32):
    import torch
    import torch.nn as nn

    def blk(a, b):
        return nn.Sequential(nn.Conv2d(a, b, 3, padding=1), nn.GroupNorm(8, b), nn.ReLU(),
                             nn.Conv2d(b, b, 3, padding=1), nn.GroupNorm(8, b), nn.ReLU())

    class UNet(nn.Module):
        """pred = base * (1 + g) + h in target-noise units; zero-initialised head => starts as the base."""

        def __init__(s):
            super().__init__()
            s.e1, s.e2, s.e3 = blk(cin, w), blk(w, 2 * w), blk(2 * w, 4 * w)
            s.u2, s.d2 = nn.ConvTranspose2d(4 * w, 2 * w, 2, 2), blk(4 * w, 2 * w)
            s.u1, s.d1 = nn.ConvTranspose2d(2 * w, w, 2, 2), blk(2 * w, w)
            s.out = nn.Conv2d(w, 2, 1)
            nn.init.zeros_(s.out.weight)
            nn.init.zeros_(s.out.bias)

        def forward(s, x, bn):
            e1 = s.e1(x)
            e2 = s.e2(nn.functional.max_pool2d(e1, 2))
            e3 = s.e3(nn.functional.max_pool2d(e2, 2))
            d2 = s.d2(torch.cat([s.u2(e3), e2], 1))
            d1 = s.d1(torch.cat([s.u1(d2), e1], 1))
            o = s.out(d1)
            return bn * (1 + 0.5 * torch.tanh(o[:, 0])) + o[:, 1]
    return UNet()


def es_loss(net, S, idx, aug, torch):
    x, bn, tn, sn, w, *_ = make_batch(S, idx)
    if aug:
        k = int(torch.randint(0, 4, (1,)))
        x, bn, tn, sn, w = [torch.rot90(t, k, (t.dim() - 2, t.dim() - 1)) for t in (x, bn, tn, sn, w)]
    pn = net(x, bn)
    chi = ((pn - tn) / sn)[w]
    return torch.nn.functional.huber_loss(chi, torch.zeros_like(chi), delta=3.0) if chi.numel() else pn.sum() * 0


def stage_es_train(deadline):
    import numpy as np
    import pandas as pd
    import torch
    import build_patches as B
    import splits_baselines as SB
    dev = torch_device()
    val, test, train = eval_patches()
    pe = pd.read_parquet(os.path.join(B.IDX, "patch_epochs_k2.parquet"))

    def targets(parts):
        """Global indices of target epochs with >= 1 reference and not in the late time bin (strict test)."""
        out, off = [], 0
        for p in parts:
            ok = (p["cand"][:, 0] >= 0) & (p["mjd"] < SB.T_LATE)
            out.append(np.where(ok)[0] + off)
            off += len(p["img"])
        return np.concatenate(out) if out else np.zeros(0, int)
    log("es_train: loading", len(train), "train and", len(val), "val patches")
    tr_parts = [load_patch(p) for p in train]
    va_parts = [load_patch(p) for p in val]
    tr_idx, va_idx = targets(tr_parts), targets(va_parts)
    Str, Sva = to_store(tr_parts, dev), to_store(va_parts, dev)
    del tr_parts, va_parts
    rng = np.random.default_rng(0)
    va_sub = rng.choice(va_idx, min(len(va_idx), 64 if A.smoke else 3000), replace=False)
    log(f"es_train: {len(tr_idx)} train targets, {len(va_idx)} val targets on {dev}")
    torch.manual_seed(0)
    net = make_unet(3 * K_REF + 2).to(dev)
    log("U-Net params", sum(p.numel() for p in net.parameters()))
    bs = 16 if A.smoke else 64
    steps = 6 if A.smoke else min(800, max(50, len(tr_idx) // bs))
    max_ep = 2 if A.smoke else 40
    opt = torch.optim.AdamW(net.parameters(), lr=1e-3, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, max_ep * steps)

    def val_loss():
        net.eval()
        with torch.no_grad():
            ls = [float(es_loss(net, Sva, torch.tensor(va_sub[i:i + 128], device=dev), False, torch))
                  for i in range(0, len(va_sub), 128)]
        net.train()
        return float(np.mean(ls))
    base_loss = val_loss()   # zero-initialised head: this is the engine-style base (mean of 2 closest refs)
    log(f"es_train: val Huber(chi) of the base (= engine-style baseline) {base_loss:.4f}")
    best, bad, hist = base_loss, 0, []
    wpath = os.path.join(A.work, "es_unet.pt")
    torch.save(net.state_dict(), wpath)
    t_ep = []
    for ep in range(max_ep):
        te = time.time()
        tl = []
        for s in range(steps):
            idx = torch.tensor(rng.choice(tr_idx, bs), device=dev)
            opt.zero_grad()
            loss = es_loss(net, Str, idx, True, torch)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(net.parameters(), 5.0)
            opt.step()
            sched.step()
            tl.append(float(loss))
        vl = val_loss()
        t_ep.append(time.time() - te)
        hist.append(dict(epoch=ep + 1, train_loss=float(np.mean(tl)), val_loss=vl, sec=round(t_ep[-1], 1)))
        log(f"es_train epoch {ep + 1}: train {np.mean(tl):.4f} val {vl:.4f} (base {base_loss:.4f}) {t_ep[-1]:.0f} s")
        if vl < best - 1e-4:
            best, bad = vl, 0
            torch.save(net.state_dict(), wpath)
        else:
            bad += 1
            if bad >= 5:
                log("es_train: early stop")
                break
        if time.time() + np.mean(t_ep) * 1.2 > deadline:
            log("es_train: time box reached")
            break
    MET["es_train"] = dict(label="MEASURED (losses on the val region NEP-C, epochs before 2026-06-17)",
                           n_train_targets=int(len(tr_idx)), n_val_targets=int(len(va_idx)), val_subset=int(len(va_sub)),
                           train_patches=train, val_patches=val, K_refs=K_REF, batch=bs, steps_per_epoch=steps,
                           epochs_run=len(hist), val_loss_base=base_loss, val_loss_best=best,
                           model_beats_base_on_val=bool(best < base_loss - 1e-4), history=hist,
                           params=int(sum(p.numel() for p in net.parameters())), device=str(dev),
                           note="loss = Huber(delta=3) of (prediction - target)/sqrt(VARIANCE) on good target pixels")


# ================================================================== stage: es_eval
def psf_aligned(psf_os, M, fx, fy, n=7):
    """ePSF (5x oversampled, native pixels) sampled on the aligned grid around a source at sub-pixel (fx, fy);
    M maps aligned offsets to native offsets (affine part of the stored mapping)."""
    import numpy as np
    from scipy.ndimage import map_coordinates
    h = n // 2
    jj, ii = np.mgrid[-h:h + 1, -h:h + 1]
    ax, ay = ii - fx, jj - fy
    nx, ny = M[0, 0] * ax + M[0, 1] * ay, M[1, 0] * ax + M[1, 1] * ay
    c = (psf_os.shape[0] - 1) / 2
    p = map_coordinates(psf_os, [c + ny * 5, c + nx * 5], order=3, mode="constant", cval=0.0)
    p[p < 0] = 0
    return p / p.sum() if p.sum() > 0 else p


class MF:
    """Matched-filter (ePSF) photometry on aligned residual maps of one patch."""

    def __init__(s, P, I):
        s.P, s.I, s.M = P, I, {}

    def psf(s, e, xa, ya):
        import numpy as np
        if e not in s.M:
            cx, cy = s.I._affine(s.P, e)
            s.M[e] = (cx, cy, np.array([[cx[0], cx[1]], [cy[0], cy[1]]]))
        cx, cy, M = s.M[e]
        xn, yn = cx[0] * xa + cx[1] * ya + cx[2], cy[0] * xa + cy[1] * ya + cy[2]
        xi, yi = int(round(xa)), int(round(ya))
        return psf_aligned(s.P.psf_at(e, xn, yn), M, xa - xi, ya - yi)

    def snr(s, res_list, var, mask, e, xa, ya, extra=None):
        """S/N (and flux) at (xa, ya) for each residual map in res_list (same pixels for all); local background =
        median of the 15x15 box. extra = signal map added to every residual (injections)."""
        import numpy as np
        xi, yi = int(round(xa)), int(round(ya))
        if not (7 <= xi < 57 and 7 <= yi < 57):
            return None
        core = (slice(yi - 3, yi + 4), slice(xi - 3, xi + 4))
        box = (slice(yi - 7, yi + 8), slice(xi - 7, xi + 8))
        if mask[core].sum() < 30:
            return None
        p = s.psf(e, xa, ya)
        out = []
        for r in res_list:
            rr = r if extra is None else r + extra
            if not np.isfinite(rr[core][mask[core]]).all():
                out.append((np.nan, np.nan))
                continue
            b = np.median(rr[box][mask[box]])
            D, V, G = rr[core] - b, var[core], mask[core]
            wsum = np.sum(p[G] ** 2 / V[G])
            out.append((float(np.sum(p[G] * D[G] / V[G]) / np.sqrt(wsum)), float(np.sum(p[G] * D[G] / V[G]) / wsum)))
        return out


METHODS = ["engine_2ref", "a8_staticref", "unet"]


def stage_es_eval(deadline):
    import numpy as np
    import pandas as pd
    import torch
    from scipy.ndimage import map_coordinates
    import build_patches as B
    import inject as I
    import splits_baselines as SB
    dev = torch_device()
    val, test, _ = eval_patches()
    net = make_unet(3 * K_REF + 2).to(dev)
    net.load_state_dict(torch.load(os.path.join(A.work, "es_unet.pt"), map_location=dev, weights_only=True))
    net.eval()
    truth = pd.read_parquet(os.path.join(A.inputs, "data/08-ai-training/injected_test_v2/truth.parquet"))
    rng = np.random.default_rng(20261115)
    pix = {m: {} for m in METHODS}       # subset -> list of chi samples
    cover = {m: [0, 0] for m in METHODS}
    pos_rows, inj_rows = [], []
    fig_done = False
    for patch in val + test:
        if time.time() > deadline:
            log("es_eval: time box reached")
            break
        is_test = patch in test
        D = load_patch(patch)
        E = len(D["img"])
        tg = np.where(D["cand"][:, 0] >= 0)[0]
        if A.smoke:
            tg = tg[:8]
        if not len(tg):
            continue
        S = to_store([D], dev)
        base = np.full((E, 64, 64), np.nan, np.float32)
        pred = np.full((E, 64, 64), np.nan, np.float32)
        with torch.no_grad():
            for i in range(0, len(tg), 128):
                idx = torch.tensor(tg[i:i + 128], device=dev)
                x, bn, tn, sn, w, o3, s3, bv = make_batch(S, idx)
                pn = net(x, bn)
                nanv = torch.full_like(pn, float("nan"))
                pred[tg[i:i + 128]] = torch.where(bv, pn * s3 + o3, nanv).cpu().numpy()
                base[tg[i:i + 128]] = torch.where(bv, bn * s3 + o3, nanv).cpu().numpy()
        del S
        srf = os.path.join(A.tmp, "staticref_v2k", patch + "_staticref.npz")
        sref = np.load(srf)["ref"] if os.path.exists(srf) else np.full((E, 64, 64), np.nan, np.float32)
        preds = dict(engine_2ref=base, a8_staticref=sref, unet=pred)
        P = I.Patch(patch, B.PAT, B.IDX)
        bx, by, _ = I.bright_sources(P)
        jj, ii = np.mgrid[0:64, 0:64]
        dist = np.min(np.hypot(ii[None] - bx[:, None, None], jj[None] - by[:, None, None]), 0) if len(bx) else np.full((64, 64), np.inf)
        near = dist <= 4
        tb = np.where(D["mjd"] < SB.T_MID, "early", np.where(D["mjd"] < SB.T_LATE, "mid", "late"))
        subset = np.where(tb == "late", "region+time", "region") if is_test else np.full(E, "val")
        mf = MF(P, I)
        # injections: frozen v2 truth tracks (same frames, A8 kit) + one fresh near-star and one isolated point per epoch
        sig = {}
        if is_test:
            fid = {f: e for e, f in enumerate(D["frame_id"])}
            img_i, var_i = P.a["img"].copy(), P.a["var"].copy()
            tr = truth[(truth.patch == patch) & truth.frame_id.isin(fid)]
            inj = []
            for r in tr.itertuples():
                e = fid[r.frame_id]
                pa = np.radians(r.pa_deg)
                _, _, t = I.inject_track(P, r.ra, r.dec, r.mjd_avg, r.rate_arcsec_min * np.sin(pa), r.rate_arcsec_min * np.cos(pa),
                                         I.Sed(**json.loads(r.sed_json)), rng=rng, epochs=[e], img=img_i, var=var_i)
                for q in t.itertuples():
                    inj.append(dict(set="frozen_v2", kind=r.kind, e=e, x_al=q.x_al, y_al=q.y_al, ab=q.ab, snr_pred=q.snr_pred_psf,
                                    trail_px=q.trail_px))
            for e in tg:
                for kind in (["near_bright"] if len(bx) else []) + ["isolated"]:
                    if kind == "near_bright":
                        k = rng.integers(len(bx))
                        r_, th = rng.uniform(1, 4), rng.uniform(0, 2 * np.pi)
                        xa, ya = bx[k] + r_ * np.cos(th), by[k] + r_ * np.sin(th)
                    else:
                        far = np.argwhere((dist > 8) & (ii >= 8) & (ii < 56) & (jj >= 8) & (jj < 56))
                        if not len(far):
                            continue
                        ya, xa = far[rng.integers(len(far))] + rng.uniform(-0.5, 0.5, 2)
                    if not (8 <= xa < 56 and 8 <= ya < 56):
                        continue
                    xn, yn = I.aligned_to_native(P, e, xa, ya)
                    t = I.inject_point(P, img_i, var_i, e, xn, yn, I.Sed(ab_ref=float(rng.uniform(16.0, 20.5))), rng=rng, shot=True)
                    if t:
                        inj.append(dict(set="fresh", kind=kind, e=int(e), x_al=float(xa), y_al=float(ya), ab=t["ab"],
                                        snr_pred=t["snr_pred_psf"], trail_px=0.0))
            for e in {d["e"] for d in inj}:
                sig[e] = map_coordinates(img_i[e] - P.a["img"][e], [P.a["al_y"][e], P.a["al_x"][e]], order=1, cval=0.0)
            del img_i, var_i
        for e in tg:
            T, V, G = D["img"][e], D["var"][e], D["good"][e]
            fin = [np.isfinite(preds[m][e]) for m in METHODS]
            for m, f in zip(METHODS, fin):
                cover[m][0] += int((G & f).sum())
                cover[m][1] += int(G.sum())
            # common pixels of the methods that predict anything for this epoch (a method with no prediction at
            # all, e.g. a static reference that was not computed in time, gets NaN and drops out of the summaries)
            avail = [f.any() for f in fin]
            if not any(avail):
                continue
            common = G & np.logical_and.reduce([f for f, a in zip(fin, avail) if a])
            if common.sum() < 200:
                continue
            res = [np.where(common, T - preds[m][e], 0.0) if a else np.full_like(T, np.nan) for m, a in zip(METHODS, avail)]
            sd = np.sqrt(V)
            gi = np.where(common.ravel())[0]
            pick = rng.choice(gi, min(400, len(gi)), replace=False)
            nb = np.where((common & near).ravel())[0][:400]
            tag = "" if all(avail) else "/no_staticref_epochs"   # every table row compares identical pixels
            for m, r, a in zip(METHODS, res, avail):
                if not a:
                    continue
                chi = (r / sd).ravel()
                pix[m].setdefault(subset[e] + tag, []).append(chi[pick])
                pix[m].setdefault(subset[e] + "/near_bright" + tag, []).append(chi[nb])
            # matched filter at bright stars (false positives) and random isolated spots (noise calibration / FP)
            far = np.argwhere((dist > 6) & (ii >= 8) & (ii < 56) & (jj >= 8) & (jj < 56))
            spots = [("star", x, y) for x, y in zip(bx, by)]
            spots += [("random", x, y) for y, x in (far[rng.choice(len(far), min(3, len(far)), replace=False)] if len(far) else [])]
            for kind, x, y in spots:
                o = mf.snr(res, V, common, e, float(x), float(y))
                if o:
                    pos_rows.append(dict(patch=patch, e=int(e), subset=subset[e], kind=kind, **{m: o[k][0] for k, m in enumerate(METHODS)}))
            if e in sig:
                for d in inj:
                    if d["e"] != e:
                        continue
                    o = mf.snr(res, V, common, e, d["x_al"], d["y_al"], extra=sig[e])
                    o0 = mf.snr([np.zeros_like(T)], V, common, e, d["x_al"], d["y_al"], extra=sig[e])
                    if o:
                        dd = float(dist[int(round(d["y_al"])), int(round(d["x_al"]))])
                        inj_rows.append(dict(patch=patch, subset=subset[e], dist_bright_px=dd, **d,
                                             **{m: o[k][0] for k, m in enumerate(METHODS)},
                                             **{m + "_flux_ratio": o[k][1] / o0[0][1] if o0 and o0[0][1] > 0 else np.nan
                                                for k, m in enumerate(METHODS)}))
            if is_test and not fig_done and len(bx) and (common & near).sum() > 20:
                es_figure(T, V, preds, e, os.path.join(A.work, "fig_expected_sky_example.png"), patch)
                fig_done = True
        log(f"es_eval {patch}: {len(tg)} targets, pos rows {len(pos_rows)}, injection rows {len(inj_rows)}")
    pos, inj = pd.DataFrame(pos_rows), pd.DataFrame(inj_rows)
    pos.to_csv(os.path.join(A.work, "es_eval_positions.csv"), index=False)
    inj.to_csv(os.path.join(A.work, "es_eval_injections.csv"), index=False)
    MET["es_eval"] = summarize_es(pix, cover, pos, inj)
    log("es_eval summary", json.dumps(MET["es_eval"].get("verdict", {})))


def summarize_es(pix, cover, pos, inj):
    import numpy as np
    nb = 100 if A.smoke else 1000
    out = dict(label="MEASURED on the region-held-out test clusters NEP-D, SEP-B, ECL-2, MID-2 (subset 'region' = epochs "
                     "before 2026-06-17, 'region+time' = later epochs, never used in training); calibration on val NEP-C; "
                     "CIs COMPUTED (bootstrap)",
               methods=dict(engine_2ref="mean of the 2 closest-wavelength other-epoch patches (same detector, > 1 day away), "
                                        "as the engine's static-sky references",
                            a8_staticref="A8 static-sky reference baseline (baselines_v2 method)",
                            unet="Expected-Sky U-Net, K=6 closest-wavelength other epochs"),
               coverage={m: c[0] / c[1] if c[1] else None for m, c in cover.items()})
    rs = {}
    for m in METHODS:
        for sub, L in pix[m].items():
            v = np.concatenate(L) if L else np.zeros(0)
            v = v[np.isfinite(v)]
            if len(v) < 10:
                continue
            med = np.median(v)
            rs.setdefault(sub, {})[m] = dict(n_pix=int(len(v)), chi_robust_std=float(1.4826 * np.median(np.abs(v - med))),
                                             chi_rms=float(np.sqrt(np.mean(v ** 2))), chi_median=float(med),
                                             frac_abs_chi_gt5=float(np.mean(np.abs(v) > 5)))
    out["residual_chi"] = rs
    out["residual_note"] = "chi = (target - prediction)/sqrt(VARIANCE) on pixels where every method in the table predicts (rows " \
                           "tagged /no_staticref_epochs: epochs without an A8 reference, engine vs U-Net only); " \
                           "'/near_bright' = pixels within 4 px of a bright static source"
    # S/N calibration per method: robust std of matched-filter S/N at random isolated val spots -> 1
    cal, ncal = {}, {}
    if len(pos):
        rv = pos[(pos.subset == "val") & (pos.kind == "random")]
        for m in METHODS:
            v = rv[m].dropna().values
            ncal[m] = int(len(v))
            cal[m] = float(1.4826 * np.median(np.abs(v - np.median(v)))) if len(v) >= 10 else 1.0
    out["snr_calibration"] = dict(factors=cal, n_spots=ncal,
                                  note="matched-filter S/N divided by this (robust std at random val spots; 1.0 if < 10 spots)")
    # '3way' = rows where all three methods have a value; '2way' = engine vs U-Net on every row
    views = [("3way", METHODS), ("2way", ["engine_2ref", "unet"])]
    fp = {}
    for view, ms in views if len(pos) else []:
        pv = pos.dropna(subset=ms)
        for sub in ["region", "region+time"]:
            for kind in ["star", "random"]:
                d = pv[(pv.subset == sub) & (pv.kind == kind)]
                if not len(d):
                    continue
                for m in ms:
                    s = d[m].values / cal.get(m, 1.0)
                    fp.setdefault(f"{view}/{sub}/{kind}", {})[m] = dict(
                        n=int(len(s)), frac_snr_gt5=float(np.mean(s > 5)), frac_snr_lt_minus5=float(np.mean(s < -5)),
                        ci95_frac_snr_gt5=bootstrap(lambda i: float(np.mean(s[i] > 5)), len(s), nb))
    out["false_positives"] = fp
    out["false_positive_note"] = "fraction of (epoch, position) with calibrated S/N > 5 where nothing was injected: " \
                                 "'star' = at bright static sources, 'random' = random spots > 6 px from them"
    comp = {}
    if len(inj):
        inj = inj.copy()
        inj["near"] = np.where(inj.dist_bright_px <= 4, "near_bright_le4px", "isolated_gt4px")
        groups = [(view, ms, g, d) for view, ms in views
                  for g, d in inj.dropna(subset=ms).groupby(["set", "subset", "near"])]
        for view, ms, (st, sub, near), d in groups:
            key = f"{view}/{st}/{sub}/{near}"
            det = d[d.snr_pred > 5]
            for m in ms:
                s = d[m].values / cal.get(m, 1.0)
                sd_ = det[m].values / cal.get(m, 1.0)
                comp.setdefault(key, {})[m] = dict(
                    n=int(len(s)), completeness_snr5=float(np.mean(s >= 5)),
                    n_detectable=int(len(sd_)), completeness_detectable=float(np.mean(sd_ >= 5)) if len(sd_) else None,
                    ci95_completeness_detectable=bootstrap(lambda i: float(np.mean(sd_[i] >= 5)), len(sd_), nb) if len(sd_) >= 10 else None,
                    median_flux_ratio=float(np.nanmedian(d[m + "_flux_ratio"])))
    out["injection_recovery"] = comp
    out["injection_note"] = "'detectable' = predicted PSF S/N > 5 from the A8 kit; completeness = calibrated matched-filter " \
                            "S/N >= 5 at the true position; flux ratio = recovered / noiseless injected (same filter)"
    out["verdict"] = es_verdict(out)
    return out


def es_verdict(o):
    """Plain comparisons of the U-Net against the better baseline, from the numbers above (COMPUTED)."""
    v = {}
    r = o["residual_chi"].get("region", {})
    if "unet" in r:
        b = min(r[m]["chi_robust_std"] for m in r if m != "unet")
        v["residual_robust_std_region"] = f"unet {r['unet']['chi_robust_std']:.3f} vs best baseline {b:.3f}: " + \
            ("U-Net lower" if r["unet"]["chi_robust_std"] < b else "U-Net NOT lower")
    rn = o["residual_chi"].get("region/near_bright", {})
    if "unet" in rn:
        b = min(rn[m]["chi_rms"] for m in rn if m != "unet")
        v["residual_rms_near_bright_region"] = f"unet {rn['unet']['chi_rms']:.2f} vs best baseline {b:.2f}: " + \
            ("U-Net lower" if rn["unet"]["chi_rms"] < b else "U-Net NOT lower")
    f = o["false_positives"].get("3way/region/star", {}) or o["false_positives"].get("2way/region/star", {})
    if "unet" in f:
        b = min(f[m]["frac_snr_gt5"] for m in f if m != "unet")
        v["false_positives_at_stars_region"] = f"unet {f['unet']['frac_snr_gt5']:.4f} vs best baseline {b:.4f}: " + \
            ("U-Net fewer" if f["unet"]["frac_snr_gt5"] < b else "U-Net NOT fewer")
    c = o["injection_recovery"].get("3way/fresh/region/near_bright_le4px", {}) or \
        o["injection_recovery"].get("2way/fresh/region/near_bright_le4px", {})
    if "unet" in c and c["unet"]["completeness_detectable"] is not None:
        b = max((c[m]["completeness_detectable"] or 0) for m in c if m != "unet")
        v["completeness_near_bright_region"] = f"unet {c['unet']['completeness_detectable']:.3f} vs best baseline {b:.3f}: " + \
            ("U-Net higher" if c["unet"]["completeness_detectable"] > b else "U-Net NOT higher")
    v["note"] = "differences inside the bootstrap CIs are not evidence that one method is better"
    return v


def es_figure(T, V, preds, e, path, patch):
    import numpy as np
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(1, 4, figsize=(11, 3))
    lo, hi = np.nanpercentile(T, [5, 99.5])
    ax[0].imshow(T, origin="lower", vmin=lo, vmax=hi, cmap="gray")
    ax[0].set_title(f"{patch} epoch {e}", fontsize=8)
    for a, m in zip(ax[1:], METHODS):
        a.imshow((T - preds[m][e]) / np.sqrt(V), origin="lower", vmin=-5, vmax=5, cmap="RdBu_r")
        a.set_title(f"(data - {m}) / sigma", fontsize=8)
    for a in ax:
        a.set_xticks([])
        a.set_yticks([])
    fig.tight_layout()
    fig.savefig(path, dpi=100)
    plt.close(fig)


# ================================================================== report
def _f(x, nd=3):
    if x is None:
        return "-"
    if isinstance(x, list):
        return "[" + ", ".join(_f(v, nd) for v in x) + "]"
    if isinstance(x, float):
        return f"{x:.{nd}f}"
    return str(x)


def write_report():
    L = ["# K2 rewind-c2-ai report", "",
         f"Updated {time.strftime('%Y-%m-%d %H:%M:%S')}, {(time.time() - T0) / 60:.1f} min after start"
         f"{' (SMOKE RUN: tiny subset, numbers are NOT meaningful)' if A.smoke else ''}.",
         "Labels: MEASURED = measured in this run on held-out data; COMPUTED = derived (bootstrap CIs, verdicts); "
         "ESTIMATED = assumption.", ""]
    L += ["## Stages (MEASURED)", "", "| stage | status | minutes |", "|-|-|-|"]
    for k, v in MET.get("stages", {}).items():
        L.append(f"| {k} | {v['status']} | {v['minutes']} |")
    rf = MET.get("realfake")
    if rf:
        L += ["", "## Real-or-fake: CNN vs gradient boosting (MEASURED on held-out groups)", "",
              f"{rf['n_samples']} samples ({rf['n_real']} real asteroid stamps, {rf['n_fake']} planted artifacts in empty "
              f"stamps), {rf['n_frames']} frames, {rf['n_sky_cells']} sky cells. GB: {rf['gb']}. CNN: {rf['cnn']}.", ""]
        for sk, s in rf["splits"].items():
            if not s["runs"]:
                continue
            r0 = s["runs"][0]
            L += [f"### split {sk} (groups = {s['group_column']}, 30% test; seed 0: {r0['n_test']} test samples, "
                  f"{r0['test_groups']} test groups)", "",
                  "| model | accuracy | ROC AUC | recall real | recall fake | precision real |", "|-|-|-|-|-|-|"]
            for m in ["cnn", "gradient_boosting", "rules", "majority"]:
                q = r0[m]
                L.append(f"| {m} | {_f(q['accuracy'])} | {_f(q.get('roc_auc'))} | {_f(q.get('recall_real'))} | "
                         f"{_f(q.get('recall_fake'))} | {_f(q.get('precision_real'))} |")
            ci = r0.get("ci95", {})
            if ci:
                L += ["", f"Bootstrap 95% CI (COMPUTED): CNN acc {_f(ci['cnn_accuracy'])}, GB acc {_f(ci['gb_accuracy'])}, "
                      f"CNN AUC {_f(ci['cnn_auc'])}, GB AUC {_f(ci['gb_auc'])}; CNN - GB accuracy {_f(ci['cnn_minus_gb_accuracy'])}, "
                      f"CNN - GB AUC {_f(ci['cnn_minus_gb_auc'])}."]
                d = ci["cnn_minus_gb_auc"]
                if d[0] is not None:
                    L.append("Verdict (COMPUTED): " + ("CNN AUC higher than GB (CI above 0)." if d[0] > 0 else
                                                      "GB AUC higher than CNN (CI below 0)." if d[1] < 0 else
                                                      "no significant AUC difference between CNN and GB."))
            sm = s["summary_over_seeds"]
            L += ["", f"Over {s['n_seeds']} group splits (mean +/- std): CNN acc {_f(sm.get('cnn_accuracy_mean'))} +/- "
                  f"{_f(sm.get('cnn_accuracy_std'))}, AUC {_f(sm.get('cnn_roc_auc_mean'))} +/- {_f(sm.get('cnn_roc_auc_std'))}; "
                  f"GB acc {_f(sm.get('gradient_boosting_accuracy_mean'))} +/- {_f(sm.get('gradient_boosting_accuracy_std'))}, "
                  f"AUC {_f(sm.get('gradient_boosting_roc_auc_mean'))} +/- {_f(sm.get('gradient_boosting_roc_auc_std'))}; "
                  f"majority acc {_f(sm.get('majority_accuracy_mean'))}.", "",
                  "Per source (seed 0, fraction correct): " + "; ".join(
                      f"{src}: CNN {_f(r0['cnn']['per_source_correct'][src]['frac_correct'])} / GB "
                      f"{_f(r0['gradient_boosting']['per_source_correct'][src]['frac_correct'])} (n={r0['cnn']['per_source_correct'][src]['n']})"
                      for src in r0["cnn"]["per_source_correct"]), ""]
    dl = MET.get("download")
    if dl:
        L += ["## v2 download (MEASURED)", "", ", ".join(f"{k}: {v}" for k, v in dl.items() if k != "label"), ""]
    ds = MET.get("dataset_v2k")
    if ds:
        L += ["## Dataset built on Kaggle (v2k = A8 v2 frame list; MEASURED)", "",
              f"{ds['frames']} frames, {ds['patch_epochs']} patch-epochs, {ds['patches']} patches; by cluster {ds['by_cluster']}; "
              f"by region/time {ds['by_region_and_time']}.", ""]
    tr = MET.get("es_train")
    if tr:
        L += ["## Expected Sky training (MEASURED)", "",
              f"{tr['n_train_targets']} train targets, {tr['n_val_targets']} val targets, {tr['epochs_run']} epochs on "
              f"{tr['device']}, {tr['params']} params. Val loss: base (engine-style 2-ref mean) {_f(tr['val_loss_base'], 4)}, "
              f"best U-Net {_f(tr['val_loss_best'], 4)} -> U-Net {'beats' if tr['model_beats_base_on_val'] else 'does NOT beat'} "
              f"the base on val.", ""]
    ev = MET.get("es_eval")
    if ev:
        L += ["## Expected Sky evaluation", "", ev["label"] + ".", "",
              "Coverage (fraction of good target pixels with a prediction): " +
              ", ".join(f"{m} {_f(c)}" for m, c in ev["coverage"].items()), "",
              "### Residual chi (" + ev["residual_note"] + ")", "",
              "| subset | method | n pix | robust std | rms | frac abs chi > 5 |", "|-|-|-|-|-|-|"]
        for sub, d in ev["residual_chi"].items():
            for m, q in d.items():
                L.append(f"| {sub} | {m} | {q['n_pix']} | {_f(q['chi_robust_std'])} | {_f(q['chi_rms'])} | {_f(q['frac_abs_chi_gt5'], 4)} |")
        L += ["", "### False positives (" + ev["false_positive_note"] + ")", "",
              f"S/N calibration factors (COMPUTED): {ev['snr_calibration']['factors']}", "",
              "| subset/kind | method | n | frac S/N > 5 | 95% CI | frac S/N < -5 |", "|-|-|-|-|-|-|"]
        for sub, d in ev["false_positives"].items():
            for m, q in d.items():
                L.append(f"| {sub} | {m} | {q['n']} | {_f(q['frac_snr_gt5'], 4)} | {_f(q['ci95_frac_snr_gt5'], 4)} | {_f(q['frac_snr_lt_minus5'], 4)} |")
        L += ["", "### Injected-source recovery (" + ev["injection_note"] + ")", "",
              "| set/subset/position | method | n | completeness | n detectable | completeness detectable | 95% CI | median flux ratio |",
              "|-|-|-|-|-|-|-|-|"]
        for key, d in ev["injection_recovery"].items():
            for m, q in d.items():
                L.append(f"| {key} | {m} | {q['n']} | {_f(q['completeness_snr5'])} | {q['n_detectable']} | "
                         f"{_f(q['completeness_detectable'])} | {_f(q['ci95_completeness_detectable'])} | {_f(q['median_flux_ratio'])} |")
        L += ["", "### Verdict (COMPUTED)", ""] + [f"- {k}: {v}" for k, v in ev["verdict"].items()] + [""]
    L += ["## Caveats", "",
          "- Real-or-fake fakes are planted artifacts (cosmic, hot pair, streak, ringing), not real junk; real = known "
          "asteroids at S/N >= 5. A model can learn the planting recipe; held-out accuracy says nothing about other junk.",
          "- Sky cells are 10 x 10 deg; a frame is assigned to the cell of its median stamp position, so neighbouring "
          "cells can share a little sky.",
          "- Expected Sky: pole clusters share exposures; the 'region+time' subset (late epochs, never trained on) is the "
          "strict test. Injections use the A8 kit (real ePSF, shot noise); the PSF on the aligned grid ignores "
          "resampling blur, the same for every method.", ""]
    with open(os.path.join(A.work, "report.md"), "w") as f:
        f.write("\n".join(L))


# ================================================================== main
def main():
    global A, LOGF
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true", help="tiny subset of every stage (minutes, CPU ok)")
    ap.add_argument("--inputs-root", default=None, help="dir with data/, code/, rewind_engine/ (default: Kaggle glob)")
    ap.add_argument("--work", default="/kaggle/working" if os.path.isdir("/kaggle/working") else "k2_out")
    ap.add_argument("--tmp", default="/kaggle/tmp" if os.path.isdir("/kaggle/tmp") else "/tmp/k2tmp")
    ap.add_argument("--threads", type=int, default=32)
    ap.add_argument("--max-frames", type=int, default=0, help="cap frames per cluster (0 = whole v2 list)")
    ap.add_argument("--disk-reserve-gb", type=float, default=6.0)
    ap.add_argument("--n-art-per", type=int, default=2, help="planted artifacts per empty stamp (engine: 1)")
    ap.add_argument("--max-hours", type=float, default=10.5)
    ap.add_argument("--keep-raw", action="store_true")
    ap.add_argument("--force", action="store_true", help="rerun stages already marked ok in metrics.json")
    ap.add_argument("--stages", default="realfake,download,build,staticref,es_train,es_eval")
    A = ap.parse_args()
    A.inputs = find_inputs(A.inputs_root)
    os.makedirs(A.work, exist_ok=True)
    os.makedirs(A.tmp, exist_ok=True)
    LOGF = os.path.join(A.work, "run_log.txt")
    ensure_packages()
    mp = os.path.join(A.work, "metrics.json")
    if os.path.exists(mp):
        try:
            MET.update(json.load(open(mp)))
        except ValueError:
            pass
    MET.update(smoke=A.smoke, inputs_root=A.inputs, python=sys.version.split()[0])
    A.root = setup_root()
    try:
        import torch
        MET["device"] = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "cpu"
        MET["torch"] = torch.__version__
    except ImportError:
        MET["device"] = "no torch"
    log("K2 start", json.dumps(dict(smoke=A.smoke, inputs=A.inputs, work=A.work, tmp=A.tmp, device=MET["device"],
                                    free_gb_tmp=round(shutil.disk_usage(A.tmp).free / 1e9, 1),
                                    free_gb_work=round(shutil.disk_usage(A.work).free / 1e9, 1))))
    sm = A.smoke
    budgets = dict(realfake=4 if sm else 45, download=6 if sm else 180, build=5 if sm else 60,
                   staticref=3 if sm else 60, es_train=4 if sm else 90, es_eval=4 if sm else 75)
    fns = dict(realfake=stage_realfake, download=stage_download, build=stage_build, staticref=stage_staticref,
               es_train=stage_es_train, es_eval=stage_es_eval)
    want = A.stages.split(",")
    ok = {}
    for name in want:
        if name in ("build", "staticref", "es_train", "es_eval") and not all(
                ok.get(d, True) for d in dict(build=["download"], staticref=["build"], es_train=["build"],
                                              es_eval=["build", "es_train"])[name]):
            log(f"== {name}: skipped (an earlier stage it needs failed)")
            MET.setdefault("stages", {})[name] = dict(status="skipped (dependency failed)", minutes=0, label="MEASURED")
            ok[name] = False
            continue
        ok[name] = run_stage(name, fns[name], budgets[name])
    save_metrics()
    write_report()
    log("K2 done", json.dumps({k: v["status"] for k, v in MET.get("stages", {}).items()}))


if __name__ == "__main__":
    main()
