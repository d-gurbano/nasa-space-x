"""A6: build the composition template set and the labeled validation set, convolved to SPHEREx channels.

Inputs: data/06-composition/ext/* (unzipped raw downloads; run code/A6/unpack.sh first)
Outputs (data/06-composition/derived/):
  spherex_channels.csv                    102 nominal channels (VERIFIED, IRSA lab calibration)
  templates_native_long.csv               every template at its native sampling (template_id, wavelength_um, value)
  spherex_templates_cent.csv / _allpix.csv one row per template, columns ch001..ch102 (COMPUTED by convolution)
  template_catalog.csv                    one row per template: family, source, label, value type, coverage, label tag
  spherex_validation_spectra.csv          every individual asteroid spectrum (SMASS2, S3OS2, MITHNEOS, AKARI,
                                          Rivkin/Lebofsky 3-um) convolved to SPHEREx, with taxonomy labels joined
usage: python code/A6/build_templates.py
"""
import os, sys, glob, re
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(__file__))
import to_spherex as TS

D = os.path.join(TS.ROOT, "data/06-composition"); E = f"{D}/ext"; O = f"{D}/derived"
os.makedirs(O, exist_ok=True)
CH = TS.channel_table(); CH.to_csv(f"{O}/spherex_channels.csv", index=False)
CHC = [f"ch{i:03d}" for i in range(1, 103)]
native, cat = [], []


def add(tid, family, source, label, w, v, vtype="reflectance", tag="VERIFIED (source data)", note=""):
    w = np.asarray(w, float); v = np.asarray(v, float); g = np.isfinite(w) & np.isfinite(v)
    w, v = w[g], v[g]
    if len(w) < 3:
        return
    native.append(pd.DataFrame({"template_id": tid, "wavelength_um": w, "value": v}))
    cat.append(dict(template_id=tid, family=family, source=source, label=label, value_type=vtype,
                    wmin_um=w.min(), wmax_um=w.max(), n_native=len(w), number_tag=tag, note=note))


# ---------- 1. Bus-DeMeo class means (0.45-2.45 um, norm 0.55 um) ----------
bd = f"{E}/busdemeo/ast.bus-demeo.taxonomy/data"
names = re.findall(r"<name>([^<]+)</name>", open(f"{bd}/meanspectra.xml").read())
cols = names[names.index("WAVELENGTH"):]
m = pd.read_csv(f"{bd}/meanspectra.tab", sep=r"\s+", header=None, names=cols)
for c in cols[1::2]:
    cl = c.split("_")[0]; cl = {"CB": "Cb", "CG": "Cg", "CGH": "Cgh", "CH": "Ch", "SA": "Sa", "SQ": "Sq", "SR": "Sr",
                                "SV": "Sv", "XC": "Xc", "XE": "Xe", "XK": "Xk"}.get(cl, cl)
    v = m[c].where(m[c] > -0.9)
    add(f"busdemeo_{cl}", "asteroid_class_mean", "Bus-DeMeo (DeMeo et al. 2009) PDS SBN", cl, m.WAVELENGTH, v,
        note="normalized to 1 at 0.55 um; covers SPHEREx bands 1-3 only")
bdmeans = {c["label"]: c for c in cat}

# ---------- labels: JPL SBDB + DeMeo table ----------
sb = pd.read_csv(f"{D}/raw/jpl_sbdb/sbdb_physical.csv", low_memory=False)
sb["num"] = pd.to_numeric(sb.pdes, errors="coerce")
dm = pd.read_fwf(f"{bd}/demeotax.tab", header=None, colspecs=[(0, 7), (8, 26), (26, 36), (36, 48)],
                 names=["num", "name", "prov", "demeo_class"])
lab = sb.set_index("pdes")[["spec_B", "spec_T", "albedo", "diameter", "rot_per"]]
dmc = dict(zip(dm.num.astype(str).str.strip(), dm.demeo_class.astype(str).str.strip()))


def complex_of(*cls):
    for c in cls:
        if not isinstance(c, str) or not c or c in ("nan", "-"):
            continue
        c0 = c.strip().rstrip(":").upper()
        if c0[:1] in "BCFG" and not c0.startswith("CX"): return "C"
        if c0.startswith("V"): return "V"
        if c0[:1] in "SKLAQRO": return "S"
        if c0[:1] in "XEMP": return "X"
        if c0[:1] in "DT": return "D"
    return ""


