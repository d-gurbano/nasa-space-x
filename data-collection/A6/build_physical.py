"""A6: one merged physical-properties table per asteroid (join key: SBDB pdes / asteroid number or designation).
Sources: JPL SBDB query (diameter, albedo, rot_per, spec_B, spec_T), NEOWISE Diameters and Albedos V2.0 (PDS;
median per object of D, pV, pIR = W1/W2 albedo), LCDB V4.0 summary (period, amplitude, quality U, class),
DeMeo 2009 classes, Gaia DR3 SSO reflectance (16 bands 0.374-1.034 um; partner ESA) presence flag.
usage: python code/A6/build_physical.py
"""
import os, glob, re, io
import numpy as np, pandas as pd
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
D = f"{ROOT}/data/06-composition"; E = f"{D}/ext"; O = f"{D}/derived"

sb = pd.read_csv(f"{D}/raw/jpl_sbdb/sbdb_physical.csv", low_memory=False)
sb = sb.rename(columns={c: "sbdb_" + c for c in sb.columns if c not in ("pdes", "full_name", "spkid")})

# NEOWISE (PDS4 csv, no header; field names from the XML label)
nw = []
for f in glob.glob(f"{E}/neowise/*/data/neowise_*.csv"):
    if "fixed" in f: continue
    names = re.findall(r"<name>([^<]+)</name>", open(f[:-4] + ".xml").read())
    if "Asteroid_Number" not in names:
        print("skip (different columns):", os.path.basename(f)); continue
    names = names[names.index("Asteroid_Number"):]
    d = pd.read_csv(f, header=None, names=names, skipinitialspace=True, low_memory=False)
    d["neowise_group"] = os.path.basename(f)[8:-4]; nw.append(d)
nw = pd.concat(nw)
for c in ["Prov_desig", "MPC_packed_name"]: nw[c] = nw[c].astype(str).str.strip()
nw["pdes"] = np.where(nw.Asteroid_Number > 0, nw.Asteroid_Number.astype(str), nw.Prov_desig)
for c in ["Diameter", "V_albedo", "IR_albedo", "Beaming_param"]:
    nw[c] = pd.to_numeric(nw[c], errors="coerce").where(lambda x: x > -9)
g = nw.groupby("pdes").agg(neowise_D_km=("Diameter", "median"), neowise_pV=("V_albedo", "median"),
                           neowise_pIR=("IR_albedo", "median"), neowise_eta=("Beaming_param", "median"),
                           neowise_nfits=("Diameter", "size"), neowise_group=("neowise_group", "first")).reset_index()
nw.to_csv(f"{O}/neowise_all_fits.csv", index=False)

# LCDB summary (skip keyword block; data after '# Data' line)
txt = open(glob.glob(f"{E}/lcdb/*/data/lc_summary.csv")[0], encoding="latin-1").read().splitlines()
hdr = [l for l in txt if l.startswith("Number,Name,Desig")][0]
start = [i for i, l in enumerate(txt) if l.startswith("# Data")][0]
lc = pd.read_csv(io.StringIO("\n".join([hdr] + txt[start + 1:])), low_memory=False)
lc["pdes"] = np.where(pd.to_numeric(lc.Number, errors="coerce") > 0, lc.Number.astype(str), lc.Name.astype(str))
lc = lc.rename(columns={"Period": "lcdb_period_h", "AmpMax": "lcdb_amp_max", "AmpMin": "lcdb_amp_min", "U": "lcdb_U",
                        "Class": "lcdb_class", "Diam": "lcdb_diam_km", "Albedo": "lcdb_albedo", "IsBinary": "lcdb_binary"})
for c in ["lcdb_period_h", "lcdb_amp_max", "lcdb_amp_min", "lcdb_diam_km", "lcdb_albedo"]:
    lc[c] = pd.to_numeric(lc[c], errors="coerce").where(lambda x: x > -9)
lc = lc[["pdes", "lcdb_period_h", "lcdb_amp_min", "lcdb_amp_max", "lcdb_U", "lcdb_class", "lcdb_diam_km",
         "lcdb_albedo", "lcdb_binary"]].drop_duplicates("pdes")

# DeMeo classes
dm = pd.read_fwf(glob.glob(f"{E}/busdemeo/*/data/demeotax.tab")[0], header=None, colspecs=[(0, 7), (8, 26), (26, 36), (36, 48)],
                 names=["num", "name", "prov", "demeo_class"])
dm["pdes"] = dm.num.astype(str).str.strip(); dm = dm[["pdes", "demeo_class"]]

# Gaia DR3 SSO reflectance: wide table per object (16 wavelengths)
gs = []
for f in sorted(glob.glob(f"{D}/raw/gaia_dr3_sso/SsoReflectanceSpectrum_*.csv.gz")):
    gs.append(pd.read_csv(f, comment="#", usecols=["number_mp", "denomination", "wavelength", "reflectance_spectrum",
                                                    "reflectance_spectrum_err", "reflectance_spectrum_flag"]))
gs = pd.concat(gs)
gw = gs.pivot_table(index=["number_mp", "denomination"], columns="wavelength", values="reflectance_spectrum").reset_index()
gw.columns = ["number_mp", "denomination"] + [f"R_{int(c)}nm" for c in gw.columns[2:]]
gf = gs.pivot_table(index="number_mp", columns="wavelength", values="reflectance_spectrum_flag").reset_index()
gw.to_csv(f"{O}/gaia_dr3_sso_reflectance_wide.csv", index=False, float_format="%.5f")
gpres = pd.DataFrame({"pdes": gw.number_mp.astype(str), "gaia_dr3_spectrum": True})

m = sb.merge(g, on="pdes", how="outer").merge(lc, on="pdes", how="left").merge(dm, on="pdes", how="left") \
      .merge(gpres, on="pdes", how="left")
m["gaia_dr3_spectrum"] = m.gaia_dr3_spectrum.fillna(False)
m.to_csv(f"{O}/physical_properties_merged.csv", index=False)
print("rows", len(m), "| SBDB", len(sb), "| NEOWISE objects", len(g), "| LCDB", len(lc), "| DeMeo", len(dm),
      "| Gaia objects", len(gw))
for c in ["sbdb_diameter", "sbdb_albedo", "sbdb_rot_per", "sbdb_spec_B", "sbdb_spec_T", "neowise_D_km", "neowise_pIR",
          "lcdb_period_h", "demeo_class"]:
    print(c, int(m[c].notna().sum()))
print("gaia", int(m.gaia_dr3_spectrum.sum()))
