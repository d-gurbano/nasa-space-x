// Sky page logic with no DOM: coordinate input, the frame index (cells, polygons, S3 keys),
// visits and survey passes, which photos to read first, wavelengths, stacks and the stretch.
import { skyToOffset } from './wcs';

export const BUCKET_URL = 'https://nasa-irsa-spherex.s3.amazonaws.com/';
export const SIZES = [60, 120, 180, 240]; // arcsec across
export const PIXEL_ARCSEC = 6.15;
const D2R = Math.PI / 180;

// ---------- coordinate input ----------

/** "133.7951 -7.2451", "133.7951, -7.2451", "08 55 10.8 -07 14 43", "08h55m10.8s -07d14m43s". RA in hours when sexagesimal. */
export function parseCoords(text: string): { ra: number; dec: number } | null {
  const t = text.trim().replace(/[−–]/g, '-');
  const nums = t.match(/[+-]?\d+(?:\.\d+)?/g)?.map(Number);
  if (!nums || /[^\d\s.,:+\-hmsd°'"]/i.test(t)) return null;
  let ra: number, dec: number;
  if (nums.length === 2) {
    ra = /h/i.test(t) ? nums[0] * 15 : nums[0];
    dec = nums[1];
  } else if (nums.length === 6 || nums.length === 4) {
    const k = nums.length / 2;
    const sex = (p: number[]) => Math.abs(p[0]) + p[1] / 60 + (p[2] ?? 0) / 3600;
    ra = sex(nums.slice(0, k)) * 15;
    // the sign of the declination comes from the text, so "-00 30 00" stays negative
    const decText = t.match(/[+-]?\d+(?:\.\d+)?/g)![k];
    dec = sex(nums.slice(k).map(Math.abs)) * (decText.startsWith('-') ? -1 : 1);
    if (nums.slice(1, k).concat(nums.slice(k + 1)).some((v) => v < 0 || v >= 60)) return null;
  } else return null;
  if (!(ra >= 0 && ra <= 360 && dec >= -90 && dec <= 90)) return null;
  return { ra: ra % 360, dec };
}

export function formatCoords(ra: number, dec: number): string {
  return `${ra.toFixed(4)} ${dec >= 0 ? '+' : ''}${dec.toFixed(4)}`;
}

// ---------- the frame index ----------

export interface SkyMeta {
  schema: string;
  built_iso?: string;
  partial?: boolean;
  partial_note?: string;
  areas?: { name: string; kind: string; ra: number; dec: number }[];
  n_shortlist_paths?: number;
  releases: string[];
  n_frames: number;
  cell_deg: number;
  key_patterns?: Record<string, string>;
  vers?: string[];
  /** full index: [release, week, proc] per compact key group */
  key_groups?: [string, string, string][];
  cells?: string[];
  bucket?: string;
}

export type Row = [string | number, number, number | string, number, number, number[], number, number, number | string];

export interface Frame {
  key: string;
  mjd: number;
  detector: number;
  release: string;
  wlMin: number;
  wlMax: number;
  /** filled by groupFrames */
  pass: number;
  visit: number;
}

/** Names of the index cells that can hold a frame covering this position. A frame centre is up to
 *  about 2.6 degrees from any point it covers, which is more than one cell in RA near the poles. */
export function cellsFor(ra: number, dec: number, cell = 5, reach = 2.6): string[] {
  const nRa = Math.round(360 / cell), nDec = Math.round(180 / cell);
  const d0 = Math.max(0, Math.floor((dec - reach + 90) / cell)), d1 = Math.min(nDec - 1, Math.floor((dec + reach + 90) / cell));
  const maxAbs = Math.min(90, Math.abs(dec) + reach);
  const dRa = maxAbs >= 89 ? 180 : Math.min(180, reach / Math.cos(maxAbs * D2R));
  const out = new Set<string>();
  for (let d = d0; d <= d1; d++) {
    if (dRa >= 180) for (let r = 0; r < nRa; r++) out.add(`r${r}_d${d}`);
    else for (let r = Math.floor((ra - dRa) / cell); r <= Math.floor((ra + dRa) / cell); r++) out.add(`r${((r % nRa) + nRa) % nRa}_d${d}`);
  }
  return [...out];
}

/** Is the position inside the frame outline? Tested on the tangent plane at the position. */
export function inPolygon(ra: number, dec: number, poly: number[]): boolean {
  let inside = false;
  const n = poly.length / 2;
  const pts: [number, number][] = [];
  for (let i = 0; i < n; i++) {
    // a corner on the far side of the sky cannot be projected
    const a = (poly[2 * i] - ra) * D2R, d = poly[2 * i + 1] * D2R;
    if (Math.sin(dec * D2R) * Math.sin(d) + Math.cos(dec * D2R) * Math.cos(d) * Math.cos(a) <= 0.5) return false;
    pts.push(skyToOffset(ra, dec, poly[2 * i], poly[2 * i + 1]));
  }
  for (let i = 0, j = n - 1; i < n; j = i++) {
    const [xi, yi] = pts[i], [xj, yj] = pts[j];
    if (yi > 0 !== yj > 0 && 0 < ((xj - xi) * (0 - yi)) / (yj - yi) + xi) inside = !inside;
  }
  return inside;
}

/** The S3 key of a row: a full key, a compact "<group>/<seq>_<n>" (full index: the group is
 *  [release, week, proc] in meta.key_groups), or "<obs>|<version index>" (partial index). */
export function resolveKey(row: Row, meta: SkyMeta): string {
  const k = String(row[0]);
  if (k.endsWith('.fits')) return k;
  const det = String(row[2]).replace(/\D/g, '');
  const compact = k.match(/^(\d+)\/(\d+_\d+)$/);
  if (compact && meta.key_groups) {
    const [release, week, proc] = meta.key_groups[Number(compact[1])] ?? [];
    const parts: Record<string, string> = { release, week, proc, detector: det, SEQ: compact[2] };
    const template = meta.key_patterns?.template ?? '{release}/level2/{week}/{proc}/{detector}/level2_{week}_{SEQ}D{detector}_spx_{proc}.fits';
    return template.replace(/\{(\w+)\}/g, (_m, name: string) => parts[name] ?? '');
  }
  const [obs, v] = k.split('|');
  const ver = meta.vers?.[Number(v)] ?? v;
  const release = typeof row[8] === 'number' ? meta.releases[row[8]] : row[8];
  const pattern = meta.key_patterns?.level2 ?? '{release}/level2/{week}/{ver}/{det}/level2_{obs}D{det}_spx_{ver}.fits';
  const parts: Record<string, string> = { release, week: obs.split('_').slice(0, 2).join('_'), ver, det, obs };
  return pattern.replace(/\{(\w+)\}/g, (_m, name: string) => parts[name] ?? '');
}

/** Frames whose outline contains the position, oldest first, with pass and visit numbers. */
export function framesAt(ra: number, dec: number, shards: { f: Row[] }[], meta: SkyMeta): Frame[] {
  const seen = new Set<string>();
  const out: Frame[] = [];
  for (const s of shards)
    for (const row of s.f ?? []) {
      if (!inPolygon(ra, dec, row[5])) continue;
      const key = resolveKey(row, meta);
      if (seen.has(key)) continue;
      seen.add(key);
      out.push({ key, mjd: row[1], detector: Number(String(row[2]).replace(/\D/g, '')), release: typeof row[8] === 'number' ? meta.releases[row[8]] : row[8], wlMin: row[6], wlMax: row[7], pass: 0, visit: 0 });
    }
  return groupFrames(out);
}

export const PASS_GAP_DAYS = 45;
export const PASS_MAX_DAYS = 183;
export const VISIT_GAP_DAYS = 0.25;

/** Sort by time and number the survey passes (SPHEREx comes back about every 6 months; a spot that
 *  is watched all the time, like the deep fields, is cut into half-year passes) and the visits. */
export function groupFrames(frames: Frame[]): Frame[] {
  frames.sort((a, b) => a.mjd - b.mjd || a.detector - b.detector);
  let pass = -1, visit = -1, passStart = 0, last = -Infinity;
  for (const f of frames) {
    const gap = f.mjd - last;
    if (gap > PASS_GAP_DAYS || f.mjd - passStart > PASS_MAX_DAYS) {
      pass++;
      passStart = f.mjd;
      visit++;
    } else if (gap > VISIT_GAP_DAYS) visit++;
    f.pass = pass;
    f.visit = visit;
    last = f.mjd;
  }
  return frames;
}

/** 0..n-1 ordered so that any prefix is spread over the whole range: middle, quarters, eighths... */
export function spreadOrder(n: number): number[] {
  const out: number[] = [];
  const seen = new Set<number>();
  for (let step = n; out.length < n; step /= 2)
    for (let x = step / 2; x < n; x += step) {
      const i = Math.floor(x);
      if (!seen.has(i)) {
        seen.add(i);
        out.push(i);
      }
    }
  return out;
}

/** Which photos to read next: `count` frames not yet taken, spread evenly over every pass and
 *  every colour band. With focusMjd, the photos nearest to that moment come first. */
export function pickFrames(frames: Frame[], taken: Set<string>, count: number, focusMjd?: number): Frame[] {
  const picked: Frame[] = [];
  const free = frames.filter((f) => !taken.has(f.key));
  if (focusMjd !== undefined) {
    const near = free.filter((f) => Math.abs(f.mjd - focusMjd) < 1).sort((a, b) => Math.abs(a.mjd - focusMjd) - Math.abs(b.mjd - focusMjd));
    picked.push(...near.slice(0, Math.ceil(count / 3)));
  }
  const buckets = new Map<string, Frame[]>();
  for (const f of frames) {
    const k = `${f.pass}/${f.detector}`;
    if (!buckets.has(k)) buckets.set(k, []);
    buckets.get(k)!.push(f);
  }
  const queues = [...buckets.values()].map((b) => spreadOrder(b.length).map((i) => b[i]));
  const used = new Set(picked.map((f) => f.key));
  for (let round = 0; picked.length < count && queues.some((q) => q.length > round); round++)
    for (const q of queues) {
      const f = q[round];
      if (!f || taken.has(f.key) || used.has(f.key) || picked.length >= count) continue;
      used.add(f.key);
      picked.push(f);
    }
  return picked.sort((a, b) => a.mjd - b.mjd);
}

// ---------- wavelength ----------

export interface WaveGrid {
  xs: number[];
  ys: number[];
  /** wave[y][x], micrometres */
  wave: number[][];
}

/** Read a detectors/D{n}_wave.json file. Accepts nested or flat grids. */
export function parseWaveGrid(j: Record<string, unknown>): WaveGrid | null {
  const raw = (j.cwave_um ?? j.wave_um ?? j.wave ?? j.cwave ?? j.values ?? j.grid) as number[] | number[][] | undefined;
  if (!Array.isArray(raw) || !raw.length) return null;
  let wave: number[][];
  if (Array.isArray(raw[0])) wave = raw as number[][];
  else {
    const nx = Number(j.nx) || Math.round(Math.sqrt(raw.length));
    wave = [];
    for (let i = 0; i < raw.length; i += nx) wave.push((raw as number[]).slice(i, i + nx));
  }
  const ny = wave.length, nx = wave[0].length;
  // naxis is [w, h] or one number for a square detector; block i spans pixels [i, i+1) * w / nx
  const [w, h] = typeof j.naxis === 'number' ? [j.naxis, j.naxis] : ((j.naxis as number[] | undefined) ?? [2040, 2040]);
  const centres = (n: number, size: number) => Array.from({ length: n }, (_v, i) => ((i + 0.5) * size) / n - 0.5);
  const xs = Array.isArray(j.xs) && j.xs.length === nx ? (j.xs as number[]) : centres(nx, w);
  const ys = Array.isArray(j.ys) && j.ys.length === ny ? (j.ys as number[]) : centres(ny, h);
  return { xs, ys, wave };
}

/** Central wavelength (micrometres) at a 0-based detector pixel, bilinear between grid samples. */
export function waveAt(g: WaveGrid, x: number, y: number): number {
  const locate = (a: number[], v: number): [number, number] => {
    let i = 0;
    while (i < a.length - 2 && a[i + 1] < v) i++;
    return [i, Math.min(1, Math.max(0, (v - a[i]) / (a[i + 1] - a[i])))];
  };
  const [i, fx] = locate(g.xs, x), [j, fy] = locate(g.ys, y);
  const w = g.wave;
  return (w[j][i] * (1 - fx) + w[j][i + 1] * fx) * (1 - fy) + (w[j + 1][i] * (1 - fx) + w[j + 1][i + 1] * fx) * fy;
}

// ---------- moving targets ----------

export interface Mover {
  /** position at a date, or null when it is not known for that date */
  at(mjd: number): [number, number] | null;
  label: string;
}

/** A star with a catalogue proper motion (mas per year; pmra already includes cos dec). Parallax is left out. */
export function properMotion(ra: number, dec: number, pmra: number, pmdec: number, epochYear: number): (mjd: number) => [number, number] {
  return (mjd) => {
    const years = 2000 + (mjd - 51544.5) / 365.25 - epochYear;
    return [ra + (pmra * years) / 3.6e6 / Math.cos(dec * D2R), dec + (pmdec * years) / 3.6e6];
  };
}

/** Predicted positions of a solar-system object at the times of its photos, joined by straight lines. */
export function trackMover(points: { mjd: number; ra: number; dec: number }[], maxGapDays = 1): (mjd: number) => [number, number] | null {
  const p = [...points].sort((a, b) => a.mjd - b.mjd);
  return (mjd) => {
    let i = p.findIndex((q) => q.mjd >= mjd);
    if (i < 0) i = p.length;
    const a = p[i - 1], b = p[i];
    if (a && b && b.mjd - a.mjd < maxGapDays) {
      const t = (mjd - a.mjd) / (b.mjd - a.mjd || 1);
      return [a.ra + (b.ra - a.ra) * t, a.dec + (b.dec - a.dec) * t];
    }
    const near = [a, b].filter(Boolean).sort((u, v) => Math.abs(u.mjd - mjd) - Math.abs(v.mjd - mjd))[0];
    return near && Math.abs(near.mjd - mjd) < 0.02 ? [near.ra, near.dec] : null;
  };
}

// ---------- pictures ----------

export function median(values: ArrayLike<number>): number {
  const v = Float32Array.from(values as ArrayLike<number>).filter((x) => Number.isFinite(x)).sort();
  if (!v.length) return NaN;
  const m = v.length >> 1;
  return v.length % 2 ? v[m] : (v[m - 1] + v[m]) / 2;
}

/** Sky level and noise of a cutout: the median, and 1.4826 times the median absolute deviation. */
export function skyStats(data: Float32Array): { sky: number; noise: number } {
  const sky = median(data);
  const dev = new Float32Array(data.length);
  for (let i = 0; i < data.length; i++) dev[i] = Math.abs(data[i] - sky);
  return { sky, noise: 1.4826 * median(dev) };
}

/** Per-pixel median of several pictures on the same grid; NaN where no picture has data. */
export function medianStack(images: Float32Array[]): Float32Array {
  const n = images[0]?.length ?? 0;
  const out = new Float32Array(n);
  const col = new Float32Array(images.length);
  for (let i = 0; i < n; i++) {
    let k = 0;
    for (const im of images) if (Number.isFinite(im[i])) col[k++] = im[i];
    if (!k) {
      out[i] = NaN;
      continue;
    }
    const s = col.subarray(0, k).sort();
    out[i] = k % 2 ? s[k >> 1] : (s[(k >> 1) - 1] + s[k >> 1]) / 2;
  }
  return out;
}

export interface Stretch {
  lo: number;
  hi: number;
  soft: number;
}

/** One stretch for every picture of a request: from 2 noise below the sky to the 99.7th percentile.
 *  The noise is that of the noisier photos (the long-wavelength bands), so none of them turns to salt and pepper. */
export function sharedStretch(images: Float32Array[], noises: number[]): Stretch {
  const sorted = noises.filter((v) => v > 0).sort((x, y) => x - y);
  const noise = sorted[Math.floor(sorted.length * 0.75)] ?? 1e-6;
  const sample: number[] = [];
  for (const im of images) {
    const step = Math.max(1, Math.floor(im.length / 2000));
    for (let i = 0; i < im.length; i += step) if (Number.isFinite(im[i])) sample.push(im[i]);
  }
  sample.sort((a, b) => a - b);
  const p = sample.length ? sample[Math.min(sample.length - 1, Math.floor(sample.length * 0.997))] : 0;
  return { lo: -2 * noise, hi: Math.max(p, 12 * noise), soft: 3 * noise };
}

/** Grey level 0..255 for a sky-subtracted value: asinh, so faint dots and bright stars both show. */
export function toGrey(v: number, s: Stretch): number {
  if (!Number.isFinite(v)) return 0;
  const t = Math.asinh((v - s.lo) / s.soft) / Math.asinh((s.hi - s.lo) / s.soft);
  return Math.round(255 * Math.min(1, Math.max(0, t)));
}

/** Grey level for a difference: 128 is no change, linear out to +/- limit. */
export function diffGrey(v: number, limit: number): number {
  if (!Number.isFinite(v)) return 128;
  return Math.round(128 + 127 * Math.min(1, Math.max(-1, v / limit)));
}

/** Mean of the grid pixels within `radius` pixels of (x, y). NaN when there is no data there. */
export function apertureMean(data: Float32Array, n: number, x: number, y: number, radius: number): number {
  let sum = 0, count = 0;
  const r = Math.ceil(radius);
  for (let j = Math.max(0, Math.floor(y) - r); j <= Math.min(n - 1, Math.floor(y) + r); j++)
    for (let i = Math.max(0, Math.floor(x) - r); i <= Math.min(n - 1, Math.floor(x) + r); i++) {
      const v = data[j * n + i];
      if (Number.isFinite(v) && Math.hypot(i + 0.5 - x, j + 0.5 - y) <= radius) {
        sum += v;
        count++;
      }
    }
  return count ? sum / count : NaN;
}