# ---------- 2. AKARI AcuA 2.5-5 um reflectance (Usui et al. 2019; JAXA, partner) ----------
ak = []
for f in sorted(glob.glob(f"{E}/AcuA_1.0/reflectance/*.txt")):
    num = os.path.basename(f).split("_")[0].lstrip("0")
    a = pd.read_csv(f, sep=r"\s+", header=None, names=["w", "r", "e", "eflag", "sflag", "tflag", "cflag"])
    a = a[(a.eflag == 0) & (a.sflag == 0) & (a.tflag == 0) & (a.cflag == 0)]
    l = lab.loc[num] if num in lab.index else None
    cx = complex_of(dmc.get(num), None if l is None else l.spec_B, None if l is None else l.spec_T)
    ak.append((num, cx, a))
grid = np.arange(2.52, 5.0, 0.01)
for cx in ["C", "S", "X", "D"]:
    arr = [np.interp(grid, a.w, a.r, left=np.nan, right=np.nan) for n, c, a in ak if c == cx and len(a) > 20]
    if len(arr) >= 2:
        A = np.array(arr)
        for j in range(A.shape[1]):  # require >=2 spectra per wavelength
            if np.isfinite(A[:, j]).sum() < 2: A[:, j] = np.nan
        add(f"akari_{cx}complex_mean", "asteroid_complex_mean_3um", "AKARI AcuA-spec (Usui et al. 2019) JAXA DARTS",
            f"{cx}-complex (n={len(arr)})", grid, np.nanmedian(A, axis=0), tag="COMPUTED (median of AKARI spectra)",
            note="normalized at 2.6 um; good (unflagged) points only; complex from SBDB/DeMeo labels")

# ---------- 3. Stitched full-range complex templates 0.45-5 um (Bus-DeMeo + AKARI) ----------
for cx, bdc in [("C", "C"), ("S", "S"), ("X", "X"), ("D", "D")]:
    akc = [c for c in cat if c["template_id"] == f"akari_{cx}complex_mean"]
    if not akc: continue
    nb = [n for n in native if n.template_id.iloc[0] == f"busdemeo_{bdc}"][0]
    na = [n for n in native if n.template_id.iloc[0] == f"akari_{cx}complex_mean"][0]
    # stitch assumption: reflectance continuous from 2.45 (Bus-DeMeo last point) to 2.55 (AKARI first good points)
    r245 = nb.value.iloc[-1]; r255 = np.nanmedian(na.value[(na.wavelength_um < 2.6)])
    w = np.r_[nb.wavelength_um, na.wavelength_um]; v = np.r_[nb.value, na.value * r245 / r255]
    add(f"stitched_{cx}_0.45-5um", "asteroid_complex_stitched", "Bus-DeMeo + AKARI AcuA (stitched by A6)",
        f"{cx}-complex", w, v, tag="ESTIMATED (stitch scale assumes continuity at 2.45-2.55 um)",
        note="normalized 1 at 0.55 um; reflected light only (no thermal tail)")

# ---------- 4. USGS splib07a minerals and ices (Beckman 0.2-3 um spliced with Nicolet 1.12-216 um) ----------
U = f"{E}/usgs_splib07/ASCIIdata_splib07a"
wB = pd.read_csv(glob.glob(f"{U}/splib07a_Wavelengths_BECK*")[0], skiprows=1, header=None)[0].to_numpy(float)
wN = pd.read_csv(glob.glob(f"{U}/splib07a_Wavelengths_NIC4*")[0], skiprows=1, header=None)[0].to_numpy(float)


def usgs(fn):
    v = np.array(pd.read_csv(fn, skiprows=1, header=None)[0], dtype=float); v[v < -1e30] = np.nan
    return v


