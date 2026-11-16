"""Pulse reader: wing photometry of saturated SPHEREx stars (R Dra, RW Aur).

R Dra and RW Aur saturate the SPHEREx core in nearly every exposure, so we measure the
PSF wings instead: the mean background-subtracted (IMAGE - ZODI) surface brightness of
unflagged pixels in an annulus 3.5 to 7 px from the predicted position. Each exposure is
compared only with exposures in the same wavelength channel (same detector, wavelength
within about 1%), as a magnitude difference from that channel's median. We then bin by time.

Input: the real SPHEREx L2 stamps cut by agent A5 (data/05-test-targets/stamps/<target>/).
Output: web/public/data/games/pulse/<slug>.json (small).

Run: .venv/bin/python web/scripts/games/pulse-photometry.py
"""
import glob
import json
import os
import sys

import numpy as np
from astropy.io import fits

ROOT = '/Users/rahmanbazarov/Data/programming/SpaceApps2026-Rewind/data/05-test-targets'
OUT = os.path.join(os.path.dirname(__file__), '..', '..', 'public', 'data', 'games', 'pulse')
BAD_BITS = (1 << 1) | (1 << 2)  # OVERFLOW, SUR_ERROR
R_IN, R_OUT = 3.5, 7.0
BIN_DAYS = 10.0
MIN_GOOD = 40  # good annulus pixels needed


def measure(path):
    with fits.open(path) as h:
        img = h['IMAGE'].data.astype(float)
        flg = h['FLAGS'].data
        var = h['VARIANCE'].data
        zod = h['ZODI'].data
        hd = h[0].header
    cx, cy = hd['XFULLT'] - hd['X0FULL'], hd['YFULLT'] - hd['Y0FULL']
    yy, xx = np.mgrid[0:img.shape[0], 0:img.shape[1]]
    r = np.hypot(xx - cx, yy - cy)
    ok = (r >= R_IN) & (r <= R_OUT) & np.isfinite(img) & np.isfinite(var) & np.isfinite(zod) & ((flg & BAD_BITS) == 0)
    if ok.sum() < MIN_GOOD:
        return None
    # the fraction of the full annulus we could use; edges of the detector cut it
    full = ((r >= R_IN) & (r <= R_OUT)).sum()
    v = img[ok] - zod[ok]
    return dict(mjd=hd['MJD-AVG'], det=hd['DETECTOR'], wave=hd['WAVEUM'], f=float(np.mean(v)), good=float(ok.sum() / full))


def run(target, slug, name):
    rows = []
    for p in sorted(glob.glob(f'{ROOT}/stamps/{target}/*.fits')):
        m = measure(p)
        if m and m['f'] > 0:
            rows.append(m)
    rows.sort(key=lambda m: m['mjd'])
    n_all = len(glob.glob(f'{ROOT}/stamps/{target}/*.fits'))
    # channel = detector + wavelength bin about 1% wide
    for m in rows:
        m['ch'] = (m['det'], int(np.round(np.log(m['wave']) / 0.01)))
    chans = {}
    for m in rows:
        chans.setdefault(m['ch'], []).append(m)
    used = []
    for c, ms in chans.items():
        mjds = np.array([m['mjd'] for m in ms])
        if len(ms) < 3 or mjds.max() - mjds.min() < 30:
            continue  # a channel seen only once, or only in one week, cannot show change
        med = np.median([m['f'] for m in ms])
        for m in ms:
            m['dmag'] = -2.5 * np.log10(m['f'] / med)
            used.append(m)
    used.sort(key=lambda m: m['mjd'])
    # short-wavelength (D1-D3, 0.75-2.4 um) and long (D4-D6, 2.4-5 um) kept apart: a Mira pulses harder at short wavelengths
    out_bins = {}
    for band, dets in (('short', (1, 2, 3)), ('long', (4, 5, 6))):
        sel = [m for m in used if m['det'] in dets]
        bins = []
        i = 0
        while i < len(sel):
            j = i
            while j < len(sel) and sel[j]['mjd'] - sel[i]['mjd'] < BIN_DAYS:
                j += 1
            grp = sel[i:j]
            d = np.array([m['dmag'] for m in grp])
            if len(d) >= 3:
                med = float(np.median(d))
                mad = float(1.4826 * np.median(np.abs(d - med)))
                bins.append(dict(mjd=round(float(np.mean([m['mjd'] for m in grp])), 2), dmag=round(med, 3), err=round(mad / np.sqrt(len(d)), 3), scatter=round(mad, 3), n=len(d)))
            i = j
        out_bins[band] = bins
    return dict(slug=slug, name=name, n_stamps=n_all, n_measured=len(rows), n_used=len(used), n_channels=len({m['ch'] for m in used}), bins=out_bins)


