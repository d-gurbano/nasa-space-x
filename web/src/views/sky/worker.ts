// Web Worker: reads small pieces of SPHEREx level-2 FITS files straight from NASA's public
// archive with HTTP Range requests. Per photo: one read for the header (WCS), one read for the
// rows that hold the cutout. The cutout is resampled north-up onto the shared grid and its own
// sky level (median) is subtracted. Headers are cached, so a new size or a nearby spot is faster.
import { skyStats } from './logic';
import { findImageHdu, makeWcs, offsetToSky, type Wcs } from './wcs';

export interface LoadRequest {
  type: 'load';
  job: number;
  base: string;
  keys: string[];
  ra: number;
  dec: number;
  /** cutout width in arcsec and in grid pixels */
  size: number;
  n: number;
}

export type FrameResult =
  | {
      type: 'frame'; job: number; key: string; ok: true;
      /** n x n, row 0 at the north edge, east to the left, sky-subtracted, MJy/sr */
      data: Float32Array;
      sky: number; noise: number; mjd: number; detector: number;
      /** detector pixel of the centre, and pixels per arcsec east and north (for the wavelength) */
      x: number; y: number; jac: [number, number, number, number];
      bytes: number;
    }
  | { type: 'frame'; job: number; key: string; ok: false; reason: 'edge' | 'error'; message: string };

export type WorkerOut = FrameResult | { type: 'done'; job: number };

interface Head {
  wcs: Wcs;
  dataOffset: number;
  nx: number;
  ny: number;
  mjd: number;
  detector: number;
}

const HEAD_BYTES = 13 * 2880; // primary + IMAGE header are 28800 or 31680 bytes in practice
const PARALLEL = 6;
const heads = new Map<string, Promise<Head>>();
let current = 0;

/** One Range read, retried once. The error names the URL, so the page can log it. */
async function range(url: string, start: number, end: number): Promise<ArrayBuffer> {
  for (let attempt = 0; ; attempt++) {
    try {
      const r = await fetch(url, { headers: { Range: `bytes=${start}-${end}` } });
      if (r.status !== 206 && r.status !== 200) throw new Error('HTTP ' + r.status);
      const buf = await r.arrayBuffer();
      return r.status === 200 ? buf.slice(start, end + 1) : buf;
    } catch (e) {
      if (attempt >= 1) throw new Error(`${String((e as Error)?.message ?? e)} for ${url} (bytes=${start}-${end})`);
      await new Promise((ok) => setTimeout(ok, 500));
    }
  }
}

async function readHead(url: string): Promise<Head> {
  let bytes = new Uint8Array(await range(url, 0, HEAD_BYTES - 1));
  let hdu = findImageHdu(bytes);
  for (let more = 0; !hdu && more < 3; more++) {
    const next = new Uint8Array(await range(url, bytes.length, bytes.length + HEAD_BYTES - 1));
    const joined = new Uint8Array(bytes.length + next.length);
    joined.set(bytes);
    joined.set(next, bytes.length);
    bytes = joined;
    hdu = findImageHdu(bytes);
  }
  if (!hdu) throw new Error('FITS header not found');
  const h = hdu.header;
  return { wcs: makeWcs(h), dataOffset: hdu.dataOffset, nx: hdu.nx, ny: hdu.ny, mjd: Number(h['MJD-AVG'] ?? h['MJD-OBS']), detector: Number(h.DETECTOR) };
}

