"""A1 - bulk pulls from the JPL SBDB Query API (https://ssd-api.jpl.nasa.gov/doc/sbdb_query.html).
Read-only. Paginates with limit/limit-from, pauses between calls, retries with backoff.
Usage: python code/A1/fetch_sbdb.py [setname ...]
Output: data/01-targets/raw/sbdb/<set>.json (raw API pages merged) and clean/<set>.parquet
"""
import json, sys, time, pathlib, requests
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[2]
RAW = ROOT / "data/01-targets/raw/sbdb"; RAW.mkdir(parents=True, exist_ok=True)
CLEAN = ROOT / "data/01-targets/clean"; CLEAN.mkdir(parents=True, exist_ok=True)
URL = "https://ssd-api.jpl.nasa.gov/sbdb_query.api"

FIELDS_FULL = ("spkid,full_name,pdes,name,prefix,kind,neo,pha,class,H,G,M1,M2,K1,K2,PC,H_sigma,diameter,diameter_sigma,albedo,extent,"
               "rot_per,spec_B,spec_T,orbit_id,epoch,epoch_cal,equinox,e,a,q,i,om,w,ma,ad,n,tp,tp_cal,per_y,moid,moid_ld,moid_jup,t_jup,"
               "sigma_e,sigma_a,sigma_q,sigma_i,sigma_om,sigma_w,sigma_ma,sigma_tp,sigma_per,producer,data_arc,first_obs,last_obs,"
               "n_obs_used,n_del_obs_used,n_dop_obs_used,condition_code,rms,two_body,A1,A2,A3,DT")
# lighter field list for the very large poorly-constrained set
FIELDS_LITE = ("spkid,full_name,pdes,kind,neo,pha,class,H,epoch,e,a,q,i,om,w,ma,tp,moid,sigma_a,sigma_e,sigma_ma,sigma_tp,"
               "data_arc,first_obs,last_obs,n_obs_used,condition_code,rms")

SETS = {
    # every object whose first used observation is on/after 2025-04-01 (all kinds)
    "new_firstobs_since_2025-04-01": dict(cdata={"AND": ["first_obs|GE|2025-04-01"]}, fields=FIELDS_FULL),
    # every object with a provisional designation from 2025 G (Apr 1 2025) onward, even if precovered earlier
    "new_desig_2025G_to_2025Y": dict(cdata={"AND": ["pdes|RE|^2025 [G-Y]"]}, fields=FIELDS_FULL),
    "new_desig_2026": dict(cdata={"AND": ["pdes|RE|^2026 "]}, fields=FIELDS_FULL),
    "neo_all": dict(group="neo", fields=FIELDS_FULL),
    "comet_all": dict(kind="c", fields=FIELDS_FULL),
    # poorly constrained / lost candidates: all objects with orbit condition code U >= 5
    "uncertain_U5plus_all": dict(cdata={"AND": ["condition_code|GE|5"]}, fields=FIELDS_LITE),
    # non-NEO short arcs that are not U>=5 are excluded on purpose (well-constrained)
}


def get(params, tries=6):
    for k in range(tries):
        try:
            r = requests.get(URL, params=params, timeout=300)
            if r.status_code == 200:
                return r.json()
            print("HTTP", r.status_code, r.text[:200])
        except Exception as ex:  # noqa
            print("err", ex)
        time.sleep(5 * 2 ** k)
    raise RuntimeError("failed " + str(params))


def fetch(name, spec, page=40000):
    out_rows, fields, off = [], None, 0
    while True:
        p = {"fields": spec["fields"], "limit": page, "limit-from": off, "full-prec": "true"}
        if "cdata" in spec: p["sb-cdata"] = json.dumps(spec["cdata"])
        if "group" in spec: p["sb-group"] = spec["group"]
        if "kind" in spec: p["sb-kind"] = spec["kind"]
        d = get(p)
        fields = d.get("fields", fields)
        rows = d.get("data", [])
        out_rows += rows
        print(name, "offset", off, "got", len(rows), "count", d.get("count"))
        if len(rows) < page:
            break
        off += page
        time.sleep(3)
    (RAW / f"{name}.json").write_text(json.dumps({"fields": fields, "data": out_rows, "query": {k: v for k, v in spec.items() if k != 'fields'},
                                                  "accessed": time.strftime("%Y-%m-%dT%H:%M:%S%z")}))
    df = pd.DataFrame(out_rows, columns=fields)
    for c in df.columns:
        if c not in ("spkid", "full_name", "pdes", "name", "prefix", "kind", "neo", "pha", "class", "epoch_cal", "tp_cal", "equinox", "producer",
                     "first_obs", "last_obs", "condition_code", "two_body", "orbit_id", "spec_B", "spec_T", "extent"):
            df[c] = pd.to_numeric(df[c], errors="coerce")
    df["full_name"] = df["full_name"].str.strip()
    df.to_parquet(CLEAN / f"sbdb_{name}.parquet", index=False)
    print(name, "rows", len(df))
    return df


if __name__ == "__main__":
    names = sys.argv[1:] or list(SETS)
    for n in names:
        fetch(n, SETS[n])
        time.sleep(3)
