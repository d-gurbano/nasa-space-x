// Connect the dots: pure logic. Builds the field of detections for a round and checks a pick.

export interface DotsRound {
  field: string;
  ra: number;
  dec: number;
  half_arcsec: number;
  mjd: [number, number, number];
  iso: [string, string, string];
  frames: string[];
  movers: { name: string; v: number; pts: [number, number][] }[];
  partial: { t: number; x: number; y: number }[];
  stars: [number, number, number][];
}
export interface DotsData { source: string; rounds: DotsRound[] }

export type DetKind = 'mover' | 'partial' | 'star' | 'noise';
/** One dot on the field. t is 0, 1 or 2; a star is seen at every time and has t = -1. */
export interface Det { id: number; t: number; x: number; y: number; kind: DetKind; track?: number }

/** Simulated noise dots per time, by round. */
export const NOISE = [3, 6, 9, 12, 14, 18];

/** A small seeded random generator (mulberry32), so a round can be replayed in tests. */
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

export function buildField(r: DotsRound, k: number, rand: () => number): Det[] {
  const d: Det[] = [];
  const add = (t: number, x: number, y: number, kind: DetKind, track?: number) => d.push({ id: 0, t, x, y, kind, track });
  r.movers.forEach((m, i) => m.pts.forEach(([x, y], t) => add(t, x, y, 'mover', i)));
  r.partial.forEach((p) => add(p.t, p.x, p.y, 'partial'));
  r.stars.forEach(([x, y]) => add(-1, x, y, 'star'));
  const h = r.half_arcsec * 0.95, n = NOISE[Math.min(k, NOISE.length - 1)];
  for (let t = 0; t < 3; t++) for (let i = 0; i < n; i++) add(t, (rand() * 2 - 1) * h, (rand() * 2 - 1) * h, 'noise');
  // shuffle, so the order of the dots (and of Tab) says nothing
  for (let i = d.length - 1; i > 0; i--) {
    const j = Math.floor(rand() * (i + 1));
    [d[i], d[j]] = [d[j], d[i]];
  }
  d.forEach((x, i) => (x.id = i));
  return d;
}

/** How far the middle dot is from where a steady straight-line motion puts it, as a fraction of the track length. */
export function offLine(p: [number, number][], mjd: number[]): number {
  const f = (mjd[1] - mjd[0]) / (mjd[2] - mjd[0]);
  const ex = p[0][0] + (p[2][0] - p[0][0]) * f, ey = p[0][1] + (p[2][1] - p[0][1]) * f;
  const len = Math.hypot(p[2][0] - p[0][0], p[2][1] - p[0][1]) || 1;
  return Math.hypot(p[1][0] - ex, p[1][1] - ey) / len;
}

export type Check =
  | { ok: true; track: number }
  | { ok: false; why: 'times' | 'line' | 'chance'; off?: number };

/** Three picked dots: one per time, all from one real track. */
export function checkPick(dets: Det[], ids: number[], mjd: number[]): Check {
  const p = ids.map((i) => dets[i]).sort((a, b) => a.t - b.t);
  if (p.length !== 3 || p.some((x, i) => x.t !== i)) return { ok: false, why: 'times' };
  if (p.every((x) => x.kind === 'mover' && x.track === p[0].track)) return { ok: true, track: p[0].track! };
  const off = offLine(p.map((x) => [x.x, x.y]), mjd);
  return { ok: false, why: off > 0.12 ? 'line' : 'chance', off };
}
