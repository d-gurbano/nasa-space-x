"""Step 6: "pretend it is new" benchmark on known asteroids SPHEREx imaged.

For each case: hide everything before T_cut (= a SPHEREx frame time + 7 d). Fit an orbit only from
MPC observations in the first 20-45 days after T_cut (like a new discovery). Predict backwards to the
SPHEREx frames in the 20 days before T_cut with that short-arc orbit and its uncertainty, read the
pixels there and run the same engine blind. Truth: the same photometry at the TRUE positions (JPL
Horizons, full orbit) - "seen" if that oracle stack passes S/N >= 5. Score found / missed / false
alarms; write site/benchmark.json.
Caveat (stated in the output): frames are found with MOST, which uses the full orbit."""
from __future__ import annotations

import json
import os
import re
import traceback

import numpy as np
import pandas as pd

from . import config as C
from . import fetch as FE
from . import frames as F
from . import pipeline as PL
from . import verdict as V
from .pilot import R, orbitfit, positions

BENCH = os.path.join(C.WORK, "bench")
N_CASES = 20
V_BINS = [(15, 16.5), (16.5, 17.5), (17.5, 18.5), (18.5, 19.5), (19.5, 20.5), (20.5, 21.3)]


FINAL_10 = ["bench-2525", "bench-2699", "bench-1542", "bench-2037", "bench-7556", "bench-9450", "bench-22015",
            "bench-12141", "bench-49421", "bench-92085"]  # cut to 10 cases (time), V 16.2-20.0, all with frames


def select_cases(seed=4, final=True):
    p = os.path.join(BENCH, "cases.csv")
    if os.path.exists(p):
        cs = pd.read_csv(p)
        return cs[cs.slug.isin(FINAL_10)].reset_index(drop=True) if final else cs
    os.makedirs(BENCH, exist_ok=True)
    a = pd.read_parquet(os.path.join(C.DATA, "07-answer-keys", "answer_key", "known_objects_in_frames.parquet"),
                        columns=["packed", "name", "H", "U", "V_pred", "rate_arcsec_min", "MJD-AVG", "position_quality",
                                 "on_detector", "delta_au"])
    a = a[a.on_detector & (a.position_quality == "gold") & a.name.str.match(r"^\(\d+\)") & (a["MJD-AVG"] > 60850)
          & (a["MJD-AVG"] < 61280) & (a.rate_arcsec_min < 3)]
    a = a.sort_values("V_pred").drop_duplicates("packed")
    rng = np.random.default_rng(seed)
    pick = []
    per = int(np.ceil(N_CASES / len(V_BINS)))
    for lo, hi in V_BINS:
        b = a[(a.V_pred >= lo) & (a.V_pred < hi)]
        pick.append(b.iloc[rng.choice(len(b), min(per, len(b)), replace=False)])
    cs = pd.concat(pick).head(N_CASES).copy()
    cs["number"] = cs.name.str.extract(r"^\((\d+)\)")[0]
    cs["slug"] = "bench-" + cs.number
    cs["t_cut_mjd"] = np.floor(cs["MJD-AVG"]) + 7
    cs.to_csv(p, index=False)
    return cs


def short_arc_fit(num, t_cut_mjd):
    """kete least-squares fit from MPC observations in [T_cut, T_cut + 20..45 d]."""
    import kete
    OF = orbitfit()
    obs = OF.fetch_obs(num)
    t0 = kete.Time.from_mjd(float(t_cut_mjd), scaling="utc").jd
    for span in (20, 30, 45):
        sub = [o for o in obs if t0 <= o.epoch.jd < t0 + span]
        if len(sub) >= 6 and (max(o.epoch.jd for o in sub) - min(o.epoch.jd for o in sub)) >= 3:
            return OF.fit(sub), len(sub), span
    return None, 0, None


