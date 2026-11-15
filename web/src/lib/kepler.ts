// Two-body orbit math shared by the scene, the tests and the sample generator.
// Positions are heliocentric ecliptic J2000 in AU. Angles in the API are degrees.

export const GAUSS_K = 0.01720209895; // rad/day, Gaussian gravitational constant
export const DEG = Math.PI / 180;
export const J2000_MJD = 51544.5;

export type Vec3 = [number, number, number];

export interface Elements {
  a: number; // AU
  e: number;
  i: number; // deg
  node: number; // deg
  peri: number; // deg (argument of perihelion)
  M: number; // deg, mean anomaly at epoch
  epoch_mjd: number;
}

/** Mean motion in rad/day for semi-major axis a (AU). */
export function meanMotion(a: number): number {
  return GAUSS_K / Math.pow(a, 1.5);
}

/** Solve Kepler's equation E - e sin E = M (radians) for elliptic orbits. */
export function solveKepler(M: number, e: number, tol = 1e-12): number {
  M = wrapPi(M);
  let E = e < 0.8 ? M : Math.PI * Math.sign(M || 1);
  for (let k = 0; k < 50; k++) {
    const f = E - e * Math.sin(E) - M;
    const d = f / (1 - e * Math.cos(E));
    E -= d;
    if (Math.abs(d) < tol) break;
  }
  return E;
}

export function wrapPi(x: number): number {
  const t = (x + Math.PI) % (2 * Math.PI);
  return (t < 0 ? t + 2 * Math.PI : t) - Math.PI;
}

/** Orbital-plane basis vectors P (towards perihelion) and Q in the ecliptic frame. */
export function basis(i: number, node: number, peri: number): { P: Vec3; Q: Vec3 } {
  const ci = Math.cos(i * DEG), si = Math.sin(i * DEG);
  const cO = Math.cos(node * DEG), sO = Math.sin(node * DEG);
  const cw = Math.cos(peri * DEG), sw = Math.sin(peri * DEG);
  return {
    P: [cw * cO - sw * sO * ci, cw * sO + sw * cO * ci, sw * si],
    Q: [-sw * cO - cw * sO * ci, -sw * sO + cw * cO * ci, cw * si],
  };
}

/** Solve the hyperbolic Kepler equation e sinh H - H = M. */
export function solveKeplerHyperbolic(M: number, e: number, tol = 1e-12): number {
  let H = Math.asinh(M / e);
  for (let k = 0; k < 60; k++) {
    const d = (e * Math.sinh(H) - H - M) / (e * Math.cosh(H) - 1);
    H -= d;
    if (Math.abs(d) < tol) break;
  }
  return H;
}

/** Orbital-plane coordinates for eccentric (E) or hyperbolic (H) anomaly. */
function planeXY(el: Elements, anomaly: number): [number, number] {
  if (el.e < 1) return [el.a * (Math.cos(anomaly) - el.e), el.a * Math.sqrt(1 - el.e * el.e) * Math.sin(anomaly)];
  const A = Math.abs(el.a);
  return [A * (el.e - Math.cosh(anomaly)), A * Math.sqrt(el.e * el.e - 1) * Math.sinh(anomaly)];
}

function toEcl(el: Elements, [x, y]: [number, number]): Vec3 {
  const { P, Q } = basis(el.i, el.node, el.peri);
  return [x * P[0] + y * Q[0], x * P[1] + y * Q[1], x * P[2] + y * Q[2]];
}

/** Heliocentric ecliptic position (AU) at time mjd. Hyperbolic orbits use a < 0 and hyperbolic M. */
export function positionAt(el: Elements, mjd: number): Vec3 {
  const M = el.M * DEG + meanMotion(Math.abs(el.a)) * (mjd - el.epoch_mjd);
  const anomaly = el.e < 1 ? solveKepler(M, el.e) : solveKeplerHyperbolic(M, el.e);
  return toEcl(el, planeXY(el, anomaly));
}

/** Points along the orbit for drawing: the full ellipse, or a hyperbola out to rMax AU. */
export function orbitPolyline(el: Elements, n = 256, rMax = 60): Vec3[] {
  const out: Vec3[] = [];
  const Hmax = el.e < 1 ? 0 : Math.acosh(Math.max(1, (rMax / Math.abs(el.a) + 1) / el.e));
  for (let k = 0; k <= n; k++) {
    const t = k / n;
    out.push(toEcl(el, planeXY(el, el.e < 1 ? t * 2 * Math.PI : (2 * t - 1) * Hmax)));
  }
  return out;
}

/** JPL "Approximate Positions of the Planets" row: values at J2000 plus rates per Julian century. */
export interface PlanetRow {
  name: string;
  a: number; a_rate: number;
  e: number; e_rate: number;
  i: number; i_rate: number;
  L: number; L_rate: number; // mean longitude
  varpi: number; varpi_rate: number; // longitude of perihelion
  node: number; node_rate: number;
}

export function planetElements(p: PlanetRow, mjd: number): Elements {
  const T = (mjd - J2000_MJD) / 36525;
  const node = p.node + p.node_rate * T;
  const varpi = p.varpi + p.varpi_rate * T;
  const L = p.L + p.L_rate * T;
  return {
    a: p.a + p.a_rate * T,
    e: p.e + p.e_rate * T,
    i: p.i + p.i_rate * T,
    node,
    peri: varpi - node,
    M: L - varpi,
    epoch_mjd: mjd,
  };
}

export function planetPosition(p: PlanetRow, mjd: number): Vec3 {
  return positionAt(planetElements(p, mjd), mjd);
}

/** Convert perihelion-time comet elements to mean anomaly at an epoch (elliptic only). */
export function cometToElements(q: number, e: number, i: number, node: number, peri: number, tp_mjd: number, epoch_mjd: number): Elements | null {
  if (e >= 1) return null;
  const a = q / (1 - e);
  const M = (meanMotion(a) * (epoch_mjd - tp_mjd)) / DEG;
  return { a, e, i, node, peri, M: ((M % 360) + 360) % 360, epoch_mjd };
}

export function dist(a: Vec3, b: Vec3): number {
  return Math.hypot(a[0] - b[0], a[1] - b[1], a[2] - b[2]);
}

/** True when an elements object can be propagated (finite numbers, bound orbit). */
export function isValidElements(o: Partial<Record<keyof Elements, number | null>> | null | undefined): o is Elements {
  if (!o) return false;
  const keys: (keyof Elements)[] = ['a', 'e', 'i', 'node', 'peri', 'M', 'epoch_mjd'];
  if (!keys.every((k) => Number.isFinite(o[k]))) return false;
  const a = o.a as number, e = o.e as number;
  // ellipse (a > 0, e < 1) or hyperbola (a < 0, e > 1); exact parabolas are not supported
  return (a > 0 && e >= 0 && e < 1) || (a < 0 && e > 1.0001);
}
