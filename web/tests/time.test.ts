import { describe, expect, it } from 'vitest';
import { fracFromMjd, isoFromMjd, mjdFromFrac, mjdFromIso, readoutFromMjd, plainDate, relativeText } from '../src/lib/time';

describe('date mapping', () => {
  it('knows fixed MJDs', () => {
    expect(mjdFromIso('1858-11-17')).toBe(0);
    expect(mjdFromIso('2000-01-01')).toBe(51544);
    expect(mjdFromIso('2026-06-09')).toBe(61200);
    expect(isoFromMjd(61299)).toBe('2026-09-16');
  });
  it('round-trips iso and mjd', () => {
    for (const d of ['2024-02-29', '2025-04-01', '2030-12-31']) expect(isoFromMjd(mjdFromIso(d))).toBe(d);
  });
  it('formats readouts', () => {
    expect(readoutFromMjd(61359)).toBe('NOV 15, 2026');
    expect(plainDate('2026-09-16')).toBe('16 Sep 2026');
  });
  it('says how far a date is from today', () => {
    expect(relativeText(0.2)).toBe('Today');
    expect(relativeText(-1)).toBe('1 day ago');
    expect(relativeText(-19)).toBe('19 days ago');
    expect(relativeText(-240)).toBe('8 months ago');
    expect(relativeText(30)).toBe('in 30 days');
    expect(relativeText(730.5)).toBe('in 2.0 years');
  });
  it('maps slider fractions both ways and clamps', () => {
    const a = 60000, b = 61000;
    expect(fracFromMjd(60250, a, b)).toBeCloseTo(0.25);
    expect(mjdFromFrac(0.25, a, b)).toBeCloseTo(60250);
    expect(fracFromMjd(59000, a, b)).toBe(0);
    expect(mjdFromFrac(2, a, b)).toBe(b);
  });
});
