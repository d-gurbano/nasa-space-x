import { describe, expect, it } from 'vitest';
import { buildField, checkPick, offLine, rng, type DotsRound } from './dots-logic';

const R: DotsRound = {
  field: 'NEP', ra: 0, dec: 0, half_arcsec: 500, mjd: [0, 1, 3], iso: ['a', 'b', 'c'], frames: [],
  movers: [{ name: 'A', v: 20, pts: [[0, 0], [10, 0], [30, 0]] }],
  partial: [{ t: 1, x: 5, y: 5 }],
  stars: [[100, 100, 30]],
};

describe('dots', () => {
  it('builds every real dot plus labelled noise', () => {
    const d = buildField(R, 0, rng(1));
    expect(d.filter((x) => x.kind === 'mover')).toHaveLength(3);
    expect(d.filter((x) => x.kind === 'star')[0].t).toBe(-1);
    expect(d.filter((x) => x.kind === 'noise')).toHaveLength(9);
    expect(d.map((x) => x.id)).toEqual(d.map((_, i) => i));
  });
  it('measures steady straight-line motion with uneven gaps', () => {
    expect(offLine([[0, 0], [10, 0], [30, 0]], [0, 1, 3])).toBeCloseTo(0);
    expect(offLine([[0, 0], [15, 0], [30, 0]], [0, 1, 3])).toBeCloseTo(5 / 30);
  });
  it('accepts the real track and explains a wrong one', () => {
    const d = buildField(R, 0, rng(2));
    const m = d.filter((x) => x.kind === 'mover').map((x) => x.id);
    expect(checkPick(d, m, R.mjd)).toEqual({ ok: true, track: 0 });
    const t0 = d.filter((x) => x.kind === 'mover' && x.t === 0)[0].id;
    expect(checkPick(d, [t0, t0, t0], R.mjd)).toEqual({ ok: false, why: 'times' });
    const p = d.find((x) => x.kind === 'partial')!.id;
    const t2 = d.filter((x) => x.kind === 'mover' && x.t === 2)[0].id;
    expect(checkPick(d, [t0, p, t2], R.mjd).ok).toBe(false);
  });
});
