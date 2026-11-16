import { describe, expect, it } from 'vitest';
import { clamp, compass, perYear, pxToSky, score } from './speed-logic';

describe('speed logic', () => {
  it('maps image pixels to sky directions (north up, east left)', () => {
    const up = pxToSky(0, -10, 0.1875);
    expect(up.north).toBeCloseTo(1.875);
    expect(up.east).toBeCloseTo(0);
    const left = pxToSky(-4, 0, 0.25);
    expect(left.east).toBeCloseTo(1);
    expect(pxToSky(3, 4, 1).total).toBeCloseTo(5);
  });

  it("matches Barnard's Star: 55.5 px north in 360 days is about 10.4 arcsec a year", () => {
    const s = pxToSky(3.76, -55.53, 0.1875);
    expect(s.total).toBeCloseTo(10.43, 1);
    expect(perYear(s.total, 360.87)).toBeCloseTo(10.56, 1);
    expect(compass(s.east, s.north)).toBe('north');
  });

  it('names compass directions and skips tiny shifts', () => {
    expect(compass(3.9, -2.4)).toBe('south-east');
    expect(compass(-1, 0)).toBe('west');
    expect(compass(0.1, 0.1)).toBeNull();
  });

  it('converts to a yearly rate and guards zero days', () => {
    expect(perYear(5, 365.25)).toBeCloseTo(5);
    expect(perYear(5, 0)).toBe(0);
  });

  it('scores by how close the guess lands', () => {
    expect(score(0.4)).toBe(10);
    expect(score(1.5)).toBe(7);
    expect(score(3)).toBe(4);
    expect(score(8)).toBe(0);
    expect(clamp(600, 0, 488)).toBe(488);
  });
});
