"""A6: quicklook figure of native templates vs SPHEREx-convolved channels (visual check of to_spherex.py)."""
import pandas as pd, numpy as np, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
O = "data/06-composition/derived"
ch = pd.read_csv(f"{O}/spherex_channels.csv"); t = pd.read_csv(f"{O}/spherex_templates_cent.csv").set_index("template_id")
nat = pd.read_csv(f"{O}/templates_native_long.csv")
sets = [["busdemeo_S", "busdemeo_C", "busdemeo_V", "busdemeo_D"], ["stitched_C_0.45-5um", "stitched_S_0.45-5um", "stitched_X_0.45-5um"],
        ["usgs_Olivine_Fo89", "usgs_Enstatite_orthopyroxene", "usgs_Antigorite_serpentine_hydrated", "usgs_H2O_ice_77K"],
        ["comet_H2O_nu3_fluor", "comet_CH_organics", "comet_CO2_nu3", "comet_CO_1-0"]]
fig, ax = plt.subplots(4, 1, figsize=(10, 13))
for a, s in zip(ax, sets):
    for i, tid in enumerate(s):
        n = nat[nat.template_id == tid]; n = n[(n.wavelength_um > 0.7) & (n.wavelength_um < 5.1)]
        off = 0 if s[0].startswith("comet") else 0
        l, = a.plot(n.wavelength_um, n.value + off, lw=0.7, alpha=0.6)
        a.plot(ch.center_um, t.loc[tid].values + off, "o", ms=3, color=l.get_color(), label=tid)
    a.legend(fontsize=7); a.set_xlim(0.7, 5.05)
ax[-1].set_xlabel("wavelength (um); dots = 102 SPHEREx channels (MiddlePixel response)")
plt.tight_layout(); plt.savefig(f"{O}/quicklook_templates.png", dpi=110)
