"""Comet or asteroid?: build web/public/data/games/comet/ from the real site data.

For each object in the pool it copies the SPHEREx stack (stack.png, 324 px) and writes
rounds.json with the real kind, the measured spectrum points (objects/<slug>/object.json,
composition.points) and three flags the game uses to word its feedback:

  bump  (comets only; null for asteroids, whose raised long end the game reads as heat)
        'co2'   the point whose bin holds 4.26 um sits more than 2 sigma above the point
                before it, AND that earlier point (3.8 um) is not itself raised (so the rise
                is not a broad warm-up that starts before 4 um). Conservative on purpose.
        'raised' the long end is raised, but the test above fails (noisy or broad rise).
        'faint' nothing to claim: no long-end point, or the rise is under 2 sigma.
  warm  the 4.6 um point is above 3 and more than 3 sigma above 1 (plain reflected sunlight).
  coma  a fuzzy glow is clear in stack.png. Judged by eye, set by hand below, only where obvious.

Usage: .venv/bin/python web/scripts/games/comet-rounds.py [SRC_DATA_DIR]
"""
import json
import math
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
WEB = HERE.parents[2]
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else WEB / 'public' / 'data'
OUT = WEB / 'public' / 'data' / 'games' / 'comet'

# our finds, plus two famous objects SPHEREx saw, plus two strong hints (asteroids) to balance the mix
COMETS = ['c2025l2', 'c2026s1', 'p2026v1', 'p2025y2', 'c2025w2', '3i-atlas']
ASTEROIDS = ['2025yh5', '2025st20', '2025yj6', 'eros', '2025vp', '2025vw1']
# clear coma in the stack, by eye (3I/ATLAS shows a wide glow around a bright core)
COMA = {'3i-atlas'}
CO2_UM = 4.26


def bin_edges(ums):
    """Each point stands for a band of wavelengths; the edges are the geometric midpoints."""
    lo = [ums[0] ** 2 / math.sqrt(ums[0] * ums[1])] + [math.sqrt(a * b) for a, b in zip(ums, ums[1:])]
    hi = lo[1:] + [ums[-1] ** 2 / math.sqrt(ums[-2] * ums[-1])]
    return list(zip(lo, hi))


def flags(pts):
    ums = [p['um'] for p in pts]
    last = pts[-1] if pts else None
    warm = bool(last and last['um'] > 4.2 and last['value'] > 3 and (last['value'] - 1) > 3 * last['err'])
    if len(pts) < 2:
        return 'faint', warm, None
    edges = bin_edges(ums)
    i = next((k for k, (a, b) in enumerate(edges) if a <= CO2_UM < b), None)
    if i is None or i == 0:
        return 'faint', warm, None
    p, q = pts[i], pts[i - 1]
    sig = (p['value'] - q['value']) / math.hypot(p['err'], q['err'])
    span = [round(edges[i][0], 2), round(edges[i][1], 2)]
    # the point before must be the 3.8 um one (not a gap back to 2 or 3 um), and not raised itself
    prev_flat = 3.5 < q['um'] < 4 and q['value'] < 1 + 2 * q['err']
    if sig > 2 and prev_flat:
        return 'co2', warm, span
    if sig > 2 or warm:
        return 'raised', warm, span
    return 'faint', warm, span


def main():
    index = {o['slug']: o for o in json.load(open(SRC / 'index.json'))['objects']}
    OUT.mkdir(parents=True, exist_ok=True)
    rounds = []
    for truth, slugs in (('comet', COMETS), ('asteroid', ASTEROIDS)):
        for s in slugs:
            o = json.load(open(SRC / 'objects' / s / 'object.json'))
            pts = [{'um': p['um'], 'value': p['value'], 'err': p['err']} for p in (o.get('composition') or {}).get('points') or []]
            bump, warm, span = flags(pts)
            if truth == 'asteroid':
                # no gas expected; a raised long end on an asteroid is read as heat (warm) in the game
                bump = None
            st = o['spherex']['stack']
            shutil.copyfile(SRC / 'objects' / s / 'stack.png', OUT / f'{s}.png')
            rounds.append({
                'slug': s, 'name': o['name'], 'truth': truth, 'class': o['facts'].get('class'),
                'verdict': index[s]['verdict'], 'snr': st.get('snr'), 'n_frames': st.get('n_frames'),
                'img': f'{s}.png', 'points': pts, 'bump': bump, 'bump_band': span, 'warm': warm, 'coma': s in COMA,
            })
            print(f"{s:10} {truth:8} {str(bump):6} warm={warm} band={span}")
    json.dump({'source': 'objects/<slug>/object.json (composition.points, spherex.stack) and stack.png', 'rounds': rounds},
              open(OUT / 'rounds.json', 'w'), indent=1)


if __name__ == '__main__':
    main()
