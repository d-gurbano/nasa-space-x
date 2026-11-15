import { describe, expect, it } from 'vitest';
import { hue, linePath, scaleTo, ux, yRange } from './rainbow-logic';

describe('rainbow logic', () => {
  it('maps the SPHEREx range onto 0..1', () => {
    expect(ux(0.75)).toBeCloseTo(0);
    expect(ux(5)).toBeCloseTo(1);
    expect(hue(0.75)).toBe(268);
    expect(hue(5)).toBe(0);
  });

  it('breaks the line where a colour is missing', () => {
    const d = linePath([1, 2, 3, 4], [1, null, 2, 3], (u) => u, (v) => v);
    expect(d).toBe('M1.0 1.0M3.0 2.0L4.0 3.0');
  });

  it('pads the value range and ignores gaps', () => {
    const [lo, hi] = yRange([[1, null, 2], [undefined, 1.5]]);
    expect(lo).toBeLessThan(1);
    expect(hi).toBeGreaterThan(2);
  });
  it('scales a template onto the points it overlaps', () => {
    const um = [1, 2, 3];
    expect(scaleTo(um, [1, 2, null], um, [2, 4, 9])).toBeCloseTo(2);
    expect(scaleTo(um, [1, 1, 1], [1.05, 2.9], [3, 3])).toBeCloseTo(3);
    expect(scaleTo(um, [null, null, null], um, [1, 2, 3])).toBe(1);
  });
});
