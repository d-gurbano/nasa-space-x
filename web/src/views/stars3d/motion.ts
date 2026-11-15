// The Sun's neighbourhood: where each star is, in 3D, and how it moves. Positions are from
// the star catalogues at epoch 2016 (Gaia), moved in a straight line by their space
// velocity (proper motion plus radial speed). Kept apart from the scene so it can be tested.

/** km/s to parsecs per year. */
const KMS_TO_PC_YR = 1 / 977_792;
const MAS = Math.PI / 180 / 3_600_000;
export const EPOCH = 2016;
export const PC_TO_LY = 3.2616;

export type Kind = 'sun' | 'red dwarf' | 'brown dwarf' | 'young variable star' | 'pulsating red giant' | 'context';

export interface Star {
  id: string;
  name: string;
  kind: Kind;
  /** Degrees. */
  ra: number;
  dec: number;
  /** Parsecs. */
  dist: number;
  /** mas/yr; pmra includes cos(dec). */
  pmra: number;
  pmdec: number;
  /** km/s, positive away from us. null when not known (drawn as 0). */
  rv: number | null;
  /** Challenge targets have a slug in public/data/stars. */
  slug?: string;
  /** Beyond the 5 pc bubble: drawn on the far ring, not to scale. */
  far?: boolean;
  /** Display colour (hex). */
  color: number;
  /** Radius in Sun radii and surface temperature in kelvin: published values, rounded. Not measured by Rewind. */
  rsun: number;
  temp: number;
}

// Challenge targets: RA/Dec and proper motion as in the star manifests (Gaia DR3 and
// Kirkpatrick et al. 2021). Distances from Gaia DR3 parallaxes; RW Aur and R Dra rounded.
// Context stars: SIMBAD (Hipparcos / Gaia). Sizes and temperatures: published values, rounded
// (R Dra: a typical size for a pulsating red giant; Eps Indi B: the larger of the pair).
export const STARS: Star[] = [
  { id: 'barnard', slug: 'barnard', name: "Barnard's Star", kind: 'red dwarf', ra: 269.446, dec: 4.769, dist: 1.828, pmra: -801.551, pmdec: 10362.394, rv: -110.5, color: 0xff6a3d, rsun: 0.187, temp: 3100 },
  { id: 'wise0855', slug: 'wise0855', name: 'WISE 0855', kind: 'brown dwarf', ra: 133.759, dec: -7.242, dist: 2.278, pmra: -8123.7, pmdec: 673.2, rv: null, color: 0xc06cff, rsun: 0.1, temp: 250 },
  { id: 'epsindib', slug: 'epsindib', name: 'Eps Indi B', kind: 'brown dwarf', ra: 331.097, dec: -56.801, dist: 3.639, pmra: 3981.977, pmdec: -2466.832, rv: -40.4, color: 0xc06cff, rsun: 0.085, temp: 1300 },
  { id: 'rwaur', slug: 'rwaur', name: 'RW Aur', kind: 'young variable star', ra: 76.956, dec: 30.401, dist: 150, pmra: 2.641, pmdec: -27.398, rv: null, far: true, color: 0x7fd8ff, rsun: 1.7, temp: 5000 },
  { id: 'rdra', slug: 'rdra', name: 'R Dra', kind: 'pulsating red giant', ra: 248.167, dec: 66.755, dist: 400, pmra: -20.643, pmdec: 6.149, rv: null, far: true, color: 0xff3a2a, rsun: 300, temp: 2800 },
  { id: 'acen', name: 'Alpha Centauri', kind: 'context', ra: 219.902, dec: -60.834, dist: 1.338, pmra: -3679.25, pmdec: 473.67, rv: -21.4, color: 0xfff1d6, rsun: 1.22, temp: 5800 },
  { id: 'sirius', name: 'Sirius', kind: 'context', ra: 101.287, dec: -16.716, dist: 2.637, pmra: -546.01, pmdec: -1223.07, rv: -5.5, color: 0xcfe0ff, rsun: 1.71, temp: 9900 },
  { id: 'procyon', name: 'Procyon', kind: 'context', ra: 114.825, dec: 5.225, dist: 3.514, pmra: -714.59, pmdec: -1036.8, rv: -3.2, color: 0xfff6e6, rsun: 2.05, temp: 6500 },
];

export const SUN: Star = { id: 'sun', name: 'Sun', kind: 'sun', ra: 0, dec: 0, dist: 0, pmra: 0, pmdec: 0, rv: 0, color: 0xfff0d2, rsun: 1, temp: 5772 };