def prepare_case(c):
    """frames.csv for the blind run (short-arc positions) with the true positions alongside."""
    d = os.path.join(C.WORK, "objects", c.slug)
    os.makedirs(d, exist_ok=True)
    out = os.path.join(d, "frames.csv")
    if os.path.exists(out):
        return pd.read_csv(out)
    P = positions()
    OF = orbitfit()
    fit, n_obs, span = short_arc_fit(str(c.number), c.t_cut_mjd)
    if fit is None:
        pd.DataFrame().to_csv(out, index=False)
        return pd.DataFrame()
    b, e = F.mjd_to_iso(c.t_cut_mjd - 20), F.mjd_to_iso(c.t_cut_mjd)
    most = R.most_query(str(c.number), b, e, cache=os.path.join(d, "most.tbl"))
    most["mjd_avg"] = most.mjd_start.astype(float) + C.MJD_AVG_OFFSET_S / 86400.0
    # newest 60 frames, then back in time order: Horizons returns rows sorted by time, so the frame list must be too
    most = most[most.mjd_avg < c.t_cut_mjd].sort_values("mjd_avg", ascending=False).head(60).sort_values("mjd_avg")
    if not len(most):
        pd.DataFrame().to_csv(out, index=False)
        return pd.DataFrame()
    jd = P.utc_mjd_to_tdb_jd(most.mjd_avg.values)
    blind = OF.sky_uncertainty(fit, jd, observer="spherex", n=200)
    hz = F.horizons_at(type("O", (), dict(hz_cmd=f"{c.number};"))(), most.mjd_avg.values)
    fr = pd.DataFrame(dict(file=most.file.values, uri=most.uri.values, det=most.productid.astype(str).values,
                           mjd_avg=most.mjd_avg.values, pred_ra=blind.ra_deg.values, pred_dec=blind.dec_deg.values,
                           true_ra=hz.ra.values, true_dec=hz.dec.values, rate_ra=hz.rate_ra.values, rate_dec=hz.rate_dec.values,
                           mag=hz["mag"].values, r_au=hz.r_au.values, delta_au=hz.delta_au.values,
                           smaa3=blind.semimajor_3s_arcsec.values))
    fr["iso"] = [F.mjd_to_iso(m, True) for m in fr.mjd_avg]
    fr["rate_arcsec_hr"] = np.hypot(fr.rate_ra, fr.rate_dec)
    fr["trail_px"] = fr.rate_arcsec_hr * C.EXPTIME_S / 3600 / C.PIX_ARCSEC
    fr["sigma_px"] = fr.smaa3 / 3 / C.PIX_ARCSEC
    sep = np.hypot((fr.pred_ra - fr.true_ra) * np.cos(np.radians(fr.true_dec)), fr.pred_dec - fr.true_dec) * 3600
    fr["blind_minus_true_arcsec"] = sep
    fr["half"] = [F.stamp_half(3 * s, t) for s, t in zip(fr.sigma_px, fr.trail_px)]
    fr["score"] = c.t_cut_mjd - fr.mjd_avg
    fr["n_arc_obs"], fr["arc_span_days"] = n_obs, span
    fr.to_csv(out, index=False)
    return fr


def fix_truth(c):
    """Recompute the Horizons truth columns of an existing frames.csv in time order (bug fix: earlier rows were
    paired newest-first against Horizons' oldest-first output)."""
    p = os.path.join(C.WORK, "objects", c.slug, "frames.csv")
    if not os.path.exists(p) or os.path.getsize(p) < 5:
        return
    fr = pd.read_csv(p).sort_values("mjd_avg").reset_index(drop=True)
    hz = F.horizons_at(type("O", (), dict(hz_cmd=f"{c.number};"))(), fr.mjd_avg.values)
    assert np.allclose(hz.mjd_utc.values, fr.mjd_avg.values)
    for a, b in (("true_ra", "ra"), ("true_dec", "dec"), ("rate_ra", "rate_ra"), ("rate_dec", "rate_dec"), ("mag", "mag"),
                 ("r_au", "r_au"), ("delta_au", "delta_au")):
        fr[a] = hz[b].values
    fr["rate_arcsec_hr"] = np.hypot(fr.rate_ra, fr.rate_dec)
    fr["trail_px"] = fr.rate_arcsec_hr * C.EXPTIME_S / 3600 / C.PIX_ARCSEC
    fr["blind_minus_true_arcsec"] = np.hypot((fr.pred_ra - fr.true_ra) * np.cos(np.radians(fr.true_dec)),
                                             fr.pred_dec - fr.true_dec) * 3600
    fr.to_csv(p, index=False)


def _obj(c):
    return type("O", (), dict(slug=c.slug, name=c["name"], desig=str(c.number), kind="mba", role="precovery",
                              disc_iso=F.mjd_to_iso(c.t_cut_mjd), hz_cmd=f"{c.number};"))()


