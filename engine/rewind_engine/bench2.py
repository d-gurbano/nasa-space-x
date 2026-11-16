"""Benchmark v2 ("pretend it is new", harder): 30 known objects - 10 NEOs, 8 comets, 12 main-belt asteroids - spanning
bright to near the limit, plus one empty-sky decoy per case (the same frames, the predicted path shifted 8 px sideways)
to count false alarms. Same method as benchmark.py: orbit only from the MPC observations in the first 20-45 days after
a hidden date, blind prediction backwards, the full engine with the final rules; truth = the same photometry at the
true JPL Horizons positions (S/N >= 5).

    python -c "from rewind_engine import bench2; bench2.prepare_all(); bench2.fetch_all(); bench2.run()"
"""
from __future__ import annotations

import json
import os
import re
import shutil

import numpy as np
import pandas as pd

from . import benchmark as B1
from . import config as C
from . import fetch as FE
from . import frames as F
from . import pipeline as PL
from . import verdict as V
from .pilot import R, orbitfit, positions

BENCH = os.path.join(C.WORK, "bench2")
NEOS = ["276033", "152679", "614313", "190161", "89959", "11500", "267136", "162998", "230599", "169352"]
COMETS = ["198P", "P/2016 G1", "244P", "217P", "P/2005 L1", "383P", "59P", "176P"]
MBA_EXTRA = ["bench-2847", "bench-15905"]
N_FRAMES = 40
DECOY_PX = 8.0


def _slug(desig):
    return "b2-" + re.sub(r"[^a-z0-9]+", "", desig.lower())


def cases():
    p = os.path.join(BENCH, "cases.csv")
    if os.path.exists(p):
        return pd.read_csv(p, dtype={"desig": str})
    os.makedirs(BENCH, exist_ok=True)
    a = pd.read_parquet(os.path.join(C.DATA, "07-answer-keys", "answer_key", "known_objects_in_frames.parquet"),
                        columns=["name", "kind", "V_pred", "MJD-AVG", "on_detector"])
    a = a[a.on_detector & (a["MJD-AVG"] > 60850) & (a["MJD-AVG"] < 61280)]
    rows = []
    for d in NEOS + COMETS:
        comet = d in COMETS
        if comet:
            key = d.split(" (")[0]
            g = a[a.name.str.startswith(key + "/") | a.name.str.startswith(key + " (") | (a.name == key)]
        else:
            g = a[a.name.str.startswith(f"({d})")]
        g = g.sort_values("V_pred").iloc[0]
        rows.append(dict(slug=_slug(d), desig=d, name=g["name"], kind="comet" if comet else "neo", V_pred=float(g.V_pred),
                         t_cut_mjd=float(np.floor(g["MJD-AVG"]) + 7),
                         hz_cmd=f"DES={d};CAP;NOFRAG" if comet else f"{d};"))
    old = pd.read_csv(os.path.join(C.WORK, "bench", "cases.csv"))
    for _, c in old[old.slug.isin(B1.FINAL_10 + MBA_EXTRA)].iterrows():
        rows.append(dict(slug=c.slug, desig=str(c.number), name=c["name"], kind="mba", V_pred=float(c.V_pred),
                         t_cut_mjd=float(c.t_cut_mjd), hz_cmd=f"{c.number};"))
    df = pd.DataFrame(rows)
    df.to_csv(p, index=False)
    return df


