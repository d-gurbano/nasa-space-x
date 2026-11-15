import { describe, expect, it } from 'vitest';
import { cometToElements, dist, meanMotion, planetPosition, positionAt, solveKepler, type PlanetRow } from '../src/lib/kepler';

const EARTH: PlanetRow = {
  name: 'Earth', a: 1.00000261, a_rate: 0.00000562, e: 0.01671123, e_rate: -0.00004392, i: -0.00001531, i_rate: -0.01294668,
  L: 100.46457166, L_rate: 35999.37244981, varpi: 102.93768193, varpi_rate: 0.32327364, node: 0, node_rate: 0,
};

describe('solveKepler', () => {
  it('satisfies E - e sin E = M across eccentricities', () => {
    for (const e of [0, 0.1, 0.5, 0.9, 0.99]) {
      for (let M = -3.1; M <= 3.1; M += 0.37) {
        const E = solveKepler(M, e);
        expect(E - e * Math.sin(E)).toBeCloseTo(M, 10);
      }
    }
  });
  it('wraps M outside -pi..pi', () => {
    const E = solveKepler(4 * Math.PI + 0.5, 0.2);
    expect(E - 0.2 * Math.sin(E)).toBeCloseTo(0.5, 10);
  });
});

describe('positions', () => {
  it('puts a circular orbit at radius a', () => {
    const p = positionAt({ a: 2.5, e: 0, i: 10, node: 30, peri: 40, M: 77, epoch_mjd: 60000 }, 61000);
    expect(Math.hypot(...p)).toBeCloseTo(2.5, 10);
  });
  it('returns to the same place after one period', () => {
    const el = { a: 1.6, e: 0.3, i: 12, node: 80, peri: 200, M: 10, epoch_mjd: 61200 };
    const P = (2 * Math.PI) / meanMotion(1.6);
    expect(dist(positionAt(el, 61200), positionAt(el, 61200 + P))).toBeLessThan(1e-3);
  });
  it('places Earth near the right spot on 2026-01-03 (perihelion, x<0 region)', () => {
    // At early January Earth is near perihelion (0.983 AU) and ecliptic longitude ~102 deg.
    const p = planetPosition(EARTH, 61043);
    const r = Math.hypot(...p);
    expect(r).toBeGreaterThan(0.982);
    expect(r).toBeLessThan(0.985);
    const lon = (Math.atan2(p[1], p[0]) * 180) / Math.PI;
    expect(lon).toBeGreaterThan(95);
    expect(lon).toBeLessThan(110);
  });
  it('converts comet perihelion time to mean anomaly 0 at perihelion', () => {
    const el = cometToElements(1.0, 0.5, 5, 10, 20, 61000, 61000)!;
    expect(el.a).toBeCloseTo(2, 10);
    expect(el.M).toBeCloseTo(0, 10);
    expect(Math.hypot(...positionAt(el, 61000))).toBeCloseTo(1.0, 8);
    expect(cometToElements(1, 1.01, 0, 0, 0, 0, 0)).toBeNull();
  });
});

describe('hyperbolic orbits', () => {
  it('solves e sinh H - H = M', async () => {
    const { solveKeplerHyperbolic } = await import('../src/lib/kepler');
    for (const e of [1.01, 1.5, 3]) for (const M of [-20, -1, 0, 0.3, 5, 40]) {
      const H = solveKeplerHyperbolic(M, e);
      expect(e * Math.sinh(H) - H).toBeCloseTo(M, 8);
    }
  });
  it('puts a hyperbola at perihelion q = |a|(e - 1) when M = 0', () => {
    const el = { a: -2, e: 1.5, i: 20, node: 40, peri: 60, M: 0, epoch_mjd: 61000 };
    expect(Math.hypot(...positionAt(el, 61000))).toBeCloseTo(1.0, 8);
    expect(Math.hypot(...positionAt(el, 62000))).toBeGreaterThan(2);
  });
});
