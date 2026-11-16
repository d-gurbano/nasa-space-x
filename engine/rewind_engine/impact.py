"""Impact of the precovery FOUNDs: how much earlier than the first known observation, how much longer the arc,
and how much smaller the future position uncertainty becomes when our SPHEREx positions are added.

For each object: JPL SBDB first/last observation (fresh query), our earliest positive day, the SPHEREx positions
measured by the orbit check, then two kete least-squares fits (orbitfit.py) on the real MPC observations: without
and with our positions. Per-position uncertainty is max(2.0", the engine's estimate) (sigma_floor): positions
come from stacks searched within +-1.25 px of the prediction, so we do not trust them better than a third of a
SPHEREx pixel. Future uncertainty = 3-sigma of the largest axis of the clone position cloud (km), from 300 samples of
each fit's covariance, at (a) 1 year after the last observation and (b) the next Earth close approach (NEOs).
The website cloud (before/after) is replaced by clones of these two fits so the animation compares like with like.
Labels: dates VERIFIED (SBDB), arcs COMPUTED, uncertainties COMPUTED (model: linear covariance, gravity only)."""
from __future__ import annotations

import datetime as dt
import glob
import json
import os
import re

import numpy as np
import requests

from . import config as C
from .frames import iso_to_mjd, mjd_to_iso

AU_KM = 149597870.7
SIGMA_FLOOR = 2.0
TODAY = "2026-11-15"
KAGGLE = os.path.join(C.DATA, "kaggle")


def result_path(slug):
    p = os.path.join(C.WORK, "objects", slug, "result.json")
    if os.path.exists(p):
        return p
    ps = sorted(glob.glob(os.path.join(KAGGLE, "rewind-c2-engine-all-*", "work", "objects", slug, "result.json")),
                key=os.path.getmtime)
    return ps[-1] if ps else None


def sbdb_fresh(desig):
    """Current SBDB record (first/last obs, close approaches); cached for this run in WORK/sbdb_fresh."""
    d = os.path.join(C.WORK, "sbdb_fresh")
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, re.sub(r"[^a-z0-9]+", "", desig.lower()) + ".json")
    if os.path.exists(p):
        return json.load(open(p))
    r = requests.get("https://ssd-api.jpl.nasa.gov/sbdb.api", params={"sstr": desig, "ca-data": "1", "ca-body": "Earth",
                                                                      "full-prec": "1"}, timeout=60)
    j = r.json()
    json.dump(j, open(p, "w"))
    return j


def next_close_approach(sb, after=TODAY):
    for c in sb.get("ca_data") or []:
        try:
            iso = dt.datetime.strptime(c["cd"][:11], "%Y-%b-%d").date().isoformat()
        except (KeyError, ValueError):
            continue
        if iso > after:
            return dict(iso=iso, dist_au=float(c["dist"]), dist_ld=round(float(c["dist"]) * 389.17, 1))
    return None


def _clones(fit, n=300, seed=7):
    import kete
    ss, _ = fit.uncertain_state.sample(n, seed=seed)
    return [fit.state] + list(ss)


def sigma_km_at(states, mjd):
    """3-sigma of the largest axis of the position cloud (km) at mjd, plus the propagated states."""
    import kete
    st = kete.propagate_n_body(states, float(mjd) + 2400000.5)
    st = list(st)
    p = np.array([list(s.pos) for s in st[1:]])
    w = np.linalg.eigvalsh(np.cov(p.T))
    return 3 * float(np.sqrt(max(w[-1], 0))) * AU_KM


