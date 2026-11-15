"""Strict review of a candidate (used for every FOUND): checks, frame QA, crowding, per-day, orbit refit with
leave-one-day-out, independent aperture cross-check, and a known-asteroid check with JPL sb_ident (geocentric,
+-0.05 deg box, V < 21) on the frames of each positive day."""
from __future__ import annotations

import json
import os
import time

import numpy as np
import pandas as pd
import requests

from . import config as C
from .pilot import R


def _sexa(ra, dec):
    h = ra / 15.0
    hh, mm = int(h), int((h - int(h)) * 60)
    ss = (h * 3600) % 60
    s = "M" if dec < 0 else ""
    d = abs(dec)
    dd, dm = int(d), int((d - int(d)) * 60)
    ds = (d * 3600) % 60
    return f"{hh:02d}-{mm:02d}-{ss:04.1f}", f"{s}{dd:02d}-{dm:02d}-{ds:04.1f}"


def known_nearby(iso, ra, dec, half_deg=0.05, vmax=21.0):
    """Known asteroids/comets within the box at the frame time (JPL sb_ident, geocentric). Returns list of dicts."""
    a, d = _sexa(ra, dec)
    p = {"sb-kind": "a", "mpc-code": "500", "obs-time": iso[:19], "fov-ra-center": a, "fov-dec-center": d,
         "fov-ra-hwidth": str(half_deg), "fov-dec-hwidth": str(half_deg), "vmag-lim": str(vmax)}
    out = []
    for kind in ("a", "c"):
        p["sb-kind"] = kind
        for k in range(3):
            try:
                r = requests.get("https://ssd-api.jpl.nasa.gov/sb_ident.api", params=p, timeout=120)
                if r.status_code == 200:
                    j = r.json()
                    f = j.get("fields_first") or []
                    for row in j.get("data_first_pass", []) + j.get("data_second_pass", []):  # filtered to <= 60" below
                        rec = dict(zip(f, row))
                        out.append(dict(name=rec.get("Object name"), sep_arcsec=rec.get('Dist. from center Norm (")'),
                                        V=rec.get("Visual magnitude (V)")))
                    break
            except Exception:  # noqa
                pass
            time.sleep(2 * (k + 1))
        time.sleep(1)
    return out


def review(slug, kind):
    from . import crosscheck as X
    from .pipeline import qa_drop
    d = os.path.join(C.WORK, "objects", slug)
    r = json.load(open(os.path.join(d, "result.json")))
    m = r["main"]
    fr = pd.read_csv(os.path.join(d, "frames.csv"))
    ph = pd.read_csv(os.path.join(d, "paths_phot.csv"), keep_default_na=False, na_values=[""])
    for c in ("flux", "err", "ref_flux", "chi2", "flag_or"):
        ph[c] = pd.to_numeric(ph[c], errors="coerce")
    t = ph[(ph.path == "target") & (ph.status == "ok")].merge(fr[["file", "mjd_avg", "iso", "pred_ra", "pred_dec"]], on="file")
    drop = qa_drop(ph)
    t["qa_ok"] = ~t.file.isin(drop)
    pos_days = [x for x in m["days"] if x.get("snr") is not None and x["snr"] >= 2]
    known = []
    if kind != "comet" or True:
        for x in pos_days:
            g = t[(t.mjd_avg.astype(int) == x["day"]) & t.qa_ok]
            if len(g):
                q = g.iloc[len(g) // 2]
                for k in known_nearby(q.iso, q.pred_ra, q.pred_dec):
                    try:
                        if float(k["sep_arcsec"]) <= 60:
                            known.append(dict(day=x["iso"], **k))
                    except (TypeError, ValueError):
                        pass
    cc = X.run(slug, kind=kind)
    orb = (r.get("extra") or {}).get("orbit_fit") or {}
    out = dict(slug=slug, verdict=r["verdict"], passed=r["passed"], snr_scaled=m.get("snr_scaled"), n=m.get("n"),
               snr_without_best_day=m.get("snr_without_best_day"), frac_positive=m.get("frac_positive"),
               qa_fraction=r.get("qa_fraction"), galactic_b=r.get("galactic_b"), crowded=r.get("crowded"),
               days=[(x["iso"], x["n_frames"], round(x["snr"], 2)) for x in m["days"] if x.get("snr") is not None],
               orbit={k: orb.get(k) for k in ("ok", "rms_arcsec_before", "rms_arcsec_after", "new_points",
                                              "new_point_resid_sigma", "leave_one_out", "combined_all_days")},
               known_objects_near_path=known, crosscheck=cc)
    json.dump(out, open(os.path.join(d, "review.json"), "w"), indent=1, default=str)
    return out
