"""Real or junk?: build the stamp pool for the game.

Artifacts: the 39 labelled real SPHEREx artifact stamps (07-answer-keys/junk), a clear subset.
Asteroids: single-frame 41 x 41 cutouts of real known asteroids from the real-or-fake CNN's held-out
test split (split by sky region, seed 0), re-cut from the public SPHEREx L2 images on S3 with the
engine's reader. Each asteroid stamp keeps the CNN's own score for that sample (p_cnn).
All stamps get the same stretch, so the style gives nothing away.

Run: .venv/bin/python web/scripts/games/junk-prep.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from astropy.io import fits
from PIL import Image

ROOT = Path('/Users/rahmanbazarov/Data/programming/SpaceApps2026-Rewind')
D = ROOT / 'data'
JUNK = D / '07-answer-keys/junk'
AI = D / 'kaggle/rewind-c2-ai'
OUT = Path(__file__).resolve().parents[2] / 'public/data/games/junk'
SCALE = 4

# label -> game category
CAT = {
    'satellite_streak': 'trail', 'satellite_trail_borlaff2026': 'trail',
    'transient_cosmic_ray': 'cosmic', 'snowball': 'cosmic',
    'ghost': 'ghost', 'ghost_ext': 'ghost', 'halo': 'ghost',
    'persistence': 'detector', 'bloom': 'detector', 'crosstalk': 'detector',
}
LABEL = {
    'satellite_streak': 'satellite streak (pipeline flag)',
    'satellite_trail_borlaff2026': 'satellite trail (Borlaff et al. 2026 catalogue)',
    'transient_cosmic_ray': 'cosmic ray hit (pipeline flag)',
    'snowball': 'snowball, a large cosmic ray hit (pipeline flag)',
    'ghost': 'optical ghost (pipeline flag)',
    'ghost_ext': 'extended optical ghost (pipeline flag)',
    'halo': 'halo around a bright star (pipeline flag)',
    'persistence': 'persistence, an after-image (pipeline flag)',
    'bloom': 'bloom from a saturated star (pipeline flag)',
    'crosstalk': 'electronic crosstalk (pipeline flag)',
}
# row numbers in artifact_stamps_labels.csv that show the artifact clearly at 41 x 41 px.
# Left out: a few faint or noisy stamps, and the one satellite_halo stamp (8 flagged pixels).
KEEP = [0, 2, 4, 5, 8, 9, 10, 11, 13, 14, 15, 16, 19, 20, 21, 23, 24, 25, 26, 27, 28, 29, 30,
        31, 33, 34, 36, 37, 38]


def png(a: np.ndarray, name: str) -> str:
    a = np.asarray(a, dtype=float)
    a = np.nan_to_num(a, nan=np.nanmedian(a))
    lo, hi = np.percentile(a, [1, 99.7])
    x = np.clip((a - lo) / (hi - lo + 1e-9), 0, 1)
    x = np.arcsinh(8 * x) / np.arcsinh(8)
    im = Image.fromarray((x * 255).astype(np.uint8)[::-1])  # FITS row 0 is the bottom
    im = im.resize((a.shape[1] * SCALE, a.shape[0] * SCALE), Image.NEAREST)
    im.save(OUT / name, optimize=True)
    return name


def artifacts():
    t = pd.read_csv(JUNK / 'artifact_stamps_labels.csv')
    out = []
    for i in KEEP:
        r = t.iloc[i]
        a = fits.getdata(JUNK / r.file, 0)
        out.append(dict(id=f'a{i:02d}', img=png(a, f'a{i:02d}.png'), cat=CAT[r.label], label=LABEL[r.label],
                        obsid=r.OBSID, det=f'D{int(r.det)}', ai=None))
    return out


def asteroids(n=10):
    sys.path.insert(0, str(ROOT.parent / 'SpaceApps2026-Rewind-c2-engine'))
    from rewind_engine import s3read  # noqa: E402

    s = pd.read_csv(AI / 'realfake_samples.csv')
    t = pd.read_csv(AI / 'realfake_test_by_sky_region_seed0.csv')
    m = t.merge(s, left_on='idx', right_index=True, suffixes=('', '_s'))
    m = m[m.source == 'positive'].sort_values('snr', ascending=False)
    k = pd.read_parquet(D / '07-answer-keys/answer_key/known_objects_in_frames.parquet',
                        columns=['key', 'name', 'ra_deg', 'dec_deg', 'OBSID', 'V_pred'])
    out, seen = [], set()
    for _, r in m.iterrows():
        if len(out) >= n:
            break
        c = k[k.OBSID == r.group]
        d = np.hypot((c.ra_deg - r.ra) * np.cos(np.radians(r.dec)), c.dec_deg - r.dec) * 3600
        if not len(c) or d.min() > 6:
            continue
        hit = c.iloc[int(np.argmin(d.values))]
        if hit['name'] in seen:
            continue
        try:
            st = s3read.read_stamp('ibe/data/spherex/' + hit.key, r.ra, r.dec, half=20)
        except Exception as e:  # noqa
            print('skip', hit['name'], e)
            continue
        seen.add(hit['name'])
        i = int(r.idx)
        out.append(dict(id=f's{i}', img=png(st.image, f's{i}.png'), cat='asteroid',
                        label=f'known asteroid {hit["name"]}', obsid=r.group, det='D' + hit.key.split('/')[-2],
                        snr=round(float(r.snr), 1), ai=round(float(r.p_cnn), 3)))
        print('ok', hit['name'], r.snr, r.p_cnn)
    return out


if __name__ == '__main__':
    OUT.mkdir(parents=True, exist_ok=True)
    pool = artifacts() + asteroids()
    (OUT / 'rounds.json').write_text(json.dumps(dict(
        ai_accuracy=0.974, ai_test_n=274,
        source='Artifacts: the 39 labelled SPHEREx artifact stamps in our answer key (pipeline flags, and satellite trails '
               'from Borlaff et al. 2026). Asteroids: known asteroids in public SPHEREx images (IRSA, AWS), '
               'from our real-or-fake test set.',
        pool=pool), indent=1))
    print(len(pool), 'stamps')
