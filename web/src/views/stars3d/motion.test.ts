import { describe, expect, it } from 'vitest';
import { STARS, SUN, at, closest, compare, len, scenePos, FAR_RING, speeds, tempLabel, yearLabel } from './motion';

const star = (id: string) => STARS.find((s) => s.id === id)!;

describe('neighbourhood motion', () => {
  it("puts Barnard's Star at its catalogue distance today", () => {
    expect(len(at(star('barnard'), 2016))).toBeCloseTo(1.828, 3);
  });

  it("has Barnard's Star pass closest around the year 11,800 at about 1.15 pc", () => {
    const c = closest(star('barnard'));
    expect(c.year).toBeGreaterThan(11_600);
    expect(c.year).toBeLessThan(11_900);
    expect(c.dist).toBeCloseTo(1.15, 1);
  });

  it("gives Barnard's Star about 90 km/s across the sky", () => {
    expect(speeds(star('barnard')).tangential).toBeCloseTo(90, 0);
  });

  it('keeps the far stars on the far ring', () => {
    expect(len(scenePos(star('rdra'), -5000))).toBeCloseTo(FAR_RING, 6);
  });

  it('names years the way people say them', () => {
    expect(yearLabel(2026)).toBe('2026');
    expect(yearLabel(11_736.4)).toBe('11,736');
    expect(yearLabel(-9999)).toBe('10,000 BCE');
  });

  it('compares each star with the Sun or Jupiter', () => {
    expect(compare(star('barnard'))).toMatchObject({ body: 'Sun', line: '0.2 × the Sun' });
    expect(compare(star('wise0855'))).toMatchObject({ body: 'Jupiter', line: 'About Jupiter-size' });
    expect(compare(star('rdra')).line).toBe('About 300 × the Sun');
    expect(compare(SUN)).toMatchObject({ body: 'Jupiter', ratio: 10 });
  });

  it('reads temperatures in Celsius', () => {
    expect(tempLabel(250)).toBe('−25 °C');
    expect(tempLabel(3100)).toBe('2,800 °C');
  });
});