def prepare_case(c):
    """frames.csv (blind short-arc positions + true positions) for one case; MBAs from the v1 benchmark are reused."""
    d = os.path.join(C.WORK, "objects", c.slug)
    os.makedirs(d, exist_ok=True)
    out = os.path.join(d, "frames.csv")
    if os.path.exists(out):
        return pd.read_csv(out)
    OF, P = orbitfit(), positions()
    fit, n_obs, span = B1.short_arc_fit(c.desig, c.t_cut_mjd)
    if fit is None:
        pd.DataFrame().to_csv(out, index=False)
        return pd.DataFrame()
    most = R.most_query(c.desig, F.mjd_to_iso(c.t_cut_mjd - 20), F.mjd_to_iso(c.t_cut_mjd), cache=os.path.join(d, "most.tbl"))
    most["mjd_avg"] = most.mjd_start.astype(float) + C.MJD_AVG_OFFSET_S / 86400.0
    most = most[most.mjd_avg < c.t_cut_mjd].sort_values("mjd_avg", ascending=False).head(N_FRAMES).sort_values("mjd_avg")
    if not len(most):
        pd.DataFrame().to_csv(out, index=False)
        return pd.DataFrame()
    jd = P.utc_mjd_to_tdb_jd(most.mjd_avg.values)
    blind = OF.sky_uncertainty(fit, jd, observer="spherex", n=200)
    hz = F.horizons_at(type("O", (), dict(hz_cmd=c.hz_cmd))(), most.mjd_avg.values)
    assert np.allclose(hz.mjd_utc.values, most.mjd_avg.values)
    fr = pd.DataFrame(dict(file=most.file.values, uri=most.uri.values, det=most.productid.astype(str).values,
                           mjd_avg=most.mjd_avg.values, pred_ra=blind.ra_deg.values, pred_dec=blind.dec_deg.values,
                           true_ra=hz.ra.values, true_dec=hz.dec.values, rate_ra=hz.rate_ra.values, rate_dec=hz.rate_dec.values,
                           mag=hz["mag"].values, r_au=hz.r_au.values, delta_au=hz.delta_au.values,
                           smaa3=blind.semimajor_3s_arcsec.values))
    fr["iso"] = [F.mjd_to_iso(m, True) for m in fr.mjd_avg]
    fr["rate_arcsec_hr"] = np.hypot(fr.rate_ra, fr.rate_dec)
    fr["trail_px"] = fr.rate_arcsec_hr * C.EXPTIME_S / 3600 / C.PIX_ARCSEC
    fr["sigma_px"] = fr.smaa3 / 3 / C.PIX_ARCSEC
    fr["blind_minus_true_arcsec"] = np.hypot((fr.pred_ra - fr.true_ra) * np.cos(np.radians(fr.true_dec)),
                                             fr.pred_dec - fr.true_dec) * 3600
    fr["half"] = [max(F.stamp_half(3 * s, t), int(DECOY_PX) + 24) if 3 * s < 300 else 64 for s, t in zip(fr.sigma_px, fr.trail_px)]
    fr["score"] = c.t_cut_mjd - fr.mjd_avg
    fr["n_arc_obs"], fr["arc_span_days"] = n_obs, span
    fr.to_csv(out, index=False)
    return fr


def prepare_all():
    cs = cases()
    for _, c in cs.iterrows():
        try:
            fr = prepare_case(c)
            print(c.slug, len(fr), flush=True)
        except Exception as e:  # noqa
            print("prepare failed", c.slug, str(e)[:200], flush=True)


def fetch_case(c, workers=10):
    p = os.path.join(C.WORK, "objects", c.slug, "frames.csv")
    fr = pd.read_csv(p) if os.path.exists(p) and os.path.getsize(p) > 5 else pd.DataFrame()
    if not len(fr):
        return
    fr = fr.assign(mag=fr["mag"].fillna(20))
    FE._run_jobs(FE.target_jobs(c.slug, fr, mag_cut=99), workers, f"{c.slug} target")
    plan = FE.plan_refs(c.slug, fr, n_ref=1, max_frames=N_FRAMES + 20)
    FE._run_jobs(FE.ref_jobs(c.slug, plan), workers, f"{c.slug} refs")


def decoy(c):
    """Empty-sky control: same stamps and references, predicted path shifted DECOY_PX sideways (perpendicular to the motion)."""
    src = os.path.join(C.WORK, "objects", c.slug)
    fr = pd.read_csv(os.path.join(src, "frames.csv"))
    slug = c.slug + "-decoy"
    d = os.path.join(C.WORK, "objects", slug)
    os.makedirs(d, exist_ok=True)
    ang = np.arctan2(fr.rate_dec, fr.rate_ra) + np.pi / 2  # perpendicular, (east, north)
    sh = DECOY_PX * C.PIX_ARCSEC
    new = [R.offset_radec(ra, de, sh * np.cos(a), sh * np.sin(a)) for ra, de, a in zip(fr.pred_ra, fr.pred_dec, ang)]
    fr = fr.assign(pred_ra=[n[0] for n in new], pred_dec=[n[1] for n in new], true_ra=np.nan, true_dec=np.nan)
    fr.to_csv(os.path.join(d, "frames.csv"), index=False)
    for sub in ("stamps", "refs"):
        a, b = os.path.join(C.WORK, sub, c.slug), os.path.join(C.WORK, sub, slug)
        if os.path.isdir(a) and not os.path.exists(b):
            os.symlink(a, b)
    plan = os.path.join(src, "refs_plan.csv")
    if os.path.exists(plan):
        shutil.copy(plan, os.path.join(d, "refs_plan.csv"))
    pl = pd.read_csv(os.path.join(d, "refs_plan.csv")) if os.path.exists(os.path.join(d, "refs_plan.csv")) else None
    if pl is not None:  # reference stamps are named after the target slug: rename the keys to the decoy slug paths
        pl.to_csv(os.path.join(d, "refs_plan.csv"), index=False)
    return type("O", (), dict(slug=slug, name=c["name"] + " (empty-sky decoy)", desig=str(c.desig),
                              kind="comet" if c.kind == "comet" else "mba", role="precovery",
                              disc_iso=F.mjd_to_iso(c.t_cut_mjd), hz_cmd=c.hz_cmd))()


