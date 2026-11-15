// Rainbow Detective: the pure parts (types, the chart axes, the line paths), kept apart so they can be tested.

export type Kind = 'S' | 'C' | 'X' | 'ice';

export interface RainbowRound {
  id: string;
  name: string;
  truth: Kind;
  /** measured: a real ground-based spectrum; model: built from lab ice bands; spherex: a Rewind find */
  kind: 'measured' | 'model' | 'spherex';
  say: string;
  /** one value per SPHEREx colour (null where nothing was measured) */
  values?: (number | null)[];
  /** a few wide colour bins with error bars (the bonus round) */
  points?: { um: number; value: number; err: number }[];
  label?: string;
  slug?: string;
}

export interface RainbowData {
  note: string;
  um: number[];
  classes: Record<Kind, (number | null)[]>;
  rounds: RainbowRound[];
  bonus: RainbowRound | null;
}

export const UM_MIN = 0.75, UM_MAX = 5.0;

/** Wavelength to 0..1 across the chart. SPHEREx colours are spaced about evenly in log wavelength. */
export function ux(um: number): number {
  return Math.log(um / UM_MIN) / Math.log(UM_MAX / UM_MIN);
}

/** A false colour for an infrared wavelength: violet at the short end, red at the long end. */
export function hue(um: number): number {
  return Math.round(268 * (1 - Math.min(1, Math.max(0, ux(um)))));
}

/** SVG path through (um, value) pairs, broken wherever a value is missing. */
export function linePath(um: number[], vals: (number | null)[], x: (um: number) => number, y: (v: number) => number): string {
  let d = '', pen = false;
  um.forEach((u, i) => {
    const v = vals[i];
    if (v == null || !Number.isFinite(v)) {
      pen = false;
      return;
    }
    d += `${pen ? 'L' : 'M'}${x(u).toFixed(1)} ${y(v).toFixed(1)}`;
    pen = true;
  });
  return d;
}

/** The value range to draw, with a little room above and below. */
export function yRange(series: (number | null | undefined)[][]): [number, number] {
  const all = series.flat().filter((v): v is number => v != null && Number.isFinite(v));
  if (!all.length) return [0, 2];
  const lo = Math.min(...all), hi = Math.max(...all), pad = Math.max(0.06, (hi - lo) * 0.12);
  return [lo - pad, hi + pad];
}

/** The factor that lays a template over the measured points best (least squares), so the shapes can be compared. */
export function scaleTo(um: number[], tpl: (number | null)[], xs: number[], ys: (number | null)[]): number {
  let num = 0, den = 0;
  xs.forEach((x, i) => {
    const y = ys[i];
    if (y == null || !Number.isFinite(y)) return;
    // the template colour nearest in log wavelength
    let j = 0;
    um.forEach((u, k) => Math.abs(Math.log(u / x)) < Math.abs(Math.log(um[j] / x)) && (j = k));
    const t = tpl[j];
    if (t == null || !Number.isFinite(t)) return;
    num += y * t;
    den += t * t;
  });
  return den > 0 ? num / den : 1;
}
