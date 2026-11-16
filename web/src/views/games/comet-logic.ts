// Comet or asteroid?: the pure parts (types, round picking, chart scale, the feedback text), kept apart so they can be tested.

export type Truth = 'comet' | 'asteroid';

export interface Pt { um: number; value: number; err: number }

export interface CometRound {
  slug: string;
  name: string;
  truth: Truth;
  /** JPL class, e.g. "Jupiter-family Comet", "Apollo" */
  class: string | null;
  verdict: string;
  snr: number | null;
  n_frames: number | null;
  img: string;
  points: Pt[];
  /** comets only. co2: the point holding 4.26 um is >2 sigma above a flat 3.8 um point; raised: long end up but noisy; faint: nothing to claim */
  bump: 'co2' | 'raised' | 'faint' | null;
  bump_band: [number, number] | null;
  /** the 4.6 um point is well above plain reflected sunlight */
  warm: boolean;
  /** a clear fuzzy glow in the stack, judged by eye in the prep script */
  coma: boolean;
}

export interface CometData { rounds: CometRound[] }

export const ROUNDS = 8;

export function shuffle<T>(a: T[], rnd = Math.random): T[] {
  const b = [...a];
  for (let i = b.length - 1; i > 0; i--) {
    const j = Math.floor(rnd() * (i + 1));
    [b[i], b[j]] = [b[j], b[i]];
  }
  return b;
}

/** n rounds, half comets and half asteroids where the pool allows, in random order. */
export function pickRounds(pool: CometRound[], n = ROUNDS, rnd = Math.random): CometRound[] {
  const c = shuffle(pool.filter((r) => r.truth === 'comet'), rnd);
  const a = shuffle(pool.filter((r) => r.truth === 'asteroid'), rnd);
  const nc = Math.min(c.length, Math.max(n - a.length, Math.ceil(n / 2)));
  return shuffle([...c.slice(0, nc), ...a.slice(0, n - nc)], rnd);
}

export const UM_MIN = 0.7, UM_MAX = 5.1;
/** Wavelength to 0..1 across the chart, in log wavelength like the SPHEREx channels. */
export const ux = (um: number) => Math.log(um / UM_MIN) / Math.log(UM_MAX / UM_MIN);

/** The value range to draw: all points with their error bars, always including 0 and 1, with a little room. */
export function yRange(pts: Pt[]): [number, number] {
  const v = pts.flatMap((p) => [p.value - p.err, p.value + p.err]).filter(Number.isFinite);
  const lo = Math.min(0, ...v), hi = Math.max(1.5, ...v), pad = (hi - lo) * 0.08;
  return [lo - pad, hi + pad];
}

const fmtUm = (x: number) => x.toFixed(1);

/** "Jupiter-family Comet*" -> "a Jupiter-family comet"; "Apollo" -> "an Apollo near-Earth asteroid". */
export function kindPhrase(r: Pick<CometRound, 'class' | 'truth'>): string {
  const c = (r.class ?? '').replace(/\*/g, '').trim();
  let s: string;
  if (r.truth === 'comet') s = c && c.toLowerCase() !== 'comet' ? c.replace(/Comet$/, 'comet').replace(/^Hyperbolic/, 'hyperbolic') : 'comet';
  else s = /^(Apollo|Aten|Amor|Atira)$/.test(c) ? `${c} near-Earth asteroid` : 'asteroid';
  return `${/^[AEIOU]/i.test(s) ? 'an' : 'a'} ${s}`;
}

/** What the image and the spectrum show, in plain sentences. Only claims what the data flags say. */
export function explain(r: CometRound): string[] {
  const out: string[] = [];
  if (r.truth === 'comet') {
    out.push(r.coma
      ? 'In this stack it is not a sharp dot. A fuzzy glow, the coma, spreads around it. It is dust and gas leaving an icy body warmed by the Sun.'
      : 'In this stack it is a faint smudge, too faint to see a coma by eye.');
    if (r.bump === 'co2' && r.bump_band) {
      out.push(`Our point for ${fmtUm(r.bump_band[0])} to ${fmtUm(r.bump_band[1])} µm sits well above the 3.8 µm point. CO2 gas glows at 4.26 µm, inside that band, so the extra light fits a comet giving off CO2. Warm dust can add light there too.`);
    } else if (r.bump === 'raised') {
      out.push('The long end of the spectrum is raised, but our points scatter too much to pin that light on CO2 gas at 4.26 µm.');
    } else if (r.bump_band) {
      out.push('Near 4.26 µm, where CO2 gas glows, our points are too faint to tell whether the gas is there.');
    } else {
      out.push('We have no spectrum point near 4.26 µm for this object, so we cannot tell whether CO2 gas is there.');
    }
  } else {
    out.push('In this stack it is a compact point of light with no coma around it.');
    if (r.warm) out.push('The points climb toward 5 µm. A near-Earth asteroid close to the Sun is warm, and its own heat adds light at these long wavelengths. That is not gas.');
  }
  return out;
}

/** The name tells too: C/ and P/ mark comets, a year and letters alone mark an asteroid. */
export function nameNote(r: Pick<CometRound, 'name' | 'truth'>): string {
  if (/^[CP]\//.test(r.name)) return `The ${r.name.slice(0, 2)} at the start of its name marks a comet.`;
  if (/^\d+I\//.test(r.name)) return 'The I in its name marks an interstellar object, here an interstellar comet.';
  return '';
}
