import { describe, expect, it } from 'vitest';
import { regolithNormals, rockGeometry, seeded } from '../src/scene/rock';

describe('procedural asteroid', () => {
  it('is deterministic per object and differs between objects', () => {
    const a = rockGeometry('2025yh5', 3).attributes.position.array;
    const b = rockGeometry('2025yh5', 3).attributes.position.array;
    const c = rockGeometry('2025st20', 3).attributes.position.array;
    expect(Array.from(a)).toEqual(Array.from(b));
    expect(Array.from(a)).not.toEqual(Array.from(c));
  });
  it('stays a closed lumpy body of radius about 1 with smooth normals', () => {
    const g = rockGeometry('c2026s1', 4, true);
    const p = g.attributes.position.array as Float32Array;
    const n = g.attributes.normal.array as Float32Array;
    expect(g.index).not.toBeNull(); // merged vertices, so normals are smooth, not faceted
    let rMin = Infinity, rMax = 0;
    for (let i = 0; i < p.length; i += 3) {
      const r = Math.hypot(p[i], p[i + 1], p[i + 2]);
      rMin = Math.min(rMin, r);
      rMax = Math.max(rMax, r);
      expect(Number.isFinite(n[i] + n[i + 1] + n[i + 2])).toBe(true);
    }
    expect(rMin).toBeGreaterThan(0.4);
    expect(rMax).toBeLessThan(2.2);
    expect(rMax / rMin).toBeGreaterThan(1.2);
  });
  it('builds the close-up mesh quickly and smooth enough to show craters', () => {
    const t0 = performance.now();
    const g = rockGeometry('2025yh5', 36);
    expect(performance.now() - t0).toBeLessThan(800);
    expect(g.index!.count / 3).toBeGreaterThan(20000);
  });
  it('makes a regolith normal map with real relief that points outwards on average', () => {
    const size = 64;
    const px = regolithNormals(size);
    expect(px.length).toBe(size * size * 4);
    let sx = 0, sy = 0, rough = 0;
    for (let i = 0; i < px.length; i += 4) {
      sx += px[i] - 127.5;
      sy += px[i + 1] - 127.5;
      rough += Math.abs(px[i] - 127.5) + Math.abs(px[i + 1] - 127.5);
      expect(px[i + 2]).toBeGreaterThan(127); // never points into the surface
    }
    const n = size * size;
    expect(Math.abs(sx / n)).toBeLessThan(3); // a tile has no overall tilt
    expect(Math.abs(sy / n)).toBeLessThan(3);
    expect(rough / n).toBeGreaterThan(10);
  });
  it('seeded random numbers are in 0..1', () => {
    const r = seeded('x');
    for (let k = 0; k < 100; k++) {
      const v = r();
      expect(v).toBeGreaterThanOrEqual(0);
      expect(v).toBeLessThan(1);
    }
  });
});