usgs_list = [  # (label, Beckman file glob, Nicolet file glob or None, family)
    ("H2O ice 77K", "ChapterL_Liquids/splib07a_H2O-Ice_GDS136_77K_BECKa_AREF.txt", None, "ice"),
    ("Olivine Fo89", "ChapterM_Minerals/splib07a_Olivine_GDS70.c_Fo89_70um_BECKb_AREF.txt", "ChapterM_Minerals/splib07a_Olivine_GDS70.c_Fo89_70um_NIC4bbb_RREF.txt", "mineral"),
    ("Enstatite (orthopyroxene)", "ChapterM_Minerals/splib07a_Enstatite_NMNH128288_BECKc_AREF.txt", "ChapterM_Minerals/splib07a_Enstatite_NMNH128288_NIC4ccc_RREF.txt", "mineral"),
    ("Hypersthene (orthopyroxene)", "ChapterM_Minerals/splib07a_Hypersthene_PYX02.b_120um_BECKc_AREF.txt", "ChapterM_Minerals/splib07a_Hypersthene_PYX02.b_120um_NIC4cbb_RREF.txt", "mineral"),
    ("Diopside (clinopyroxene)", "ChapterM_Minerals/splib07a_Diopside_HS15.3B_Pyroxene_BECKc_AREF.txt", "ChapterM_Minerals/splib07a_Diopside_HS15.3B_Pyroxene_NIC4dbb_RREF.txt", "mineral"),
    ("Pigeonite (clinopyroxene)", "ChapterM_Minerals/splib07a_Pigeonite_HS199.3B_BECKc_AREF.txt", "ChapterM_Minerals/splib07a_Pigeonite_HS199.3B_NIC4cc_RREF.txt", "mineral"),
    ("Anorthite (plagioclase)", "ChapterM_Minerals/splib07a_Anorthite_HS201.3B_Plagio_BECKa_AREF.txt", "ChapterM_Minerals/splib07a_Anorthite_HS201.3B_Plagio_NIC4aa_RREF.txt", "mineral"),
    ("Antigorite (serpentine, hydrated)", "ChapterM_Minerals/splib07a_Antigorite_NMNH96917.b_165um_BECKb_AREF.txt", "ChapterM_Minerals/splib07a_Antigorite_NMNH96917.b_165_NIC4bb_RREF.txt", "hydrated_mineral"),
    ("Lizardite (serpentine, hydrated)", "ChapterM_Minerals/splib07a_Lizardite_NMNHR4687.c_70um_BECKa_AREF.txt", "ChapterM_Minerals/splib07a_Lizardite_NMNHR4687.c_70um_NIC4aa_RREF.txt", "hydrated_mineral"),
    ("Saponite (smectite clay, hydrated)", "ChapterM_Minerals/splib07a_Saponite_SapCa-1.AcB_BECKb_AREF.txt", "ChapterM_Minerals/splib07a_Saponite_SapCa-1.AcB_NIC4bbb_RREF.txt", "hydrated_mineral"),
    ("Montmorillonite (clay, hydrated)", "ChapterM_Minerals/splib07a_Montmorillonite_CM20_BECKb_AREF.txt", "ChapterM_Minerals/splib07a_Montmorillonite_CM20_NIC4bc_RREF.txt", "hydrated_mineral"),
    ("Kaolinite (clay, hydrated)", "ChapterM_Minerals/splib07a_Kaolinite_CM5_BECKb_AREF.txt", "ChapterM_Minerals/splib07a_Kaolinite_CM5_NIC4bb_RREF.txt", "hydrated_mineral"),
    ("Magnetite", "ChapterM_Minerals/splib07a_Magnetite_HS195.3B_BECKb_AREF.txt", "ChapterM_Minerals/splib07a_Magnetite_HS195.3B_NIC4bbu_RREF.txt", "mineral"),
    ("Pyrrhotite (Fe sulfide)", "ChapterM_Minerals/splib07a_Pyrrhotite_HS269.3B_BECKc_AREF.txt", "ChapterM_Minerals/splib07a_Pyrrhotite_HS269.3B_NIC4ccu_RREF.txt", "mineral"),
    ("Calcite (carbonate)", "ChapterM_Minerals/splib07a_Calcite_WS272_BECKa_AREF.txt", "ChapterM_Minerals/splib07a_Calcite_WS272_NIC4aaa_RREF.txt", "mineral"),
    ("Hematite", "ChapterM_Minerals/splib07a_Hematite_GDS69.b_104-150u_BECKb_AREF.txt", "ChapterM_Minerals/splib07a_Hematite_GDS69.b_104-150u_NIC4bbb_RREF.txt", "mineral"),
    ("Goethite (hydrated Fe oxide)", "ChapterM_Minerals/splib07a_Goethite_HS36.3_BECKb_AREF.txt", "ChapterM_Minerals/splib07a_Goethite_HS36.3B_NIC4bcb_RREF.txt", "hydrated_mineral"),
    ("Gypsum (hydrated sulfate)", "ChapterM_Minerals/splib07a_Gypsum_HS333.3B_(Selenite)_BECKa_AREF.txt", "ChapterM_Minerals/splib07a_Gypsum_HS333.3B_(Selenite)_NIC4aaa_RREF.txt", "hydrated_mineral"),
    ("Ethane ice 77K", None, "ChapterO_OrganicCompounds/splib07a_Ethane_MTG_77K_NIC4aa_RREF.txt", "organic_ice"),
    ("Methane liquid 77K", None, "ChapterO_OrganicCompounds/splib07a_Methane_XCEL_liquid_T~77K_NIC4aa_RREF.txt", "organic_ice"),
    ("Anthracene (PAH) 85K", None, "ChapterO_OrganicCompounds/splib07a_Anthracene_AA-42197_85K_NIC4aa_RREF.txt", "organic"),
]
for label, fb, fn, fam in usgs_list:
    try:
        parts = []
        vb = usgs(f"{U}/{fb}") if fb else None
        vn = usgs(f"{U}/{fn}") if fn else None
        if vb is not None and vn is not None:
            ov = (wB > 1.3) & (wB < 2.5)
            sc = np.nanmedian(vb[ov] / np.interp(wB[ov], wN, vn))  # scale Nicolet to Beckman in overlap
            w = np.r_[wB[wB < 2.5], wN[(wN >= 2.5) & (wN <= 5.6)]]; v = np.r_[vb[wB < 2.5], vn[(wN >= 2.5) & (wN <= 5.6)] * sc]
            tag = "COMPUTED (Beckman<2.5um + Nicolet>=2.5um scaled in 1.3-2.5um overlap)"
        elif vb is not None:
            w, v, tag = wB, vb, "VERIFIED (source data)"
        else:
            sel = wN <= 5.6; w, v, tag = wN[sel], vn[sel], "VERIFIED (source data)"
        o = np.argsort(w)
        add(f"usgs_{re.sub(r'[^A-Za-z0-9]+', '_', label).strip('_')}", fam, "USGS splib07a (Kokaly et al. 2017)", label,
            w[o], v[o], tag=tag, note=f"files: {fb} | {fn}")
    except Exception as e:
        print("USGS skip", label, e)

