import { describe, expect, it } from 'vitest';
import { byOutcome, byType, curveBars, decoyTally, explain, failedChecks, median, outcome, posErrors, tally, usable, type Bench, type BenchCase } from './logic';
import { readFileSync } from 'node:fs';

const mk = (truth: string, rewind_verdict: string, extra: Partial<BenchCase> = {}): BenchCase => ({ name: 'x', hidden_until_iso: '2026-01-01', truth, rewind_verdict, ...extra });

// the shape of the real file: 5 found, 3 hints and 1 too faint among 9 seen, plus a hint on one not seen
const real = [
  ...Array.from({ length: 5 }, () => mk('seen', 'FOUND')),
  ...Array.from({ length: 3 }, () => mk('seen', 'HINT')),
  mk('seen', 'TOO_FAINT'),
  mk('not seen', 'HINT'),
];

describe('benchmark logic', () => {
  it('counts hints on their own, not as misses', () => {
    expect(tally(real)).toEqual({ found: 5, hint: 3, missed: 1, quiet: 1, false: 0, total: 10, seen: 9 });
  });

  it('only a FOUND on an unseen object is a false alarm', () => {
    expect(outcome(mk('not seen', 'HINT'))).toBe('quiet');
    expect(outcome(mk('not seen', 'FOUND'))).toBe('false');
  });

  it('sorts found first, then brightest first', () => {
    const a = mk('seen', 'FOUND', { V_pred: 18 });
    const b = mk('seen', 'FOUND', { V_pred: 16 });
    const h = mk('seen', 'HINT', { V_pred: 12 });
    expect(byOutcome([h, a, b])).toEqual([b, a, h]);
  });

  it('explains a hint with the checks that failed', () => {
    const c = mk('seen', 'HINT', { checks: { snr: true, time_shift: false } });
    expect(failedChecks(c)).toEqual(['the signal is not strongest at the right time']);
    expect(explain(c)).toBe('Rewind saw a signal but did not call it a find: the signal is not strongest at the right time.');
  });

  it('survives cases without the optional fields', () => {
    for (const c of real) expect(explain(c)).not.toMatch(/undefined|null|NaN/);
  });
});

describe('orbit keys and bars', () => {
  it('finds the orbit key from the case name', async () => {
    const { orbitKey } = await import('./logic');
    expect(orbitKey("(2525) O'Steen")).toBe('2525');
    expect(orbitKey('(22015) 1999 XM100')).toBe('22015');
    expect(orbitKey('217P/LINEAR')).toBe('217p');
    expect(orbitKey('C/2025 L2 (ATLAS)')).toBe('c2025l2');
  });
  it('scales S/N bars on a log scale, 0 for no signal', async () => {
    const { snrBar } = await import('./logic');
    expect(snrBar(null)).toBe(0);
    expect(snrBar(-2)).toBe(0);
    expect(snrBar(150)).toBe(1);
    expect(snrBar(5)).toBeGreaterThan(0.3);
  });
});

describe('benchmark v2 file', () => {
  const data = JSON.parse(readFileSync(new URL('../../../public/data/benchmark.json', import.meta.url), 'utf8')) as Bench;
  const cases = (data.cases ?? []).filter(usable);

  it('counts 10 of 18 found, 7 hints, 1 missed, no false alarm in 23 usable cases and 22 decoys', () => {
    expect(tally(cases)).toMatchObject({ found: 10, seen: 18, hint: 7, missed: 1, false: 0, total: 23 });
    expect(decoyTally(data.decoys ?? [])).toEqual({ ran: 22, false: 0 });
  });

  it('splits the result by type and keeps the totals', () => {
    const t = byType(cases);
    expect([...t.keys()].sort()).toEqual(['comet', 'mba', 'neo']);
    expect([...t.values()].reduce((s, x) => s + x.found, 0)).toBe(10);
  });

  it('has a median position error of 0.5 arcsec', () => {
    expect(median(posErrors(cases))).toBeCloseTo(0.5, 1);
    expect(median([])).toBeNull();
  });

  it('turns the curve into bars that never exceed the bin', () => {
    const bars = curveBars(data.completeness_curve ?? []);
    expect(bars.length).toBe(5);
    for (const b of bars) expect(b.found + b.hint).toBeLessThanOrEqual(b.n);
    expect(curveBars([{ n: 0 }, {}])).toEqual([]);
  });

  it('survives cases with almost no fields', () => {
    const bare = { name: 'x', truth: 'unknown', rewind_verdict: 'ERROR' } as BenchCase;
    expect(usable(bare)).toBe(false);
    expect(explain(bare)).not.toMatch(/undefined|NaN/);
    expect(tally([]).seen).toBe(0);
  });
});