def impact_one(obj, sigma_floor=SIGMA_FLOOR):
    from .pilot import orbitfit, positions
    OF, P = orbitfit(), positions()
    r = json.load(open(result_path(obj.slug)))
    sb = sbdb_fresh(obj.desig)
    orb = sb.get("orbit", {})
    first, last = orb.get("first_obs"), orb.get("last_obs")
    pos_days = [d for d in r["main"].get("days", []) if d.get("snr") is not None and d["snr"] >= 2]
    earliest = min(d["day"] for d in pos_days) if pos_days else None
    fmjd, lmjd = iso_to_mjd(first), iso_to_mjd(last)
    before = (fmjd - earliest) if earliest is not None and earliest < fmjd else None
    pre = [d["day"] for d in pos_days if d["day"] < fmjd]
    pts = (r.get("extra", {}).get("orbit_fit") or {}).get("positions") or []
    out = dict(slug=obj.slug, name=obj.name, kind=obj.kind, first_known_obs_iso=first, last_known_obs_iso=last,
               earliest_spherex_day_iso=mjd_to_iso(earliest) if earliest else None,
               days_before_first_known_obs=int(before) if before is not None else None,
               latest_positive_before_iso=mjd_to_iso(max(pre)) if pre else None,
               spherex_positions=len(pts), sigma_floor_arcsec=sigma_floor,
               arc_days_before=round(lmjd - fmjd, 1))
    first_pos = min([p["mjd"] for p in pts], default=None)
    out["arc_days_after"] = round(lmjd - min(fmjd, first_pos), 1) if first_pos is not None else out["arc_days_before"]
    out["positions_earlier_than_first_obs"] = int(sum(p["mjd"] < fmjd for p in pts))
    if not pts:
        out["note"] = "no SPHEREx position measured (no day bright enough), so the orbit cannot change"
        return out, None, None
    obs = OF.fetch_obs(obj.desig)
    f0 = OF.fit(obs)
    rows = [(float(P.utc_mjd_to_tdb_jd([p["mjd"]])[0]), p["ra"], p["dec"], max(sigma_floor, p["sigma_arcsec"]), "spherex")
            for p in pts]
    f1 = OF.fit(OF.add_precovery(obs, rows), initial_state=f0.state)
    out.update(n_mpc_obs=len(obs), rms_arcsec_before=round(float(f0.rms), 3), rms_arcsec_after=round(float(f1.rms), 3),
               converged_after=bool(f1.converged))
    c0, c1 = _clones(f0), _clones(f1)
    t1 = lmjd + 365.25
    s0, s1 = sigma_km_at(c0, t1), sigma_km_at(c1, t1)
    out["one_year_after_last_obs"] = dict(iso=mjd_to_iso(t1), sigma3_km_before=round(s0), sigma3_km_after=round(s1),
                                          factor=round(s0 / s1, 2) if s1 > 0 else None)
    if obj.kind == "neo":
        ca = next_close_approach(sb)
        if ca:
            a0, a1 = sigma_km_at(c0, iso_to_mjd(ca["iso"])), sigma_km_at(c1, iso_to_mjd(ca["iso"]))
            out["next_close_approach"] = dict(ca, sigma3_km_before=round(a0), sigma3_km_after=round(a1),
                                              factor=round(a0 / a1, 2) if a1 > 0 else None)
    return out, f0, f1


def cloud_from_fits(f0, f1, dates_mjd, n=60):
    from .extras import _propagate_cloud, _sigma_km
    b = _propagate_cloud(_clones(f0, n), None, dates_mjd)
    a = _propagate_cloud(_clones(f1, n), None, dates_mjd)
    ref = int(np.argmin(np.abs(np.asarray(dates_mjd) - (iso_to_mjd(TODAY) + 365.25))))
    return b, a, ref, _sigma_km(b[ref]), _sigma_km(a[ref])


def relabel(text, imp):  # apply once, to the engine's original sentence
    """Verdict sentence: 'before its discovery' -> before the first known observation, or say plainly it is not.
    Accepts both the current wording ('detected ... in SPHEREx images') and the older one ('found ... in SPHEREx photos')."""
    d = imp["days_before_first_known_obs"]
    first = imp["first_known_obs_iso"]
    text = re.sub(r" taken \d+(-\d+)? days before its discovery", "", text)
    if d:
        lo = max(1, int(iso_to_mjd(first) - iso_to_mjd(imp["latest_positive_before_iso"]))) if imp.get("latest_positive_before_iso") else 1
        span = f"{lo}-{d}" if lo != d else f"{d}"
        return re.sub(r" in SPHEREx (photos|images)", f" in SPHEREx images taken {span} days before the first known observation "
                                                          f"({first})", text, count=1)
    text = re.sub(r"^Rewind (?:found|detected) (.+?) in SPHEREx (?:photos|images):", r"SPHEREx detected \1:", text)
    return (text.rstrip(".") +
            f". These images are not earlier than the first known observation ({first}): they add positions, not a precovery.")


ORDER = ["2025yh5", "c2026s1", "2025st20", "2025yj6", "p2025y2", "c2025l2", "p2026v1", "c2025w2"]


