"""Blink!: cut pairs of real SPHEREx images of the same patch of sky around a real known asteroid.

Source: the answer key (07-answer-keys/answer_key/known_objects_in_frames.parquet) gives each known
asteroid's predicted position in real SPHEREx L2 frames. We pick pairs of frames on the same
detector at nearly the same wavelength (within 3 percent), 1.5 hours to 3 days apart, where the
asteroid moved 3 to 30 pixels. For each frame we read only the needed image rows from the public
S3 bucket (HTTPS byte ranges, read-only) and resample both onto one north-up grid (6.15"/px)
centred between the two positions. Each frame is scaled by its own background and noise so the
stars look alike in both. Isolated one-pixel spikes (cosmic rays, hot pixels) are smoothed out
first (see despike). Output: web/public/data/games/blink/rounds.json + PNGs.

Run: .venv/bin/python web/scripts/games/blink-prep.py
"""
import io
import json
import os
import sys

import numpy as np
import pandas as pd
import requests
from astropy.io import fits
from astropy.wcs import WCS
from PIL import Image
from scipy.ndimage import map_coordinates, maximum_filter, median_filter

KEY = '/Users/rahmanbazarov/Data/programming/SpaceApps2026-Rewind/data/07-answer-keys/answer_key/known_objects_in_frames.parquet'
OUT = os.path.join(os.path.dirname(__file__), '../../public/data/games/blink')
S3 = 'https://nasa-irsa-spherex.s3.amazonaws.com/'
N = 49          # output stamp, pixels
SCALE = 6.15    # arcsec per output pixel (the SPHEREx pixel)
S = requests.Session()


def rng(url, a, n):
    r = S.get(url, headers={'Range': f'bytes={a}-{a + n - 1}'}, timeout=120)
    r.raise_for_status()
    return r.content