# ---------- 5. RELAB meteorites (added by relab_select.py output if present) ----------
rs = f"{O}/relab_selected_long.csv"
if os.path.exists(rs):
    r = pd.read_csv(rs)
    for tid, g in r.groupby("template_id"):
        add(tid, g.family.iloc[0], "RELAB (Brown Univ./NASA) RelabDatabase2025Dec31", g.label.iloc[0],
            g.wavelength_um, g.value, note=g.note.iloc[0])

# ---------- 6. Comet gas emission and ice band shapes (synthetic, ESTIMATED) ----------
wg = np.arange(0.70, 5.10, 0.0005)
feat = [  # (id, label, center um, FWHM um, kind) band centers are standard lab/comet values
    ("H2O_nu3_fluor", "H2O gas fluorescence (nu3/nu1, ~2.7 um)", 2.69, 0.08, "emission"),
    ("CH_organics", "C-H stretch organics / CH3OH / C2H6 (3.3-3.5 um)", 3.42, 0.15, "emission"),
    ("CO2_nu3", "CO2 gas fluorescence (nu3, 4.26 um)", 4.26, 0.04, "emission"),
    ("CO_1-0", "CO gas fluorescence (1-0, 4.67 um)", 4.67, 0.06, "emission"),
    ("OCS_nu3", "OCS gas (4.85 um, weak)", 4.85, 0.03, "emission"),
    ("H2Oice_3um", "Water ice absorption (3.0 um)", 3.05, 0.25, "absorption"),
    ("H2Oice_2um", "Water ice absorption (2.0 um)", 2.02, 0.12, "absorption"),
    ("H2Oice_1p5um", "Water ice absorption (1.5 um)", 1.52, 0.10, "absorption"),
    ("CO2ice_4p27", "CO2 ice absorption (4.27 um)", 4.27, 0.02, "absorption"),
    ("COice_4p67", "CO ice absorption (4.67 um)", 4.67, 0.01, "absorption"),
]
for fid, label, c, fw, kind in feat:
    g = np.exp(-0.5 * ((wg - c) / (fw / 2.3548)) ** 2)
    v = g if kind == "emission" else 1 - 0.5 * g
    add(f"comet_{fid}", f"comet_{kind}_feature", "A6 synthetic Gaussian at literature band center", label, wg, v,
        vtype="relative_emission" if kind == "emission" else "relative_reflectance",
        tag="ESTIMATED (Gaussian shape; center VERIFIED from standard band positions)",
        note="unit peak emission or 50% depth absorption; use to see which SPHEREx channels a feature lands in")

