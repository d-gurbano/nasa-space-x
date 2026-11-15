"""site/detectives/rounds.json: a 'spot the asteroid' game.

Round types (truth): known = a catalogued asteroid in a real SPHEREx frame (answer key);
planted = a fake ePSF source we added to an empty real frame (revealed after the answer);
empty = a real frame with nothing at the marked spot; real = a Rewind FOUND object (day stack).
Each image is cut off-centre so the answer is not always in the middle."""
from __future__ import annotations

import os
import shutil

import numpy as np
import pandas as pd

from . import config as C
from . import images as IM
from . import phot as PH
from .pilot import R
from .realfake import LAB
from .site import dump

N_KNOWN, N_PLANTED, N_EMPTY = 8, 6, 6


def _cut(st, ra, dec, rng, image=None):
    de, dn = rng.uniform(-30, 30, 2)  # arcsec offset of the image centre from the source
    rc, dc = R.offset_radec(ra, dec, -de, -dn)
    a = IM.north_up(st, rc, dc, image=image)
    return a, IM.xy_in_png(de, dn)


def _save(a, path):
    v = a[np.isfinite(a)]
    s = 1.4826 * np.median(np.abs(v - np.median(v))) if v.size else 1
    IM.save(a, path, -3 * s, 12 * s)


def write_rounds(found_slugs=(), seed=8):
    rng = np.random.default_rng(seed)
    out = os.path.join(C.SITE, "detectives")
    os.makedirs(out, exist_ok=True)
    lab = pd.read_parquet(os.path.join(LAB, "labels.parquet"))
    lab = lab[lab.status == "ok"]
    pos = lab[(lab.kind == "positive") & (lab.snr.between(6, 40))]
    neg = lab[(lab.kind == "negative") & (lab.snr.abs() < 2)]
    rounds = []
    for k, r in enumerate(pos.sample(min(N_KNOWN, len(pos)), random_state=seed).itertuples()):
        st = R.load_stamp_fits(os.path.join(LAB, r.file))
        a, xy = _cut(st, r.ra, r.dec, rng)
        _save(a, os.path.join(out, f"known_{k}.png"))
        rounds.append(dict(truth="known", images=[f"known_{k}.png"], answer_xy=xy,
                           explain=f"This is the known asteroid {r.name}, caught by SPHEREx (S/N {r.snr:.0f}, about V {r.V_pred:.1f})."))
    ns = neg.sample(min(N_PLANTED + N_EMPTY, len(neg)), random_state=seed)
    for k, r in enumerate(ns.itertuples()):
        st = R.load_stamp_fits(os.path.join(LAB, r.file))
        if k < N_PLANTED:
            noise = np.nanmedian(np.sqrt(st.variance)) * R.pixel_sr(st) * 1e12
            f_in = noise * rng.uniform(4, 9)  # uJy; roughly S/N 8-20 in one frame
            img = PH.plant(st, r.ra, r.dec, f_in)
            a, xy = _cut(st, r.ra, r.dec, rng, image=img)
            name = f"planted_{k}.png"
            _save(a, os.path.join(out, name))
            rounds.append(dict(truth="planted", images=[name], answer_xy=xy,
                               explain=f"A trick: we planted a fake star-like dot ({f_in:.0f} uJy) into a real, empty SPHEREx photo. "
                                       "Rewind plants fakes like this to measure how faint it can see."))
        else:
            a, _ = _cut(st, r.ra, r.dec, rng)
            name = f"empty_{k}.png"
            _save(a, os.path.join(out, name))
            rounds.append(dict(truth="empty", images=[name], answer_xy=None,
                               explain="Nothing moving here: just stars, galaxies and noise. Saying 'nothing' is the right answer."))
    for slug in found_slugs:
        src = os.path.join(C.SITE, "objects", slug, "stack.png")
        if os.path.exists(src):
            name = f"real_{slug}.png"
            shutil.copy(src, os.path.join(out, name))
            rounds.append(dict(truth="real", images=[name], answer_xy=IM.xy_in_png(0, 0),
                               explain=f"A real Rewind find: {slug}, stacked along its predicted path."))
    order = rng.permutation(len(rounds))
    rounds = [dict(id=f"r{i + 1:02d}", **rounds[j]) for i, j in enumerate(order)]
    dump(dict(schema="rewind-detectives-v1", sample=False, rounds=rounds,
              note="images: north up, east left, 1.5 arcsec per pixel before 4x nearest-neighbour upscaling"),
         os.path.join(out, "rounds.json"))
    return rounds
