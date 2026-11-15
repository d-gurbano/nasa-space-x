// Shift-and-stack, the heart of Rewind, small enough to run on every turn of a dial.
// Frames are grey images of ONE fixed patch of sky. A motion (direction + speed) shifts each
// frame back along that path to the middle time of the set, and the shifted frames are averaged.
// If the motion is the object's real one, its light lands on one spot and adds up; if not, it smears.
// Angle convention (as in rounds.json): 0 = up (north), clockwise, in image pixels per hour.

export interface Frames {
  w: number;
  h: number;
  px: Float32Array[];
  dt: number[]; // hours since the first frame
}

export interface Motion {
  angle: number; // degrees, 0 = up, clockwise
  rate: number; // image pixels per hour
}

export type XY = [number, number];

export function velocity(m: Motion): XY {
  const a = (m.angle * Math.PI) / 180;
  return [m.rate * Math.sin(a), -m.rate * Math.cos(a)];
}

export function midTime(dt: number[]): number {
  return (Math.min(...dt) + Math.max(...dt)) / 2;
}

/** Hours from the middle time to the farthest frame. */
export function halfSpan(dt: number[]): number {
  return (Math.max(...dt) - Math.min(...dt)) / 2;
}

/** Whole-pixel shift for each frame that undoes the motion (to the middle time). */
export function shifts(dt: number[], m: Motion): XY[] {
  const [vx, vy] = velocity(m);
  const t0 = midTime(dt);
  return dt.map((t) => [Math.round(-(t - t0) * vx), Math.round(-(t - t0) * vy)]);
}

/**
 * Average the frames after shifting each by the motion. out[k] = mean of the frames that cover
 * pixel k (NaN-free: uncovered pixels get `fill`); cover[k] = how many frames covered it.
 */
export function stack(f: Frames, m: Motion, out: Float32Array, cover: Uint8Array, fill = 0): void {
  const { w, h } = f;
  out.fill(0);
  cover.fill(0);
  shifts(f.dt, m).forEach(([sx, sy], i) => {
    const src = f.px[i];
    const x0 = Math.max(0, sx), x1 = Math.min(w, w + sx);
    const y0 = Math.max(0, sy), y1 = Math.min(h, h + sy);
    for (let y = y0; y < y1; y++) {
      const o = y * w, s = (y - sy) * w - sx;
      for (let x = x0; x < x1; x++) {
        out[o + x] += src[s + x];
        cover[o + x]++;
      }
    }
  });
  for (let k = 0; k < out.length; k++) out[k] = cover[k] ? out[k] / cover[k] : fill;
}

/** Sum and pixel count of the square box of half-size r around (cx, cy), clipped to the image. */
export function boxSum(img: Float32Array, w: number, h: number, cx: number, cy: number, r: number): [number, number] {
  const x0 = Math.max(0, Math.round(cx - r)), x1 = Math.min(w - 1, Math.round(cx + r));
  const y0 = Math.max(0, Math.round(cy - r)), y1 = Math.min(h - 1, Math.round(cy + r));
  let s = 0;
  for (let y = y0; y <= y1; y++) for (let x = x0; x <= x1; x++) s += img[y * w + x];
  return [s, Math.max(0, x1 - x0 + 1) * Math.max(0, y1 - y0 + 1)];
}

export function median(v: number[]): number {
  const s = [...v].sort((a, b) => a - b);
  const n = s.length;
  return n ? (n % 2 ? s[(n - 1) / 2] : (s[n / 2 - 1] + s[n / 2]) / 2) : 0;
}

/** Robust spread: 1.4826 x the median absolute deviation. */
export function robustSigma(v: number[]): number {
  const m = median(v);
  return 1.4826 * median(v.map((x) => Math.abs(x - m)));
}

export function rng(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** How box sums of each size scatter on empty parts of an image: the noise for an S/N. */
export interface Calib {
  radii: number[];
  med: number[];
  sigma: number[];
}

/** `ok(x, y, r)` may veto a spot (for example where not every photo overlaps). */
export function calibrate(img: Float32Array, w: number, h: number, avoid: XY, radii: number[], seed = 7, n = 240, ok?: (x: number, y: number, r: number) => boolean): Calib {
  const rand = rng(seed);
  const med: number[] = [], sigma: number[] = [], used: number[] = [];
  for (const r of radii) {
    const sums: number[] = [];
    for (let tries = 0; sums.length < n && tries < n * 6; tries++) {
      const x = r + rand() * (w - 2 * r), y = r + rand() * (h - 2 * r);
      if (Math.hypot(x - avoid[0], y - avoid[1]) < 2 * r + 6 || (ok && !ok(x, y, r))) continue;
      sums.push(boxSum(img, w, h, x, y, r)[0]);
    }
    if (sums.length < 40) continue; // not enough empty sky for boxes this big
    used.push(r);
    med.push(median(sums));
    sigma.push(robustSigma(sums) || 1e-9);
  }
  return { radii: used, med, sigma };
}

/** S/N at a spot: the best of the calibrated box sizes, so a slightly smeared dot still counts a little. */
export function snrAt(img: Float32Array, w: number, h: number, p: XY, c: Calib): number {
  let best = c.radii.length ? -Infinity : 0;
  c.radii.forEach((r, i) => {
    best = Math.max(best, (boxSum(img, w, h, p[0], p[1], r)[0] - c.med[i]) / c.sigma[i]);
  });
  return best;
}

/** The brightest spot after a light box smoothing (where the dot sits in the true stack). */
export function findPeak(img: Float32Array, w: number, h: number, r: number, margin = 8, ok?: (x: number, y: number, r: number) => boolean): XY {
  let best = -Infinity, at: XY = [w / 2, h / 2];
  const step = Math.max(1, Math.floor(r / 2));
  for (let y = margin; y < h - margin; y += step)
    for (let x = margin; x < w - margin; x += step) {
      if (ok && !ok(x, y, r)) continue;
      const s = boxSum(img, w, h, x, y, r)[0];
      if (s > best) (best = s), (at = [x, y]);
    }
  return at;
}

/** How far apart (pixels) two motions put the object at the ends of the set: the error that smears it. */
export function endError(dt: number[], a: Motion, b: Motion): number {
  const va = velocity(a), vb = velocity(b);
  return Math.hypot(va[0] - vb[0], va[1] - vb[1]) * halfSpan(dt);
}

/** Pixel values of a sample of the image, for its median and noise. */
export function pixelStats(img: Float32Array, n = 4096): { med: number; sigma: number } {
  const step = Math.max(1, Math.floor(img.length / n));
  const v: number[] = [];
  for (let k = 0; k < img.length; k += step) v.push(img[k]);
  return { med: median(v), sigma: robustSigma(v) || 1e-9 };
}

export const wrap360 = (a: number) => ((a % 360) + 360) % 360;