# ---------- write templates ----------
nat = pd.concat(native); nat.to_csv(f"{O}/templates_native_long.csv", index=False)
catdf = pd.DataFrame(cat)
for resp in ["cent", "allpix"]:
    rows = []
    for tid, g in nat.groupby("template_id", sort=False):
        solar = catdf.set_index("template_id").loc[tid, "value_type"].startswith("reflectance")
        rows.append([tid] + list(TS.convolve(g.wavelength_um, g.value, resp, solar_weight=solar)))
    t = pd.DataFrame(rows, columns=["template_id"] + CHC)
    t.to_csv(f"{O}/spherex_templates_{resp}.csv", index=False, float_format="%.5f")
catdf["n_spherex_channels"] = catdf.template_id.map(t.set_index("template_id")[CHC].notna().sum(axis=1))
catdf.to_csv(f"{O}/template_catalog.csv", index=False)
print("templates:", len(catdf)); print(catdf.groupby("family").size())

# ---------- 7. validation set: individual asteroid spectra ----------
val = []


def vadd(survey, num, name, date, w, r, e=None):
    l = lab.loc[str(num)] if str(num) in lab.index else None
    sB = None if l is None else l.spec_B; sT = None if l is None else l.spec_T
    if isinstance(sB, pd.Series): sB, sT = sB.iloc[0], sT.iloc[0]
    dmcl = dmc.get(str(num), "")
    conv = TS.convolve(w, r, "cent", solar_weight=True)
    if np.isfinite(conv).sum() == 0: return
    val.append([survey, str(num), name, date, dmcl, sB, sT, complex_of(dmcl, sB, sT),
                None if l is None else (l.albedo if not isinstance(l.albedo, pd.Series) else l.albedo.iloc[0]),
                float(np.nanmin(w)), float(np.nanmax(w))] + list(conv))


# SMASSII (0.44-0.92) and S3OS2 (0.49-0.92): filename starts with number
for survey, pat in [("SMASSII", f"{E}/smass2/*/data/*/*.tab"), ("S3OS2", f"{E}/s3os2/*/data/*/*.tab")]:
    for f in glob.glob(pat):
        b = os.path.basename(f); num = b.split("_")[0].lstrip("0")
        try:
            a = pd.read_csv(f, sep=r"\s+", header=None).to_numpy(float)
            if a[:, 0].max() > 100: a[:, 0] /= 1e4  # Angstrom safety
            vadd(survey, num, b, "", a[:, 0], a[:, 1])
        except Exception:
            pass
# MITHNEOS (0.45-2.45, csv w,r,e)
op = pd.concat([pd.read_csv(f, header=None) for f in glob.glob(f"{E}/mithneos/*/data/observationalparameters_*.csv")])
for f in glob.glob(f"{E}/mithneos/*/data/*/*.csv"):
    b = os.path.basename(f); key = b.split("_")[0]
    a = pd.read_csv(f, header=None).to_numpy(float)
    num = key if key.isdigit() else ""
    if not num:
        hit = op[op[3].astype(str).str.endswith(b)]
        num = str(hit.iloc[0, 1]).replace(" ", "") if len(hit) else key
    vadd("MITHNEOS", num if num else key, b, b.split("_")[-1].split(".")[0], a[:, 0], a[:, 1])
# AKARI 2.5-5
for num, cx, a in ak:
    vadd("AKARI_AcuA", num, "", "", a.w, a.r)
# 3-micron sets (Rivkin, Lebofsky): names like 620drakonia.tab / atalante19831223.tab
nm = sb.assign(n=sb.name.astype(str).str.lower()).dropna(subset=["n"])
n2num = dict(zip(nm.n, nm.pdes))
for f in glob.glob(f"{E}/3micron/*/data/**/*.tab", recursive=True):
    b = os.path.basename(f)[:-4]; mm = re.match(r"(\d*)([a-z]+)", b)
    num = mm.group(1) or n2num.get(mm.group(2), "") if mm else ""
    try:
        a = pd.read_csv(f, sep=r"\s+", header=None).to_numpy(float)
        a = a[a[:, 1] > -9]
        vadd("3um_" + ("Rivkin" if "rivkin" in f else "Lebofsky"), num, b, "", a[:, 0], a[:, 1])
    except Exception:
        pass
V = pd.DataFrame(val, columns=["survey", "number", "file", "date", "demeo_class", "sbdb_spec_B", "sbdb_spec_T",
                               "complex", "sbdb_albedo", "wmin_um", "wmax_um"] + CHC)
V.to_csv(f"{O}/spherex_validation_spectra.csv", index=False, float_format="%.5f")
print("validation spectra:", len(V)); print(V.groupby("survey").size()); print("labeled (complex):", (V.complex != "").sum())
