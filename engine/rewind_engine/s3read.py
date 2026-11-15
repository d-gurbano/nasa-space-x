"""Faster variant of the pilot S3 range reader (read_stamp_http).

The pilot walks the 7 HDU headers one by one (about 15 sequential HTTPS requests per stamp, so
it is latency-bound). In SPHEREx L2 files the last four HDUs have fixed sizes (MEASURED on
v27 files): VARIANCE starts 37,189,440 bytes before the end (11,520-byte header), ZODI
20,531,520, EPSF 3,873,600 (5,760-byte header), WCS-WAVE 5,760. IMAGE and FLAGS headers
come right after PRIMARY. So after one first request (headers + file size) every other read
is known and runs in parallel: 3 rounds instead of 15 sequential requests. Every offset is
checked (EXTNAME cards); on any mismatch it falls back to the pilot reader. ZODI is not read
(we never use it; the stamp gets NaN there)."""
from __future__ import annotations

import io
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import requests
from astropy.io import fits

from .pilot import R

TAIL = dict(VARIANCE=(37189440, 11520), EPSF=(3873600, 5760), WAVE=(5760, 2880))
_POOL = ThreadPoolExecutor(32)


def _get(url, start, length):
    return R._range(url, start, length)


def _first(url, n=31680):
    """First n bytes plus total file size (from Content-Range)."""
    for k in range(4):
        try:
            r = R._sess().get(url, headers={"Range": f"bytes=0-{n - 1}"}, timeout=120)
            if r.status_code == 206:
                return r.content, int(r.headers["Content-Range"].split("/")[1])
        except Exception:  # noqa
            pass
    raise RuntimeError("first read failed " + url)