export type V3 = [number, number, number];
const add = (a: V3, b: V3, k = 1): V3 => [a[0] + b[0] * k, a[1] + b[1] * k, a[2] + b[2] * k];
const dot = (a: V3, b: V3) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
export const len = (a: V3) => Math.sqrt(dot(a, a));

/** Equatorial unit vectors at (ra, dec): towards the star, east, north. */
function basis(ra: number, dec: number): [V3, V3, V3] {
  const a = (ra * Math.PI) / 180, d = (dec * Math.PI) / 180;
  return [
    [Math.cos(d) * Math.cos(a), Math.cos(d) * Math.sin(a), Math.sin(d)],
    [-Math.sin(a), Math.cos(a), 0],
    [-Math.sin(d) * Math.cos(a), -Math.sin(d) * Math.sin(a), Math.cos(d)],
  ];
}

/** Position at the epoch (pc) and space velocity (pc per year), equatorial x, y, z. */
export function stateOf(s: Star): { pos: V3; vel: V3 } {
  const [r, e, n] = basis(s.ra, s.dec);
  const pos: V3 = [r[0] * s.dist, r[1] * s.dist, r[2] * s.dist];
  let vel = add([0, 0, 0], r, (s.rv ?? 0) * KMS_TO_PC_YR);
  vel = add(vel, e, s.pmra * MAS * s.dist);
  vel = add(vel, n, s.pmdec * MAS * s.dist);
  return { pos, vel };
}

/** Where the star is in a given year (straight-line motion). */
export function at(s: Star, year: number): V3 {
  const { pos, vel } = stateOf(s);
  return add(pos, vel, year - EPOCH);
}

/** Speed across and along the line of sight, km/s. */
export function speeds(s: Star): { tangential: number; total: number } {
  const tangential = 4.7405 * (Math.hypot(s.pmra, s.pmdec) / 1000) * s.dist;
  return { tangential, total: Math.hypot(tangential, s.rv ?? 0) };
}

/** The year the star passes closest to the Sun, and how close (pc). */
export function closest(s: Star): { year: number; dist: number } {
  const { pos, vel } = stateOf(s);
  const t = -dot(pos, vel) / dot(vel, vel);
  return { year: EPOCH + t, dist: len(add(pos, vel, t)) };
}

/** Equatorial (x to RA 0, z to the north pole) to scene axes (y up). */
export const toScene = (p: V3): V3 => [p[0], p[2], -p[1]];

/** Nearby stars are drawn at their true distance; far ones on a ring of this radius. */
export const NEAR_LIMIT = 5;
export const FAR_RING = 6.4;

/** Scene position of a star in a given year. */
export function scenePos(s: Star, year: number): V3 {
  if (!s.far) return toScene(at(s, year));
  const [r] = basis(s.ra, s.dec);
  return toScene([r[0] * FAR_RING, r[1] * FAR_RING, r[2] * FAR_RING]);
}

/** "1.83 pc (6.0 light-years)". */
export function distLabel(pc: number): string {
  return pc >= 20 ? `${Math.round(pc)} pc` : `${pc.toFixed(2)} pc`;
}

/** Year as people say it: "2026", "9,800 BCE". Year 0 does not exist; -9999 is 10,000 BCE. */
export function yearLabel(y: number): string {
  const r = Math.round(y), n = (v: number) => (v >= 10_000 ? v.toLocaleString('en-US') : String(v));
  return r > 0 ? n(r) : `${n(1 - r)} BCE`;
}

/** Jupiter's radius in Sun radii. */
const JUPITER = 0.1;

/** What to draw beside a star for size, how many times wider the star is, and a line that says it. */
export function compare(s: Star): { body: 'Sun' | 'Jupiter'; ratio: number; line: string } {
  if (s.kind === 'sun') return { body: 'Jupiter', ratio: 1 / JUPITER, line: '10 × Jupiter' };
  if (s.rsun < 0.15) {
    const ratio = s.rsun / JUPITER;
    return { body: 'Jupiter', ratio, line: Math.abs(ratio - 1) <= 0.2 ? 'About Jupiter-size' : `${ratio.toFixed(1)} × Jupiter` };
  }
  return { body: 'Sun', ratio: s.rsun, line: s.rsun >= 100 ? `About ${Math.round(s.rsun / 100) * 100} × the Sun` : `${s.rsun.toFixed(1)} × the Sun` };
}

/** "2,800 °C": kelvin to a rounded Celsius reading. */
export function tempLabel(k: number): string {
  const c = k - 273.15, r = Math.abs(c) >= 1000 ? Math.round(c / 100) * 100 : Math.round(c / 5) * 5;
  return `${r < 0 ? '−' : ''}${Math.abs(r).toLocaleString('en-US')} °C`;
}
