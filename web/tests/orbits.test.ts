import { describe, expect, it } from 'vitest';
import { type Elements, type Vec3 } from '../src/lib/kepler';
import { dotPosition, orbitPath, type OrbitBody } from '../src/scene/orbits';

const BODIES: Record<string, Elements> = {
  mainBelt: { a: 2.6, e: 0.12, i: 9, node: 80, peri: 200, M: 40, epoch_mjd: 61200 },
  nearEarth: { a: 1.4, e: 0.62, i: 24, node: 310, peri: 95, M: 355, epoch_mjd: 61200 },
  comet: { a: 48, e: 0.97, i: 71, node: 12, peri: 130, M: 0.4, epoch_mjd: 61200 },
  steep: { a: 3.1, e: 0.4, i: 118, node: 200, peri: 20, M: 181, epoch_mjd: 61200 },
  hyperbolic: { a: -0.26, e: 6.1, i: 175, node: 322, peri: 128, M: 300, epoch_mjd: 61000 },
};

/** Distance from point p to the polyline (nearest point on any segment), in AU. */
function toPolyline(p: Vec3, pts: Vec3[]): number {
  let best = Infinity;
  for (let k = 0; k < pts.length - 1; k++) {
    const a = pts[k], b = pts[k + 1];
    const ab = [b[0] - a[0], b[1] - a[1], b[2] - a[2]], ap = [p[0] - a[0], p[1] - a[1], p[2] - a[2]];
    const len2 = ab[0] ** 2 + ab[1] ** 2 + ab[2] ** 2;
    const t = len2 > 0 ? Math.min(1, Math.max(0, (ap[0] * ab[0] + ap[1] * ab[1] + ap[2] * ab[2]) / len2)) : 0;
    best = Math.min(best, Math.hypot(ap[0] - ab[0] * t, ap[1] - ab[1] * t, ap[2] - ab[2] * t));
  }
  return best;
}

/** Path vertices as offsets from the dot at the path's own date (what the scene draws). */
const offsets = (rel: Float32Array): Vec3[] => Array.from({ length: rel.length / 3 }, (_, k) => [rel[k * 3], rel[k * 3 + 1], rel[k * 3 + 2]]);

describe('orbit line and dot', () => {
  for (const [name, el] of Object.entries(BODIES)) {
    const body: OrbitBody = { el };
    it(`${name}: the dot is a vertex of its own line`, () => {
      for (const mjd of [60400, 61200.37, 61987.5]) {
        const path = orbitPath(body, mjd);
        expect(path.origin).toEqual(dotPosition(body, mjd));
        expect([...path.rel.slice(path.head * 3, path.head * 3 + 3)].map(Math.abs)).toEqual([0, 0, 0]);
        expect(path.u[path.head]).toBe(0);
      }
    });
    it(`${name}: the dot stays on the line as it moves, at every zoom`, () => {
      const mjd = 61200.37;
      const path = orbitPath(body, mjd);
      const pts = offsets(path.rel);
      // from a few seconds to a month away: the line must pass within a thousandth of the distance moved
      for (const dt of [1e-4, 1e-2, 0.5, 5, 30]) {
        for (const sign of [-1, 1]) {
          const p = dotPosition(body, mjd + sign * dt);
          const moved: Vec3 = [p[0] - path.origin[0], p[1] - path.origin[1], p[2] - path.origin[2]];
          expect(toPolyline(moved, pts) / Math.hypot(...moved)).toBeLessThan(1e-3);
        }
      }
    });
  }

  it('closes an ellipse: both ends meet on the far side', () => {
    const { rel } = orbitPath({ el: BODIES.nearEarth }, 61200);
    const n = rel.length / 3;
    expect(Math.hypot(rel[0] - rel[(n - 1) * 3], rel[1] - rel[(n - 1) * 3 + 1], rel[2] - rel[(n - 1) * 3 + 2])).toBeLessThan(1e-6);
  });

  it('keeps the dot on the line when the engine track shifts it off the two-body path', () => {
    const el = BODIES.nearEarth;
    const shift = (mjd: number): Vec3 => {
      const p = dotPosition({ el }, mjd);
      return [p[0] + 2e-4, p[1] - 1e-4, p[2] + 3e-4];
    };
    const body: OrbitBody = { el, track: { dates: [61100, 61200, 61300], nominal: [shift(61100), shift(61200), shift(61300)] } };
    const at = dotPosition(body, 61250);
    const plain = dotPosition({ el }, 61250);
    expect(Math.hypot(at[0] - plain[0], at[1] - plain[1], at[2] - plain[2])).toBeGreaterThan(1e-4);
    const path = orbitPath(body, 61250);
    expect(path.origin).toEqual(at);
    expect(toPolyline([0, 0, 0], offsets(path.rel))).toBe(0);
  });
});