def _obj(c):
    return type("O", (), dict(slug=c.slug, name=c["name"], desig=str(c.desig), kind="comet" if c.kind == "comet" else c.kind,
                              role="precovery", disc_iso=F.mjd_to_iso(c.t_cut_mjd), hz_cmd=c.hz_cmd))()


def measure_case(c):
    """Blind run, oracle (true positions) and the decoy. Returns (case dict, decoy dict)."""
    p = os.path.join(C.WORK, "objects", c.slug, "frames.csv")
    fr = pd.read_csv(p) if os.path.exists(p) and os.path.getsize(p) > 5 else pd.DataFrame()
    base = dict(name=c["name"], type=c.kind, hidden_until_iso=F.mjd_to_iso(c.t_cut_mjd), V_pred=round(float(c.V_pred), 2))
    if not len(fr):
        return dict(base, truth="unknown", rewind_verdict="NO_PHOTOS", snr=None, pos_err_arcsec=None,
                    note="no short-arc fit (too few MPC observations) or no SPHEREx frames before the hidden date"), None
    obj = _obj(c)
    out = PL.measure_object(obj, verbose=False)
    if "rows" not in out or not (out["ph"].path == "target").any():
        return dict(base, truth="unknown", rewind_verdict=out.get("verdict", "NO_PHOTOS"), snr=None, pos_err_arcsec=None), None
    res = PL.summarize(out["ph"], out["rows"], obj)
    m = res["main"]
    verdict, _, checks = V.decide(obj, res, {"ok": True})
    fr_true = fr.assign(pred_ra=fr.true_ra, pred_dec=fr.true_dec)
    fr_true.to_csv(p, index=False)
    try:
        out_t = PL.measure_object(obj, verbose=False)
        snr_t = PL.summarize(out_t["ph"], out_t["rows"], obj)["main"]["snr_scaled"]
    except Exception:  # noqa
        snr_t = np.nan
    finally:
        fr.to_csv(p, index=False)
    truth = "seen" if np.isfinite(snr_t) and snr_t >= 5 else "not seen"
    pos_err = None
    if verdict in ("FOUND", "HINT"):
        from .extras import _day_offsets
        pts = _day_offsets(obj, fr, out, res) or _day_offsets(obj, fr, out, res, all_days=True)
        if pts:
            q = max(pts, key=lambda x: x["snr"])
            t = fr.iloc[(fr.mjd_avg - q["mjd"]).abs().argmin()]
            pos_err = float(np.hypot((q["ra"] - t.true_ra) * np.cos(np.radians(t.true_dec)), q["dec"] - t.true_dec) * 3600)
    case = dict(base, truth=truth, rewind_verdict=verdict, snr=round(float(m["snr_scaled"]), 2) if np.isfinite(m["snr_scaled"]) else None,
                oracle_snr=round(float(snr_t), 2) if np.isfinite(snr_t) else None,
                pos_err_arcsec=round(pos_err, 2) if pos_err is not None else None, n_frames=int(m.get("n") or 0),
                arc_obs=int(fr.n_arc_obs.iloc[0]), arc_days=int(fr.arc_span_days.iloc[0]),
                median_blind_minus_true_arcsec=round(float(fr.blind_minus_true_arcsec.median()), 1),
                V_true_median=round(float(np.nanmedian(fr["mag"])), 2), checks=checks)
    dec = None
    try:
        od = decoy(c)
        o2 = PL.measure_object(od, verbose=False)
        if "rows" in o2 and (o2["ph"].path == "target").any():
            r2 = PL.summarize(o2["ph"], o2["rows"], od)
            v2, _, _ = V.decide(od, r2, {"ok": True})
            dec = dict(name=od.name, type="empty", truth="empty", rewind_verdict=v2,
                       snr=round(float(r2["main"]["snr_scaled"]), 2) if np.isfinite(r2["main"]["snr_scaled"]) else None)
    except Exception as e:  # noqa
        dec = dict(name=c["name"] + " (empty-sky decoy)", type="empty", truth="empty", rewind_verdict="ERROR", note=str(e)[:120])
    return case, dec


