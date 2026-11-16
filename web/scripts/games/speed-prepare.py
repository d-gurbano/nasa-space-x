"""Star speedometer: build web/public/data/games/speed/rounds.json from our measured star motion.

Each round pairs two SPHEREx season stacks of one star (the PNGs in public/data/stars/<slug>/seasons)
with the positions we measured in those passes (data/05-test-targets/results/<target>_spherex_motion_per_pass.csv).
A pass position in the PNG = the predicted pixel at the pass time (interpolated from the manifest's
per-frame pred_xy) plus our measured offset from the prediction. PNG scale 0.1875 arcsec per px,
north up, east left.

Run: .venv/bin/python web/scripts/games/speed-prepare.py
"""
import csv
import json
import math
from pathlib import Path

WEB = Path(__file__).resolve().parents[2]
RES = Path('/Users/rahmanbazarov/Data/programming/SpaceApps2026-Rewind/data/05-test-targets/results')
OUT = WEB / 'public/data/games/speed/rounds.json'
SCALE = 0.1875  # arcsec per PNG px

# (site slug, results name, pass a, pass b); season i matches pass i for these stars
ROUNDS = [
    ('barnard', 'barnard', 0, 1),
    ('epsindib', 'eps_indi_b', 0, 2),
    ('rwaur', 'rw_aur', 0, 2),
    ('barnard', 'barnard', 0, 2),
    ('epsindib', 'eps_indi_b', 1, 3),
]


def pred_xy(frames, mjd):
    """Linear interpolation of the predicted PNG pixel between the two frames nearest in time."""
    fs = sorted(frames, key=lambda f: abs(f['mjd'] - mjd))[:2]
    (a, b) = sorted(fs, key=lambda f: f['mjd'])
    t = 0.0 if b['mjd'] == a['mjd'] else (mjd - a['mjd']) / (b['mjd'] - a['mjd'])
    return [a['pred_xy'][i] + t * (b['pred_xy'][i] - a['pred_xy'][i]) for i in (0, 1)]


def main():
    rounds = []
    for slug, name, ia, ib in ROUNDS:
        man = json.loads((WEB / f'public/data/stars/{slug}/manifest.json').read_text())
        passes = {int(r['pass_']): r for r in csv.DictReader(open(RES / f'{name}_spherex_motion_per_pass.csv'))}
        summ = json.loads((RES / f'{name}_summary.json').read_text())
        ends = []
        for i in (ia, ib):
            p = passes[i]
            mjd = float(p['mjd'])
            px = pred_xy(man['frames'], mjd)
            re, rn = float(p['resid_east']), float(p['resid_north'])
            ends.append({
                'date': p['date'],
                'mjd': round(mjd, 3),
                'season': man['seasons'][i]['png'],
                'n_frames': man['seasons'][i]['n_frames'],
                'xy': [round(px[0] - re / SCALE, 2), round(px[1] - rn / SCALE, 2)],
                'east': float(p['meas_east_from_ref']),
                'north': float(p['meas_north_from_ref']),
                'err': round(math.hypot(float(p['err_east']), float(p['err_north'])), 3),
            })
        a, b = ends
        de, dn = b['east'] - a['east'], b['north'] - a['north']
        rounds.append({
            'slug': slug,
            'name': man['name'],
            'a': {k: a[k] for k in ('date', 'mjd', 'season', 'n_frames', 'xy')},
            'b': {k: b[k] for k in ('date', 'mjd', 'season', 'n_frames', 'xy')},
            'meas_east': round(de, 3),
            'meas_north': round(dn, 3),
            'meas_err': round(math.hypot(a['err'], b['err']), 3),
            'gaia_mas_yr': man['pm']['total_mas_yr'],
            'gaia_source': man['pm']['source'],
            'year_pred_arcsec': round(summ['pred_shift_arcsec'], 2),
            'year_meas_arcsec': round(summ['meas_shift_arcsec'], 2),
        })
        print(slug, ia, ib, a['date'], b['date'], round(math.hypot(de, dn), 2), 'arcsec', a['xy'], b['xy'])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        'scale_arcsec_per_px': SCALE,
        'size_px': 488,
        'source': 'SPHEREx L2 images (NASA/IPAC IRSA), season stacks; positions measured by the Rewind team with ePSF fits; Gaia DR3 proper motions',
        'rounds': rounds,
    }, indent=1))
    print('wrote', OUT)


if __name__ == '__main__':
    main()
