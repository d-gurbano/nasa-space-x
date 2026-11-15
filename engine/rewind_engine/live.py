"""LIVE run: objects first observed in the last ~14 days (JPL SBDB first_obs >= 2026-11-01), screened with IRSA MOST
for public SPHEREx frames before their first observation, then the full engine (same final rules) on the best ones,
and REAL orbit refits with their current few-day MPC arcs plus our SPHEREx positions.

    python -c "from rewind_engine import live; live.screen()"     # candidates + MOST screen -> WORK/live/screen.csv
"""
from __future__ import annotations

import json
import os
import re
import time

import numpy as np
import pandas as pd
import requests

from . import config as C
from .frames import iso_to_mjd, mjd_to_iso

LIVE = os.path.join(C.WORK, "live")
FIELDS = "full_name,pdes,prefix,kind,first_obs,last_obs,data_arc,n_obs_used,H,M1,K1,neo,pha,e,a,q,i,condition_code,class"


def candidates(since="2026-11-01"):
    os.makedirs(LIVE, exist_ok=True)
    rows = []
    for kind in ("a", "c"):
        r = requests.get("https://ssd-api.jpl.nasa.gov/sbdb_query.api", params={
            "fields": FIELDS, "sb-kind": kind, "sb-cdata": json.dumps({"AND": [f"first_obs|GE|{since}"]})}, timeout=120)
        j = r.json()
        rows += [dict(zip(j["fields"], x)) for x in j.get("data", [])]
    d = pd.DataFrame(rows)
    for c in ("data_arc", "n_obs_used", "H", "M1", "e", "q", "a", "condition_code"):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d["desig"] = [f"{p}/{x}" if isinstance(p, str) and p else x for p, x in zip(d.prefix, d.pdes)]
    d["slug"] = d.desig.map(lambda s: re.sub(r"[^a-z0-9]+", "", s.lower()))
    d.to_csv(os.path.join(LIVE, "candidates.csv"), index=False)
    return d


def _screen_one(r, window_d=120):
    from .pilot import R
    cache = os.path.join(LIVE, "most", r["slug"] + ".tbl")
    rec = dict(slug=r["slug"], desig=r["desig"], first_obs=r["first_obs"], arc=r["data_arc"], n_obs=r["n_obs_used"], H=r["H"],
               neo=r["neo"], cls=r["class"], pha=r["pha"], U=r["condition_code"])
    f0 = iso_to_mjd(r["first_obs"])
    try:
        m = R.most_query(r["desig"], mjd_to_iso(f0 - window_d), r["first_obs"], cache=cache)
        m = m[m.mjd_start < f0]
        v = pd.to_numeric(m.vmag, errors="coerce")
        rec.update(n_frames=len(m), newest=mjd_to_iso(m.mjd_start.max()) if len(m) else None,
                   vmin=float(v.min()) if len(m) else None, n_v21=int((v <= 21.0).sum()),
                   days_before=float(f0 - m.mjd_start.max()) if len(m) else None)
    except Exception as e:  # noqa
        rec.update(n_frames=0, error=str(e)[:120])
    return rec


def screen(since="2026-11-01", h_max_mba=18.5, workers=3):
    """MOST (catalog=spherex, last 120 days before the first observation) for NEOs, comets and bright main-belt objects."""
    from concurrent.futures import ThreadPoolExecutor
    d = candidates(since)
    d = d[(d.neo == "Y") | d.prefix.notna() | (d.H <= h_max_mba)].copy()
    os.makedirs(os.path.join(LIVE, "most"), exist_ok=True)
    out = []
    with ThreadPoolExecutor(workers) as ex:
        for rec in ex.map(_screen_one, [r for _, r in d.iterrows()]):
            out.append(rec)
            if len(out) % 25 == 0:
                pd.DataFrame(out).to_csv(os.path.join(LIVE, "screen.csv"), index=False)
                print(len(out), "screened", flush=True)
    s = pd.DataFrame(out)
    s.to_csv(os.path.join(LIVE, "screen.csv"), index=False)
    return s


def obj_rows(sel):
    """Engine object rows for live candidates (role precovery: discovery = first known observation)."""
    from .objects import horizons_command
    rows = []
    for r in sel.itertuples():
        comet = isinstance(r.desig, str) and "/" in r.desig
        rows.append(dict(name=r.desig, slug=r.slug, desig=r.desig, kind="comet" if comet else ("neo" if r.neo == "Y" else "mba"),
                         role="precovery", disc_iso=str(r.first_obs), earliest_obs_iso=str(r.first_obs), by="", site="",
                         pred_ab=None, y1=False, hz_cmd=horizons_command(r.desig), most_name=r.desig))
    return pd.DataFrame(rows)


