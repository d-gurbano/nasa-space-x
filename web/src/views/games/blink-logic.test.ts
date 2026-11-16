import { describe, expect, it } from 'vitest';
import { isHit, missBy, pickRounds, points, span, toPixel } from './blink-logic';

describe('blink logic', () => {
  const r = { pos: [[10, 10], [20, 14]] as [[number, number], [number, number]] };

  it('counts a tap near the asteroid in either image', () => {
    expect(isHit(r, 11, 11)).toBe(true);
    expect(isHit(r, 21.5, 15)).toBe(true);
    expect(isHit(r, 15, 12)).toBe(false);
    expect(missBy(r, 10, 13)).toBeCloseTo(3);
  });

  it('orders rounds from easy to hard', () => {
    const pool = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((i) => ({ snr: i * 10, moved_px: 10, id: i }));
    const got = pickRounds(pool, 5, () => 0);
    expect(got.map((g) => g.id)).toEqual([10, 8, 6, 4, 2]);
    expect(pickRounds(pool.slice(0, 3), 5).length).toBe(3);
  });

  it('scores the first and second tap', () => {
    expect(points(1, true)).toBe(10);
    expect(points(2, true)).toBe(5);
    expect(points(1, false)).toBe(0);
  });

  it('says time spans plainly', () => {
    expect(span(1.6)).toBe('1.6 hours');
    expect(span(0.5)).toBe('30 minutes');
    expect(span(48)).toBe('2 days');
  });

  it('maps a pointer onto image pixels', () => {
    const [x, y] = toPixel(150, 50, { left: 100, top: 0, width: 98, height: 98 }, 49);
    expect(x).toBeCloseTo(24.5);
    expect(y).toBeCloseTo(24.5);
  });
});