def header_at(buf, off):
    for i in range(off, len(buf) - 79, 80):
        if buf[i:i + 8] == b'END     ':
            return fits.Header.fromstring(buf[off:i + 80].decode('ascii')), ((i + 80 - off + 2879) // 2880) * 2880
    raise ValueError('END not found')


def sky_grid(ra0, dec0):
    """RA/Dec of an N x N north-up grid (east to the left) centred on ra0, dec0 (tangent plane)."""
    c = (np.arange(N) - (N - 1) / 2) * SCALE / 3600
    xi, eta = np.meshgrid(-c, -c)  # row 0 at the top is north
    xi, eta = np.radians(xi), np.radians(eta)
    a0, d0 = np.radians(ra0), np.radians(dec0)
    den = np.cos(d0) - eta * np.sin(d0)
    ra = a0 + np.arctan2(xi, den)
    dec = np.arctan2(np.sin(d0) + eta * np.cos(d0), np.hypot(xi, den))
    return np.degrees(ra) % 360, np.degrees(dec)


def cut(key, ra, dec):
    """Resample one frame onto the sky grid; also return the frame header."""
    url = S3 + key
    buf = rng(url, 0, 31680)
    _, l0 = header_at(buf, 0)
    hdr, l1 = header_at(buf, l0)
    assert hdr['EXTNAME'] == 'IMAGE'
    w = WCS(hdr, relax=True, key=' ')
    NX, NY = hdr['NAXIS1'], hdr['NAXIS2']
    x, y = w.all_world2pix(ra.ravel(), dec.ravel(), 0)
    y0, y1 = int(np.floor(y.min())) - 2, int(np.ceil(y.max())) + 3
    if y0 < 0 or y1 > NY or x.min() < 2 or x.max() > NX - 3:
        raise RuntimeError('grid runs off the detector')
    raw = rng(url, l0 + l1 + y0 * NX * 4, (y1 - y0) * NX * 4)
    img = np.frombuffer(raw, dtype='>f4').reshape(y1 - y0, NX).astype(np.float64)
    img = np.where(np.isfinite(img), img, np.nanmedian(img))
    img = despike(img)
    out = map_coordinates(img, [y - y0, x], order=1).reshape(N, N)
    return out, hdr, w


def despike(img):
    """Replace isolated one-pixel spikes (cosmic-ray hits, hot pixels) with the local median.
    A spike is far above its 3x3 median while none of its 8 neighbours is even an eighth as high;
    a star or asteroid spreads its light over the neighbours, so it is kept."""
    med = median_filter(img, 3)
    ring = np.ones((3, 3), bool)
    ring[1, 1] = False
    nb = maximum_filter(img, footprint=ring)
    d = img - med
    mad = np.median(np.abs(d)) * 1.4826 or 1.0
    spike = (d > 8 * mad) & (nb - med < d / 8)
    return np.where(spike, med, img)


def norm(a):
    med = np.median(a)
    mad = np.median(np.abs(a - med)) * 1.4826 or 1.0
    return (a - med) / mad


def to_png(z, path):
    v = np.arcsinh(np.clip(z, -3, None) / 3.0)
    lo, hi = np.arcsinh(-2 / 3.0), np.arcsinh(60 / 3.0)
    u = np.clip((v - lo) / (hi - lo), 0, 1)
    Image.fromarray((u * 255).astype(np.uint8), 'L').save(path, optimize=True)


def pix(ra, dec, ra0, dec0):
    """Sky position to grid pixel (x right, y down), same projection as sky_grid."""
    a, d, a0, d0 = map(np.radians, (ra, dec, ra0, dec0))
    cosc = np.sin(d0) * np.sin(d) + np.cos(d0) * np.cos(d) * np.cos(a - a0)
    xi = np.cos(d) * np.sin(a - a0) / cosc
    eta = (np.cos(d0) * np.sin(d) - np.sin(d0) * np.cos(d) * np.cos(a - a0)) / cosc
    c = (N - 1) / 2
    return c - np.degrees(xi) * 3600 / SCALE, c - np.degrees(eta) * 3600 / SCALE


def peak_snr(z, x, y):
    xi, yi = int(round(x)), int(round(y))
    return float(z[max(yi - 1, 0):yi + 2, max(xi - 1, 0):xi + 2].max())


def main():
    os.makedirs(OUT, exist_ok=True)
    d = pd.read_parquet(KEY)
    d = d[d.on_detector]
    good = d[(d.kind == 'asteroid') & (d.position_quality == 'gold') & (d.V_pred < 18.5)].sort_values('MJD-AVG')
    pairs = []
    for name, g in good.groupby('name'):
        g = g.reset_index(drop=True)
        best = None
        for i in range(len(g)):
            for j in range(i + 1, len(g)):
                a, b = g.iloc[i], g.iloc[j]
                dt = b['MJD-AVG'] - a['MJD-AVG']
                if not 0.04 < dt < 3 or a.DETECTOR != b.DETECTOR or abs(a.wave_um - b.wave_um) / a.wave_um > 0.03:
                    continue
                px = np.hypot((b.ra_deg - a.ra_deg) * np.cos(np.radians(a.dec_deg)), b.dec_deg - a.dec_deg) * 3600 / SCALE
                if 3 <= px <= 30 and (best is None or dt < best[2]):
                    best = (a, b, dt, px)
        if best:
            pairs.append(best)
    pairs.sort(key=lambda p: p[0].V_pred)
    print(len(pairs), 'candidate pairs', file=sys.stderr)
    rounds = []
    for a, b, dt, px in pairs[:40]:
        ra0 = (a.ra_deg + b.ra_deg) / 2
        dec0 = (a.dec_deg + b.dec_deg) / 2
        ra, dec = sky_grid(ra0, dec0)
        try:
            ia, ha, _ = cut(a.key, ra, dec)
            ib, hb, _ = cut(b.key, ra, dec)
        except Exception as e:  # noqa
            print('skip', a['name'], e, file=sys.stderr)
            continue
        za, zb = norm(ia), norm(ib)
        xa, ya = pix(a.ra_deg, a.dec_deg, ra0, dec0)
        xb, yb = pix(b.ra_deg, b.dec_deg, ra0, dec0)
        # other known objects inside the stamp in either frame would also move: skip such stamps
        others = d[(d.key.isin([a.key, b.key])) & (d.name != a['name'])]
        ox, oy = pix(others.ra_deg.values, others.dec_deg.values, ra0, dec0)
        inside = (ox > -2) & (ox < N + 1) & (oy > -2) & (oy < N + 1) & (others.V_pred.values < a.V_pred + 3)
        sa, sb = peak_snr(za, xa, ya), peak_snr(zb, xb, yb)
        print(f"{a['name']:28s} V={a.V_pred:5.2f} dt={dt:5.2f} px={px:5.1f} snr={sa:6.1f},{sb:6.1f} others={inside.sum()}", file=sys.stderr)
        if inside.any() or min(sa, sb) < 8:
            continue
        i = len(rounds)
        to_png(za, f'{OUT}/r{i}_a.png')
        to_png(zb, f'{OUT}/r{i}_b.png')
        rounds.append(dict(
            id=f'r{i}', name=a['name'], packed=a.packed, imgs=[f'r{i}_a.png', f'r{i}_b.png'],
            pos=[[round(float(xa), 2), round(float(ya), 2)], [round(float(xb), 2), round(float(yb), 2)]],
            mjd=[round(float(a['MJD-AVG']), 5), round(float(b['MJD-AVG']), 5)],
            hours=round(float(dt * 24), 2), moved_px=round(float(px), 1), moved_arcsec=round(float(px * SCALE), 1),
            um=[round(float(a.wave_um), 3), round(float(b.wave_um), 3)], detector=int(a.DETECTOR),
            V=round(float(a.V_pred), 1), snr=round(min(sa, sb), 1), r_au=round(float(a.r_au), 2),
            delta_au=round(float(a.delta_au), 2), obsid=[a.OBSID, b.OBSID], keys=[a.key, b.key]))
        if len(rounds) >= 20:
            break
    meta = dict(n=N, arcsec_per_px=SCALE, note='Pairs of real SPHEREx L2 exposures on the same detector at nearly the same wavelength, resampled north up. Positions from the known-object answer key (JPL orbits).', rounds=rounds)
    with open(f'{OUT}/rounds.json', 'w') as f:
        json.dump(meta, f, indent=1)
    print(len(rounds), 'rounds written', file=sys.stderr)


if __name__ == '__main__':
    main()
