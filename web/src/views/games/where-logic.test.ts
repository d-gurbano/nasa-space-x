import { describe, expect, it } from 'vitest';
import { cloudShape, factorText, fmtKm, pickRounds, scoreGuess, sizesOf, type WhereRound } from './where-logic';

describe('where will it be: logic', () => {
  it('scores 100 on the spot and 0 for "it did not move"', () => {
    expect(scoreGuess([1, 1], [1, 1], [0, 0])).toBe(100);
    expect(scoreGuess([0, 0], [1, 1], [0, 0])).toBe(0);
    expect(scoreGuess([0.5, 0.5], [1, 1], [0, 0])).toBe(50);
    expect(scoreGuess([9, 9], [1, 1], [0, 0])).toBe(0);
  });

  it('prefers the discovery-week scenario, and falls back to the full orbit', () => {
    const y = { iso: '2027-01-01', sigma3_km_before: 200, sigma3_km_after: 100 };
    expect(sizesOf({ at_discovery_scenario: { at_iso: '2026-09-27', sigma3_km_before: 590, sigma3_km_after: 100, converged: true }, one_year_after_last_obs: y })).toMatchObject({ scenario: true, factor: 5.9 });
    expect(sizesOf({ at_discovery_scenario: { at_iso: '2026-09-27', sigma3_km_before: 590, sigma3_km_after: 100, converged: false }, one_year_after_last_obs: y })).toMatchObject({ scenario: false, factor: 2 });
    expect(sizesOf({ at_discovery_scenario: { error: 'x' } as never, one_year_after_last_obs: y })).toMatchObject({ scenario: false });
    expect(sizesOf(null)).toBeNull();
  });

  it('finds the long axis of a stretched cloud', () => {
    const pts = Array.from({ length: 50 }, (_, i) => [i, i + (i % 2 ? 0.5 : -0.5)] as [number, number]);
    const s = cloudShape(pts);
    expect(s.angle).toBeCloseTo(Math.PI / 4, 1);
    expect(s.ratio).toBeLessThan(0.1);
  });

  it('plays the biggest change last', () => {
    const r = (factor: number, scenario = true) => ({ sizes: { factor, scenario } }) as WhereRound;
    expect(pickRounds([r(5.9), r(1.0, false), r(1.1), r(3.2), r(0.9), r(1.5), r(1.0, false)]).map((x) => x.sizes.factor)).toEqual([0.9, 1.1, 1.5, 3.2, 5.9]);
  });

  it('words the numbers plainly', () => {
    expect(fmtKm(2719821)).toBe('2.7 million km');
    expect(fmtKm(15967617)).toBe('16 million km');
    expect(fmtKm(19329)).toBe('19,000 km');
    expect(factorText(5.9)).toBe('5.9x smaller');
    expect(factorText(1.01)).toBe('about the same');
    expect(factorText(0.9)).toBe('1.1x larger');
  });
});