def run(slugs=ORDER):
    """Compute the impact table, update object.json / index.json (fields, sentences, flash labels, cloud) in the site."""
    from . import merge_kaggle as MK
    from .site import dump
    objs = {o.slug: o for o in MK.rewind_objects(slugs).itertuples()}
    rows = []
    idx_p = os.path.join(C.SITE, "index.json")
    idx = json.load(open(idx_p))
    ent = {e["slug"]: e for e in idx["objects"]}
    for s in slugs:
        o = objs[s]
        imp, f0, f1 = impact_one(o)
        rows.append(imp)
        print(json.dumps({k: v for k, v in imp.items()}, default=str)[:600], flush=True)
        pp = os.path.join(C.SITE, "objects", s, "object.json")
        page = json.load(open(pp))
        keys = ("first_known_obs_iso", "days_before_first_known_obs", "arc_days_before", "arc_days_after")
        for k in keys:
            page[k] = imp[k]
            ent[s][k] = imp[k]
        page["verdict_text"] = relabel(page["verdict_text"], imp)
        ent[s]["verdict_text"] = page["verdict_text"]
        if not imp["days_before_first_known_obs"]:
            page["claim"] = ent[s]["claim"] = "seen in SPHEREx (not earlier than known observations)"
        else:
            page["claim"] = ent[s]["claim"] = "precovery: seen before the first known observation"
        page["impact"] = {k: v for k, v in imp.items() if k not in ("slug", "name", "kind")}
        if f0 is not None and page.get("cloud"):
            dates = page["cloud"]["dates_mjd"]
            b, a, ref, sb_, sa_ = cloud_from_fits(f0, f1, dates)
            page["cloud"].update(before=b, after=a, before_sigma_km_at=dict(iso=mjd_to_iso(dates[ref]), km=sb_),
                                 after_sigma_km_at=dict(iso=mjd_to_iso(dates[ref]), km=sa_),
                                 note=("before = kete fit of the MPC observations only; after = the same plus our SPHEREx "
                                       f"positions (sigma >= {SIGMA_FLOOR} arcsec each). 60 covariance clones, gravity only "
                                       "(COMPUTED). First entry per date is the nominal orbit."))
        dump(page, pp)
    fk = {r["slug"]: r for r in rows}
    for f in idx["flash_events"]:
        r = fk.get(f["slug"])
        if not r:
            continue
        d = iso_to_mjd(r["first_known_obs_iso"]) - f["mjd"]
        f["label"] = (f"SPHEREx photo, {int(d)} days before the first known observation" if d >= 1
                      else "SPHEREx photo (after the first known observation: extra position, not a precovery)")
        f["before_first_known_obs"] = bool(d >= 1)
    idx["final"] = True
    dump(idx, idx_p)
    json.dump(rows, open(os.path.join(C.WORK, "impact.json"), "w"), indent=1, default=str)
    return rows


def discovery_scenario(obj, days=(7, 14), sigma_floor=SIGMA_FLOOR):
    """COMPUTED scenario: only the MPC observations of the first 7 (or 14) days after the first known observation,
    without and with our SPHEREx positions; 3-sigma (km) one year after the first observation."""
    import kete
    from .pilot import orbitfit, positions
    OF, P = orbitfit(), positions()
    r = json.load(open(result_path(obj.slug)))
    pts = (r.get("extra", {}).get("orbit_fit") or {}).get("positions") or []
    sb = sbdb_fresh(obj.desig)
    fmjd = iso_to_mjd(sb["orbit"]["first_obs"])
    obs_all = OF.fetch_obs(obj.desig)
    t0 = kete.Time.from_mjd(fmjd, scaling="utc").jd
    for n in days:
        obs = [o for o in obs_all if o.epoch.jd < t0 + n + 1]
        if len(obs) >= 6:
            break
    rows = [(float(P.utc_mjd_to_tdb_jd([p["mjd"]])[0]), p["ra"], p["dec"], max(sigma_floor, p["sigma_arcsec"]), "spherex")
            for p in pts if p["mjd"] < fmjd]
    if not rows:
        return None
    f0 = OF.fit(obs)
    f1 = OF.fit(OF.add_precovery(obs, rows), initial_state=f0.state)
    t = fmjd + 365.25
    s0, s1 = sigma_km_at(_clones(f0), t), sigma_km_at(_clones(f1), t)
    return dict(first_days_of_obs=n, n_mpc_obs=len(obs), spherex_positions_used=len(rows), at_iso=mjd_to_iso(t),
                sigma3_km_before=round(s0), sigma3_km_after=round(s1), factor=round(s0 / s1, 1) if s1 > 0 else None,
                converged=bool(f0.converged and f1.converged),
                label="COMPUTED scenario: as if Rewind had run right after discovery")
