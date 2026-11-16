// Pulse reader logic: sine fits to the measured brightness points, period scoring, and round building.
// The points come from web/scripts/games/pulse-photometry.py (wing photometry of real SPHEREx stamps).

export interface Bin { mjd: number; dmag: number; err: number; scatter: number; n: number }
export interface Fit { best: number; lo: number; hi: number; red_chi2: number; span_days: number }
export interface PulseData {
  method: string;
  rdra: { n_stamps: number; n_used: number; n_channels: number; short: Bin[]; long: Bin[]; fit_short: Fit; fit_long: Fit; seasons: Season[]; vsx: { period: number; epoch_jd: number; max: string; min: string; spectral: string } };
  rwaur: { n_stamps: number; n_used: number; n_channels: number; short: Bin[]; long: Bin[]; seasons: Season[] };
}
export interface Season { iso: string; n_frames: number; png: string }

export type Band = 'short' | 'long';
export type Round =
  | { type: 'compare'; star: 'rdra'; a: number; b: number; truth: 'a' | 'b'; da: number; db: number }
  | { type: 'period'; star: 'rdra'; band: Band }
  | { type: 'trend'; star: 'rwaur'; passes: { mjd: number; dmag: number }[]; truth: Trend }
  | { type: 'few'; star: 'rwaur' };
export type Trend = 'fade' | 'brighten' | 'none';
export type Grade = 'ok' | 'half' | 'no';

export const isoToMjd = (iso: string) => Date.parse(iso.length <= 10 ? iso + 'T00:00:00Z' : iso) / 86400000 + 40587;
export const mjdToIso = (mjd: number) => new Date((mjd - 40587) * 86400000).toISOString().slice(0, 10);

/** Weighted least-squares fit of y = a sin(2 pi t / P) + b cos(2 pi t / P) + c. */
export function fitSine(t: number[], y: number[], err: number[], P: number) {
  const M = [[0, 0, 0], [0, 0, 0], [0, 0, 0]], v = [0, 0, 0];
  const row = (x: number) => [Math.sin((2 * Math.PI * x) / P), Math.cos((2 * Math.PI * x) / P), 1];
  t.forEach((x, i) => {
    const r = row(x), w = 1 / Math.max(err[i], 0.01) ** 2;
    for (let j = 0; j < 3; j++) {
      v[j] += w * r[j] * y[i];
      for (let k = 0; k < 3; k++) M[j][k] += w * r[j] * r[k];
    }
  });
  const [a, b, c] = solve3(M, v);
  const at = (x: number) => { const r = row(x); return a * r[0] + b * r[1] + c; };
  const res = t.map((x, i) => y[i] - at(x));
  const rms = Math.sqrt(res.reduce((s, r) => s + r * r, 0) / Math.max(1, res.length));
  return { a, b, c, amp: Math.hypot(a, b), rms, at };
}

function solve3(M: number[][], v: number[]): number[] {
  const det = (m: number[][]) => m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1]) - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0]) + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0]);
  const D = det(M);
  if (!D) return [0, 0, v[2] / (M[2][2] || 1)];
  return [0, 1, 2].map((j) => det(M.map((r, i) => r.map((x, k) => (k === j ? v[i] : x)))) / D);
}

/** Within 10% of the catalogue period is right, within 25% is close. */
export function gradePeriod(guess: number, truth: number): Grade {
  const f = Math.abs(guess - truth) / truth;
  return f <= 0.1 ? 'ok' : f <= 0.25 ? 'half' : 'no';
}
export const points = (g: Grade) => (g === 'ok' ? 10 : g === 'half' ? 5 : 0);

const median = (a: number[]) => {
  const s = [...a].sort((x, y) => x - y), m = s.length >> 1;
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
};

/** Median brightness change of the bins within `win` days of a date, or null if none. */
export function dmagNear(bins: Bin[], mjd: number, win = 20): number | null {
  const near = bins.filter((b) => Math.abs(b.mjd - mjd) <= win).map((b) => b.dmag);
  return near.length ? median(near) : null;
}

/** Group bins into passes (gaps over 60 days), one median per pass. */
export function passes(bins: Bin[]): { mjd: number; dmag: number }[] {
  const out: Bin[][] = [];
  bins.forEach((b, i) => (i && b.mjd - bins[i - 1].mjd < 60 ? out[out.length - 1].push(b) : out.push([b])));
  return out.map((g) => ({ mjd: median(g.map((b) => b.mjd)), dmag: median(g.map((b) => b.dmag)) }));
}

export function trend(p: { dmag: number }[], tol = 0.1): Trend {
  const steps = p.slice(1).map((x, i) => x.dmag - p[i].dmag);
  if (steps.length && steps.every((s) => s > tol)) return 'fade';
  if (steps.length && steps.every((s) => s < -tol)) return 'brighten';
  return 'none';
}

/** Season pairs to compare, by date, checked against the measured points. Pairs closer than 0.2 mag are dropped. */
export const PAIRS: [string, string][] = [['2025-07-14', '2025-10-17'], ['2026-06-23', '2026-09-16']];

export function buildRounds(d: PulseData, seasons: Season[]): Round[] {
  const rounds: Round[] = [];
  for (const [ia, ib] of PAIRS) {
    const a = seasons.findIndex((s) => s.iso === ia), b = seasons.findIndex((s) => s.iso === ib);
    if (a < 0 || b < 0) continue;
    const da = dmagNear(d.rdra.short, isoToMjd(ia)), db = dmagNear(d.rdra.short, isoToMjd(ib));
    if (da == null || db == null || Math.abs(da - db) < 0.2) continue;
    rounds.push({ type: 'compare', star: 'rdra', a, b, truth: da < db ? 'a' : 'b', da, db });
  }
  rounds.push({ type: 'period', star: 'rdra', band: 'short' }, { type: 'period', star: 'rdra', band: 'long' });
  const p = passes(d.rwaur.long);
  if (p.length >= 2) rounds.push({ type: 'trend', star: 'rwaur', passes: p, truth: trend(p) }, { type: 'few', star: 'rwaur' });
  return rounds;
}
