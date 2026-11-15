import { describe, expect, it } from 'vitest';
import { blur, hitRadius, isRight, judge, sinceFirst, stretch, windowOf } from '../src/lib/detect';

const track: [number, number][] = [[185.7, 199.7], [178.5, 191.2], [171.3, 182.6], [164.1, 174.1], [156.9, 165.6]];
const planted = { id: 'r01', track_xy: track, tolerance_px: 30 };
const empty = { id: 'r07', track_xy: null, tolerance_px: 30 };

describe('windowOf', () => {
  it('shows a whole asteroid cutout (324 px) and the same width of sky from a wide patch (320 px)', () => {
    expect(windowOf({ id: 'r03', track_xy: [[218.8, 188.4], [105.2, 135.6]] }, 324)).toEqual({ x: 0, y: 0, size: 324 });
    expect(windowOf(empty, 320).size).toBe(99);
  });

  it('keeps the whole track inside the crop, away from its edge, and is the same every time', () => {
    const w = windowOf(planted, 320);
    for (const [x, y] of track) {
      expect(x - w.x).toBeGreaterThan(0.13 * w.size);
      expect(w.x + w.size - x).toBeGreaterThan(0.13 * w.size);
      expect(y - w.y).toBeGreaterThan(0.13 * w.size);
      expect(w.y + w.size - y).toBeGreaterThan(0.13 * w.size);
    }
    expect(windowOf(planted, 320)).toEqual(w);
  });

  it('falls back to the whole photo when the track is too long for the crop', () => {
    expect(windowOf({ id: 'long', track_xy: [[20, 20], [300, 300]] }, 320)).toEqual({ x: 0, y: 0, size: 320 });
  });
});

describe('judge', () => {
  const w = windowOf(planted, 320);
  it('a ring that covers the mover in any photo is a hit; elsewhere it is not', () => {
    expect(hitRadius(planted, w)).toBeCloseTo(9.9);
    expect(judge(planted, w, [172, 190])).toBe('hit'); // near the third photo's position
    expect(judge(planted, w, [156.9 + 9, 165.6])).toBe('hit');
    expect(judge(planted, w, [156.9 + 11, 165.6 - 11])).toBe('far');
    expect(judge(planted, w, null)).toBe('missed');
  });

  it('uses the data tolerance when the whole photo is shown', () => {
    const full = { x: 0, y: 0, size: 324 };
    expect(hitRadius(planted, full)).toBe(30);
    expect(judge(planted, full, [156.9 + 29, 165.6])).toBe('hit');
  });

  it('on empty sky only "Nothing moves" is right', () => {
    expect(judge(empty, w, null)).toBe('clear');
    expect(judge(empty, w, [100, 100])).toBe('alarm');
    expect(['hit', 'clear', 'far', 'missed', 'alarm'].map((o) => isRight(o as never))).toEqual([true, true, false, false, false]);
  });
});

describe('photo treatment', () => {
  it('blur keeps the total light and spreads a single bright pixel', () => {
    const n = 21;
    const src = new Float32Array(n * n);
    src[10 * n + 10] = 100;
    const out = blur(src, n, 2);
    expect(out.reduce((a, b) => a + b, 0)).toBeCloseTo(100, 3);
    expect(out[10 * n + 10]).toBeLessThan(10);
    expect(out[10 * n + 12]).toBeGreaterThan(0);
  });

  it('one stretch for the round: sky is dark grey, a bright star is bright, noise alone stays dim', () => {
    const sky = () => Float32Array.from({ length: 1000 }, (_, i) => 20 + (i % 5) - 2);
    const withStar = sky();
    withStar.fill(250, 0, 10);
    const [a, b] = stretch([withStar, sky()]);
    expect(a[0]).toBeGreaterThan(150);
    expect(a[500]).toBeGreaterThan(5);
    expect(a[500]).toBeLessThan(60);
    expect(Math.max(...b)).toBeLessThan(80);
    const [noise] = stretch([sky()]);
    expect(Math.max(...noise)).toBeLessThan(140);
  });
});

describe('sinceFirst', () => {
  it('reads as minutes, hours, then days', () => {
    expect(sinceFirst('2026-08-31T11:39:43', '2026-08-31T11:41:50')).toBe('+2 min');
    expect(sinceFirst('2026-08-31T11:39:43', '2026-08-31T14:48:44')).toBe('+3.2 h');
    expect(sinceFirst('2026-05-20T01:13:00', '2026-05-23T01:13:00')).toBe('+3.0 d');
  });
});
