import { describe, expect, it } from 'vitest';
import { calibrate, endError, findPeak, shifts, snrAt, stack, velocity, wrap360 } from '../src/views/game/stack';
import { sampleRounds, synthRound } from '../src/views/game/rounds';

describe('shift-and-stack', () => {
  it('angle 0 points up, 90 points right', () => {
    const [x0, y0] = velocity({ angle: 0, rate: 1 });
    const [x1, y1] = velocity({ angle: 90, rate: 1 });
    expect(x0).toBeCloseTo(0);
    expect(y0).toBeCloseTo(-1);
    expect(x1).toBeCloseTo(1);
    expect(y1).toBeCloseTo(0);
  });

  it('shifts undo the motion around the middle time', () => {
    const s = shifts([0, 5, 10], { angle: 90, rate: 2 });
    expect(s.map(([x, y]) => [x + 0, y + 0])).toEqual([[10, 0], [0, 0], [-10, 0]]);
  });

  it('the true motion makes a faint dot pop and a wrong one does not', () => {
    const r = synthRound(5, 1.2, 16, 6, 30);
    const { w, h } = r.data;
    const out = new Float32Array(w * h), cover = new Uint8Array(w * h);
    const truth = { angle: r.truth.angle_deg, rate: r.truth.rate_px_per_hr };
    stack(r.data, truth, out, cover);
    const p = findPeak(out, w, h, 5);
    const cal = calibrate(out, w, h, p, [5, 10, 20]);
    const hit = snrAt(out, w, h, p, cal);
    stack(r.data, { angle: wrap360(truth.angle + 120), rate: truth.rate }, out, cover);
    const miss = snrAt(out, w, h, p, cal);
    expect(hit).toBeGreaterThan(4);
    expect(miss).toBeLessThan(hit / 2);
  });

  it('end error is zero at the truth and grows with the angle', () => {
    const dt = [0, 4, 8];
    expect(endError(dt, { angle: 30, rate: 5 }, { angle: 30, rate: 5 })).toBeCloseTo(0);
    expect(endError(dt, { angle: 30, rate: 5 }, { angle: 40, rate: 5 })).toBeGreaterThan(3);
  });

  it('the sample has 6 rounds, easy to hard', () => {
    const s = sampleRounds();
    expect(s).toHaveLength(6);
    expect(s[0].difficulty).toBe('easy');
    expect(s[5].difficulty).toBe('hard');
  });
});
