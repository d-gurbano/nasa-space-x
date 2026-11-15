"""Object list: who Rewind searches for, and the facts it needs about each one.

An object row has: name, slug, kind (comet|neo|mba|lost|famous), role (precovery|lost|known),
horizons command, MOST name, discovery date/station, earliest ground observation."""
from __future__ import annotations

import json
import os
import re
import time

import numpy as np
import pandas as pd
import requests

from . import config as C

Y1_FORCED = ["C/2026 S1", "C/2026 H2", "P/2026 V1", "C/2026 B2", "2026 KC3", "2026 PW6", "2026 JS1"]
# Famous objects: shown with their SPHEREx history, never as precovery claims.
# Discovery facts are VERIFIED from JPL SBDB / MPC (well known; re-read from SBDB when available).
FAMOUS = [
    dict(name="99942 Apophis", slug="apophis", desig="99942", disc_iso="2004-06-19", by="R. Tucker, D. Tholen, F. Bernardi",
         site="Kitt Peak (695)"),
    dict(name="101955 Bennu", slug="bennu", desig="101955", disc_iso="1999-09-11", by="LINEAR", site="Socorro (704)",
         most_name="1999 RQ36"),  # plain "101955" is ambiguous in MOST
    dict(name="433 Eros", slug="eros", desig="433", disc_iso="1898-08-13", by="G. Witt", site="Berlin (Urania)"),
    dict(name="2024 YR4", slug="2024yr4", desig="2024 YR4", disc_iso="2024-12-27", by="ATLAS", site="Rio Hurtado, Chile (W68)"),
    dict(name="3I/ATLAS", slug="3i-atlas", desig="C/2025 N1", disc_iso="2025-07-01", by="ATLAS", site="Rio Hurtado, Chile (W68)"),
]
LOST = ["2025 OZ"]


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", name.lower())


def is_comet(desig: str) -> bool:
    return bool(re.match(r"^[CPDXI]/|^\d+[PI]$|^\d+[PI]-", desig)) or desig.startswith("C/")


def horizons_command(desig: str) -> str:
    if is_comet(desig):
        return f"DES={desig};CAP;NOFRAG"
    if desig.isdigit():
        return f"{desig};"
    return f"DES={desig};"


_OBSCODES = None


def station_name(code) -> str:
    global _OBSCODES
    if code is None or (isinstance(code, float) and not np.isfinite(code)):
        return ""
    if _OBSCODES is None:
        p = os.path.join(C.ORBITS, "mpc", "obscodes_api.json")
        _OBSCODES = json.load(open(p)) if os.path.exists(p) else {}
    code = str(code).strip()
    rec = _OBSCODES.get(code)
    return f"{rec['name_utf8'].strip()} ({code})" if rec else code


SURVEY_BY_STATION = {"F51": "Pan-STARRS1", "F52": "Pan-STARRS2", "G96": "Mt. Lemmon Survey", "703": "Catalina Sky Survey",
                     "V00": "Bok NEO Survey", "W68": "ATLAS", "M22": "ATLAS", "T08": "ATLAS", "T05": "ATLAS",
                     "X05": "Rubin Observatory", "W94": "", "I41": "ZTF", "704": "LINEAR", "691": "Spacewatch",
                     "C51": "NEOWISE", "273": "Euclid"}


def sbdb_record(desig: str) -> dict:
    """JPL SBDB record (orbit + covariance + phys + discovery + close approaches), cached in WORK."""
    d = os.path.join(C.WORK, "sbdb")
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, slugify(desig) + ".json")
    if os.path.exists(p):
        return json.load(open(p))
    url = "https://ssd-api.jpl.nasa.gov/sbdb.api"
    prm = {"sstr": desig, "cov": "mat", "phys-par": "1", "discovery": "1", "ca-data": "1", "ca-body": "Earth", "full-prec": "1"}
    for k in range(4):
        try:
            r = requests.get(url, params=prm, timeout=60)
            if r.status_code == 200:
                j = r.json()
                if "orbit" in j:
                    json.dump(j, open(p, "w"))
                    time.sleep(1.0)
                    return j
                if "list" in j:  # ambiguous (comet fragments): take the first match
                    prm["sstr"] = j["list"][0]["pdes"]
                    continue
        except Exception:  # noqa
            pass
        time.sleep(3 * (k + 1))
    return {}


def _precovery_rows(sl: pd.DataFrame, pick, y1=()) -> list:
    rows = []
    for des in pick:
        r = sl[sl.designation == des]
        r = r.iloc[0] if len(r) else None
        comet = is_comet(des)
        st = None if r is None else r.disc_station
        rows.append(dict(name=des, slug=slugify(des), desig=des, kind="comet" if comet else ("neo" if r is not None and r.neo == "Y" else "mba"),
                         role="precovery", disc_iso=None if r is None else str(r.disc_date_best)[:10],
                         earliest_obs_iso=None if r is None else str(r.first_obs)[:10],
                         by=SURVEY_BY_STATION.get(str(st), "") if st is not None else "", site=station_name(st),
                         pred_ab=None if r is None else float(r.lead7_eff_AB_est), y1=des in Y1_FORCED or des in set(y1)))
    return rows