BINS = [(0, 17), (17, 18), (18, 19), (19, 20), (20, 21), (21, 30)]


def run():
    cs = cases()
    out, decs = [], []
    for _, c in cs.iterrows():
        try:
            case, dec = measure_case(c)
        except Exception as e:  # noqa
            case, dec = dict(name=c["name"], type=c.kind, truth="unknown", rewind_verdict="ERROR", note=str(e)[:200]), None
        out.append(case)
        if dec:
            decs.append(dec)
        print(case, dec, flush=True)
        json.dump(dict(cases=out, decoys=decs), open(os.path.join(BENCH, "partial.json"), "w"), default=str)
    return write(out, decs)


def write(cases_, decoys):
    from .site import dump
    known = [x for x in cases_ if x["truth"] in ("seen", "not seen")]
    seen = [x for x in known if x["truth"] == "seen"]
    found = [x for x in seen if x["rewind_verdict"] == "FOUND"]
    hints = [x for x in seen if x["rewind_verdict"] == "HINT"]
    missed = [x for x in seen if x["rewind_verdict"] not in ("FOUND", "HINT")]
    fa_cases = [x for x in known if x["rewind_verdict"] == "FOUND" and (x["truth"] == "not seen" or (x.get("pos_err_arcsec") or 0) > 12)]
    fa_decoys = [x for x in decoys if x["rewind_verdict"] == "FOUND"]
    curve = []
    for lo, hi in BINS:
        g = [x for x in known if lo <= (x.get("V_true_median") or x["V_pred"]) < hi]
        if g:
            curve.append(dict(v_min=lo, v_max=hi, n=len(g), found=sum(x["rewind_verdict"] == "FOUND" for x in g),
                              found_or_hint=sum(x["rewind_verdict"] in ("FOUND", "HINT") for x in g),
                              seen_by_oracle=sum(x["truth"] == "seen" for x in g),
                              frac_found=round(sum(x["rewind_verdict"] == "FOUND" for x in g) / len(g), 2)))
    by_type = {}
    for t in ("neo", "comet", "mba"):
        g = [x for x in known if x["type"] == t]
        by_type[t] = dict(n=len(g), seen=sum(x["truth"] == "seen" for x in g), found=sum(x["rewind_verdict"] == "FOUND" for x in g),
                          hints=sum(x["rewind_verdict"] == "HINT" for x in g))
    errs = [x["pos_err_arcsec"] for x in cases_ if x.get("pos_err_arcsec") is not None]
    summ = dict(n=len(known), n_cases_total=len(cases_), seen=len(seen), found=len(found), hints=len(hints), missed=len(missed),
                false_alarms=len(fa_cases) + len(fa_decoys), false_alarms_on_cases=len(fa_cases), false_alarms_on_decoys=len(fa_decoys),
                n_decoys=len(decoys), by_type=by_type,
                pos_err_arcsec=dict(n=len(errs), median=round(float(np.median(errs)), 2) if errs else None,
                                    p90=round(float(np.percentile(errs, 90)), 2) if errs else None),
                plain=(f"With the observed arc truncated, Rewind recovered {len(found)} of {len(seen)} known objects that were detectable "
                       f"in SPHEREx before the truncation date ({len(hints)} more were HINT, {len(missed)} missed), with "
                       f"{len(fa_cases) + len(fa_decoys)} false FOUNDs in {len(known)} real cases and {len(decoys)} empty-sky decoys."),
                method=("v2: 10 NEOs, 8 comets, 12 main-belt; orbit from the MPC observations in the first 20-45 days after a "
                        "hidden date; up to 40 SPHEREx frames in the 20 days before it; blind engine with the final rules "
                        "(orbit-refit check skipped); truth = same photometry at the true JPL Horizons positions (S/N >= 5); "
                        "decoy = same frames, path shifted 8 px sideways. missed excludes hints. Frames listed with MOST "
                        "(full orbit)."), label="MEASURED")
    old = json.load(open(os.path.join(C.SITE, "benchmark.json")))
    doc = dict(schema="rewind-benchmark-v2", sample=False, cases=cases_, decoys=decoys, completeness_curve=curve, summary=summ,
               v1=dict(cases=old.get("cases"), summary=old.get("summary")))
    dump(doc, os.path.join(C.SITE, "benchmark.json"))
    print(json.dumps(summ, indent=1, default=str))
    return doc


