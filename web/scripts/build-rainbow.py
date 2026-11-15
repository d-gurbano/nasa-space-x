"""Build web/public/data/games/rainbow.json for the Rainbow Detective game.

Rounds are real ground-based asteroid spectra (MITHNEOS, IRTF) already resampled to the 102
SPHEREx colours, picked so the label and the nearest class template agree (clean examples).
Icy comet rounds are a model: a red dust slope times lab water-ice and CO2-ice bands.
The bonus round is a Rewind find measured by SPHEREx itself (object.json composition).

Run: .venv/bin/python web/scripts/build-rainbow.py
"""
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

MAIN = Path('/Users/rahmanbazarov/Data/programming/SpaceApps2026-Rewind')
DER = MAIN / 'data/06-composition/derived'
WEB = Path(__file__).resolve().parents[1]
OUT = WEB / 'public/data/games/rainbow.json'

wl = pd.read_csv(DER / 'spherex_channels.csv').center_um.to_numpy()
tpl = pd.read_csv(DER / 'spherex_templates_cent.csv').set_index('template_id')
spec = pd.read_csv(DER / 'spherex_validation_spectra.csv', low_memory=False)
CH = [f'ch{i:03d}' for i in range(1, 103)]
NORM = (wl >= 1.2) & (wl <= 1.6)  # every spectrum and template is set to 1 here


def norm(v):
    v = np.asarray(v, float)
    m = NORM & np.isfinite(v)
    return v / np.nanmean(v[m]) if m.sum() >= 3 else None


def r3(v):
    return [None if not np.isfinite(x) else round(float(x), 3) for x in v]


T = {k: norm(tpl.loc[f'stitched_{k}_0.45-5um'].to_numpy()) for k in 'SCX'}


def ice_model(depth, slope):
    """Red dust continuum times water-ice (1.5, 2, 3 um) and CO2-ice (4.27 um) bands."""
    v = 1 + slope * (wl - 1.4)
    for band, k in [('comet_H2Oice_1p5um', 0.6), ('comet_H2Oice_2um', 0.8), ('comet_H2Oice_3um', 1.0), ('comet_CO2ice_4p27', 0.7)]:
        b = tpl.loc[band].to_numpy()
        v = v * (1 - depth * k * (1 - b))
    return norm(v)


T['ice'] = ice_model(0.8, 0.12)


def fit_err(v, t):
    m = np.isfinite(v) & np.isfinite(t)
    return float(np.sqrt(np.mean((v[m] - t[m]) ** 2)))


NAMES = {'3200': '3200 Phaethon', '719': '719 Albert'}


def nice(number):
    s = str(number)
    if s in NAMES:
        return NAMES[s]
    m = re.fullmatch(r'(\d{4})([a-z]{2})(\d*)', s)
    return f'{m[1]} {m[2].upper()}{m[3]}' if m else f'({s})'


def band_depth(v):
    """Depth of the 1 um dip below a straight line from 0.78 to 1.5 um."""
    def at(u):
        ok = np.where(np.isfinite(v))[0]
        i = ok[int(np.argmin(abs(wl[ok] - u)))]
        return v[i]
    lo, hi = at(0.78), at(1.5)
    inside = (wl > 0.85) & (wl < 1.15) & np.isfinite(v)
    i = np.where(inside)[0][int(np.nanargmin(v[inside]))]
    cont = lo + (hi - lo) * (wl[i] - 0.78) / (1.5 - 0.78)
    return 1 - v[i] / cont


def slope_pct(v):
    m = np.isfinite(v) & (wl < 2.45)
    return 100 * np.polyfit(wl[m], v[m], 1)[0]


mith = spec[(spec.survey == 'MITHNEOS') & spec.complex.isin(['S', 'C', 'X'])].copy()
cand = []
for _, row in mith.iterrows():
    v = norm(row[CH].to_numpy(float))
    if v is None or np.isfinite(v).sum() < 46 or str(row.number) in {c['id'] for c in cand}:
        continue
    errs = {k: fit_err(v, T[k]) for k in 'SCX'}
    best = min(errs, key=errs.get)
    if best != row.complex:
        continue
    # roughness: a clean spectrum changes smoothly from one colour to the next
    rough = float(np.nanmedian(abs(np.diff(v[np.isfinite(v)], 2))))
    margin = sorted(errs.values())[1] - errs[best]
    cand.append(dict(id=str(row.number), truth=best, v=v, rough=rough, margin=margin, cls=str(row.ssodnet_class)))

