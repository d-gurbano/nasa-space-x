// "Predict the orbit": the numbers behind a round. Positions come from the object's orbit
// (two-body, heliocentric ecliptic), flattened to the ecliptic plane: a map seen from above the
// solar system. The guess-area sizes are the engine's own numbers from the object page.
import { DEG, isValidElements, meanMotion, orbitPolyline, positionAt, type Elements, type Vec3 } from '../../lib/kepler';
import { mjdFromIso } from '../../lib/time';
import type { IndexObject, ObjectPage } from '../../lib/types';

export type P2 = [number, number];
export const AU_KM = 149597870.7;
export const STEP_DAYS = 15; // between the known positions
export const AHEAD_DAYS = 30; // from the last known position to the answer

export interface Sizes {
  before_km: number;
  after_km: number;
  factor: number;
  /** true = the engine's "as if Rewind had run right after discovery" scenario; false = today's full orbit. */
  scenario: boolean;
  at_iso: string;
}

export interface WhereRound {
  slug: string;
  name: string;
  kind: string;
  days_earlier: number | null;
  dots: { mjd: number; p: P2 }[];
  target: { mjd: number; p: P2 };
  path: P2[];
  sizes: Sizes;
  /** Shape of the guess area on the map: minor/major axis and the tilt of the major axis (radians). */
  shape: { ratio: number; angle: number };
}

interface Impact {
  first_known_obs_iso?: string | null;
  one_year_after_last_obs?: { iso?: string; sigma3_km_before?: number; sigma3_km_after?: number } | null;
  at_discovery_scenario?: { at_iso?: string; sigma3_km_before?: number; sigma3_km_after?: number; converged?: boolean } | null;
}

const flat = (v: Vec3): P2 => [v[0], v[1]];
const ok = (x: unknown): x is number => typeof x === 'number' && Number.isFinite(x) && x > 0;

/** The before/after guess-area sizes: the discovery-week scenario when the engine has one, else today's orbit. */
export function sizesOf(impact: Impact | null | undefined): Sizes | null {
  const s = impact?.at_discovery_scenario, y = impact?.one_year_after_last_obs;
  if (s && s.converged && ok(s.sigma3_km_before) && ok(s.sigma3_km_after) && s.at_iso)
    return { before_km: s.sigma3_km_before, after_km: s.sigma3_km_after, factor: s.sigma3_km_before / s.sigma3_km_after, scenario: true, at_iso: s.at_iso };
  if (y && ok(y.sigma3_km_before) && ok(y.sigma3_km_after) && y.iso)
    return { before_km: y.sigma3_km_before, after_km: y.sigma3_km_after, factor: y.sigma3_km_before / y.sigma3_km_after, scenario: false, at_iso: y.iso };
  return null;
}

/** Axis ratio and tilt of a cloud of points (from its 2x2 covariance). */
export function cloudShape(pts: P2[]): { ratio: number; angle: number } {
  const n = pts.length;
  if (n < 3) return { ratio: 0.35, angle: 0 };
  const mx = pts.reduce((a, p) => a + p[0], 0) / n, my = pts.reduce((a, p) => a + p[1], 0) / n;
  let xx = 0, yy = 0, xy = 0;
  for (const [x, y] of pts) (xx += (x - mx) ** 2), (yy += (y - my) ** 2), (xy += (x - mx) * (y - my));
  const tr = xx + yy, d = Math.sqrt(Math.max(0, ((xx - yy) / 2) ** 2 + xy * xy));
  const big = tr / 2 + d, small = Math.max(0, tr / 2 - d);
  if (!(big > 0)) return { ratio: 0.35, angle: 0 };
  return { ratio: Math.sqrt(small / big), angle: 0.5 * Math.atan2(2 * xy, xx - yy) };
}

export function buildRound(o: IndexObject, page: ObjectPage): WhereRound | null {
  const impact = (page.impact ?? null) as Impact | null;
  const sizes = sizesOf(impact);
  if (!sizes || !isValidElements(page.orbit)) return null;
  let el = page.orbit as Elements;
  // a very long orbit: the rounded mean anomaly is days off, so take it from the perihelion time
  const tp = (page.orbit as { tp_jd?: number }).tp_jd;
  if (el.a > 50 && el.e < 1 && typeof tp === 'number' && Number.isFinite(tp)) el = { ...el, M: (meanMotion(el.a) * (el.epoch_mjd - (tp - 2400000.5))) / DEG };
  const t0 = mjdFromIso(impact?.first_known_obs_iso ?? o.first_known_obs_iso ?? o.discovered.iso);
  if (!Number.isFinite(t0)) return null;
  const at = (mjd: number) => ({ mjd, p: flat(positionAt(el, mjd)) });
  const dots = [0, 1, 2].map((k) => at(t0 + k * STEP_DAYS));
  const target = at(t0 + 2 * STEP_DAYS + AHEAD_DAYS);
  // the shape of the guess area: the real clone cloud on the date nearest to the size estimate
  let shape = { ratio: 0.35, angle: Math.atan2(target.p[1] - dots[2].p[1], target.p[0] - dots[2].p[0]) };
  const c = page.cloud;
  if (c?.before?.length) {
    const want = mjdFromIso(sizes.at_iso);
    const k = c.dates_mjd.reduce((b, d, i) => (Math.abs(d - want) < Math.abs(c.dates_mjd[b] - want) ? i : b), 0);
    if (c.before[k]?.length >= 3) shape = cloudShape(c.before[k].map(flat));
  }
  return {
    slug: o.slug, name: o.name, kind: o.kind, days_earlier: o.days_before_first_known_obs ?? null,
    dots, target, sizes, shape,
    path: orbitPolyline(el, 360, 80).map(flat),
  };
}

/** Which rounds to play: up to `n`, the ones where the old photos matter most last. */
export function pickRounds(all: WhereRound[], n = 5): WhereRound[] {
  return [...all].sort((a, b) => Number(b.sizes.scenario) - Number(a.sizes.scenario) || b.sizes.factor - a.sizes.factor).slice(0, n).sort((a, b) => a.sizes.factor - b.sizes.factor);
}

export const dist2 = (a: P2, b: P2) => Math.hypot(a[0] - b[0], a[1] - b[1]);

/** 100 for a perfect guess, 0 for a guess no better than "it stays where it was last seen". */
export function scoreGuess(guess: P2, truth: P2, last: P2): number {
  const travel = dist2(truth, last) || 1e-9;
  return Math.round(100 * Math.max(0, 1 - dist2(guess, truth) / travel));
}

/** "2.7 million km", "320,000 km". */
export function fmtKm(km: number): string {
  if (km >= 1e6) return `${(km / 1e6).toFixed(km >= 1e7 ? 0 : 1)} million km`;
  return `${Math.round(km / (km >= 1e4 ? 1000 : 1)) * (km >= 1e4 ? 1000 : 1)}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',') + ' km';
}

/** "5.9x smaller", "about the same", "1.1x larger". */
export function factorText(f: number): string {
  if (f >= 1.05) return `${f.toFixed(1)}x smaller`;
  if (f > 0.95) return 'about the same';
  return `${(1 / f).toFixed(1)}x larger`;
}
