"""to_spherex.py - convolve any spectrum (wavelength in micron) to the 102 SPHEREx channels.

Channel definitions: IRSA "SPHEREx Spectral Calibrations" package SPHERExSpectralFiles_202607.tar
(lab-measured normalized spectral response functions, 6 bands x 17 channels = 102 channels).
Extracted to data/06-composition/ext/spherex_bandpass/.

  response="cent"   -> MiddlePixel curves (one pixel at the spectral center of the channel; IRSA says this
                       is "generally more representative of an individual measurement")
  response="allpix" -> MeanAllPixel curves (average of all pixels in the channel; better for averaged data)

Note from IRSA: in a real SPHEREx image each pixel has its own central wavelength (linear variable filter),
so these 102 curves are NOMINAL channels. For a measured object, the per-pixel wavelength from the image's
WCS-WAVE table should be used; this tool is for building comparable templates.

Convolution (per channel k, response T_k):
  flux mode        F_k = int F(l) T_k(l) dl / int T_k(l) dl
  reflectance mode R_k = int R(l) S(l) T_k(l) dl / int S(l) T_k(l) dl   (S = solar spectrum weighting, optional)
Channels where the input covers < min_cover (default 0.95) of the response area return NaN.

usage (CLI):
  python code/A6/to_spherex.py input.csv --wcol wavelength_um --vcol reflectance [--response cent|allpix]
         [--solar] [--out out.csv]
  python code/A6/to_spherex.py --channels      # print the 102-channel table
"""
import os, glob, argparse
import numpy as np
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
BP = os.path.join(ROOT, "data/06-composition/ext/spherex_bandpass")
SOLAR = os.path.join(ROOT, "data/06-composition/derived/solar_reference_0.3-5.5um.csv")
_cache = {}


def channel_table():
    """102 rows: band, ch (1-17), chan_id (1-102), center/width (cent and allpix), in micron. VERIFIED (IRSA)."""
    rows = []
    for b in range(1, 7):
        f = glob.glob(f"{BP}/FidSpecSummary/SubChannel17/Band{b}/FidSpecSummary_Band{b}_SpecCh17.csv")[0]
        d = pd.read_csv(f)
        for _, r in d.iterrows():
            rows.append(dict(band=b, ch=int(r.SpecCh), chan_id=(b - 1) * 17 + int(r.SpecCh),
                             center_um=r.BandCenter_um, width_um=r.BandWidth_um,
                             center_allpix_um=r.BandCenter_Allpix_um, width_allpix_um=r.BandWidth_Allpix_um))
    return pd.DataFrame(rows)


def responses(response="cent"):
    """list of 102 (wavelength_um array, transmission array) with negatives clipped to 0."""
    key = ("resp", response)
    if key in _cache:
        return _cache[key]
    sub, suf = ("MiddlePixel", "Cent") if response == "cent" else ("MeanAllPixel", "Allpix")
    out = []
    for b in range(1, 7):
        for c in range(1, 18):
            fs = glob.glob(f"{BP}/{sub}/SubChannel17/Band{b}/FiducialSpec_Band{b}_SubCh{c:02d}_17_*.csv")
            if not fs:
                raise FileNotFoundError(f"missing response Band{b} ch{c} ({sub})")
            d = pd.read_csv(fs[0])
            w = d.iloc[:, 0].to_numpy(float); t = np.clip(d.iloc[:, 1].to_numpy(float), 0, None)
            o = np.argsort(w)
            out.append((w[o], t[o]))
    _cache[key] = out
    return out


def solar(wl):
    if "sun" not in _cache:
        s = pd.read_csv(SOLAR)
        _cache["sun"] = (s.wavelength_um.to_numpy(), s.flux_flam.to_numpy())
    w, f = _cache["sun"]
    return np.interp(wl, w, f, left=np.nan, right=np.nan)


def convolve(wl_um, val, response="cent", solar_weight=False, min_cover=0.95):
    """Return np.array(102) of channel values (NaN where input does not cover the channel)."""
    wl_um = np.asarray(wl_um, float); val = np.asarray(val, float)
    good = np.isfinite(wl_um) & np.isfinite(val)
    wl_um, val = wl_um[good], val[good]
    o = np.argsort(wl_um); wl_um, val = wl_um[o], val[o]
    res = np.full(102, np.nan)
    if len(wl_um) < 2:
        return res
    for k, (w, t) in enumerate(responses(response)):
        area = np.trapezoid(t, w)
        inside = (w >= wl_um[0]) & (w <= wl_um[-1])
        if area <= 0 or np.trapezoid(t * inside, w) / area < min_cover:
            continue
        # also require input sampling inside the channel (no huge gaps): at least 1 sample within FWHM-ish range
        v = np.interp(w, wl_um, val)
        wt = t * inside
        if solar_weight:
            s = solar(w); wt = wt * np.nan_to_num(s)
        den = np.trapezoid(wt, w)
        if den > 0:
            res[k] = np.trapezoid(v * wt, w) / den
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input", nargs="?")
    ap.add_argument("--wcol", default=None); ap.add_argument("--vcol", default=None)
    ap.add_argument("--response", default="cent", choices=["cent", "allpix"])
    ap.add_argument("--solar", action="store_true"); ap.add_argument("--out")
    ap.add_argument("--channels", action="store_true")
    a = ap.parse_args()
    ch = channel_table()
    if a.channels or not a.input:
        print(ch.to_string(index=False)); return
    d = pd.read_csv(a.input, sep=None, engine="python")
    wcol = a.wcol or d.columns[0]; vcol = a.vcol or d.columns[1]
    ch["value"] = convolve(d[wcol], d[vcol], a.response, a.solar)
    if a.out:
        ch.to_csv(a.out, index=False)
    else:
        print(ch[["chan_id", "band", "ch", "center_um", "value"]].to_string(index=False))


if __name__ == "__main__":
    main()