async function readFrame(req: LoadRequest, key: string): Promise<FrameResult> {
  const url = req.base + key;
  if (!heads.has(key)) heads.set(key, readHead(url));
  let head: Head;
  try {
    head = await heads.get(key)!;
  } catch (e) {
    heads.delete(key);
    throw e;
  }
  const { wcs, nx, ny } = head;
  const n = req.n, scale = req.size / n;
  // detector pixel of every grid pixel centre
  const px = new Float32Array(n * n), py = new Float32Array(n * n);
  let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity;
  for (let j = 0; j < n; j++)
    for (let i = 0; i < n; i++) {
      const [ra, dec] = offsetToSky(req.ra, req.dec, (n / 2 - (i + 0.5)) * scale, (n / 2 - (j + 0.5)) * scale);
      const [x, y] = wcs.world2pix(ra, dec);
      px[j * n + i] = x;
      py[j * n + i] = y;
      if (x < x0) x0 = x;
      if (x > x1) x1 = x;
      if (y < y0) y0 = y;
      if (y > y1) y1 = y;
    }
  const [cx, cy] = wcs.world2pix(req.ra, req.dec);
  if (cx < 0 || cy < 0 || cx > nx - 1 || cy > ny - 1) return { type: 'frame', job: req.job, key, ok: false, reason: 'edge', message: 'The position falls outside the edge of this image' };
  const [ex, ey] = wcs.world2pix(...offsetToSky(req.ra, req.dec, 10, 0));
  const [nxx, nyy] = wcs.world2pix(...offsetToSky(req.ra, req.dec, 0, 10));
  const c0 = Math.max(0, Math.floor(x0)), c1 = Math.min(nx - 1, Math.ceil(x1));
  const r0 = Math.max(0, Math.floor(y0)), r1 = Math.min(ny - 1, Math.ceil(y1));
  // one contiguous read from (c0, r0) to (c1, r1)
  const first = r0 * nx + c0, last = r1 * nx + c1;
  const buf = await range(url, head.dataOffset + first * 4, head.dataOffset + last * 4 + 3);
  const view = new DataView(buf);
  const count = buf.byteLength >> 2;
  const at = (x: number, y: number) => {
    if (x < c0 || x > c1 || y < r0 || y > r1) return NaN;
    const k = y * nx + x - first;
    return k >= 0 && k < count ? view.getFloat32(k * 4, false) : NaN;
  };
  const data = new Float32Array(n * n);
  for (let k = 0; k < n * n; k++) {
    const x = px[k], y = py[k];
    const xi = Math.floor(x), yi = Math.floor(y), fx = x - xi, fy = y - yi;
    const a = at(xi, yi), b = at(xi + 1, yi), c = at(xi, yi + 1), d = at(xi + 1, yi + 1);
    // bilinear where all four pixels have data, else the nearest pixel
    data[k] = Number.isFinite(a + b + c + d) ? (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy : at(Math.round(x), Math.round(y));
  }
  const { sky, noise } = skyStats(data);
  if (!Number.isFinite(sky)) return { type: 'frame', job: req.job, key, ok: false, reason: 'edge', message: 'No valid pixels at this position in this image' };
  for (let k = 0; k < data.length; k++) data[k] -= sky;
  return {
    type: 'frame', job: req.job, key, ok: true, data, sky, noise, mjd: head.mjd, detector: head.detector,
    x: cx, y: cy, jac: [(ex - cx) / 10, (nxx - cx) / 10, (ey - cy) / 10, (nyy - cy) / 10], bytes: HEAD_BYTES + buf.byteLength,
  };
}

const post = (m: WorkerOut, transfer: Transferable[] = []) => (self as unknown as { postMessage(m: unknown, t: Transferable[]): void }).postMessage(m, transfer);

self.onmessage = async (ev: MessageEvent<LoadRequest | { type: 'cancel' }>) => {
  const req = ev.data;
  if (req.type === 'cancel') {
    current = 0;
    return;
  }
  current = req.job;
  const queue = [...req.keys];
  const lane = async () => {
    while (queue.length && current === req.job) {
      const key = queue.shift()!;
      let out: FrameResult;
      try {
        out = await readFrame(req, key);
      } catch (e) {
        out = { type: 'frame', job: req.job, key, ok: false, reason: 'error', message: String((e as Error)?.message ?? e) };
      }
      if (current !== req.job) return;
      post(out, out.ok ? [out.data.buffer] : []);
    }
  };
  await Promise.all(Array.from({ length: PARALLEL }, lane));
  if (current === req.job) post({ type: 'done', job: req.job });
};
