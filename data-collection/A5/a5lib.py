"""A5 (challenge test targets) shared helpers: target list, astrometric position
propagation (proper motion + parallax as seen from Earth/SPHEREx), IRSA cone search.

Team SpaceX, NASA Space Apps 2026, project Rewind. Public data only, read-only.
"""
from __future__ import annotations
import io, os, sys, time, json, hashlib
import numpy as np
import requests
from astropy.time import Time
from astropy.coordinates import get_body_barycentric
import astropy.units as u

ROOT = "/Users/rahmanbazarov/Data/programming/SpaceApps2026-Rewind"
OUT = os.path.join(ROOT, "data/05-test-targets")
sys.path.insert(0, os.path.join(ROOT, "code/A0"))

TARGETS = {
    # key: label, gaia DR3 id (None for WISE 0855), approx 2016 position for cone search
    "barnard": dict(label="Barnard's Star", gaia="4472832130942575872", ra=269.4486, dec=4.7394),
    "eps_indi_b": dict(label="Epsilon Indi Ba+Bb", gaia="6412596012146801152", ra=331.0765, dec=-56.7938),
    "wise0855": dict(label="WISE J085510.83-071442.5", gaia=None, ra=133.7951, dec=-7.2451),
    "rw_aur": dict(label="RW Aurigae A(+B)", gaia="156430822114424576", ra=76.9562, dec=30.4010),
    "r_dra": dict(label="R Draconis", gaia="1648328016354496384", ra=248.1675, dec=66.7550),
}


def get(url, params=None, timeout=200, tries=5, **kw):
    last = None
    for k in range(tries):
        try:
            r = requests.get(url, params=params, timeout=timeout, **kw)
            if r.status_code == 200:
                return r
            last = f"HTTP {r.status_code} {r.text[:200]}"
        except Exception as e:  # noqa
            last = repr(e)
        time.sleep(2 * (k + 1) ** 2)
    raise RuntimeError(f"GET failed {url} {params}: {last}")


def scs(table, ra, dec, sr_deg):
    """IRSA Simple Cone Search -> astropy Table."""
    from astropy.io.votable import parse_single_table
    r = get("https://irsa.ipac.caltech.edu/SCS", dict(table=table, RA=ra, DEC=dec, SR=sr_deg))
    return parse_single_table(io.BytesIO(r.content)).to_table(use_names_over_ids=True), r.url


def radec_at(ra0, dec0, pmra, pmdec, plx, ep0_jyear, t: Time, rv=None):
    """Astrometric RA/Dec (deg) at time(s) t as seen from the geocentre (SPHEREx in
    LEO differs by < 1e-3 arcsec for these stars). ra0/dec0 at epoch ep0 (Julian
    year, barycentric), pmra = mu_alpha* (mas/yr), parallax mas. Linear space motion
    on the tangent plane (fine for decades at these PMs; radial velocity ignored, which
    matters at the < 0.1" level only for Barnard over 70 yr - noted in REPORT)."""
    t = Time(t)
    dt = (t.jyear - ep0_jyear)
    a0, d0 = np.radians(ra0), np.radians(dec0)
    # unit vectors
    p_hat = np.array([-np.sin(a0), np.cos(a0), 0.0])
    q_hat = np.array([-np.sin(d0) * np.cos(a0), -np.sin(d0) * np.sin(a0), np.cos(d0)])
    r_hat = np.array([np.cos(d0) * np.cos(a0), np.cos(d0) * np.sin(a0), np.sin(d0)])
    mas = np.radians(1 / 3.6e6)
    dtt = np.atleast_1d(dt)
    if rv is None:
        vec = r_hat[None, :] + (pmra * mas * dtt)[:, None] * p_hat[None, :] + (pmdec * mas * dtt)[:, None] * q_hat[None, :]
    else:
        # rigorous linear space motion incl. radial velocity (perspective acceleration),
        # positions in AU: r0 = (1/plx) * r_hat, v = tangential + radial (AU/yr)
        d_au = 1.0 / (plx * 1e-3) * 206264.806
        kms_to_auyr = 0.210945
        v = (pmra * 1e-3 / 206264.806 * d_au) * p_hat + (pmdec * 1e-3 / 206264.806 * d_au) * q_hat + rv * kms_to_auyr * r_hat
        vec = (d_au * r_hat)[None, :] + dtt[:, None] * v[None, :]
        vec = vec / d_au
    # parallax: subtract Earth barycentric position (AU) * plx
    eb = get_body_barycentric("earth", t)
    E = np.atleast_2d(np.c_[eb.x.to(u.au).value, eb.y.to(u.au).value, eb.z.to(u.au).value])
    vec = vec - (plx * mas) * E if rv is None else vec - E / (1.0 / (plx * 1e-3) * 206264.806)
    vec /= np.linalg.norm(vec, axis=1)[:, None]
    ra = np.degrees(np.arctan2(vec[:, 1], vec[:, 0])) % 360
    dec = np.degrees(np.arcsin(vec[:, 2]))
    return ra, dec


def sky_offset_arcsec(ra1, dec1, ra2, dec2):
    """(east, north) offset of point 2 relative to point 1, arcsec (small angles)."""
    dra = (np.asarray(ra2) - np.asarray(ra1) + 180) % 360 - 180
    e = dra * np.cos(np.radians(dec1)) * 3600
    n = (np.asarray(dec2) - np.asarray(dec1)) * 3600
    return e, n


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


MANIFEST = os.path.join(OUT, "manifest.csv")


def manifest_add(path, url):
    import datetime
    new = not os.path.exists(MANIFEST)
    with open(MANIFEST, "a") as f:
        if new:
            f.write("filename,url,bytes,sha256,date\n")
        rel = os.path.relpath(path, OUT)
        f.write(f"{rel},\"{url}\",{os.path.getsize(path)},{sha256(path)},{datetime.date.today()}\n")


def pos(A, t):
    """Adopted-astrometry position at time t (uses radial velocity if A has 'rv')."""
    return radec_at(A["ra"], A["dec"], A["pmra"], A["pmdec"], A["plx"], A["ep"], t, rv=A.get("rv"))
