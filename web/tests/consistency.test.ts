// Cross-page consistency: the numbers and definitions shown on different pages must agree.
// Reads public/data/ when it has been synced, otherwise public/data-sample/.
import { describe, expect, it } from 'vitest';
import { existsSync, readdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { CHECKS, N_CHECKS, VERDICT_DEF, checkResults } from '../src/lib/checks';
import { tally } from '../src/lib/rank';
import { tally as benchTally, usable, type BenchCase } from '../src/views/benchmark/logic';
import { farText, shortDate } from '../src/ui/panel-text';
import type { IndexObject, ObjectPage } from '../src/lib/types';

const PUB = join(__dirname, '..', 'public');
const BASE = existsSync(join(PUB, 'data', 'index.json')) ? join(PUB, 'data') : join(PUB, 'data-sample');
const json = <T>(rel: string): T => JSON.parse(readFileSync(join(BASE, rel), 'utf8')) as T;
const index = json<{ objects: IndexObject[] }>('index.json');
const pages: ObjectPage[] = readdirSync(join(BASE, 'objects'))
  .filter((s) => existsSync(join(BASE, 'objects', s, 'object.json')))
  .map((s) => json<ObjectPage>(`objects/${s}/object.json`));

describe('check definitions', () => {
  it('lists the same nine checks as the engine', () => {
    const src = readFileSync(join(__dirname, '..', '..', 'engine', 'rewind_engine', 'verdict.py'), 'utf8');
    const body = src.slice(src.indexOf('def checks_passed'), src.indexOf('return c', src.indexOf('def checks_passed')));
    const engineKeys = [...body.matchAll(/^\s+(\w+)=/gm)].map((m) => m[1]).filter((k) => k !== 'c');
    expect(new Set(CHECKS.map((c) => c.key))).toEqual(new Set(engineKeys));
    expect(N_CHECKS).toBe(9);
  });
  it('defines every verdict the data uses', () => {
    const used = new Set(index.objects.map((o) => o.verdict).filter((v) => v !== 'PENDING'));
    for (const v of used) expect(VERDICT_DEF[v], v).toBeTruthy();
  });
  it('never shows more checks for an object than are defined', () => {
    for (const p of pages) {
      const rows = checkResults(p.checks?.passed);
      expect(rows.length, p.slug).toBeLessThanOrEqual(N_CHECKS);
      if (p.checks?.passed) expect(rows.length, p.slug).toBe(Object.keys(p.checks.passed).filter((k) => CHECKS.some((c) => c.key === k)).length);
    }
  });
  it('a FOUND (not a control) passes every check it reports', () => {
    for (const p of pages.filter((x) => x.verdict === 'FOUND' && x.checks?.passed)) {
      const failed = checkResults(p.checks.passed).filter((r) => !r.ok && r.def.key !== 'orbit');
      expect(failed.map((r) => r.def.key), p.slug).toEqual([]);
    }
  });
});

describe('headline numbers', () => {
  it('precoveries are a subset of the finds', () => {
    const t = tally(index.objects);
    expect(t.before).toBeLessThanOrEqual(t.found);
    expect(t.found + t.known + t.hints + t.tooFaint + t.noPhotos + t.pending).toBe(t.searched);
  });
  it('lead times agree between index.json and each object page', () => {
    for (const p of pages) {
      const o = index.objects.find((x) => x.slug === p.slug);
      if (!o || p.days_before_first_known_obs === undefined) continue;
      expect(p.days_before_first_known_obs, p.slug).toBe(o.days_before_first_known_obs);
      expect(p.first_known_obs_iso ?? null, p.slug).toBe(o.first_known_obs_iso ?? null);
    }
  });
  it('the 3σ table and the uncertainty figure use one definition', () => {
    for (const p of pages) {
      const y = p.impact?.one_year_after_last_obs;
      if (!y) continue;
      expect(y.sigma3_km_before, p.slug).toBeGreaterThan(0);
      expect(y.sigma3_km_after, p.slug).toBeGreaterThan(0);
      expect(y.factor, p.slug).toBeCloseTo(y.sigma3_km_before / y.sigma3_km_after, 1);
    }
  });
});

describe('blind test', () => {
  const bench = json<{ cases?: BenchCase[]; summary?: { found?: number; seen?: number; hints?: number; missed?: number } }>('benchmark.json');
  const t = benchTally((bench.cases ?? []).filter(usable));
  it('the headline parts add up', () => {
    expect(t.found + t.hint + t.missed).toBe(t.seen);
    expect(t.seen + t.quiet + t.false).toBe(t.total);
  });
  it('matches the engine summary when it has one', () => {
    const s = bench.summary;
    if (s?.seen != null) expect(t.seen).toBe(s.seen);
    if (s?.found != null && s.seen != null) expect(t.found).toBe(s.found);
    if (s?.hints != null) expect(t.hint).toBe(s.hints);
  });
});

describe('number wording', () => {
  it('never rounds a false-alarm rate to zero', () => {
    expect(farText(1 / 7800, 7800)).toBe('1 in 7,800 null trials (0.013%)');
    expect(farText(0, 300)).toBe('0 in 300 null trials');
    expect(farText(0.05)).toBe('5.0%');
  });
  it('keeps the year in compact dates', () => {
    expect(shortDate('26 Dec 2025')).toBe("26 Dec '25");
  });
});
