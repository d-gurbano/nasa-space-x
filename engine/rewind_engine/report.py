"""Per-object driver: measure -> controls -> extras (clones, orbit, cloud, composition, score) ->
verdict -> website page. Saves WORK/objects/<slug>/result.json and entry.json."""
from __future__ import annotations

import json
import os
import traceback

import numpy as np
import pandas as pd

from . import brightness as B
from . import config as C
from . import pipeline as PL
from . import site as S
from . import verdict as V


def _odir(slug):
    return os.path.join(C.WORK, "objects", slug)


def _try(label, fn, *a, **k):
    try:
        return fn(*a, **k)
    except Exception as e:  # noqa
        print(f"  {label} failed: {e}", flush=True)
        traceback.print_exc(limit=2)
        return None


def run_object(obj):
    d = _odir(obj.slug)
    fr_path = os.path.join(d, "frames.csv")
    fr = pd.read_csv(fr_path) if os.path.exists(fr_path) and os.path.getsize(fr_path) > 2 else pd.DataFrame()
    out = PL.measure_object(obj)
    res, extra = None, {}
    if "rows" in out and (out["ph"].get("path") == "target").any():
        res = PL.summarize(out["ph"], out["rows"], obj)
        m = res["main"]
        pred_ab = float(B.ujy_to_ab(np.nanmedian(out["rows"].s_exp_ujy)))
        m["pred_ab"] = pred_ab
        from astropy.coordinates import SkyCoord
        import astropy.units as u
        b = SkyCoord(np.nanmedian(fr.pred_ra) * u.deg, np.nanmedian(fr.pred_dec) * u.deg).galactic.b.deg
        res["galactic_b"] = float(b)
        res["crowded"] = bool(abs(b) < 10)
        m["limit_mag"] = pred_ab + m["limit_dmag"] if np.isfinite(m["limit_dmag"]) else np.nan
        from . import extras as X
        extra["clone_search"] = _try("clone search", X.clone_search, obj, fr, out, res)
        extra["composition"] = _try("composition", X.composition, obj, out, res)
        extra["real_or_fake_score"] = _try("real/fake", X.real_or_fake, obj, out, res)
        # orbit check only when the photometric checks already pass
        c0 = V.checks_passed(m, {"ok": True}, res.get("cleaned"))
        if obj.role != "known" and all(c0[k] for k in ("snr", "nulls", "time_shift", "days")):
            extra["orbit_fit"] = _try("orbit check", X.orbit_check, obj, fr, out, res)
    elif out.get("verdict") == "PENDING":
        res = dict(pending=True)
    elif os.path.exists(os.path.join(d, "most_error.txt")):
        res = dict(most_error=True)
    verdict, sentence, passed = V.decide(obj, res if res and "main" in res else res, extra.get("orbit_fit"), extra.get("clone_search"))
    extra["passed"] = passed
    from . import crosscheck as CC
    kind = "comet" if obj.kind == "comet" else "asteroid"
    if verdict == "FOUND" and res.get("cleaned"):
        extra["crosscheck"] = _try("crosscheck", CC.run, obj.slug, kind)
    elif verdict == "HINT" and res.get("cleaned"):
        pos = {d["day"] for d in res["main"].get("days", []) if d.get("snr") is not None and d["snr"] >= 2}
        cc = _try("crosscheck", CC.run, obj.slug, kind, qa=False, days=pos) if pos else None
        if cc:
            cc["note"] = "positive days only and no frame QA: chosen after looking, so not an independent test"
            extra["crosscheck"] = cc
            if cc.get("snr") is not None and cc["snr"] >= 5:
                sentence += (f" A simpler second method (median of the sky-cleaned photos from its best days) shows a clear "
                             f"source at the predicted spot (S/N {cc['snr']:.0f}): the signal is strong, but not every check passed.")
    from . import extras as X
    extra["cloud"] = _try("cloud", X.cloud, obj, extra.get("orbit_fit"))
    entry, flashes = S.object_page(obj, fr, out if res and "main" in res else None, res, verdict, sentence, extra)
    n_read = int(len(out["rows"])) if "rows" in out else 0
    summ = dict(slug=obj.slug, verdict=verdict, sentence=sentence, passed=passed, n_read=n_read)
    if res and "main" in res:
        summ["main"] = {k: v for k, v in res["main"].items() if k != "tab"}
        summ["cleaned"] = res.get("cleaned")
        for k in ("n_qa_dropped", "qa_fraction", "snr_before_qa", "galactic_b", "crowded"):
            summ[k] = res.get(k)
        for t in ("raw", "diff"):
            if t in res:
                summ[t] = {k: v for k, v in res[t].items() if k != "tab"}
    summ["extra"] = {k: v for k, v in extra.items() if k != "cloud"}
    S.dump(summ, os.path.join(_odir(obj.slug), "result.json"))
    S.dump(dict(entry=entry, flashes=flashes, n_read=n_read), os.path.join(_odir(obj.slug), "entry.json"))
    print(f"{obj.slug}: {verdict} - {sentence}", flush=True)
    return entry, flashes, n_read


def page_for(obj):
    p = os.path.join(_odir(obj.slug), "entry.json")
    if not os.path.exists(p):
        return run_object(obj)
    j = json.load(open(p))
    return j["entry"], j["flashes"], j["n_read"]
