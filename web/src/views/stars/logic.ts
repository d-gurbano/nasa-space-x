// Test targets logic, kept apart from the page so it can be tested: reading the engine's
// CSV tables, the "years of motion" track, the brightness curve, and where the star should
// be in each pass picture.
import { mjdFromIso } from '../../lib/time';
import type { StarManifest } from '../../lib/types';

export type Row = Record<string, string>;

/** The engine's tables have no quoted cells, so a plain split is enough. */
export function parseCsv(text: string): Row[] {
  const [head, ...lines] = text.trim().split(/\r?\n/);
  const keys = head.split(',');
  return lines.map((l) => {
    const v = l.split(',');
    return Object.fromEntries(keys.map((k, i) => [k, v[i] ?? '']));
  });
}

const num = (s: string | undefined) => (s ? +s : NaN);
const median = (v: number[]) => {
  const s = [...v].sort((a, b) => a - b);
  return s.length % 2 ? s[(s.length - 1) / 2] : (s[s.length / 2 - 1] + s[s.length / 2]) / 2;
};
const mean = (v: number[]) => v.reduce((a, b) => a + b, 0) / v.length;

const FAMILIES: [RegExp, string][] = [
  [/^DASCH/, 'Harvard glass plate'],
  [/^DSS/, 'Digitized Sky Survey'],
  [/^2MASS/, '2MASS infrared survey'],
  [/^(unTimely|NEOWISE)/, 'WISE space telescope'],
  [/^SPHEREx/, 'SPHEREx'],
];
const familyOf = (source: string) => FAMILIES.find(([re]) => re.test(source))?.[1] ?? source;

/** One dot of the track: the photos of one telescope in one year (all SPHEREx passes together). */
export interface TrackPoint { family: string; spherex: boolean; year: number; first: number; last: number; n: number; moved: number; miss: number }
export interface Track {
  points: TrackPoint[];
  /** The prediction: [year, arcsec moved since the first measured photo]. */
  line: [number, number][];
  /** Older photos left out because the target is too faint for that survey. */
  tooFaint: number;
}

/**
 * The star's path over the decades, from <target>_decades_positions.csv. Distances are in
 * arcsec from where the star was predicted to be in the first photo that shows it.
 */
export function track(rows: Row[]): Track | null {
  const all = rows
    .map((r) => ({
      family: familyOf(r.source), year: num(r.year), note: r.note ?? '',
      pe: num(r.pred_east_from_ref), pn: num(r.pred_north_from_ref),
      me: num(r.meas_east_from_ref), mn: num(r.meas_north_from_ref), miss: num(r.resid_arcsec),
    }))
    .filter((r) => isFinite(r.year) && isFinite(r.pe) && isFinite(r.pn))
    .sort((a, b) => a.year - b.year);
  const seen = all.filter((r) => isFinite(r.me) && isFinite(r.mn));
  if (seen.length < 2) return null;
  const o = seen[0];
  const moved = (e: number, n: number) => Math.hypot(e - o.pe, n - o.pn);
  const groups = new Map<string, typeof seen>();
  for (const r of seen) {
    const key = r.family === 'SPHEREx' ? r.family : `${r.family} ${Math.floor(r.year)}`;
    groups.set(key, [...(groups.get(key) ?? []), r]);
  }
  // a dot sits where its last photo is, so the SPHEREx dot is the latest pass
  const points = [...groups.values()].map((g) => {
    const end = g[g.length - 1];
    return {
      family: end.family, spherex: end.family === 'SPHEREx', n: g.length,
      year: end.year, first: g[0].year, last: end.year, moved: moved(end.me, end.mn),
      miss: mean(g.map((r) => (isFinite(r.miss) ? r.miss : Math.hypot(r.me - r.pe, r.mn - r.pn)))),
    };
  });
  return {
    points,
    line: all.filter((r) => r.year >= o.year).map((r) => [r.year, moved(r.pe, r.pn)]),
    tooFaint: all.filter((r) => !isFinite(r.me) && /too faint/.test(r.note)).length,
  };
}

/** Magnitude difference to per cent brighter (+) or fainter (-). */
export const pctFromMag = (dmag: number) => (10 ** (-0.4 * dmag) - 1) * 100;

/** band 0 = detectors 1 to 3 (0.75 to 2.4 µm), band 1 = detectors 4 to 6 (2.4 to 5 µm). */
export interface LcPoint { mjd: number; pct: number; band: 0 | 1; saturated: boolean; pass: number }
export interface LcMedian { mjd: number; pct: number; band: 0 | 1; pass: number; n: number }
export const BANDS = ['0.75 to 2.4 µm', '2.4 to 5 µm'];

/**
 * Brightness of each photo compared with the star's own median at the same wavelength,
 * from <target>_lightcurve.csv, and the median of each pass in each half of the spectrum.
 */
export function lightCurve(rows: Row[]): { points: LcPoint[]; medians: LcMedian[] } {
  const points = rows
    .map((r) => ({
      mjd: num(r.mjd), pct: pctFromMag(num(r.dmag_vs_median_sed)), band: (num(r.detector) > 3 ? 1 : 0) as 0 | 1,
      saturated: r.saturated === 'True', pass: num(r.pass),
    }))
    .filter((p) => isFinite(p.mjd) && isFinite(p.pct) && isFinite(p.pass));
  const groups = new Map<string, LcPoint[]>();
  for (const p of points) groups.set(`${p.band} ${p.pass}`, [...(groups.get(`${p.band} ${p.pass}`) ?? []), p]);
  const medians = [...groups.values()]
    .map((g) => ({ band: g[0].band, pass: g[0].pass, n: g.length, mjd: median(g.map((p) => p.mjd)), pct: median(g.map((p) => p.pct)) }))
    .sort((a, b) => a.band - b.band || a.mjd - b.mjd);
  return { points, medians };
}

/**
 * Where the star should be in each pass picture, in PNG pixels: the mean predicted spot of
 * the photos taken within 25 days of the pass date. null when no photo is that close.
 */
export function passSpots(m: Pick<StarManifest, 'seasons' | 'frames'>): ([number, number] | null)[] {
  return m.seasons.map((s) => {
    const at = mjdFromIso(s.iso);
    const near = m.frames.filter((f) => f.pred_xy && Math.abs(f.mjd - at) <= 25);
    return near.length ? [mean(near.map((f) => f.pred_xy[0])), mean(near.map((f) => f.pred_xy[1]))] : null;
  });
}

/** A round step for axis ticks: 1, 2 or 5 times a power of ten, giving about `count` ticks. */
export function niceStep(span: number, count: number): number {
  const raw = span / count, pow = 10 ** Math.floor(Math.log10(raw)), m = raw / pow;
  return (m < 1.5 ? 1 : m < 3 ? 2 : m < 7 ? 5 : 10) * pow;
}