def _hdr_from(buf, off):
    for i in range(off, len(buf) - 79, 80):
        if buf[i:i + 8] == b"END     ":
            hl = ((i + 80 - off + 2879) // 2880) * 2880
            return fits.Header.fromstring(buf[off:i + 80].decode("ascii")), hl
    raise ValueError("END not found")


def _extname(raw):
    for i in range(0, len(raw) - 79, 80):
        if raw[i:i + 8] == b"EXTNAME ":
            return raw[i + 10:i + 80].decode("ascii", "replace").split("/")[0].strip().strip("'").strip()
    return None


def read_stamp(uri: str, ra: float, dec: float, half: int = 20):
    try:
        return _read_fast(uri, ra, dec, half)
    except (ValueError, AssertionError, KeyError):
        return R.read_stamp_http(uri, ra, dec, half=half)


def _read_fast(uri, ra, dec, half):
    import time
    t0 = time.time()
    url = R.S3_HTTP + uri.split("ibe/data/spherex/", 1)[1]
    buf, size = _first(url)
    h0, l0 = _hdr_from(buf, 0)
    hdr, l1 = _hdr_from(buf, l0)
    assert hdr.get("EXTNAME") == "IMAGE"
    dimg = l0 + l1
    NX, NY = hdr["NAXIS1"], hdr["NAXIS2"]
    flag_off = dimg + ((NX * NY * 4 + 2879) // 2880) * 2880
    w = R._celestial_wcs(hdr)
    x, y = w.all_world2pix([[ra, dec]], 0)[0]
    xi, yi = int(round(x)), int(round(y))
    x0, y0 = xi - half, yi - half
    n = 2 * half + 1
    X0, Y0, X1, Y1 = max(x0, 0), max(y0, 0), min(x0 + n, NX), min(y0 + n, NY)
    if X1 <= X0 or Y1 <= Y0:
        raise RuntimeError(f"target off detector: x={x:.1f} y={y:.1f}")
    voff = size - TAIL["VARIANCE"][0]
    vdat = voff + TAIL["VARIANCE"][1]
    eoff = size - TAIL["EPSF"][0]
    woff = size - TAIL["WAVE"][0]
    # round 2: everything whose offset is now known
    jobs = dict(img=(dimg + Y0 * NX * 4, (Y1 - Y0) * NX * 4), var=(vdat + Y0 * NX * 4, (Y1 - Y0) * NX * 4),
                vhdr=(voff, 2880), flg=(flag_off, 17280 + NY * 8), eps=(eoff, TAIL["EPSF"][1] + 2880 * 4),
                wave=(woff, TAIL["WAVE"][0]))
    futs = {k: _POOL.submit(_get, url, *v) for k, v in jobs.items()}
    got = {k: f.result() for k, f in futs.items()}
    assert _extname(got["vhdr"]) == "VARIANCE"
    fh, fhl = _hdr_from(got["flg"], 0)
    assert fh.get("EXTNAME") == "FLAGS" and fh["ZTILE2"] == 1 and fh["NAXIS1"] == 8
    eh, ehl = _hdr_from(got["eps"], 0)
    assert eh.get("EXTNAME") == "EPSF" and ehl == TAIL["EPSF"][1]
    wh, whl = _hdr_from(got["wave"], 0)
    assert wh.get("EXTNAME") == "WCS-WAVE"
    # FLAGS: descriptors of rows Y0..Y1 then one heap read
    desc = np.frombuffer(got["flg"][fhl + Y0 * 8: fhl + Y1 * 8], dtype=">i4").reshape(Y1 - Y0, 2).copy()
    theap = fh.get("THEAP", fh["NAXIS1"] * fh["NAXIS2"])
    lo, hi = desc[:, 1].min(), (desc[:, 1] + desc[:, 0]).max()
    edat = eoff + ehl
    rowlen = eh["NAXIS1"]
    dt = R._epsf_dtype(eh)
    rec0 = np.frombuffer(got["eps"][ehl:ehl + rowlen], dtype=dt)[0]
    xw, yw = float(rec0["XWIDTH"]), float(rec0["YWIDTH"])
    nzx = int(round(2040 / xw))
    nzy = int(round(2040 / yw))
    zi = min(int(y // yw), nzy - 1) * nzx + min(int(x // xw), nzx - 1)
    f_heap = _POOL.submit(_get, url, flag_off + fhl + theap + lo, hi - lo)
    f_zone = _POOL.submit(_get, url, edat + zi * rowlen, rowlen)
    heap, rz = f_heap.result(), f_zone.result()
    desc[:, 1] -= lo
    h2 = fh.copy()
    h2["NAXIS2"] = Y1 - Y0
    h2["ZNAXIS2"] = Y1 - Y0
    h2["PCOUNT"] = len(heap)
    if "THEAP" in h2:
        del h2["THEAP"]
    body = desc.astype(">i4").tobytes() + heap
    body += b"\0" * ((-len(body)) % 2880)
    prim = fits.PrimaryHDU().header.tostring().encode()
    fl = np.asarray(fits.open(io.BytesIO(prim + h2.tostring().encode() + body))[1].data)[:, X0:X1]

    def block(raw, fill):
        b = np.frombuffer(raw, dtype=">f4").reshape(Y1 - Y0, NX)
        a = np.full((n, n), fill, dtype=np.float64)
        a[Y0 - y0:Y1 - y0, X0 - x0:X1 - x0] = b[:, X0:X1]
        return a
    img, var = block(got["img"], np.nan), block(got["var"], np.nan)
    flg = np.full((n, n), 1 << 9, dtype=np.int64)
    flg[Y0 - y0:Y1 - y0, X0 - x0:X1 - x0] = fl
    ep = np.frombuffer(rz, dtype=dt).copy()
    zone_ok = abs(ep["XCENTER"][0] - x) <= xw / 2 + 1 and abs(ep["YCENTER"][0] - y) <= yw / 2 + 1
    assert zone_ok
    ep_out = {k: ep[k] for k in ep.dtype.names}
    ep_out["EPSF"] = ep["EPSF"].reshape(1, 33, 33)
    wave = np.array(fits.open(io.BytesIO(prim + got["wave"]))[1].data)
    nbytes = len(buf) + sum(len(v) for v in got.values()) + len(heap) + len(rz)
    return R.Stamp(img, flg, var, np.full((n, n), np.nan), R._shift_wcs(w, x0, y0), x0, y0, hdr.copy(), ep_out, wave,
                   source="s3-fast", meta=dict(t_read=time.time() - t0, x_full=x, y_full=y, zone_index=zi,
                                               zone_ok=True, bytes=nbytes, requests=9))