def lane(k, n_lanes=3):
    """Prepare, fetch and measure every n_lanes-th case (lane k); writes BENCH/lane_<k>.json."""
    cs = cases()
    sub = cs.iloc[k::n_lanes]
    out, decs = [], []
    for _, c in sub.iterrows():
        try:
            prepare_case(c)
            fetch_case(c)
            case, dec = measure_case(c)
        except Exception as e:  # noqa
            import traceback
            traceback.print_exc()
            case, dec = dict(name=c["name"], type=c.kind, truth="unknown", rewind_verdict="ERROR", note=str(e)[:200]), None
        out.append(case)
        if dec:
            decs.append(dec)
        print(case, dec, flush=True)
        json.dump(dict(cases=out, decoys=decs), open(os.path.join(BENCH, f"lane_{k}.json"), "w"), default=str)


def merge_lanes(n_lanes=3):
    cases_, decs = [], []
    for k in range(n_lanes):
        p = os.path.join(BENCH, f"lane_{k}.json")
        if os.path.exists(p):
            j = json.load(open(p))
            cases_ += j["cases"]
            decs += j["decoys"]
    return write(cases_, decs)


def choose_tcut(c, min_obs=6, arc_d=30, before_d=20):
    """Adaptive hidden date: >= min_obs MPC observations in the arc_d days after it AND SPHEREx frames (MOST, full
    survey) in the before_d days before it; among those, the date with the most SPHEREx frames."""
    import kete
    OF = orbitfit()
    obs = OF.fetch_obs(c.desig)
    t_obs = np.sort([o.epoch.jd - 2400000.5 for o in obs])
    d = os.path.join(C.WORK, "objects", c.slug)
    os.makedirs(d, exist_ok=True)
    most = R.most_query(c.desig, "2025-04-01", "2026-11-14", cache=os.path.join(d, "most_full.tbl"))
    t_fr = np.sort(most.mjd_start.astype(float).values)
    best = None
    for t in np.unique(np.floor(t_obs[(t_obs > 60780) & (t_obs < 61350)])):
        n_after = int(((t_obs >= t) & (t_obs < t + arc_d)).sum())
        n_fr = int(((t_fr < t) & (t_fr >= t - before_d)).sum())
        if n_after >= min_obs and n_fr > 0 and (best is None or n_fr > best[1]):
            best = (float(t), n_fr, n_after)
    return best


FALLBACK = dict(comet=["C/2025 N1", "C/2025 L2", "P/2025 Y2", "C/2025 W2", "C/2026 S1", "P/2026 V1", "C/2025 Y1", "C/2026 H2",
                       "C/2026 J1", "C/2026 M3", "C/2025 W1", "P/2026 T1", "P/2026 U1", "C/2026 B2"],
                neo=["504711", "530938", "612012", "752296", "175706", "620084", "514652", "7977", "27346"])


def _claim(desig):
    """Atomic claim so parallel retry lanes never take the same fallback object."""
    d = os.path.join(BENCH, "claims")
    os.makedirs(d, exist_ok=True)
    try:
        os.close(os.open(os.path.join(d, re.sub(r"[^a-z0-9]+", "", desig.lower())), os.O_CREAT | os.O_EXCL))
        return True
    except FileExistsError:
        return False


def _case_row(desig, kind):
    comet = kind == "comet"
    return pd.Series(dict(slug=_slug(desig), desig=desig, name=desig, kind=kind, V_pred=np.nan, t_cut_mjd=np.nan,
                          hz_cmd=f"DES={desig};CAP;NOFRAG" if comet else f"{desig};"))


