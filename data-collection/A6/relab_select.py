"""A6: pick RELAB meteorite spectra that span 0.75-5 um (RELAB-spliced VNIR+FTIR spectra) and build class medians.
Input : data/06-composition/raw/relab/RelabDatabase2025Dec31.zip (read in place with Python zipfile; zip64, macOS unzip fails)
Output: derived/relab_meteorite_selected_spectra.csv  (every chosen spectrum: id, sample, class, native points)
        derived/relab_selected_long.csv               (class medians on a 0.005 um grid; picked up by build_templates.py)
        derived/relab_catalogue_samples.csv / relab_catalogue_spectra.csv (full RELAB catalogues, for later searches)
usage: python code/A6/relab_select.py
"""
import os, io, re, zipfile
import numpy as np, pandas as pd
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
D = f"{ROOT}/data/06-composition"; O = f"{D}/derived"
z = zipfile.ZipFile(f"{D}/raw/relab/RelabDatabase2025Dec31.zip")
rd = lambda f: pd.read_csv(io.BytesIO(z.read(f)), sep="\t", encoding="latin-1", dtype=str).dropna(axis=1, how="all")
S = rd("catalogues/Sample_Catalogue.txt"); P = rd("catalogues/Spectra_Catalogue.txt")
for df in (S, P):
    for c in df.columns: df[c] = df[c].str.strip()
S.to_csv(f"{O}/relab_catalogue_samples.csv", index=False); P.to_csv(f"{O}/relab_catalogue_spectra.csv", index=False)
P["Start"] = pd.to_numeric(P.Start, errors="coerce"); P["Stop"] = pd.to_numeric(P.Stop, errors="coerce")
X = P.merge(S, on="SampleID", suffixes=("", "_s"))
X = X[(X.Start <= 750) & (X.Stop >= 5000)]
X = X[X.Type1.str.contains("Chondrite|Achondrite|Iron|Stony", case=False, na=False)]
X = X[~X.SubType.str.contains("Heated|heat|Shock|Weather|Chondrule|Inclusion| or |Mixture|Unusual CI$", case=False, na=False) | X.SampleName.str.contains("Tagish", na=False)]
X = X[~X.SampleName.str.contains("heated|°C|deg|irradiat|laser|leach|residue|separate|magnetic|spot|slab|chondrule|inclusion|matrix|clast", case=False, na=False)]

classes = [  # (class label, regex on SubType or SampleName)
    ("CI", r"^CI\b|CI1"), ("CM", r"^CM"), ("Tagish_Lake_C2ung", r"Tagish"), ("CR", r"^CR"), ("CV", r"^CV"),
    ("CO", r"^CO"), ("CK", r"^CK"), ("H", r"^H\s?[3-6]"), ("L", r"^L\s?[3-6]"), ("LL", r"^LL"),
    ("Eucrite", r"Eucrite"), ("Howardite", r"Howardite"), ("Diogenite", r"Diogenite"), ("Ureilite", r"Ureilite"),
    ("Enstatite_chondrite_aubrite", r"^E[HL]|Aubrite|Enstatite"), ("Iron_mesosiderite_pallasite", r"Iron|Mesosiderite|Pallasite"),
]
grid = np.round(np.arange(0.30, 5.5001, 0.005), 4)
sel_rows, long_rows = [], []


def read_spec(spec_id, pi, sid):
    path = f"data/{pi.lower()}/{sid[:2].lower()}/{spec_id.lower()}.txt"
    if path not in names: return None
    t = z.read(path).decode("latin-1").splitlines()[2:]
    a = []
    for l in t:
        p = l.split()
        try: a.append([float(p[0]), float(p[1])])
        except Exception: pass
    a = np.array(a)
    return a if len(a) > 10 else None


names = set(z.namelist())
for cl, rx in classes:
    m = X[X.SubType.str.contains(rx, na=False, regex=True) | X.SampleName.str.contains(rx, na=False, regex=True)]
    if cl == "CO": m = m[~m.SubType.str.contains("CO2", na=False)]
    m = m.sort_values(["Particulate", "Stop"], ascending=[False, False]).drop_duplicates("SampleID").head(12)
    arr = []
    for _, r in m.iterrows():
        a = read_spec(r.SpectrumID, r.PI, r.SampleID)
        if a is None: continue
        w, v = a[:, 0], a[:, 1]
        if w.max() > 100: w = w / 1000.0  # nm safety
        o = np.argsort(w); w, v = w[o], v[o]
        g = np.interp(grid, w, v, left=np.nan, right=np.nan)
        n055 = np.nanmedian(g[(grid >= 0.54) & (grid <= 0.56)])
        if not np.isfinite(n055) or n055 <= 0: continue
        arr.append(g / n055)
        sel_rows.append(dict(meteorite_class=cl, SpectrumID=r.SpectrumID, SampleID=r.SampleID, SampleName=r.SampleName,
                             SubType=r.SubType, SpecCode=r.SpecCode, start_nm=r.Start, stop_nm=r.Stop,
                             particulate=r.Particulate, maxsize_um=r.MaxSize, PI=r.PI, refl_055=n055))
    if len(arr) >= 1:
        med = np.nanmedian(np.array(arr), axis=0)
        ok = np.isfinite(med)
        for w, v in zip(grid[ok], med[ok]):
            long_rows.append(dict(template_id=f"relab_{cl}", family="meteorite_class_median", label=f"{cl} meteorites (n={len(arr)})",
                                  wavelength_um=w, value=v, note="RELAB VNIR+FTIR spliced spectra, each normalized to 1 at 0.55 um, median; lab spectra include adsorbed terrestrial water near 3 um"))
    print(cl, "spectra used:", len(arr))
pd.DataFrame(sel_rows).to_csv(f"{O}/relab_meteorite_selected_spectra.csv", index=False)
pd.DataFrame(long_rows).to_csv(f"{O}/relab_selected_long.csv", index=False)
print("selected", len(sel_rows))