def _lost_rows(lost) -> list:
    b = pd.read_csv(os.path.join(C.TARGETS, "lists", "b_lost_recovery_shortlist.csv"))
    rows = []
    for des in lost:
        r = b[b.designation == des].iloc[0]
        rows.append(dict(name=des, slug=slugify(des), desig=des, kind="lost", role="lost", disc_iso=str(r.first_obs)[:10],
                         earliest_obs_iso=str(r.first_obs)[:10], last_obs_iso=str(r.last_obs)[:10], by="", site="",
                         pred_ab=float(r.post_best_AB_est), y1=False))
    return rows


def searchable_lost(max_px: float = 20.0) -> list:
    """Lost objects with useful SPHEREx frames (outside the observed arc, bright enough) whose 3-sigma
    search ellipse stays under max_px (A2 phase-B summaries)."""
    d = os.path.join(C.ORBITS, "lost_spherex")
    out = []
    for f in ("lost_top20_phaseB_summary.csv", "lost_L1top20_phaseB_summary.csv"):
        s = pd.read_csv(os.path.join(d, f))
        ok = (s.n_useful_files > 0) & (s.useful_max_major_3s_px < max_px)
        out += [o for o in s.object[ok] if o not in out]
    return out


def all_objects(lost_max_px: float = 20.0) -> pd.DataFrame:
    """Kaggle run: every row of the A1 precovery shortlist (Y1 stack candidates keep 300 frames) + the
    searchable lost objects. No famous objects."""
    sl = pd.read_csv(os.path.join(C.TARGETS, "lists", "a_spherex_precovery_shortlist.csv"))
    pick = list(sl.designation) + [d for d in Y1_FORCED if d not in set(sl.designation)]
    y1 = sl.designation[sl.y1_stack_candidate.astype(bool)]
    df = pd.DataFrame(_precovery_rows(sl, pick, y1) + _lost_rows(searchable_lost(lost_max_px)))
    df["hz_cmd"] = df.desig.map(horizons_command)
    df["most_name"] = df.desig
    return df


def first_run_objects() -> pd.DataFrame:
    """Top 30 of the A1 precovery shortlist + every Y1 stack candidate + 2025 OZ + famous objects."""
    sl = pd.read_csv(os.path.join(C.TARGETS, "lists", "a_spherex_precovery_shortlist.csv"))
    pick = list(sl.designation.head(30)) + [d for d in Y1_FORCED if d not in set(sl.designation.head(30))]
    rows = _precovery_rows(sl, pick) + _lost_rows(LOST)
    for f in FAMOUS:
        rows.append(dict(name=f["name"], slug=f["slug"], desig=f["desig"], kind="famous", role="known", disc_iso=f["disc_iso"],
                         earliest_obs_iso=None, by=f["by"], site=f["site"], pred_ab=None, y1=False, most_name=f.get("most_name")))
    df = pd.DataFrame(rows)
    df["hz_cmd"] = df.desig.map(horizons_command)
    df["most_name"] = [m if isinstance(m, str) else d for m, d in zip(df.get("most_name", df.desig), df.desig)]
    return df


def load_objects(spec: str) -> pd.DataFrame:
    """spec: 'first' (first-run list), a CSV path (columns as first_run_objects), or comma-separated slugs/names
    that are filtered from the first-run list. 'all' is the Kaggle list (all_objects)."""
    if spec == "all":
        return all_objects()
    full = first_run_objects()
    if spec == "first":
        return full
    pilot = {"c2026s1", "eros", "2025oz"}
    if spec == "y1":
        return full[full.y1.astype(bool) | full.slug.isin(pilot)].reset_index(drop=True)
    if spec == "rest_rev":  # same set, reverse order (a second lane works from the other end)
        return full[~(full.y1.astype(bool) | full.slug.isin(pilot))].iloc[::-1].reset_index(drop=True)
    if spec == "rest":
        return full[~(full.y1.astype(bool) | full.slug.isin(pilot))].reset_index(drop=True)
    if os.path.exists(spec):
        df = pd.read_csv(spec)
        if "hz_cmd" not in df:
            df["hz_cmd"] = df.desig.map(horizons_command)
        if "most_name" not in df:
            df["most_name"] = df.desig
        return df
    want = [s.strip() for s in spec.split(",") if s.strip()]
    keys = {slugify(w) for w in want}
    sel = full[full.slug.isin(keys) | full.name.map(slugify).isin(keys) | full.desig.map(slugify).isin(keys)]
    missing = keys - set(sel.slug) - set(sel.name.map(slugify)) - set(sel.desig.map(slugify))
    if missing:
        raise SystemExit(f"unknown objects: {sorted(missing)}")
    return sel.reset_index(drop=True)
