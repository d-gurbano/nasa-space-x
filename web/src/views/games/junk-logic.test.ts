import { describe, expect, it } from 'vitest';
import { aiLine, buildRounds, CATS, pct, type Cat, type JunkStamp } from './junk-logic';

const st = (id: string, cat: Cat, ai: number | null = null): JunkStamp => ({ id, img: id + '.png', cat, label: cat, obsid: 'x', det: 'D1', ai });
const pool: JunkStamp[] = [
  ...Array.from({ length: 6 }, (_, i) => st('s' + i, 'asteroid', 0.99)),
  ...(['trail', 'cosmic', 'ghost', 'detector'] as Cat[]).flatMap((c) => Array.from({ length: 5 }, (_, i) => st(c + i, c))),
];

describe('junk logic', () => {
  it('builds ten distinct rounds with three asteroids and every artifact kind', () => {
    const r = buildRounds(pool, 10, 3);
    expect(r).toHaveLength(10);
    expect(new Set(r.map((s) => s.id)).size).toBe(10);
    expect(r.filter((s) => s.cat === 'asteroid')).toHaveLength(3);
    for (const c of CATS) expect(r.some((s) => s.cat === c.id)).toBe(true);
  });

  it('copes with a small pool', () => {
    expect(buildRounds(pool.slice(0, 8), 10).length).toBeLessThanOrEqual(8);
  });

  it('says plainly when the AI was not run, and reports a real score as given', () => {
    expect(aiLine(st('a', 'ghost'))).toBe('Our AI was not run on this image.');
    expect(aiLine(st('b', 'asteroid', 0.998))).toContain('scored this exact image 1.00');
    expect(aiLine(st('b', 'asteroid', 0.998))).toContain('That was right.');
    expect(aiLine(st('c', 'asteroid', 0.31))).toContain('junk. That was wrong.');
  });

  it('keys are 1 to 5 and the percentage rounds', () => {
    expect(CATS.map((c) => c.key).join('')).toBe('12345');
    expect(pct(7, 10)).toBe(70);
    expect(pct(0, 0)).toBe(0);
  });
});
