"""A6: one bulk JPL SBDB Query API call for all small bodies with any physical parameter.
usage: python code/A6/sbdb_physical.py"""
import requests, json, pandas as pd, hashlib, datetime, csv, os
F = "spkid,full_name,pdes,name,prefix,kind,neo,pha,class,H,G,diameter,diameter_sigma,extent,albedo,rot_per,GM,density,BV,UB,IR,spec_B,spec_T,H_sigma,data_arc,n_obs_used,condition_code"
cdata = json.dumps({"OR": ["spec_B|DF", "spec_T|DF", "albedo|DF", "diameter|DF", "rot_per|DF"]})
url = "https://ssd-api.jpl.nasa.gov/sbdb_query.api"
r = requests.get(url, params={"fields": F, "sb-cdata": cdata, "full-prec": "false"}, timeout=600)
r.raise_for_status(); d = r.json()
df = pd.DataFrame(d["data"], columns=d["fields"])
os.makedirs("data/06-composition/raw/jpl_sbdb", exist_ok=True)
out = "data/06-composition/raw/jpl_sbdb/sbdb_physical.csv"; df.to_csv(out, index=False)
json.dump({"signature": d.get("signature"), "count": d.get("count"), "url": r.url}, open(out.replace(".csv", "_meta.json"), "w"), indent=1)
b = open(out, "rb").read()
with open("data/06-composition/manifest.csv", "a", newline="") as f:
    csv.writer(f).writerow([out.replace("data/06-composition/", ""), r.url, len(b), hashlib.sha256(b).hexdigest(), datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%MZ")])
print(len(df), d.get("signature"))
for c in ["spec_B", "spec_T", "albedo", "diameter", "rot_per"]: print(c, df[c].notna().sum())
