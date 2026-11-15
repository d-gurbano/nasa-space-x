"""Final verdict table (docs/RESULTS.md + progress file) from the saved per-object results."""
from __future__ import annotations

import datetime as dt
import json
import os

import numpy as np

from . import config as C
from . import objects as O
from .frames import iso_to_mjd

CHECKS = ["snr", "cleaned", "nulls", "time_shift", "days", "detectable", "sign_test", "not_one_day", "orbit"]


def _f(x, nd=1):
    try:
        x = float(x)
        return f"{x:.{nd}f}" if np.isfinite(x) else "-"
    except (TypeError, ValueError):
        return "-"


def rows():
    out = []
    for o in O.load_objects("first").itertuples():
        p = os.path.join(C.WORK, "objects", o.slug, "result.json")
        if not os.path.exists(p):
            out.append(dict(o=o, r=None))
            continue
        out.append(dict(o=o, r=json.load(open(p))))
    return out


def days_before(o, r):
    if o.role != "precovery" or not isinstance(o.disc_iso, str) or not r or "main" not in r:
        return "-"
    pos = [d["day"] for d in r["main"].get("days", []) if d.get("snr") is not None and d["snr"] >= 2]
    if not pos:
        return "-"
    dd = sorted(int(iso_to_mjd(o.disc_iso) - d) for d in pos)
    return f"{dd[0]}-{dd[-1]}" if dd[0] != dd[-1] else str(dd[0])


def table_md(rs):
    order = {"FOUND": 0, "HINT": 1, "TOO_FAINT": 2, "NO_PHOTOS": 3, "PENDING": 4}
    rs = sorted(rs, key=lambda x: (order.get((x["r"] or {}).get("verdict", "PENDING"), 9), x["o"].slug))
    lines = ["| Object | Role | Verdict | Null-scaled S/N | Days before discovery | Frames (cleaned / read) | Checks passed | "
             "Second method (aperture on median) |", "|-|-|-|-|-|-|-|-|"]
    for x in rs:
        o, r = x["o"], x["r"] or {}
        m = r.get("main", {})
        p = r.get("passed") or {}
        ok = [k for k in CHECKS if p.get(k)]
        bad = [k for k in CHECKS if k in p and not p.get(k) and not (k == "orbit" and o.role == "known")]
        cc = (r.get("extra") or {}).get("crosscheck")
        ccs = "-"
        if cc and cc.get("snr") is not None:
            ccs = f"S/N {cc['snr']:.1f}, {cc.get('flux_ujy', 0):.0f} uJy, {cc.get('n_frames')} frames"
            if cc.get("days"):
                ccs += " (best days only, post hoc)"
        chk = (f"{len(ok)}/{len(ok) + len(bad)}" + (f"; failed: {', '.join(bad)}" if bad else "")) if p else "-"
        lines.append(f"| {o.name} | {o.role} | {r.get('verdict', 'PENDING')} | {_f(m.get('snr_scaled'))} | {days_before(o, r)} | "
                     f"{m.get('n', '-')} / {r.get('n_read', 0)} | {chk} | {ccs} |")
    return "\n".join(lines)


def write(extra_md=""):
    rs = rows()
    md = table_md(rs)
    v = [(x["r"] or {}).get("verdict", "PENDING") for x in rs]
    head = (f"# Rewind final results ({dt.datetime.now().strftime('%Y-%m-%d %H:%M')} Arizona)\n\n"
            f"Engine: rewind_engine (branch c2-engine). All numbers MEASURED from SPHEREx pixels unless marked; "
            f"verdict rules in rewind_engine/README.md. Nothing was submitted to the MPC or anywhere else.\n\n"
            f"Totals: {len(rs)} objects; FOUND {v.count('FOUND')}, HINT {v.count('HINT')}, TOO_FAINT {v.count('TOO_FAINT')}, "
            f"NO_PHOTOS {v.count('NO_PHOTOS')}.\n\n"
            f"Checks: snr = null-scaled S/N >= 5 in the sky-cleaned stack; cleaned = static-sky references for >= 10 frames; "
            f"nulls = no null path reaches it; time_shift = peak at shift 0; days = >= 2 days with S/N >= 2; detectable = "
            f"injection recovers >= 50% at the predicted brightness; sign_test = more frames positive than on every null "
            f"path (>= 3 sigma); not_one_day = S/N >= 3 without the best day; orbit = refit with the new positions stays "
            f"good (not required for known objects).\n\n")
    out = head + md + "\n" + extra_md
    os.makedirs(os.path.join(C.WORKTREE, "docs"), exist_ok=True)
    open(os.path.join(C.WORKTREE, "docs", "RESULTS.md"), "w").write(out)
    return out
