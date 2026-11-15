"""A6: solar reference spectrum 0.3-5.5 um for reflectance work.
CALSPEC (STScI, US) sun_reference_stis_002.fits (measured composite, to ~2.7 um) joined with
sun_mod_001.fits (Kurucz model) beyond 2.6 um, model scaled to match the measured spectrum in 2.0-2.6 um."""
import numpy as np, pandas as pd
from astropy.io import fits
D = "data/06-composition"
a = fits.getdata(f"{D}/raw/solar/sun_reference_stis_002.fits"); m = fits.getdata(f"{D}/raw/solar/sun_mod_001.fits")
wa, fa = a["WAVELENGTH"] / 1e4, a["FLUX"]; wm, fm = m["WAVELENGTH"] / 1e4, m["FLUX"]
sel = (wa > 2.0) & (wa < 2.6)
scale = np.median(fa[sel] / np.interp(wa[sel], wm, fm))
grid = np.arange(0.30, 5.5001, 0.001)
fm_s = np.interp(grid, wm, fm) * scale
# smooth model to ~R 1000 to match SPHEREx use (R 35-130): box over 0.001 um grid is fine
out = np.where(grid <= 2.6, np.interp(grid, wa, fa), fm_s)
pd.DataFrame({"wavelength_um": grid, "flux_flam": out}).to_csv(f"{D}/derived/solar_reference_0.3-5.5um.csv", index=False)
print("model scale (COMPUTED):", scale, "range", wa.min(), wa.max(), wm.min(), wm.max())
