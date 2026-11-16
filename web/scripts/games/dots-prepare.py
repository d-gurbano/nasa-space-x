"""Connect the dots: build six rounds from real data.

Asteroid positions: known_objects_in_frames.parquet (the answer key), at three real SPHEREx frames.
Star positions: the brightest fixed sources in the middle SPHEREx frame (public L2 image on AWS S3,\nread by byte range with the engine reader), known asteroids excluded.
Noise dots are added later in the browser and labelled as simulated.

Run: .venv/bin/python web/scripts/games/dots-prepare.py
"""
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, "/Users/rahmanbazarov/Data/programming/SpaceApps2026-Rewind-c2-engine")

import numpy as np
import pandas as pd

ROOT = Path("/Users/rahmanbazarov/Data/programming/SpaceApps2026-Rewind/data/07-answer-keys")
OUT = Path(__file__).resolve().parents[2] / "public/data/games/dots/rounds.json"

d = pd.read_parquet(ROOT / "answer_key/known_objects_in_frames.parquet",
                    columns=["key", "name", "ra_deg", "dec_deg", "MJD-AVG", "field", "on_detector", "V_pred", "position_quality"])
d = d[d.on_detector & (d.position_quality != "uncertain")].rename(columns={"MJD-AVG": "mjd"})


def stars(key, ra0, dec0, half_arcsec, n, avoid):
    """Brightest fixed sources in the real SPHEREx frame, read by byte range from the public S3 copy."""
    from rewind_engine.s3read import read_stamp
    st = read_stamp("ibe/data/spherex/" + key, ra0, dec0, half=int(half_arcsec / 6.15) + 2)
    img = np.where((st.flags & (1 << 9)) == 0, st.image, np.nan)  # bit 9 marks pixels off the detector
    med = np.nanmedian(img)
    sig = 1.4826 * np.nanmedian(np.abs(img - med))
    a = np.nan_to_num(img - med, nan=-1e9)
    pk = np.zeros_like(a, dtype=bool)
    pk[1:-1, 1:-1] = a[1:-1, 1:-1] > 10 * sig
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dx or dy:
                pk[1:-1, 1:-1] &= a[1:-1, 1:-1] >= a[1 + dy:a.shape[0] - 1 + dy, 1 + dx:a.shape[1] - 1 + dx]
    yy, xx = np.nonzero(pk)
    order = np.argsort(-a[yy, xx])
    ra, dec = st.wcs.all_pix2world(xx[order], yy[order], 0)
    x, y = xy(ra, dec, ra0, dec0)
    out = []
    for i in range(len(x)):
        if abs(x[i]) > half_arcsec or abs(y[i]) > half_arcsec:
            continue
        if any(math.hypot(x[i] - ax, y[i] - ay) < 25 for ax, ay in avoid):
            continue  # a known asteroid, not a star
        out.append([round(float(x[i]), 1), round(float(y[i]), 1), round(float(a[yy[order[i]], xx[order[i]]] / sig), 1)])
        if len(out) >= n:
            break
    return out


def xy(ra, dec, ra0, dec0):
    dra = (np.asarray(ra) - ra0 + 180) % 360 - 180
    return dra * math.cos(math.radians(dec0)) * 3600, (np.asarray(dec) - dec0) * 3600


def build(field, want_movers, motion_frac, n_stars, min_gap=0.04, skip=0):
    """Find three frames and a patch holding exactly `want_movers` asteroids seen at all three."""
    f = d[d.field == field]
    found = 0
    for name, g in f.groupby("name"):
        g = g.sort_values("mjd").drop_duplicates("key")
        if len(g) < 3:
            continue
        # three frames spread over hours to a few days
        t = g.mjd.values
        for i in range(len(g) - 2):
            j, k = i + 1, i + 2
            if t[j] - t[i] < min_gap or t[k] - t[j] < min_gap or t[k] - t[i] > 3:
                continue
            sel = g.iloc[[i, j, k]]
            keys = list(sel.key)
            ra0, dec0 = float(sel.ra_deg.mean()), float(sel.dec_deg.mean())
            x, y = xy(sel.ra_deg, sel.dec_deg, ra0, dec0)
            span = math.hypot(x[2] - x[0], y[2] - y[0])
            half = span / motion_frac / 2
            if span < 40 or half > 1400:
                continue
            sub = f[f.key.isin(keys)].copy()
            sub["x"], sub["y"] = xy(sub.ra_deg, sub.dec_deg, ra0, dec0)
            sub = sub[(sub.x.abs() < half) & (sub.y.abs() < half)]
            full = [n for n, h in sub.groupby("name") if set(h.key) >= set(keys)]
            if len(full) != want_movers:
                continue
            found += 1
            if found <= skip:
                continue
            movers, partial = [], []
            for n, h in sub.groupby("name"):
                h = h.drop_duplicates("key").set_index("key")
                if n in full:
                    movers.append({"name": n, "v": round(float(h.V_pred.min()), 1),
                                   "pts": [[round(float(h.loc[kk].x), 1), round(float(h.loc[kk].y), 1)] for kk in keys]})
                else:
                    for kk in keys:
                        if kk in h.index:
                            partial.append({"t": keys.index(kk), "x": round(float(h.loc[kk].x), 1), "y": round(float(h.loc[kk].y), 1)})
            avoid = [(float(r.x), float(r.y)) for r in sub[sub.key == keys[1]].itertuples()]
            star_list = stars(keys[1], ra0, dec0, half, n_stars, avoid)
            return {
                "field": field, "ra": round(ra0, 4), "dec": round(dec0, 4), "half_arcsec": round(half, 1),
                "mjd": [round(float(v), 4) for v in sel.mjd], "iso": [pd.Timestamp("1858-11-17") + pd.Timedelta(days=float(v)) for v in sel.mjd],
                "frames": keys, "movers": movers, "partial": partial,
                "stars": star_list,
            }
    raise SystemExit(f"no patch for {field} {want_movers} {motion_frac}")


PLAN = [  # field, movers, how much of the patch the motion spans, stars
    ("NEP", 1, 0.55, 8),
    ("ecl_L060", 1, 0.45, 14),
    ("ecl_L180", 1, 0.3, 20),
    ("ecl_L330", 1, 0.16, 26),
    ("ecl_L000", 2, 0.3, 26),
    ("ecl_L225", 2, 0.16, 32),
]
rounds = []
for p in PLAN:
    r = build(*p)
    r["iso"] = [t.strftime("%Y-%m-%d %H:%M") for t in r["iso"]]
    print(p, r["movers"][0]["name"], len(r["partial"]), len(r["stars"]), r["half_arcsec"], file=sys.stderr)
    rounds.append(r)
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps({
    "source": "Asteroid positions: Rewind answer key (known_objects_in_frames.parquet, JPL orbits at real SPHEREx frame times). Stars: brightest fixed sources in the middle real SPHEREx frame of each round.",
    "rounds": rounds}, separators=(",", ":")))
print(OUT, OUT.stat().st_size, file=sys.stderr)
