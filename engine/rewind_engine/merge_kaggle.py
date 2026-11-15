"""Merge the Kaggle K1 outputs into a copy of the website folder.

  python -m rewind_engine.merge_kaggle [--site MAIN/data/site] [--kaggle MAIN/data/kaggle]
                                       [--out MAIN/data/kaggle/site_merged] [--no-orbits]

Kaggle run folders are <kaggle>/rewind-c2-engine-all-*/ (from `kaggle kernels output`), each with
site/objects/<slug>/ and work/objects/<slug>/entry.json. Objects already in the site index stay as they are
(the Mac run owns them); Kaggle re-runs of those are only compared, in <out>/kaggle_crosscheck.json. New
objects are copied in. Then index.json (entries, headline stats, flash_events) and the orbits slugs map
(orbits.json / orbits.bin / orbits.bin.json, in_rewind bit) are rebuilt in <out>. <site> is only read."""
from __future__ import annotations

import argparse
import glob
import json
import os
import shutil

import pandas as pd

from . import config as C


def kaggle_entries(kdir: str) -> dict:
    """{slug: (run folder, entry.json path)}; the newest entry wins if a slug is in several runs."""
    best = {}
    for p in glob.glob(os.path.join(kdir, "rewind-c2-engine-all-*", "work", "objects", "*", "entry.json")):
        slug = p.split(os.sep)[-2]
        run = p.split(os.sep + "work" + os.sep)[0]
        if slug not in best or os.path.getmtime(p) > os.path.getmtime(best[slug][1]):
            best[slug] = (run, p)
    return best


def rewind_objects(slugs) -> pd.DataFrame:
    """Object rows (desig, name, kind, slug) for every slug in the merged index."""
    from . import objects as O
    df = pd.concat([O.first_run_objects(), O.all_objects()], ignore_index=True).drop_duplicates("slug")
    return df[df.slug.isin(set(slugs))].reset_index(drop=True)


def merge(site: str, kdir: str, out: str, orbits: bool = True) -> dict:
    from . import site as S
    if os.path.abspath(out) == os.path.abspath(site):
        raise SystemExit("--out must not be the site folder")
    if os.path.isdir(out):
        shutil.rmtree(out)
    shutil.copytree(site, out)
    idx = json.load(open(os.path.join(site, "index.json")))
    have = {e["slug"]: e for e in idx["objects"]}
    entries, flashes = list(idx["objects"]), list(idx.get("flash_events", []))
    nread = int(idx.get("headline_stats", {}).get("frames_read", 0))
    cross, added, missing = [], [], []
    for slug, (run, p) in sorted(kaggle_entries(kdir).items()):
        j = json.load(open(p))
        e = j["entry"]
        if slug in have:
            m = have[slug]
            cross.append(dict(slug=slug, run=os.path.basename(run), mac_verdict=m["verdict"], kaggle_verdict=e["verdict"],
                              mac_snr=m.get("best_snr"), kaggle_snr=e.get("best_snr"), mac_frames=m.get("n_frames"),
                              kaggle_frames=e.get("n_frames"), same_verdict=m["verdict"] == e["verdict"]))
            continue
        src = os.path.join(run, "site", "objects", slug)
        if not os.path.isdir(src):
            missing.append(slug)
            continue
        shutil.copytree(src, os.path.join(out, "objects", slug))
        entries.append(e)
        flashes += j["flashes"]
        nread += int(j["n_read"])
        added.append(slug)
    C.SITE = out
    new = S.write_index(entries, flashes, nread)
    for k, v in idx.items():  # keep any extra top-level fields of the original index
        new.setdefault(k, v)
    S.dump(new, os.path.join(out, "index.json"))
    if orbits:
        work = os.path.join(kdir, "merge_work")  # SBDB cache for the slugs map (Mac + Kaggle records), not the Mac WORK
        os.makedirs(os.path.join(work, "sbdb"), exist_ok=True)
        for p in glob.glob(os.path.join(C.WORK, "sbdb", "*.json")) + glob.glob(os.path.join(kdir, "rewind-c2-engine-all-*", "work", "sbdb", "*.json")):
            shutil.copy(p, os.path.join(work, "sbdb", os.path.basename(p)))
        C.WORK = work
        from . import site_static
        objs = rewind_objects([e["slug"] for e in entries])
        site_static.write_orbits(out, rewind_desigs=list(objs.desig), rewind=objs)
    summary = dict(added=len(added), already_in_site=len(cross), missing_site_folder=missing,
                   crosscheck_same_verdict=sum(c["same_verdict"] for c in cross), objects_total=len(entries),
                   verdicts=pd.Series([e["verdict"] for e in entries]).value_counts().to_dict(), added_slugs=added)
    json.dump(dict(summary=summary, crosscheck=cross), open(os.path.join(out, "kaggle_crosscheck.json"), "w"), indent=1)
    print(json.dumps(summary, indent=1))
    return summary


def main(argv=None):
    ap = argparse.ArgumentParser(prog="rewind_engine.merge_kaggle")
    ap.add_argument("--site", default=C.SITE)
    ap.add_argument("--kaggle", default=os.path.join(C.DATA, "kaggle"))
    ap.add_argument("--out", default=os.path.join(C.DATA, "kaggle", "site_merged"))
    ap.add_argument("--no-orbits", action="store_true")
    a = ap.parse_args(argv)
    merge(a.site, a.kaggle, a.out, orbits=not a.no_orbits)


if __name__ == "__main__":
    main()
