// Blink!: the pure parts (types, the tap test, round order, wording of time spans), kept apart so they can be tested.

export interface BlinkRound {
  id: string;
  name: string;
  /** the two images, north up, same patch of sky */
  imgs: [string, string];
  /** the asteroid's position in each image, in image pixels (x right, y down) */
  pos: [[number, number], [number, number]];
  mjd: [number, number];
  hours: number;
  moved_px: number;
  moved_arcsec: number;
  um: [number, number];
  detector: number;
  V: number;
  /** the asteroid's peak, in units of the image noise (the fainter of the two images) */
  snr: number;
  r_au: number;
  delta_au: number;
  obsid: [string, string];
}

export interface BlinkData {
  n: number;
  arcsec_per_px: number;
  note: string;
  rounds: BlinkRound[];
}

/** A tap counts if it lands within this many image pixels of the asteroid in either image. */
export const TOL = 2.5;

/** Distance from a tap to the nearer of the asteroid's two positions, in image pixels. */
export function missBy(r: Pick<BlinkRound, 'pos'>, x: number, y: number): number {
  return Math.min(...r.pos.map(([px, py]) => Math.hypot(x - px, y - py)));
}

export const isHit = (r: Pick<BlinkRound, 'pos'>, x: number, y: number, tol = TOL) => missBy(r, x, y) <= tol;

/** How easy a round is: a bright asteroid that moves far is easy. Higher is easier. */
export const ease = (r: Pick<BlinkRound, 'snr' | 'moved_px'>) => Math.log(Math.max(r.snr, 1)) + 0.6 * Math.log(Math.max(r.moved_px, 1));

/**
 * Pick k rounds that get harder: the pool is sorted easy to hard, cut into k bands,
 * and one round is drawn from each band (rand lets a test fix the draw).
 */
export function pickRounds<T extends Pick<BlinkRound, 'snr' | 'moved_px'>>(pool: T[], k: number, rand: () => number = Math.random): T[] {
  const sorted = [...pool].sort((a, b) => ease(b) - ease(a));
  if (sorted.length <= k) return sorted;
  const out: T[] = [];
  for (let i = 0; i < k; i++) {
    const a = Math.floor((i * sorted.length) / k), b = Math.floor(((i + 1) * sorted.length) / k);
    out.push(sorted[a + Math.floor(rand() * (b - a))]);
  }
  return out;
}

/** Points for a round: 10 on the first tap, 5 on the second, 0 after that. */
export const points = (tries: number, hit: boolean) => (!hit ? 0 : tries <= 1 ? 10 : tries === 2 ? 5 : 0);

/** "40 minutes", "6.5 hours", "1.2 days". */
export function span(hours: number): string {
  if (hours < 1.5) return `${Math.round(hours * 60)} minutes`;
  if (hours < 36) return `${+hours.toFixed(1)} hours`;
  return `${+(hours / 24).toFixed(1)} days`;
}

/** Image pixel under a pointer, given the image's box on screen. */
export function toPixel(clientX: number, clientY: number, box: { left: number; top: number; width: number; height: number }, n: number): [number, number] {
  return [((clientX - box.left) / box.width) * n - 0.5, ((clientY - box.top) / box.height) * n - 0.5];
}