def select(n=20, vmax=21.5):
    s = pd.read_csv(os.path.join(LIVE, "screen.csv"))
    s = s[(s.n_frames > 0) & (s.vmin <= vmax)].copy()
    s["score"] = s.vmin - 0.3 * np.log10(1 + s.n_v21)
    return s.sort_values("score").head(n)


def fetch_and_measure(sel, workers=12):
    """Prepare (MOST cached from the screen), fetch stamps + 1 reference per frame (120 frames), then measure."""
    import shutil
    from . import fetch as FE
    from . import frames as F
    from . import report
    objs = obj_rows(sel)
    os.environ.setdefault("REWIND_LANE", "L")
    results = []
    for o in objs.itertuples():
        d = os.path.join(C.WORK, "objects", o.slug)
        os.makedirs(d, exist_ok=True)
        src = os.path.join(LIVE, "most", o.slug + ".tbl")
        if os.path.exists(src) and not os.path.exists(os.path.join(d, "most.tbl")):
            shutil.copy(src, os.path.join(d, "most.tbl"))
        try:
            fr = F.prepare(o, cap=120)
            if len(fr):
                FE._run_jobs(FE.target_jobs(o.slug, fr), workers, f"{o.slug} target")
                plan = FE.plan_refs(o.slug, fr, n_ref=1, max_frames=120)
                FE._run_jobs(FE.ref_jobs(o.slug, plan), workers, f"{o.slug} refs")
            e, f, n = report.run_object(o)
            results.append(dict(slug=o.slug, verdict=e["verdict"], text=e["verdict_text"]))
        except Exception as ex:  # noqa
            import traceback
            traceback.print_exc()
            results.append(dict(slug=o.slug, verdict="ERROR", text=str(ex)[:200]))
        pd.DataFrame(results).to_csv(os.path.join(LIVE, "results.csv"), index=False)
        print(results[-1], flush=True)
    return results


def publish(sel, run_iso=None):
    """Merge the live objects into site/index.json (live, run_iso, flashes, live_stats; final kept) and, for every FOUND,
    add the real refit (current MPC arc + our SPHEREx positions) and the before/after cloud from those two fits."""
    import datetime as dt
    from . import impact as I
    from .site import dump
    run_iso = run_iso or dt.datetime.now(dt.timezone.utc).isoformat(timespec="minutes")
    objs = obj_rows(sel)
    idx_p = os.path.join(C.SITE, "index.json")
    idx = json.load(open(idx_p))
    slugs = set(objs.slug)
    idx["objects"] = [e for e in idx["objects"] if e["slug"] not in slugs]
    idx["flash_events"] = [f for f in idx["flash_events"] if f["slug"] not in slugs]
    impacts, stats = [], dict(searched=0, found=0, hints=0, too_faint=0, no_photos_yet=0)
    for o in objs.itertuples():
        ep = os.path.join(C.WORK, "objects", o.slug, "entry.json")
        if not os.path.exists(ep):
            continue
        j = json.load(open(ep))
        e, fl = j["entry"], j["flashes"]
        stats["searched"] += 1
        stats[{"FOUND": "found", "HINT": "hints", "TOO_FAINT": "too_faint"}.get(e["verdict"], "no_photos_yet")] += 1
        pp = os.path.join(C.SITE, "objects", o.slug, "object.json")
        page = json.load(open(pp))
        imp = None
        if e["verdict"] == "FOUND":
            try:
                imp, f0, f1 = I.impact_one(o)
                if f0 is not None and page.get("cloud"):
                    b, a, ref, sb_, sa_ = I.cloud_from_fits(f0, f1, page["cloud"]["dates_mjd"])
                    page["cloud"].update(before=b, after=a, before_sigma_km_at=dict(iso=mjd_to_iso(page["cloud"]["dates_mjd"][ref]), km=sb_),
                                         after_sigma_km_at=dict(iso=mjd_to_iso(page["cloud"]["dates_mjd"][ref]), km=sa_),
                                         note="LIVE: before = kete fit of today's MPC observations; after = the same plus our "
                                              "SPHEREx positions (sigma >= 2 arcsec). 60 clones, gravity only (MEASURED fits, "
                                              "COMPUTED propagation).")
                for k in ("first_known_obs_iso", "days_before_first_known_obs", "arc_days_before", "arc_days_after"):
                    page[k] = e[k] = imp[k]
                page["impact"] = {k: v for k, v in imp.items() if k not in ("slug", "name", "kind")}
                page["verdict_text"] = e["verdict_text"] = I.relabel(page["verdict_text"], imp)
                impacts.append(imp)
            except Exception as ex:  # noqa
                page["impact"] = dict(error=str(ex)[:200])
        page["live"] = e["live"] = True
        page["run_iso"] = e["run_iso"] = run_iso
        dump(page, pp)
        f0m = iso_to_mjd(o.disc_iso)
        for f in fl:
            d = f0m - f["mjd"]
            f["label"] = f"LIVE: SPHEREx photo, {int(d)} days before the first known observation" if d >= 1 else "LIVE: SPHEREx photo"
            f["live"] = True
        idx["objects"].append(e)
        idx["flash_events"] += fl
    idx["flash_events"].sort(key=lambda f: f.get("mjd") or 0)
    idx["live_stats"] = dict(stats, run_iso=run_iso, since_first_obs="2026-11-01",
                             note="objects first observed 2026-11-01 or later, searched with the same final rules")
    v = [e["verdict"] for e in idx["objects"]]
    idx["headline_stats"].update(objects_searched=len(idx["objects"]), found=v.count("FOUND"), hints=v.count("HINT"),
                                 too_faint=v.count("TOO_FAINT"))
    idx["final"] = True
    dump(idx, idx_p)
    json.dump(impacts, open(os.path.join(LIVE, "impact.json"), "w"), indent=1, default=str)
    return stats, impacts


