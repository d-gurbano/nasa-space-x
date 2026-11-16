import { describe, expect, it } from 'vitest';
import { buildRounds, dmagNear, fitSine, gradePeriod, isoToMjd, mjdToIso, passes, trend, type Bin, type PulseData } from './pulse-logic';

const bin = (mjd: number, dmag: number): Bin => ({ mjd, dmag, err: 0.02, scatter: 0.1, n: 10 });

describe('pulse logic', () => {
  it('converts dates', () => {
    expect(isoToMjd('2025-04-30')).toBe(60795);
    expect(mjdToIso(60795.4)).toBe('2025-04-30');
  });

  it('recovers a sine of known period, amplitude and offset', () => {
    const t = Array.from({ length: 40 }, (_, i) => 60800 + i * 13);
    const y = t.map((x) => 0.5 * Math.sin((2 * Math.PI * x) / 246 + 1) + 0.1);
    const f = fitSine(t, y, t.map(() => 0.02), 246);
    expect(f.amp).toBeCloseTo(0.5, 6);
    expect(f.c).toBeCloseTo(0.1, 6);
    expect(f.rms).toBeLessThan(1e-9);
    expect(fitSine(t, y, t.map(() => 0.02), 150).rms).toBeGreaterThan(0.1);
  });

  it('grades a period guess', () => {
    expect(gradePeriod(240, 246.12)).toBe('ok');
    expect(gradePeriod(200, 246.12)).toBe('half');
    expect(gradePeriod(400, 246.12)).toBe('no');
  });

  it('finds passes, the median near a date and the trend', () => {
    const b = [bin(100, -0.3), bin(110, -0.2), bin(300, 0), bin(500, 0.3), bin(505, 0.4)];
    expect(passes(b).map((p) => p.dmag)).toEqual([-0.25, 0, 0.35]);
    expect(dmagNear(b, 104, 10)).toBe(-0.25);
    expect(dmagNear(b, 200, 10)).toBeNull();
    expect(trend(passes(b))).toBe('fade');
    expect(trend([{ dmag: 0 }, { dmag: 0.05 }])).toBe('none');
  });

  it('builds compare rounds from the measured points', () => {
    const d = {
      rdra: { short: [bin(isoToMjd('2025-07-14'), -0.2), bin(isoToMjd('2025-10-17'), 0.9), bin(isoToMjd('2026-06-23'), 0.1), bin(isoToMjd('2026-09-16'), 0.0)], long: [] },
      rwaur: { short: [], long: [bin(100, -0.3), bin(300, 0), bin(500, 0.3)] },
    } as unknown as PulseData;
    const seasons = ['2025-07-14', '2025-10-17', '2026-06-23', '2026-09-16'].map((iso) => ({ iso, n_frames: 1, png: '' }));
    const r = buildRounds(d, seasons);
    expect(r.map((x) => x.type)).toEqual(['compare', 'period', 'period', 'trend', 'few']); // second pair is under 0.2 mag apart
    expect(r[0]).toMatchObject({ truth: 'a' });
    expect(r[3]).toMatchObject({ truth: 'fade' });
  });
});
