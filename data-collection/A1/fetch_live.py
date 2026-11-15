"""A1 - live / risk lists and MPC bulk files (read-only).
JPL Scout, Sentry, CAD (2025-2027), interstellar objects; MPC NEOCP, NEA.txt, CometEls, extended JSON, critical list, MPECs.
Usage: python code/A1/fetch_live.py [jpl|mpc|all]
"""
import json, sys, time, re
from common import get, save, RAW

SSD = "https://ssd-api.jpl.nasa.gov"
STAMP = time.strftime("%Y%m%dT%H%M")


def jpl():
    # Scout: full list, then per-object detail (orbits summary + ephemeris uncertainty + impact info)
    u = f"{SSD}/scout.api"
    r = get(u); save(f"scout/scout_list_{STAMP}.json", r.content, u)
    lst = r.json().get("data", [])
    print("scout objects", len(lst))
    for o in lst:
        t = o["objectName"]
        try:
            r2 = get(u, params={"tdes": t}, pause=1.5)
            save(f"scout/detail/{t}_{STAMP}.json", r2.content, r2.url)
        except Exception as ex:
            print("scout detail fail", t, ex)
    # Sentry: summary of all objects, removed objects, and per-object VI tables for the riskiest
    u = f"{SSD}/sentry.api"
    r = get(u); save(f"sentry/sentry_summary_{STAMP}.json", r.content, u)
    sen = r.json().get("data", [])
    print("sentry objects", len(sen))
    r = get(u, params={"removed": "1"}); save(f"sentry/sentry_removed_{STAMP}.json", r.content, r.url)
    r = get(u, params={"all": "1"}); save(f"sentry/sentry_all_VIs_{STAMP}.json", r.content, r.url)
    # CNEOS close approaches 2025-2027, NEOs and comets, within 0.2 au
    u = f"{SSD}/cad.api"
    for kind in ("a", "c"):
        r = get(u, params={"date-min": "2025-01-01", "date-max": "2027-12-31", "dist-max": "0.2", "fullname": "true",
                           "diameter": "true", "kind": kind, "neo": "false" if kind == "c" else "true"})
        save(f"cad/cad_2025-2027_{kind}_0.2au_{STAMP}.json", r.content, r.url)
        print("cad", kind, r.json().get("count"))
    # interstellar objects and a few special objects: full SBDB record with covariance, discovery, close approaches
    u = f"{SSD}/sbdb.api"
    for s in ["1I", "2I", "3I"]:
        try:
            r = get(u, params={"sstr": s, "cov": "mat", "discovery": "1", "phys-par": "1", "ca-data": "1", "full-prec": "1"})
            save(f"special/interstellar_{s}.json", r.content, r.url)
        except Exception as ex:
            print("fail", s, ex)


def mpc():
    files = {
        "mpc/NEA.txt": "https://minorplanetcenter.net/iau/MPCORB/NEA.txt",
        "mpc/CometEls.txt": "https://minorplanetcenter.net/iau/MPCORB/CometEls.txt",
        "mpc/nea_extended.json.gz": "https://minorplanetcenter.net/Extended_Files/nea_extended.json.gz",
        "mpc/pha_extended.json.gz": "https://minorplanetcenter.net/Extended_Files/pha_extended.json.gz",
        "mpc/unusual_extended.json.gz": "https://minorplanetcenter.net/Extended_Files/unusual_extended.json.gz",
        "mpc/cometels.json.gz": "https://minorplanetcenter.net/Extended_Files/cometels.json.gz",
        "mpc/daily_extended.json.gz": "https://minorplanetcenter.net/Extended_Files/daily_extended.json.gz",
        "mpc/Unusual.txt": "https://minorplanetcenter.net/iau/lists/Unusual.html",
        "mpc/Soft00CritList.txt": "https://minorplanetcenter.net/iau/Ephemerides/CritList/Soft00CritList.txt",
        "mpc/CriticalList.html": "https://minorplanetcenter.net/iau/Ephemerides/CritList/CritList.html",
        "mpc/LastMonthUnusual.html": "https://minorplanetcenter.net/iau/lists/LastMonthsUnusual.html",
        "mpc/RecentMPECs.html": "https://minorplanetcenter.net/mpec/RecentMPECs.html",
        f"neocp/toconfirm_tabular_{STAMP}.html": "https://minorplanetcenter.net/iau/NEO/toconfirm_tabular.html",
        f"neocp/neocp_{STAMP}.txt": "https://minorplanetcenter.net/iau/NEO/neocp.txt",
        f"neocp/neocp_{STAMP}.json": "https://minorplanetcenter.net/Extended_Files/neocp.json",
        f"neocp/pccp_{STAMP}.txt": "https://minorplanetcenter.net/iau/NEO/pccp.txt",
        f"neocp/pccp_tabular_{STAMP}.html": "https://minorplanetcenter.net/iau/NEO/pccp_tabular.html",
        "mpc/NumberedMPs.txt.gz": "https://minorplanetcenter.net/iau/lists/NumberedMPs.txt.gz",
    }
    for rel, u in files.items():
        try:
            r = get(u, timeout=600, pause=2)
            save(rel, r.content, u)
            print("ok", rel, len(r.content))
        except Exception as ex:
            print("FAIL", rel, ex)
    # NEOCP observations (all objects at once) and orbits
    for rel, u in {f"neocp/neocp_obs_{STAMP}.txt": "https://minorplanetcenter.net/iau/NEO/neocp.obs",
                   f"neocp/neocp_orbits_{STAMP}.txt": "https://minorplanetcenter.net/iau/NEO/neocp.orb"}.items():
        try:
            r = get(u, pause=2); save(rel, r.content, u); print("ok", rel, len(r.content))
        except Exception as ex:
            print("FAIL", rel, ex)


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    if what in ("jpl", "all"): jpl()
    if what in ("mpc", "all"): mpc()