def write_doc(stats, impacts, extra_lines=()):
    """docs/LIVE.md from the screen, the results and the live refits."""
    s = pd.read_csv(os.path.join(LIVE, "screen.csv"))
    sel = pd.read_csv(os.path.join(LIVE, "selected.csv"))
    res = {}
    for o in sel.slug:
        p = os.path.join(C.WORK, "objects", o, "result.json")
        if os.path.exists(p):
            res[o] = json.load(open(p))
    L = ["# Rewind LIVE run (2026-11-15)", "",
         f"Objects first observed on or after 2026-11-01 (JPL SBDB query, 2026-11-15): {len(pd.read_csv(os.path.join(LIVE, 'candidates.csv')))} "
         f"(0 new comets). Screened with IRSA MOST (catalog=spherex, 120 days before the first observation): {len(s)} NEOs and "
         f"main-belt objects with H <= 18.5. Newest public SPHEREx frame for any of them: {s.newest.dropna().max()} "
         f"(VERIFIED in MOST), so the public photos end at least {int(s.days_before.dropna().min())} days before these objects "
         f"were first seen. Brightest predicted V in those photos: {s.vmin.min():.2f} (MOST, reflected light only).", "",
         "Engine run on the 12 most promising (8 NEOs, 4 bright non-NEOs), with exactly the same final rules (frame QA, nulls, "
         "time shift, days, injection, sign test, best-day test, orbit check). Nothing was loosened and nothing was submitted.", "",
         "| Object | NEO | H | Arc today (days, MPC obs) | SPHEREx frames read | Days before first obs | Verdict | Null-scaled S/N | Injection limit (AB) | Predicted (AB) |",
         "|-|-|-|-|-|-|-|-|-|-|"]
    for r in sel.itertuples():
        x = res.get(r.slug)
        m = (x or {}).get("main", {})
        L.append(f"| {r.desig} | {r.neo} | {r.H} | {r.arc:.0f} ({r.n_obs}) | {(x or {}).get('n_read', '-')} | {r.days_before:.0f} | "
                 f"{(x or {}).get('verdict', 'not run')} | {m.get('snr_scaled', float('nan')):.1f} | {m.get('limit_mag', float('nan')):.1f} | "
                 f"{m.get('pred_ab', float('nan')):.1f} |")
    L += ["", f"Live stats: {stats}", ""]
    if impacts:
        L += ["## Real orbit improvement (MEASURED fits on today's MPC arc, COMPUTED propagation)", "",
              "| Object | First obs | Days earlier | Arc before -> after | 3-sigma 1 yr after last obs (km) before -> after | Factor |", "|-|-|-|-|-|-|"]
        for i in impacts:
            o = i.get("one_year_after_last_obs", {})
            L.append(f"| {i['name']} | {i['first_known_obs_iso']} | {i['days_before_first_known_obs']} | {i['arc_days_before']} -> "
                     f"{i['arc_days_after']} | {o.get('sigma3_km_before')} -> {o.get('sigma3_km_after')} | {o.get('factor')} |")
    L += [""] + list(extra_lines)
    open(os.path.join(C.WORKTREE, "docs", "LIVE.md"), "w").write("\n".join(L) + "\n")
    return "\n".join(L)