PICK = {'S': 4, 'C': 3, 'X': 3}
rounds = []
for k, n in PICK.items():
    pool = sorted([c for c in cand if c['truth'] == k and c['rough'] < (0.01 if k != 'X' else 0.02)], key=lambda c: -c['margin'])
    for c in pool[:n]:
        v = c['v']
        if k == 'S':
            say = f'The dip near 1 um is the mineral olivine, with pyroxene. This one dips {100 * band_depth(v):.0f}% below the straight line. Stony meteorites look the same.'
        elif k == 'C':
            sl = slope_pct(v)
            trend = f'rising only {sl:.0f}% per um' if sl >= 1 else 'with almost no slope' if sl > -1 else 'even sloping down a little'
            say = f'Nearly flat, {trend}, and no clear dips. Dark carbon-rich dust hides the minerals underneath.'
        else:
            say = f'No dips at all, just a steady climb to the red of {slope_pct(v):.0f}% per um. Metal and iron-poor rock look like this.'
        rounds.append(dict(id=c['id'], name=f'Asteroid {nice(c["id"])}', truth=k, kind='measured', values=r3(v), say=say))

for i, (depth, slope) in enumerate([(0.9, 0.1), (0.55, 0.2)]):
    say = ('The deep band near 3 um is water ice, with smaller ice bands near 1.5 and 2 um. '
           + ('A dip near 4.3 um is frozen carbon dioxide.' if i == 0 else 'Here a dusty red coat makes the ice bands shallower, but the 3 um band still shows.'))
    rounds.append(dict(id=f'ice-{i + 1}', name=['An icy comet nucleus', 'A dusty icy comet'][i], truth='ice', kind='model', values=r3(ice_model(depth, slope)), say=say))

# bonus: a Rewind find that SPHEREx measured, with a composition best match
bonus = None
for slug in ['3i-atlas']:
    p = WEB / f'public/data/objects/{slug}/object.json'
    o = json.loads(p.read_text())
    c = o.get('composition') or {}
    key = {'S': 'S', 'C': 'C', 'X': 'X'}.get(c.get('best_match') or '')
    if o.get('verdict') != 'FOUND' or not key:
        continue
    um = np.array([q['um'] for q in c['points']])
    val = np.array([q['value'] for q in c['points']])
    err = np.array([q['err'] for q in c['points']])
    # put the points on the same scale as the class template, matched below 1.3 um like the engine
    t_at = np.interp(um, wl[np.isfinite(T[key])], T[key][np.isfinite(T[key])])
    s = t_at[um < 1.3].mean() / val[um < 1.3].mean()
    bonus = dict(id=slug, name=o['name'], truth=key, kind='spherex', label=c.get('label'), slug=slug,
                 points=[dict(um=round(float(a), 3), value=round(float(b * s), 3), err=round(float(e * s), 3)) for a, b, e in zip(um, val, err)],
                 say=f'Rewind measured {o["name"]} in {len(um)} wide SPHEREx colour bins and its best match is {key}, a {c.get("label")}. The error bars are big, so treat it as a first guess. It is a comet, so its glowing coma adds light at the longest colours.')

out = dict(
    schema='rewind-rainbow-v1',
    note='Asteroid rounds are real ground-based spectra (MITHNEOS, NASA IRTF, 0.75-2.5 um) resampled to the 102 SPHEREx colours. Beyond 2.5 um the ground cannot see well, so those colours are blank. Icy comet rounds are a model built from lab ice bands. Class curves are the stitched 0.45-5 um templates (an estimate). All set to 1 at 1.2-1.6 um.',
    um=[round(float(x), 4) for x in wl],
    classes={k: r3(T[k]) for k in ['S', 'C', 'X', 'ice']},
    rounds=rounds,
    bonus=bonus,
)
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(out, separators=(',', ':')))
print(f'{len(rounds)} rounds, bonus={bonus and bonus["name"]} -> {OUT} ({OUT.stat().st_size // 1024} KB)', file=sys.stderr)
for r in rounds:
    print(r['truth'], r['name'], r['say'], file=sys.stderr)