def measure_case(c):
    fr = prepare_case(c)
    if not len(fr):
        return dict(name=c["name"], hidden_until_iso=F.mjd_to_iso(c.t_cut_mjd), truth="not seen", rewind_verdict="NO_PHOTOS",
                    snr=None, pos_err_arcsec=None, note="no short-arc fit or no SPHEREx frames")
    obj = _obj(c)
    # blind run (short-arc predicted positions)
    out = PL.measure_object(obj, verbose=False)
    if "rows" not in out:
        return dict(name=c["name"], hidden_until_iso=F.mjd_to_iso(c.t_cut_mjd), truth="not seen", rewind_verdict=out.get("verdict"),
                    snr=None, pos_err_arcsec=None)
    res = PL.summarize(out["ph"], out["rows"], obj)
    m = res["main"]
    blind_ok = V.checks_passed(m, {"ok": True}, True)
    verdict, _, _ = V.decide(obj, res, {"ok": True})  # orbit refit not run in the benchmark (stated in output)
    # oracle run at the true positions, same stamps
    fr_true = fr.assign(pred_ra=fr.true_ra, pred_dec=fr.true_dec)
    fr_true.to_csv(os.path.join(C.WORK, "objects", c.slug, "frames.csv"), index=False)
    try:
        out_t = PL.measure_object(obj, verbose=False)
        res_t = PL.summarize(out_t["ph"], out_t["rows"], obj)
        snr_t = res_t["main"]["snr_scaled"]
    finally:
        fr.to_csv(os.path.join(C.WORK, "objects", c.slug, "frames.csv"), index=False)
    truth = "seen" if np.isfinite(snr_t) and snr_t >= 5 else "not seen"
    pos_err = None
    if verdict in ("FOUND", "HINT"):
        from .extras import _day_offsets
        pts = _day_offsets(obj, fr, out, res)
        if pts:
            p = max(pts, key=lambda q: q["snr"])
            t = fr[fr.mjd_avg.astype(int) == p["day"]].iloc[len(fr[fr.mjd_avg.astype(int) == p["day"]]) // 2]
            pos_err = float(np.hypot((p["ra"] - t.true_ra) * np.cos(np.radians(t.true_dec)), p["dec"] - t.true_dec) * 3600)
    return dict(name=c["name"], hidden_until_iso=F.mjd_to_iso(c.t_cut_mjd), truth=truth, rewind_verdict=verdict,
                snr=round(float(m["snr_scaled"]), 2) if np.isfinite(m["snr_scaled"]) else None,
                oracle_snr=round(float(snr_t), 2) if np.isfinite(snr_t) else None,
                pos_err_arcsec=round(pos_err, 2) if pos_err is not None else None, V_pred=round(float(c.V_pred), 2),
                n_frames=int(m["n"]), arc_obs=int(fr.n_arc_obs.iloc[0]), arc_days=int(fr.arc_span_days.iloc[0]),
                median_blind_minus_true_arcsec=round(float(fr.blind_minus_true_arcsec.median()), 1),
                cleaned=bool(res.get("cleaned")), checks=blind_ok)


def fetch_cases(workers=6):
    cs = select_cases()
    jobs = []
    for _, c in cs.iterrows():
        try:
            fr = prepare_case(c)
        except Exception as e:  # noqa
            print("prepare failed", c.slug, e, flush=True)
            continue
        if len(fr):
            fr = fr.assign(mag=fr["mag"].fillna(20))
            jobs += FE.target_jobs(c.slug, fr, mag_cut=99)
    FE._run_jobs(jobs, workers, "benchmark target")
    for _, c in cs.iterrows():
        p = os.path.join(C.WORK, "objects", c.slug, "frames.csv")
        fr = pd.read_csv(p) if os.path.exists(p) and os.path.getsize(p) > 2 else pd.DataFrame()
        if len(fr):
            try:
                plan = FE.plan_refs(c.slug, fr, max_frames=60)
                FE._run_jobs(FE.ref_jobs(c.slug, plan), workers, f"{c.slug} refs")
            except Exception as e:  # noqa
                print("refs failed", c.slug, e, flush=True)


def run():
    cs = select_cases()
    cases = []
    for _, c in cs.iterrows():
        try:
            cases.append(measure_case(c))
        except Exception as e:  # noqa
            traceback.print_exc()
            cases.append(dict(name=c["name"], hidden_until_iso=F.mjd_to_iso(c.t_cut_mjd), truth="unknown", rewind_verdict="ERROR",
                              snr=None, pos_err_arcsec=None, note=str(e)[:200]))
        print(cases[-1], flush=True)
    seen = [x for x in cases if x["truth"] == "seen"]
    found = [x for x in seen if x["rewind_verdict"] == "FOUND"]
    hints = [x for x in seen if x["rewind_verdict"] == "HINT"]
    fa = [x for x in cases if x["truth"] == "not seen" and x["rewind_verdict"] == "FOUND"]
    n = len([x for x in cases if x["truth"] in ("seen", "not seen")])
    summ = dict(n=n, seen=len(seen), found=len(found), hints_on_seen=len(hints), missed=len(seen) - len(found),
                false_alarms=len(fa),
                plain=f"With the observed arc truncated, Rewind recovered {len(found)} of {len(seen)} known asteroids that were "
                      f"detectable in SPHEREx before the truncation date (plus {len(hints)} HINT), with {len(fa)} false FOUNDs in {n} cases.",
                method="short-arc orbit from MPC observations in the first 20-45 days after the hidden date; blind photometry at "
                       "the short-arc positions; truth = same photometry at the true JPL Horizons positions (S/N >= 5). "
                       "The blind verdict here skips the orbit-refit check. Frames were listed with MOST (full orbit).",
                label="MEASURED")
    from .site import dump
    dump(dict(schema="rewind-benchmark-v1", sample=False, cases=cases, summary=summ), os.path.join(C.SITE, "benchmark.json"))
    print(json.dumps(summ, indent=1))
    return summ
