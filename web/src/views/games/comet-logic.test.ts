import { describe, expect, it } from 'vitest';
import { explain, kindPhrase, nameNote, pickRounds, ux, yRange, type CometRound } from './comet-logic';

const mk = (slug: string, truth: 'comet' | 'asteroid', o: Partial<CometRound> = {}): CometRound => ({
  slug, name: slug, truth, class: null, verdict: 'FOUND', snr: 5, n_frames: 10, img: `${slug}.png`, points: [],
  bump: truth === 'comet' ? 'faint' : null, bump_band: [4.17, 5.05], warm: false, coma: false, ...o,
});

describe('comet logic', () => {
  it('picks eight rounds, half comets and half asteroids', () => {
    const pool = [...'abcdef'].map((s) => mk('c' + s, 'comet')).concat([...'abcdef'].map((s) => mk('a' + s, 'asteroid')));
    const r = pickRounds(pool, 8);
    expect(r).toHaveLength(8);
    expect(new Set(r.map((x) => x.slug)).size).toBe(8);
    expect(r.filter((x) => x.truth === 'comet')).toHaveLength(4);
  });

  it('fills from comets when asteroids run short', () => {
    const pool = [...'abcdef'].map((s) => mk('c' + s, 'comet')).concat([mk('a', 'asteroid')]);
    const r = pickRounds(pool, 6);
    expect(r).toHaveLength(6);
    expect(r.filter((x) => x.truth === 'asteroid')).toHaveLength(1);
  });

  it('maps the wavelength range and keeps 0 and 1 in view', () => {
    expect(ux(0.7)).toBeCloseTo(0);
    expect(ux(5.1)).toBeCloseTo(1);
    const [lo, hi] = yRange([{ um: 1, value: 0.9, err: 0.1 }, { um: 4.6, value: 6, err: 2 }]);
    expect(lo).toBeLessThan(0);
    expect(hi).toBeGreaterThan(8);
  });

  it('claims CO2 only when the data flags it', () => {
    expect(explain(mk('x', 'comet', { bump: 'co2' })).join(' ')).toContain('CO2 gas glows at 4.26');
    expect(explain(mk('x', 'comet', { bump: 'faint' })).join(' ')).toContain('too faint to tell');
    expect(explain(mk('x', 'comet', { bump: 'faint', bump_band: null })).join(' ')).toContain('no spectrum point');
    expect(explain(mk('x', 'comet', { bump: 'raised' })).join(' ')).not.toContain('fits a comet');
    expect(explain(mk('x', 'asteroid', { warm: true })).join(' ')).toContain('heat');
    expect(explain(mk('x', 'asteroid')).join(' ')).not.toContain('CO2');
  });

  it('words the kind and the name', () => {
    expect(kindPhrase({ truth: 'comet', class: 'Halley-type Comet*' })).toBe('a Halley-type comet');
    expect(kindPhrase({ truth: 'comet', class: 'Comet' })).toBe('a comet');
    expect(kindPhrase({ truth: 'asteroid', class: 'Apollo' })).toBe('an Apollo near-Earth asteroid');
    expect(nameNote({ truth: 'comet', name: 'P/2026 V1' })).toContain('P/');
    expect(nameNote({ truth: 'comet', name: '3I/ATLAS' })).toContain('interstellar');
    expect(nameNote({ truth: 'asteroid', name: '2025 YH5' })).toBe('');
  });
});
