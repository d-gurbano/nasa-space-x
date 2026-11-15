// Where a Rewind object is, and the line of its orbit. Both come from the same propagation
// (same elements, same epoch, same Kepler solver, all in double precision), and the line is
// stored as offsets from the dot: its middle vertex IS the dot, and the vertices bunch up
// around it. So the dot sits on its line at every zoom, from the whole system to the close-up.
// No three.js or DOM in here, so the tests can run it.
import { basis, DEG, meanMotion, positionAt, solveKepler, solveKeplerHyperbolic, type Elements, type Vec3 } from '../lib/kepler';

/** Engine nominal positions at dates (first clone of the cloud), used to correct the 2-body path. */
export interface Track {
  dates: number[];
  nominal: Vec3[];
}

export interface OrbitBody {
  el: Elements;
  track?: Track;
}

/** The smooth correction from the two-body path towards the engine's nominal track at time mjd. */
export function trackOffset(o: OrbitBody, mjd: number): Vec3 {
  const t = o.track;
  if (!t || t.dates.length < 2) return [0, 0, 0];
  let k = 0;
  while (k < t.dates.length - 2 && mjd > t.dates[k + 1]) k++;
  const w = Math.min(1, Math.max(0, (mjd - t.dates[k]) / (t.dates[k + 1] - t.dates[k])));
  const a = positionAt(o.el, t.dates[k]), b = positionAt(o.el, t.dates[k + 1]);
  const A = t.nominal[k], B = t.nominal[k + 1];
  return [0, 1, 2].map((j) => (A[j] - a[j]) * (1 - w) + (B[j] - b[j]) * w) as Vec3;
}

/**
 * Two-body position plus a smooth correction towards the engine's nominal track, so the dot
 * sits in the middle of its uncertainty cloud even where two-body and n-body orbits drift apart.
 */
export function dotPosition(o: OrbitBody, mjd: number): Vec3 {
  const p = positionAt(o.el, mjd), c = trackOffset(o, mjd);
  return [p[0] + c[0], p[1] + c[1], p[2] + c[2]];
}

export interface OrbitPath {
  origin: Vec3; // the dot, heliocentric ecliptic AU: exactly dotPosition(o, mjd)
  rel: Float32Array; // vertices as offsets from the dot (ecliptic AU), 2n + 1 of them
  u: Float32Array; // how far along the orbit from the dot: -1 (behind) .. 0 (the dot) .. 1 (ahead)
  head: number; // index of the dot's own vertex
}

/**
 * The orbit as a polyline around the dot at time mjd. An ellipse runs half a turn behind and
 * half a turn ahead of the dot; a hyperbola runs out to rMax AU. Vertex spacing grows with the
 * cube of the step away from the dot, so the line stays smooth next to it however far one zooms in.
 */
export function orbitPath(o: OrbitBody, mjd: number, n = 192, rMax = 60): OrbitPath {
  const { el } = o;
  const A = Math.abs(el.a), ell = el.e < 1;
  const M = el.M * DEG + meanMotion(A) * (mjd - el.epoch_mjd);
  const a0 = ell ? solveKepler(M, el.e) : solveKeplerHyperbolic(M, el.e);
  let back = Math.PI, fwd = Math.PI;
  if (!ell) {
    const hMax = Math.acosh(Math.max(1, (rMax / A + 1) / el.e));
    back = Math.max(0.05, a0 + hMax);
    fwd = Math.max(0.05, hMax - a0);
  }
  const { P, Q } = basis(el.i, el.node, el.peri);
  const b = A * Math.sqrt(Math.abs(1 - el.e * el.e));
  // in-plane offset from the dot, written as differences so nothing is lost next to it
  const plane = (d: number): [number, number] => {
    const s = Math.sin(d / 2);
    if (ell) return [-2 * A * Math.sin(a0 + d / 2) * s, 2 * b * Math.cos(a0 + d / 2) * s];
    const sh = Math.sinh(d / 2);
    return [-2 * A * Math.sinh(a0 + d / 2) * sh, 2 * b * Math.cosh(a0 + d / 2) * sh];
  };
  const rel = new Float32Array((2 * n + 1) * 3), u = new Float32Array(2 * n + 1);
  for (let k = 0; k <= 2 * n; k++) {
    const s = (k - n) / n, w = s * s * s;
    const [x, y] = plane(w * (w < 0 ? back : fwd));
    rel.set([x * P[0] + y * Q[0], x * P[1] + y * Q[1], x * P[2] + y * Q[2]], k * 3);
    u[k] = w;
  }
  return { origin: dotPosition(o, mjd), rel, u, head: n };
}

/** The selected object's glowing orbit: the same path as the map line, denser, so it stays smooth in the close-up. */
export function focusPath(o: OrbitBody, mjd: number): OrbitPath {
  return orbitPath(o, mjd, 360, 40);
}

const f32 = Math.fround;

/**
 * The asteroid cloud's vertex shader (asteroids.ts) in TypeScript, float32 inputs and all, so the
 * tests can hold the GPU dots against the CPU lines. `orb` is the shader's aOrb (a, e, M0 rad,
 * n rad/day), P and Q its basis, dt the days since the table epoch. AU out, in the frame of P and Q.
 */
export function cloudPosition(orb: ArrayLike<number>, P: ArrayLike<number>, Q: ArrayLike<number>, dt: number): Vec3 {
  const a = f32(orb[0]), e = f32(orb[1]);
  let M = f32(f32(orb[2]) + f32(f32(orb[3]) * f32(dt)));
  M = M - 6.2831853 * Math.floor(M / 6.2831853); // GLSL mod
  if (M > 3.1415927) M -= 6.2831853;
  let E = e < 0.8 ? M : 3.1415927 * Math.sign(M);
  for (let k = 0; k < 10; k++) {
    const d = (E - e * Math.sin(E) - M) / (1 - e * Math.cos(E));
    E -= d;
    if (Math.abs(d) < 1e-5) break;
  }
  const x = a * (Math.cos(E) - e), y = a * Math.sqrt(1 - e * e) * Math.sin(E);
  return [0, 1, 2].map((j) => x * f32(P[j]) + y * f32(Q[j])) as Vec3;
}
