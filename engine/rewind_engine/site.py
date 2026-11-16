"""Step 9: website files per docs/DATA-CONTRACT.md (index.json, objects/<slug>/...)."""
from __future__ import annotations

import datetime as dt
import json
import os

import numpy as np
import pandas as pd

from . import config as C
from . import fetch as FE
from . import images as IM
from .frames import iso_to_mjd, mjd_to_iso
from .pilot import R

CREDITS = ["NASA/IPAC IRSA SPHEREx QR3/DR1 (public L2 images, AWS open data)", "JPL Horizons and SBDB (orbits, positions)",
           "Minor Planet Center (observations, discovery data)", "kete (Caltech/IPAC) orbit tools"]
FRAME_PNG_MAX = 40


def _f(x, nd=3):
    try:
        x = float(x)
    except (TypeError, ValueError):
        return None
    return round(x, nd) if np.isfinite(x) else None


def clean(o):
    """JSON-safe: numpy -> python, NaN -> None."""
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items() if not str(k).startswith("_")}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating, float)):
        return None if not np.isfinite(o) else float(o)
    if isinstance(o, np.bool_):
        return bool(o)
    return o


def dump(obj, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(clean(obj), f, separators=(",", ":"))


# ------------------------------------------------------------------ facts / orbit / story
def sbdb_facts(sb: dict, obj) -> tuple[dict, dict]:
    el = {e["name"]: e.get("value") for e in sb.get("orbit", {}).get("elements", [])}
    pp = {p["name"]: p.get("value") for p in sb.get("phys_par", [])}
    o = sb.get("object", {})
    ca = sb.get("ca_data") or []
    nxt = None
    now = dt.date(2026, 11, 15).isoformat()
    for c in ca:
        d = c.get("cd", "")[:11]
        try:
            iso = dt.datetime.strptime(d.strip(), "%Y-%b-%d").date().isoformat()
        except ValueError:
            continue
        if iso >= now:
            nxt = dict(iso=iso, dist_ld=_f(float(c["dist"]) * 389.17, 1))
            break
    facts = dict(H=_f(pp.get("H"), 2), diameter_km=_f(pp.get("diameter"), 3), albedo=_f(pp.get("albedo"), 3),
                 **{"class": (o.get("orbit_class") or {}).get("name")}, neo=bool(o.get("neo")), pha=bool(o.get("pha")),
                 sentry=bool(sb.get("signature") and o.get("sentry", False)), moid_au=_f(sb.get("orbit", {}).get("moid"), 4),
                 next_close_approach=nxt)
    epoch_jd = _f(sb.get("orbit", {}).get("epoch"), 4)
    orbit = orbit_elements(el, epoch_jd)
    if facts["H"] is None and pp.get("M1") is not None:  # comets: total-magnitude parameters instead of H
        facts.update(M1=_f(pp.get("M1"), 2), K1=_f(pp.get("K1"), 2))
    return facts, orbit


def orbit_elements(el: dict, epoch_jd) -> dict:
    """Contract orbit block from SBDB elements. Comets and hyperbolic objects often lack a and M:
    a = q / (1 - e) (negative if e > 1), M = n (epoch - tp) with n = k / |a|^1.5 (COMPUTED)."""
    g = lambda k: _f(el.get(k), 8)  # noqa
    e, q, a, M = g("e"), g("q"), g("a"), g("ma")
    if a is None and e is not None and q is not None and abs(1 - e) > 1e-9:
        a = q / (1 - e)
    if M is None and a is not None and g("tp") is not None and epoch_jd:
        n = 0.9856076686 / abs(a) ** 1.5
        M = n * (epoch_jd - g("tp"))
        if e is not None and e < 1:
            M %= 360
    Q = g("ad") if g("ad") is not None else (a * (1 + e) if a is not None and e is not None and e < 1 else None)
    per = el.get("per")
    period = float(per) / 365.25 if per else (abs(a) ** 1.5 if a is not None and e is not None and e < 1 else None)
    return dict(epoch_mjd=_f(epoch_jd - 2400000.5, 4) if epoch_jd else None, a=_f(a, 6), e=_f(e, 6), i=_f(g("i"), 4),
                node=_f(g("om"), 4), peri=_f(g("w"), 4), M=_f(M, 4), q=_f(q, 6), Q=_f(Q, 6), period_yr=_f(period, 3),
                tp_jd=_f(g("tp"), 5), hyperbolic=bool(e is not None and e >= 1))


def story_for(obj) -> dict:
    p = os.path.join(C.DATA, "09-people", "stories", "featured_discovery_stories.json")
    if os.path.exists(p):
        for s in json.load(open(p)):
            key = s["object"].lower()
            if obj.name.lower() in key or obj.desig.lower() in key or obj.slug in key.replace(" ", ""):
                return dict(discovered_iso=s.get("discovery_date"), by=s.get("discoverer"), site=s.get("site"),
                            plain=s.get("story"), sources=s.get("sources", []))
    by = obj.by or "a sky survey"
    site = f" at {obj.site}" if obj.site else ""
    if obj.role == "precovery":
        txt = (f"{obj.name} was discovered on {obj.disc_iso} by {by}{site}. "
               f"Rewind searched SPHEREx images taken before that date for precovery detections.")
    elif obj.role == "lost":
        txt = (f"{obj.name} was seen only from {obj.earliest_obs_iso} to {obj.last_obs_iso} and then lost. "
               f"Rewind searched SPHEREx images outside that short arc.")
    else:
        txt = f"{obj.name} was discovered on {obj.disc_iso} by {by}{site}."
    return dict(discovered_iso=obj.disc_iso, by=obj.by or None, site=obj.site or None, plain=txt,
                sources=["https://ssd.jpl.nasa.gov/tools/sbdb_lookup.html#/?sstr=" + obj.desig.replace(" ", "%20")])


# ------------------------------------------------------------------ positions in 3D
def spherex_xyz(mjds):
    """Heliocentric ecliptic J2000 AU of SPHEREx (Horizons TLE vectors via positions.observer_state)."""
    from .pilot import positions
    P = positions()
    out = []
    for m in mjds:
        try:
            s = P.observer_state("spherex", float(P.utc_mjd_to_tdb_jd([m])[0]))
            out.append([round(float(v), 6) for v in s.pos])
        except Exception:  # noqa
            out.append(None)
    return out


def object_xyz(hz_cmd, mjds):
    """Heliocentric ecliptic J2000 AU from Horizons vectors (center 500@10)."""
    import requests
    if len(mjds) == 0:
        return []
    p = dict(format="json", COMMAND=f"'{hz_cmd}'", OBJ_DATA="NO", MAKE_EPHEM="YES", EPHEM_TYPE="VECTORS",
             CENTER="'500@10'", TLIST_TYPE="MJD", TIME_TYPE="UT", TLIST=" ".join(f"{x:.6f}" for x in mjds),
             OUT_UNITS="AU-D", REF_PLANE="ECLIPTIC", VEC_TABLE="1", CSV_FORMAT="YES")
    try:
        res = R._get("https://ssd.jpl.nasa.gov/api/horizons.api", p, timeout=120).json()["result"]
        body = res.split("$$SOE")[1].split("$$EOE")[0].strip().splitlines()
        return [[round(float(v), 6) for v in l.split(",")[2:5]] for l in body]
    except Exception:  # noqa
        return [None] * len(mjds)


# ------------------------------------------------------------------ images
def make_images(obj, fr, rows, ph, res, odir):
    """Frame, day and stack PNGs. Returns (frame_png map, day png map, stack dict)."""
    os.makedirs(os.path.join(odir, "frames"), exist_ok=True)
    os.makedirs(os.path.join(odir, "days"), exist_ok=True)
    tg = ph[(ph.path == "target") & (ph.status == "ok")].set_index("file")
    good = rows[rows.file.isin(tg.index)].copy()
    good["exp_snr"] = good.s_exp_ujy / good.file.map(tg.err)
    raw, dif, meta = {}, {}, {}
    from .pipeline import load_refs
    for r in good.itertuples():
        st = R.load_stamp_fits(FE.stamp_path(obj.slug, r.file))
        f = fr.set_index("file").loc[r.file]
        a = IM.north_up(st, f.pred_ra, f.pred_dec)
        raw[r.file] = a
        refs = load_refs(obj.slug, r.file, f.rate_arcsec_hr, obj.kind == "comet", r.trail_px)
        if refs:
            b = np.nanmedian([IM.north_up(s2, f.pred_ra, f.pred_dec) for s2 in refs], 0)
            dif[r.file] = a - b
        meta[r.file] = r
    clean_imgs = dif if len(dif) >= 10 else raw
    lo, hi = None, None
    stack_c = IM.clipped_mean([clean_imgs[k] for k in clean_imgs]) if clean_imgs else None
    stack_m = np.nanmedian([raw[k] for k in raw], 0) if raw else None
    if stack_c is not None:
        v = stack_c[np.isfinite(stack_c)]
        s = 1.4826 * np.median(np.abs(v - np.median(v))) if v.size else 1
        k = (stack_c.shape[0] - 1) // 2
        peak = np.nanmax(stack_c[k - 3:k + 4, k - 3:k + 4]) if np.isfinite(stack_c[k - 3:k + 4, k - 3:k + 4]).any() else 0
        lo_s, hi_s = -3 * s, max(10 * s, 0.9 * peak)  # bright objects: do not saturate the centre
        IM.save(stack_c, os.path.join(odir, "stack.png"), lo_s, hi_s)
        IM.save(stack_m, os.path.join(odir, "stack_median.png"), lo_s, hi_s)
    # shared stretch for single frames: robust spread over all frames
    lo, hi = IM.stretch_from([raw[k] for k in list(raw)[:80]], 5, 99.5)
    pick = good.sort_values("exp_snr", ascending=False).head(FRAME_PNG_MAX).sort_values("mjd")
    fpng = {}
    for k, r in enumerate(pick.itertuples()):
        name = f"frames/f{k:03d}.png"
        IM.save(raw[r.file], os.path.join(odir, name), lo, hi)
        fpng[r.file] = name
    dpng = {}
    days = res["main"]["days"] if res else []
    good["day"] = good.mjd.astype(int)
    for k, d in enumerate(days):
        ks = [f for f in good[good.day == d["day"]].file if f in clean_imgs]
        if len(ks) < 2:
            continue
        img = IM.clipped_mean([clean_imgs[f] for f in ks]) if len(ks) >= 3 else np.nanmean([clean_imgs[f] for f in ks], 0)
        name = f"days/d{k}.png"
        IM.save(img, os.path.join(odir, name), lo_s * 2.5, hi_s * 2.5)  # fewer frames -> noisier
        dpng[d["day"]] = name
    return fpng, dpng, (stack_c is not None)


# ------------------------------------------------------------------ per object
def object_page(obj, fr, out, res, verdict, sentence, extra):
    """Build object.json (+ PNGs) and the index entry and flash events for one object."""
    from . import objects as O
    odir = os.path.join(C.SITE, "objects", obj.slug)
    os.makedirs(odir, exist_ok=True)
    sb = O.sbdb_record(obj.desig)
    facts, orbit = sbdb_facts(sb, obj)
    page = dict(schema="rewind-object-v1", slug=obj.slug, name=obj.name, kind=obj.kind, verdict=verdict,
                verdict_text=sentence, sample=False, story=story_for(obj), facts=facts, orbit=orbit,
                cloud=extra.get("cloud"), shape_model=None, credits=CREDITS)
    flashes, first_hint, stack_ok = [], None, False
    if out is not None and "rows" in out:
        rows, ph = out["rows"], out["ph"]
        m = res["main"]
        fpng, dpng, stack_ok = make_images(obj, fr, rows, ph, res, odir)
        tg = ph[ph.path == "target"].set_index("file")
        frs = fr.set_index("file")
        frames = []
        for r in rows.sort_values("mjd").itertuples():
            t = tg.loc[r.file] if r.file in tg.index else None
            ok = t is not None and t.status == "ok"
            fl = (float(t.flux) - (float(t.ref_flux) if res.get("cleaned") and np.isfinite(t.get("ref_flux", np.nan)) else 0)) if ok else None
            frames.append(dict(key=frs.loc[r.file].uri.split("ibe/data/spherex/")[-1], mjd=_f(r.mjd, 6), iso=r.iso, detector=r.det,
                               wavelength_um=_f(r.wave_um, 4), pred_ra=_f(frs.loc[r.file].pred_ra, 6), pred_dec=_f(frs.loc[r.file].pred_dec, 6),
                               sigma_px=_f(r.sigma_px, 2), flux_ujy=_f(fl, 2), flux_err=_f(t.err, 2) if ok else None,
                               snr=_f(fl / t.err, 2) if ok and t.err else None,
                               flags=R.decode_flags(int(t.flag_or)) if ok and np.isfinite(t.flag_or) else None,
                               used=bool(ok), png=fpng.get(r.file), survey="SPHEREx"))
        days = [dict(iso=d["iso"], n_frames=d["n_frames"], snr=_f(d["snr"], 2), png=dpng.get(d["day"])) for d in m["days"]]
        ab = None
        if np.isfinite(m["amp"]) and m["amp"] > 0:
            ab = _f(-2.5 * np.log10(m["amp"] * np.nanmedian(rows.s_exp_ujy) / 3631e6), 2)
        sx = spherex_xyz(rows.sort_values("mjd").mjd.values)
        page["spherex"] = dict(frames=frames, days=days,
                               stack=dict(png="stack.png" if stack_ok else None, png_median="stack_median.png" if stack_ok else None,
                                          snr=_f(m["snr_scaled"], 2), snr_raw=_f(m["target_snr"], 2), ab_mag=ab, n_frames=m["n"],
                                          flux_fraction_of_predicted=_f(m["amp"], 3), cleaned=bool(res.get("cleaned"))),
                               spherex_xyz_au_at_frames=sx)
        page["checks"] = dict(
            null_paths=dict(n=m["null_n"], snr_mean=_f(m["null_mean"], 2), snr_std=_f(m["null_std"], 2), n_exceeding=m["null_exceed"]),
            time_shift=m["time_shift"], per_day_positive=f"{m['days_positive']} of {m['days_tested']}",
            static_sky_subtracted=dict(snr=_f(res["diff"]["target_snr"], 2) if "diff" in res else None,
                                       n_frames=res["diff"]["n"] if "diff" in res else 0),
            injection=dict(limit_ab_mag=_f(m.get("limit_mag"), 2), recovered_fraction_at_object_mag=_f(m["recovered_at_pred"], 2),
                           curve=m["injection_curve"]),
            frac_positive=m.get("frac_positive"), galactic_b=_f(res.get("galactic_b"), 1), crowded_field=res.get("crowded"), median_frame_snr=_f(m.get("median_frame_snr"), 2),
            orbit_fit=extra.get("orbit_fit"), trail_px=_f(np.nanmedian(rows.trail_px), 2), clone_search=extra.get("clone_search"),
            real_or_fake_score=extra.get("real_or_fake_score"), second_method=extra.get("crosscheck"), passed=extra.get("passed"), labels="MEASURED")
        page["composition"] = extra.get("composition")
        # quiz: best day image (or stack); answer at the centre
        qsrc = next((os.path.join(odir, p) for d, p in dpng.items()), os.path.join(odir, "stack.png") if stack_ok else None)
        if qsrc and os.path.exists(qsrc):
            import shutil
            shutil.copy(qsrc, os.path.join(odir, "quiz.png"))
            page["quiz"] = dict(image="quiz.png", answer_xy=IM.xy_in_png(0, 0), answer_text=f"{obj.name} is at the centre of the photo.")
        if stack_ok:
            import shutil
            shutil.copy(os.path.join(odir, "stack.png"), os.path.join(odir, "thumb.png"))
        if verdict in ("FOUND", "HINT"):
            pos = [d for d in m["days"] if d["snr"] >= 2 and d["day"] in dpng]
            if pos:
                first_hint = pos[0]
            mj = [float(rows[rows.mjd.astype(int) == d["day"]].mjd.mean()) for d in pos]
            sxyz = spherex_xyz(mj)
            oxyz = object_xyz(obj.hz_cmd, mj)
            for d, mm, a, b in zip(pos, mj, sxyz, oxyz):
                if obj.role == "precovery" and isinstance(obj.disc_iso, str):
                    lab = f"SPHEREx photo, {int(iso_to_mjd(obj.disc_iso) - mm)} days before discovery"
                elif obj.role == "known":
                    lab = "SPHEREx photo of a known object"
                else:
                    lab = "SPHEREx photo"
                flashes.append(dict(slug=obj.slug, mjd=_f(mm, 4), iso=mjd_to_iso(mm), photo=f"objects/{obj.slug}/{dpng[d['day']]}",
                                    spherex_xyz_au=a, object_xyz_au=b, label=lab, snr=_f(d["snr"], 2)))
    else:
        page["spherex"] = dict(frames=[], days=[], stack=None, spherex_xyz_au_at_frames=[])
        page["checks"] = None
        page["composition"] = None
    page.setdefault("quiz", None)
    page["neowise"] = neowise_block(obj.slug, odir)
    dump(page, os.path.join(odir, "object.json"))
    disc = dict(mjd=_f(iso_to_mjd(obj.disc_iso), 1) if isinstance(obj.disc_iso, str) else None, iso=obj.disc_iso,
                by=page["story"].get("by"), site=page["story"].get("site"))
    fh = None
    if first_hint:
        fh = dict(mjd=float(first_hint["day"]), iso=first_hint["iso"],
                  days_before_discovery=int(disc["mjd"] - first_hint["day"]) if disc["mjd"] and obj.role == "precovery" else None)
    entry = dict(slug=obj.slug, name=obj.name, kind=obj.kind, verdict=verdict, verdict_text=sentence, discovered=disc,
                 first_spherex_hint=fh, best_snr=page["spherex"]["stack"]["snr"] if page["spherex"].get("stack") else None,
                 n_frames=len(page["spherex"]["frames"]), thumb=f"objects/{obj.slug}/thumb.png" if stack_ok else None,
                 page=f"objects/{obj.slug}/object.json")
    return entry, flashes


NEOWISE_TEXT = {"CONFIRMED-LIKELY": "Also detected in archival NEOWISE images, and the same checks agree.",
                "HINT": "A faint NEOWISE catalogue source lies on the predicted path, but the images cannot confirm it.",
                "NOT_SUPPORTED": "A faint NEOWISE catalogue source near the path is not this object: the "
                                 "NEOWISE images do not show it when checked."}


def neowise_block(slug, odir):
    """Older NEOWISE infrared photos checked by rewind_engine.neowise (same controls), or None."""
    import shutil
    from . import neowise as N
    try:
        r = N.neowise_frames_for_site(slug)
    except Exception:  # noqa
        return None
    if not r:
        return None
    nd = os.path.join(odir, "neowise")
    os.makedirs(os.path.join(nd, "frames"), exist_ok=True)
    for f in r["frames"]:
        if f.get("png") and os.path.exists(os.path.join(r["base_dir"], f["png"])):
            shutil.copy(os.path.join(r["base_dir"], f["png"]), os.path.join(nd, f["png"]))
            f["png"] = "neowise/" + f["png"]
        else:
            f["png"] = None
    stack = None
    if r.get("stack_png") and os.path.exists(os.path.join(r["base_dir"], r["stack_png"])):
        shutil.copy(os.path.join(r["base_dir"], r["stack_png"]), os.path.join(nd, r["stack_png"]))
        stack = "neowise/" + r["stack_png"]
    return dict(survey="NEOWISE", verdict=r["verdict"], verdict_text=NEOWISE_TEXT.get(r["verdict"], ""), frames=r["frames"],
                stack=dict(png=stack, band=r["stack_band"], snr=r.get("stack_snr")), checks=r.get("verdict_checks"),
                flux_unit=r.get("flux_unit"), label="MEASURED (NEOWISE L1b pixels, IRSA)")


def write_index(entries, flashes, frames_read, final=False):
    v = [e["verdict"] for e in entries]
    idx = dict(schema="rewind-site-v1", generated=dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), sample=False,
               final=bool(final),
               headline_stats=dict(objects_searched=len(entries), found=v.count("FOUND"), hints=v.count("HINT"),
                                   too_faint=v.count("TOO_FAINT"), frames_read=int(frames_read)),
               benchmark="benchmark.json", objects=entries, flash_events=sorted(flashes, key=lambda f: f["mjd"] or 0))
    dump(idx, os.path.join(C.SITE, "index.json"))
    return idx


def rebuild_index(final=False):
    """index.json from every first-run object that has a saved page (WORK/objects/<slug>/entry.json)."""
    from . import objects as O
    entries, flashes, nread = [], [], 0
    for o in O.load_objects("first").itertuples():
        p = os.path.join(C.WORK, "objects", o.slug, "entry.json")
        if os.path.exists(p):
            j = json.load(open(p))
            entries.append(j["entry"])
            flashes += j["flashes"]
            nread += j["n_read"]
    return write_index(entries, flashes, nread, final=final)


def write_all(objs, static=True):
    """Assemble pages from the saved results of `measure`, then the static files (orbits with the
    in_rewind flag, planets, challenge stars) and the detectives rounds."""
    from . import detectives, report, site_static
    entries, flashes, nread = [], [], 0
    for o in objs.itertuples():
        e, f, n = report.page_for(o)
        entries.append(e)
        flashes += f
        nread += n
    idx = write_index(entries, flashes, nread)
    if static:
        site_static.write_static(C.SITE, rewind_desigs=list(objs.desig), rewind=objs)
    from . import detectives2
    detectives2.write_rounds_v2()  # v2: moving-dot rounds on fixed sky patches (v1 fields kept)
    return idx