def period_scan(bins, pmin=100, pmax=600, n=5001):
    """Best sine period by weighted least squares, with a 1-sigma range after scaling chi2 to the scatter."""
    t = np.array([b['mjd'] for b in bins])
    y = np.array([b['dmag'] for b in bins])
    w = 1 / np.maximum(np.array([b['err'] for b in bins]), 0.01) ** 2
    Ps = np.linspace(pmin, pmax, n)
    chis = []
    for P in Ps:
        A = np.vstack([np.sin(2 * np.pi * t / P), np.cos(2 * np.pi * t / P), np.ones_like(t)]).T
        c, *_ = np.linalg.lstsq(A * np.sqrt(w)[:, None], y * np.sqrt(w), rcond=None)
        chis.append(float(np.sum(w * (y - A @ c) ** 2)))
    chis = np.array(chis)
    i = int(chis.argmin())
    red = chis[i] / (len(t) - 4)  # errors from bin scatter are too small; scale them
    ok = Ps[(chis - chis[i]) / red < 1]
    return dict(best=round(float(Ps[i]), 1), lo=round(float(ok.min()), 1), hi=round(float(ok.max()), 1), red_chi2=round(float(red), 1), span_days=round(float(t.max() - t.min()), 0))


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    rd = run('r_dra', 'rdra', 'R Draconis')
    rw = run('rw_aur', 'rwaur', 'RW Aurigae')
    vsx = json.load(open(f'{ROOT}/refs/r_dra_vsx.json'))['VSXObject']
    out = dict(
        method=('We measured the PSF wings, because the star saturates the core of every SPHEREx exposure. '
                f'For each real L2 stamp we took the mean of IMAGE minus ZODI over unflagged pixels {R_IN} to {R_OUT} px from the star, '
                'compared it only with exposures in the same wavelength channel (same detector, wavelength within 1%), '
                f'and took the median in {BIN_DAYS:.0f}-day bins.'),
        rdra=dict(n_stamps=rd['n_stamps'], n_used=rd['n_used'], n_channels=rd['n_channels'],
                  short=rd['bins']['short'], long=rd['bins']['long'],
                  fit_short=period_scan(rd['bins']['short']), fit_long=period_scan(rd['bins']['long']),
                  vsx=dict(period=float(vsx['Period']), epoch_jd=float(vsx['Epoch']), type=vsx['VariabilityType'], max=vsx['MaxMag'], min=vsx['MinMag'], spectral=vsx['SpectralType'])),
        rwaur=dict(n_stamps=rw['n_stamps'], n_used=rw['n_used'], n_channels=rw['n_channels'], long=rw['bins']['long'], short=rw['bins']['short']),
    )
    # the season stacks shown in the game; copied here because the R Dra manifest holds a NaN (not valid JSON for browsers)
    stars = os.path.join(os.path.dirname(__file__), '..', '..', 'public', 'data', 'stars')
    for slug in ('rdra', 'rwaur'):
        man = json.load(open(os.path.join(stars, slug, 'manifest.json')))
        out[slug]['seasons'] = [dict(iso=x['iso'], n_frames=x['n_frames'], png=x['png']) for x in man['seasons']]
    with open(os.path.join(OUT, 'pulse.json'), 'w') as f:
        json.dump(out, f, separators=(',', ':'))
    print(json.dumps({k: (v if k == 'method' else {kk: vv for kk, vv in v.items() if kk not in ('short', 'long')}) for k, v in out.items()}, indent=1))
    sys.exit(0)
