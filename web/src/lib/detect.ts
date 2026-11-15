// Detectives game logic, kept apart from the page so it can be tested: which part of each
// photo is shown, whether a mark is right, and how the photos are smoothed and stretched.
// Every round gets the same treatment, so the look of a photo does not give the answer away.
import type { DetectiveRounds } from './types';

export type Round = DetectiveRounds['rounds'][number];
export type XY = [number, number];
/** The square part of the PNG that is shown, in PNG pixels. */
export interface Window { x: number; y: number; size: number }

const SKY_ARCSEC = 121.5; // every round shows this much sky across
const SPHEREX_PX = 6.15; // arcsec per SPHEREx pixel
const SMOOTH = 0.42; // blur radius (sigma) in SPHEREx pixels: hides the pixel blocks, keeps the dots

/** Arcsec per PNG pixel, from the note in rounds.json: asteroid cutouts are 324 px at 1.5 / 4, sky patches 320 px at 6.15 / 5. */
const pngScale = (width: number) => (width === 324 ? 1.5 / 4 : SPHEREX_PX / 5);

// a stable fraction 0..1 from a string, so a round always shows the same part of the sky
function frac(s: string): number {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) h = Math.imul(h ^ s.charCodeAt(i), 16777619);
  return ((h >>> 0) % 1000) / 1000;
}

/**
 * The part of a round's photos to show: the same width of sky for every round. Wide sky
 * patches are cropped; the crop always holds the whole track, but not in its centre.
 */
export function windowOf(r: Pick<Round, 'id' | 'track_xy'>, width: number): Window {
  const size = Math.min(width, Math.round(SKY_ARCSEC / pngScale(width)));
  const free = width - size;
  const edge = 0.14 * size; // keep the mover this far inside the frame
  const at = (axis: 0 | 1): number | null => {
    let lo = 0.15 * free, hi = 0.85 * free;
    if (r.track_xy) {
      const v = r.track_xy.map((p) => p[axis]);
      lo = Math.max(0, Math.max(...v) + edge - size);
      hi = Math.min(free, Math.min(...v) - edge);
      if (lo > hi) return null;
    }
    return Math.round(lo + frac(r.id + axis) * (hi - lo));
  };
  const x = at(0), y = at(1);
  // a track too long for the crop: show the whole photo
  return x == null || y == null ? { x: 0, y: 0, size: width } : { x, y, size };
}

/** Blur radius in pixels of a grid that is `grid` pixels across, for a window of a PNG `width` pixels wide. */
export function smoothing(w: Window, width: number, grid: number): number {
  return (SMOOTH * (SPHEREX_PX / pngScale(width)) * grid) / w.size;
}

/** How close a mark must be, in PNG pixels: the data's tolerance, but never more than a tenth of what is shown. */
export function hitRadius(r: Pick<Round, 'tolerance_px'>, w: Window): number {
  return Math.min(r.tolerance_px, 0.1 * w.size);
}

export type Outcome = 'hit' | 'far' | 'missed' | 'clear' | 'alarm';

/** mark = where the player put the ring (PNG pixels), or null for "Nothing moves". The ring counts if it covers the mover in any photo. */
export function judge(r: Pick<Round, 'track_xy' | 'tolerance_px'>, w: Window, mark: XY | null): Outcome {
  if (!r.track_xy) return mark ? 'alarm' : 'clear';
  if (!mark) return 'missed';
  const reach = hitRadius(r, w);
  return r.track_xy.some((p) => Math.hypot(p[0] - mark[0], p[1] - mark[1]) <= reach) ? 'hit' : 'far';
}

export const isRight = (o: Outcome | undefined) => o === 'hit' || o === 'clear';

const utc = (iso: string) => Date.parse(/Z$|[+-]\d\d:\d\d$/.test(iso) ? iso : iso + 'Z');

/** Time since the first photo: "+2 min", "+3.2 h", "+2.1 d". */
export function sinceFirst(first: string, iso: string): string {
  const min = (utc(iso) - utc(first)) / 60000;
  return min < 60 ? `+${Math.round(min)} min` : min < 2880 ? `+${(min / 60).toFixed(1)} h` : `+${(min / 1440).toFixed(1)} d`;
}

/** "31 Aug 2026, 14:48" (UTC). */
export function photoTime(iso: string): string {
  return new Date(utc(iso)).toLocaleString('en-GB', { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit', timeZone: 'UTC' });
}

/** Gaussian blur of an n x n image. Edges repeat. */
export function blur(src: Float32Array, n: number, sigma: number): Float32Array {
  const rad = Math.max(1, Math.ceil(sigma * 3));
  const k = Float32Array.from({ length: 2 * rad + 1 }, (_, i) => Math.exp(-((i - rad) ** 2) / (2 * sigma * sigma)));
  const sum = k.reduce((a, b) => a + b, 0);
  const clamp = (v: number) => (v < 0 ? 0 : v >= n ? n - 1 : v);
  const pass = (a: Float32Array, dx: number, dy: number) => {
    const out = new Float32Array(n * n);
    for (let y = 0; y < n; y++)
      for (let x = 0; x < n; x++) {
        let s = 0;
        for (let i = -rad; i <= rad; i++) s += k[i + rad] * a[clamp(y + i * dy) * n + clamp(x + i * dx)];
        out[y * n + x] = s / sum;
      }
    return out;
  };
  return pass(pass(src, 1, 0), 0, 1);
}

const SKY = 0.07; // the sky level, as a fraction of white
const KNEE = 16; // a dot this many times the sky noise above the sky is shown half way to white

/**
 * One brightness stretch for all photos of a round, set by the round's own sky noise: the
 * typical sky becomes dark grey, and brightness then rises along a soft curve, so faint dots
 * show and bright stars keep their shape. Every round looks equally noisy, whatever it holds.
 * Returns grey levels 0..255.
 */
export function stretch(frames: Float32Array[]): Uint8ClampedArray[] {
  const all = new Float32Array(frames.reduce((a, f) => a + f.length, 0));
  frames.reduce((at, f) => (all.set(f, at), at + f.length), 0);
  all.sort();
  const pct = (q: number) => all[Math.floor(q * (all.length - 1))];
  const sky = pct(0.5);
  // a flat sky has no noise to measure: fall back to a small part of the bright range
  const noise = Math.max(sky - pct(0.16), 0.02 * (pct(0.997) - sky), 0.1);
  return frames.map((f) =>
    Uint8ClampedArray.from(f, (v) => {
      const t = (v - sky) / noise;
      return 255 * (SKY + (1 - SKY) * (t > 0 ? t / (t + KNEE) : t / KNEE));
    }),
  );
}