def retry_no_photos(k=0, n=1, tag="b"):
    """Lane 3: cases that ended NO_PHOTOS get an adaptive hidden date; if the object has no usable date at all (e.g. a
    periodic comet without 2025-2026 ground observations), it is replaced by a fallback object of the same type."""
    cs = cases()
    done = []
    for i in range(3):  # (not k: k is this lane's index)
        p = os.path.join(BENCH, f"lane_{i}.json")
        if os.path.exists(p):
            done += json.load(open(p))["cases"]
    import glob
    fixed = set()
    for p in glob.glob(os.path.join(BENCH, "lane_3_*.json")):
        fixed |= {x["retry_of"] for x in json.load(open(p))["cases"] if x["rewind_verdict"] not in ("NO_PHOTOS", "ERROR")}
    bad = [x["name"] for x in done if x["rewind_verdict"] in ("NO_PHOTOS", "ERROR") and x["name"] not in fixed][k::n]
    used = set(cs.desig)
    out, decs = [], []
    for name in bad:
        c0 = cs[cs.name == name].iloc[0]
        tries = [c0] + [_case_row(d, c0.kind) for d in FALLBACK.get(c0.kind, []) if d not in used]
        case, dec = None, None
        for c in tries:
            try:
                b = choose_tcut(c)
            except Exception as e:  # noqa
                print("choose_tcut failed", c.desig, str(e)[:120], flush=True)
                b = None
            if not b or (c.desig != c0.desig and not _claim(c.desig)):
                continue
            used.add(c.desig)
            c = pd.Series({k: v for k, v in c.items()}, dtype=object)
            c["t_cut_mjd"] = float(b[0])
            for f in ("frames.csv", "most.tbl"):
                fp = os.path.join(C.WORK, "objects", c.slug, f)
                if os.path.exists(fp):
                    os.remove(fp)
            try:
                prepare_case(c)
                fetch_case(c)
                case, dec = measure_case(c)
            except Exception as e:  # noqa
                case, dec = dict(name=c["name"], type=c.kind, truth="unknown", rewind_verdict="ERROR", note=str(e)[:200]), None
            if case.get("rewind_verdict") in ("NO_PHOTOS", "ERROR"):
                continue
            case.update(adaptive_hidden_date=True, replaces=name if c.desig != c0.desig else None)
            break
        if case is None:
            case = dict(name=name, type=c0.kind, truth="unknown", rewind_verdict="NO_PHOTOS", V_pred=float(c0.V_pred),
                        note="no usable hidden date (MPC observations after it and SPHEREx frames before it), no fallback left")
        out.append(dict(case, retry_of=name))
        if dec:
            decs.append(dec)
        print(case, dec, flush=True)
        json.dump(dict(cases=out, decoys=decs), open(os.path.join(BENCH, f"lane_3_{tag}{k}.json"), "w"), default=str)


def merge_all():
    """Lanes 0-2 plus the retry lane (its result replaces a NO_PHOTOS entry of the same object)."""
    cases_, decs = [], []
    for k in range(3):
        p = os.path.join(BENCH, f"lane_{k}.json")
        if os.path.exists(p):
            j = json.load(open(p))
            cases_ += j["cases"]
            decs += j["decoys"]
    import glob
    j = dict(cases=[], decoys=[])
    for p3 in sorted(glob.glob(os.path.join(BENCH, "lane_3_*.json"))):
        jj = json.load(open(p3))
        j["cases"] += jj["cases"]
        j["decoys"] += jj["decoys"]
    if j["cases"]:
        retry = {}
        for x in j["cases"]:  # a later successful retry wins over an earlier failed one
            if x["retry_of"] not in retry or retry[x["retry_of"]]["rewind_verdict"] in ("NO_PHOTOS", "ERROR"):
                retry[x["retry_of"]] = x
        cases_ = [retry.get(x["name"], x) if x["rewind_verdict"] in ("NO_PHOTOS", "ERROR") else x for x in cases_]
        decs += j["decoys"]
    p4 = os.path.join(BENCH, "lane_4.json")  # re-measured cases (truth-ordering fix): replace by name
    if os.path.exists(p4):
        j = json.load(open(p4))
        fix = {x["name"]: x for x in j["cases"]}
        cases_ = [fix.get(x["name"], x) for x in cases_]
        names = {x["name"] + " (empty-sky decoy)" for x in j["cases"]}
        decs = [d for d in decs if d["name"] not in names] + j["decoys"]
    return write(cases_, decs)


def remeasure(slugs=("bench-2847", "bench-15905")):
    """Cases reused from the v1 list whose truth columns still had the ordering bug: fix, then measure again (lane 4)."""
    cs = cases()
    out, decs = [], []
    for _, c in cs[cs.slug.isin(slugs)].iterrows():
        B1.fix_truth(pd.Series(dict(slug=c.slug, number=c.desig)))
        fetch_case(c)
        case, dec = measure_case(c)
        out.append(case)
        if dec:
            decs.append(dec)
        print(case, dec, flush=True)
        json.dump(dict(cases=out, decoys=decs), open(os.path.join(BENCH, "lane_4.json"), "w"), default=str)
