"""Build the private Kaggle dataset "rewind-c2-inputs" and the K1 kernel folders.

  python kaggle/build_inputs.py [--out /tmp/c2k] [--shards 3]

Dataset tree (<out>/ds/rewind_inputs/, mirrors MAIN): rewind_engine/, code/A0, code/A2, small data tables,
the real-or-fake model, K1 shard lists (kaggle/k1_<shard>.csv) and the K2 files from kaggle/k2/k2_inputs_manifest.txt.
K1 objects = objects.all_objects() minus the objects already in MAIN/data/site/index.json, except the Y1
stack candidates (re-run independently as a cross-check). No secrets, no personal data."""
import argparse
import glob
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
WT = os.path.dirname(HERE)
sys.path.insert(0, WT)
from rewind_engine import config as C  # noqa: E402
from rewind_engine import objects as O  # noqa: E402

OWNER = "danilbobrow"
DATASET = "rewind-c2-inputs"
DATA_FILES = [
    "data/01-targets/lists/a_spherex_precovery_shortlist.csv",
    "data/01-targets/lists/b_lost_recovery_shortlist.csv",
    "data/02-orbits/lost_spherex/lost_top20_phaseB_summary.csv",
    "data/02-orbits/lost_spherex/lost_L1top20_phaseB_summary.csv",
    "data/02-orbits/horizons/spherex_vectors_geo_5min.parquet",
    "data/02-orbits/mpc/obscodes_api.json",
    "data/06-composition/derived/spherex_channels.csv",
    "data/06-composition/derived/spherex_templates_cent.csv",
    "data/06-composition/derived/spherex_templates_allpix.csv",
    "data/06-composition/derived/template_catalog.csv",
    "data/09-people/stories/featured_discovery_stories.json",
]
DATA_DIRS = ["data/07-answer-keys/labeled_set"]
SMOKE = ["c2026s1", "c2026q1", "2026aq1"]


def kernel_meta(slug, code_file, gpu=False):
    return {"id": f"{OWNER}/{slug}", "title": slug, "code_file": code_file, "language": "python", "kernel_type": "script",
            "is_private": True, "enable_gpu": gpu, "enable_internet": True, "dataset_sources": [f"{OWNER}/{DATASET}"],
            "competition_sources": [], "kernel_sources": []}


def k1_lists(n_shards):
    allo = O.all_objects()
    idx = json.load(open(os.path.join(C.SITE, "index.json")))
    mac = {e["slug"] for e in idx["objects"]}
    keep = allo[~allo.slug.isin(mac) | allo.y1.astype(bool)].copy()
    first = (keep.slug == "c2026s1").astype(int) * 2 + keep.y1.astype(int)  # S1 first, then Y1 (300 frames), then rank order
    keep = keep.assign(_o=-first).sort_values("_o", kind="stable").drop(columns="_o").reset_index(drop=True)
    shards = {chr(97 + i): keep.iloc[i::n_shards] for i in range(n_shards)}
    shards["smoke"] = allo.set_index("slug").loc[SMOKE].reset_index()[allo.columns]
    skipped = sorted(mac & set(allo.slug) - set(keep.slug))
    return shards, skipped


def k2_kernel(out):
    """Kernel folder for K2 (GPU): kaggle/k2/k2_main.py as is."""
    kd = os.path.join(out, "kernels", "rewind-c2-ai")
    os.makedirs(kd, exist_ok=True)
    shutil.copy(os.path.join(HERE, "k2", "k2_main.py"), os.path.join(kd, "k2_main.py"))
    json.dump(kernel_meta("rewind-c2-ai", "k2_main.py", gpu=True), open(os.path.join(kd, "kernel-metadata.json"), "w"), indent=1)
    print("K2 kernel folder:", kd)


