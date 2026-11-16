import { describe, expect, it } from 'vitest';
import { perImage, pickRounds, score, type FaintObj, type Verdict } from './faint-logic';
import { rng } from './dots-logic';

const mk = (v: Verdict, i: number): FaintObj => ({ slug: v + i, name: v + i, kind: 'neo', verdict: v, pred_ab: 20, n_frames: 100, snr: 1, limit_ab: 20.5 });
const ALL = [...Array.from({ length: 5 }, (_, i) => mk('FOUND', i)), ...Array.from({ length: 9 }, (_, i) => mk('HINT', i)), ...Array.from({ length: 20 }, (_, i) => mk('TOO_FAINT', i))];

describe('faint', () => {
  it('draws a 3/3/4 mix of ten', () => {
    const r = pickRounds(ALL, rng(3));
    expect(r).toHaveLength(10);
    expect(r.filter((o) => o.verdict === 'FOUND')).toHaveLength(3);
    expect(r.filter((o) => o.verdict === 'HINT')).toHaveLength(3);
    expect(new Set(r).size).toBe(10);
  });
  it('tops up when a group is short', () => {
    expect(pickRounds([mk('FOUND', 0), ...ALL.slice(5)], rng(4))).toHaveLength(10);
  });
  it('scores a bet', () => {
    expect(score('show', 'FOUND')).toBe(10);
    expect(score('faint', 'FOUND')).toBe(0);
    expect(score('faint', 'TOO_FAINT')).toBe(10);
    expect(score('show', 'HINT')).toBe(5);
  });
  it('scales S/N with the square root of the number of images', () => {
    expect(perImage(10, 100)).toBeCloseTo(1);
  });
});
