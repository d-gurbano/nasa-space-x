"""Robust stack statistics for a pilot run vs its null paths (same frames, same method).
usage: python code/A0/robust_summary.py C2026S1"""
import os, sys, json
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(__file__))
import rewind as R
OUT = os.path.join(os.path.dirname(__file__), "..", "..", "data", "00-pilot")


def summarize(tag):
    ph = pd.read_csv(os.path.join(OUT, "tables", f"{tag}_photometry.csv"))
    nu = pd.read_csv(os.path.join(OUT, "tables", f"{tag}_nulls.csv"))
    ok = ph[ph.status == "ok"]
    res = {}
    for g, dets in [("all", None), ("D1-D3", ["D1", "D2", "D3"]), ("D4-D6", ["D4", "D5", "D6"])]:
        sub = ok if dets is None else ok[ok.det.isin(dets)]
        out = {}
        for name, fn in [("ivw", R.weighted_stack), ("clipped", R.robust_stack)]:
            F, E, S, n = fn(sub.flux_uJy, sub.err_uJy)
            ns = []
            for j in sorted(nu.null.unique()):
                q = nu[(nu.null == j) & nu.file.isin(sub.file) & (nu.status == "ok")]
                ns.append(fn(q.flux_uJy, q.err_uJy)[2])
            ns = np.array(ns)
            out[name] = dict(n=n, flux_uJy=round(F, 2), err_uJy=round(E, 2), snr=round(S, 2),
                             ab=round(-2.5 * np.log10(F * 1e-6 / 3631), 2) if F > 0 else None,
                             null_mean=round(np.nanmean(ns), 2), null_std=round(np.nanstd(ns), 2),
                             z_vs_nulls=round((S - np.nanmean(ns)) / np.nanstd(ns), 2),
                             n_null_ge=int(np.sum(ns >= S)), n_null=len(ns))
        # per-frame median S/N (sign test)
        out["median_frame_snr"] = round(float(np.median(sub.flux_uJy / sub.err_uJy)), 3)
        out["frac_positive"] = round(float(np.mean(sub.flux_uJy > 0)), 3)
        res[g] = out
    json.dump(res, open(os.path.join(OUT, "tables", f"{tag}_robust_summary.json"), "w"), indent=1)
    print(json.dumps(res, indent=1))
    return res


if __name__ == "__main__":
    summarize(sys.argv[1])