def build(out, n_shards, catchup=()):
    ds = os.path.join(out, "ds")
    root = os.path.join(ds, "rewind_inputs")
    shutil.rmtree(ds, ignore_errors=True)
    os.makedirs(root)
    import subprocess
    import time
    head = subprocess.run(["git", "-C", WT, "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    open(os.path.join(root, "MARKER"), "w").write(f"rewind_inputs built {time.strftime('%Y-%m-%d %H:%M')} from c2-kaggle {head}\n")
    ign = shutil.ignore_patterns("__pycache__", "*.pyc")
    shutil.copytree(os.path.join(WT, "rewind_engine"), os.path.join(root, "rewind_engine"), ignore=ign)
    for sub in ("code/A0", "code/A2"):
        shutil.copytree(os.path.join(WT, sub), os.path.join(root, sub), ignore=ign)
    k2 = os.path.join(HERE, "k2", "k2_inputs_manifest.txt")
    k2_files = [l.strip() for l in open(k2) if l.strip() and not l.startswith("#")] if os.path.exists(k2) else []
    for rel in DATA_FILES + DATA_DIRS + k2_files:
        src = os.path.join(C.MAIN, rel)
        if not os.path.exists(src):  # code paths (rewind_engine/, code/) live in this worktree
            src = os.path.join(WT, rel)
        if not os.path.exists(src):
            print("missing, skipped:", rel)
            continue
        dst = os.path.join(root, rel)
        if os.path.exists(dst):
            continue
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if os.path.isdir(src):
            shutil.copytree(src, dst, dirs_exist_ok=True, ignore=ign)
        else:
            shutil.copy(src, dst)
    if os.path.isdir(os.path.join(HERE, "k2")):
        shutil.copytree(os.path.join(HERE, "k2"), os.path.join(root, "kaggle", "k2"), ignore=ign, dirs_exist_ok=True)
    for sub in ("kernels", "debias"):  # kete starts with an empty cache otherwise (no planet SPK files)
        shutil.copytree(os.path.join(C.KETE_CACHE, sub), os.path.join(root, "kete-cache-seed", sub))
    os.makedirs(os.path.join(root, "realfake"))
    shutil.copy(os.path.join(C.WORK, "realfake", "models.joblib"), os.path.join(root, "realfake", "models.joblib"))
    shards, skipped = k1_lists(n_shards)
    if catchup:  # re-run of objects that failed in the shards (after fixes), as one more kernel
        allo = O.all_objects()
        shards[chr(97 + n_shards)] = allo[allo.slug.isin(catchup)].reset_index(drop=True)
    os.makedirs(os.path.join(root, "kaggle"), exist_ok=True)
    for k, df in shards.items():
        df.to_csv(os.path.join(root, "kaggle", f"k1_{k}.csv"), index=False)
    json.dump({"title": DATASET, "id": f"{OWNER}/{DATASET}", "isPrivate": True,
               "licenses": [{"name": "other"}],
               "description": "Private inputs for the Rewind engine Kaggle runs (code, small tables, labelled stamps)."},
              open(os.path.join(ds, "dataset-metadata.json"), "w"), indent=1)
    # kernels
    src = open(os.path.join(HERE, "k1", "k1_main.py")).read()
    for k in list(shards):
        if k == "smoke":
            continue
        kd = os.path.join(out, "kernels", f"rewind-c2-engine-all-{k}")
        os.makedirs(kd, exist_ok=True)
        open(os.path.join(kd, "k1_main.py"), "w").write(src.replace('SHARD = "__SHARD__"', f'SHARD = "{k}"'))
        json.dump(kernel_meta(f"rewind-c2-engine-all-{k}", "k1_main.py"), open(os.path.join(kd, "kernel-metadata.json"), "w"), indent=1)
    kd = os.path.join(out, "kernels", "smoke")  # smoke = shard a's kernel slug with the smoke list
    os.makedirs(kd, exist_ok=True)
    open(os.path.join(kd, "k1_main.py"), "w").write(src.replace('SHARD = "__SHARD__"', 'SHARD = "smoke"'))
    json.dump(kernel_meta("rewind-c2-engine-all-a", "k1_main.py"), open(os.path.join(kd, "kernel-metadata.json"), "w"), indent=1)
    mb = sum(os.path.getsize(p) for p in glob.glob(os.path.join(root, "**"), recursive=True) if os.path.isfile(p)) / 1e6
    print(f"dataset {root}: {mb:.0f} MB; shards " + ", ".join(f"{k}={len(v)}" for k, v in shards.items()))
    print(f"skipped (already in the Mac index, not Y1): {len(skipped)} {skipped}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="/tmp/c2k")
    ap.add_argument("--shards", type=int, default=3)
    ap.add_argument("--catchup", default="", help="slugs for an extra catch-up shard")
    ap.add_argument("--k2-only", action="store_true", help="only (re)write the K2 kernel folder")
    a = ap.parse_args()
    if not a.k2_only:
        build(a.out, a.shards, [s for s in a.catchup.split(",") if s])
    k2_kernel(a.out)
