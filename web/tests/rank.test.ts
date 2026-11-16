import { describe, expect, it } from 'vitest';
import { beforeWhat, clusterMarks, daysBefore, knownSince, rankObjects, tally } from '../src/lib/rank';

const o = (slug: string, verdict: string, kind = 'comet', best_snr = 5, disc = 61300) =>
  ({ slug, name: slug, verdict, kind, best_snr, discovered: { mjd: disc, iso: '', by: '', site: '' } }) as any;
const f = (slug: string, mjd: number, snr: number) => ({ slug, mjd, snr, iso: '', photo: '', label: '', spherex_xyz_au: [0, 0, 0], object_xyz_au: [0, 0, 0] }) as any;

describe('ranking', () => {
  it('orders by verdict, new finds before known objects, then by signal', () => {
    const list = [o('faint', 'TOO_FAINT'), o('eros', 'FOUND', 'famous', 100), o('none', 'NO_PHOTOS'), o('q1', 'FOUND', 'comet', 9), o('s1', 'FOUND', 'comet', 7), o('h', 'HINT')];
    expect(rankObjects(list).map((x) => x.slug)).toEqual(['q1', 's1', 'eros', 'h', 'faint', 'none']);
  });
});

describe('tally', () => {
  it('counts new finds apart from known objects and only claims "before discovery" when every find has it', () => {
    const before = (x: any, d: number) => ({ ...x, first_spherex_hint: { days_before_discovery: d } });
    const list = [before(o('a', 'FOUND'), 14), before(o('b', 'FOUND'), 0), o('eros', 'FOUND', 'famous'), o('h', 'HINT'), o('t', 'TOO_FAINT'), o('n', 'NO_PHOTOS')];
    expect(tally(list)).toEqual({ searched: 6, found: 2, before: 2, allBefore: true, known: 1, hints: 1, tooFaint: 1, noPhotos: 1, pending: 0 });
    expect(tally([...list, o('c', 'FOUND')]).allBefore).toBe(false);
  });
});

describe('how early', () => {
  const hint = (d: number) => ({ mjd: 0, iso: '', days_before_discovery: d });
  const disc = { mjd: 61372, iso: '2026-11-03', by: '', site: '' };
  it('counts to the first known observation when the engine gives it', () => {
    // announced on 3 Nov, but first observed on 15 Sep: 13 days, not 62
    const v1 = { discovered: disc, first_spherex_hint: hint(62), first_known_obs_iso: '2026-09-15', days_before_first_known_obs: 13 };
    expect(daysBefore(v1)).toBe(13);
    expect(beforeWhat(v1)).toBe('the first known observation');
    expect(knownSince(v1)).toBe(61298);
  });
  it('photos that are not earlier than the known observations are not a find before discovery', () => {
    const w2 = { verdict: 'FOUND', kind: 'comet', first_spherex_hint: hint(32), days_before_first_known_obs: null } as any;
    expect(daysBefore(w2)).toBeNull();
    expect(tally([w2])).toMatchObject({ found: 1, before: 0, allBefore: false });
  });
  it('falls back to the discovery date in data without those fields', () => {
    const old = { discovered: disc, first_spherex_hint: hint(14) };
    expect(daysBefore(old)).toBe(14);
    expect(beforeWhat(old)).toBe('discovery');
    expect(knownSince(old)).toBe(61372);
  });
});

describe('time bar marks', () => {
  it('photos closer than the gap share one mark, which stands for the best of them', () => {
    const snr = [3, 9, 5, 2, 7];
    const marks = clusterMarks([100, 104, 111, 140, 300], 12, (a, b) => snr[a] > snr[b]);
    expect(marks).toEqual([{ first: 0, last: 2, best: 1 }, { first: 3, last: 3, best: 3 }, { first: 4, last: 4, best: 4 }]);
  });
  it('a mark never grows wider than the gap', () => {
    const xs = Array.from({ length: 40 }, (_, k) => k * 5);
    for (const m of clusterMarks(xs, 12, () => false)) expect(xs[m.last] - xs[m.first]).toBeLessThanOrEqual(12);
  });
});

describe('showcase pick', () => {
  it('prefers FOUND, picks the object with the strongest single photo, skips known objects', async () => {
    const { pickShowcase } = await import('../src/lib/rank');
    const idx = {
      objects: [o('eros', 'FOUND', 'famous', 99, 1000), o('h1', 'HINT', 'comet', 9, 62000), o('v1', 'FOUND', 'comet', 9, 62000), o('yh5', 'FOUND', 'neo', 5, 62000)],
      flash_events: [f('eros', 61000, 70), f('h1', 61900, 30), f('v1', 61950, 4.3), f('yh5', 61940, 7), f('yh5', 61960, 18.4), f('yh5', 61970, 13)],
    };
    const s = pickShowcase(idx);
    expect(s!.object.slug).toBe('yh5');
    expect(s!.flash.mjd).toBe(61960);
    expect(s!.score).toBe(18.4);
    expect(s!.sure).toBe(true);
  });
  it('?flash=<slug> overrides the pick', async () => {
    const { pickShowcase } = await import('../src/lib/rank');
    const idx = { objects: [o('v1', 'FOUND', 'comet', 9, 62000), o('yh5', 'FOUND', 'neo', 5, 62000)], flash_events: [f('v1', 61950, 4.3), f('yh5', 61960, 18.4)] };
    expect(pickShowcase(idx, 'v1')!.object.slug).toBe('v1');
    expect(pickShowcase(idx, 'nope')!.object.slug).toBe('yh5');
  });
  it('never shows a photo taken after the first known observation', async () => {
    const { pickShowcase } = await import('../src/lib/rank');
    const late = { ...f('w2', 61900, 30), before_first_known_obs: false };
    const idx = { objects: [o('w2', 'FOUND', 'comet', 30, 62000), o('yh5', 'FOUND', 'neo', 9, 62000)], flash_events: [late, f('yh5', 61950, 4), { ...f('yh5', 61990, 8), before_first_known_obs: false }] };
    const s = pickShowcase(idx);
    expect(s!.object.slug).toBe('yh5');
    expect(s!.flash.mjd).toBe(61950);
  });
  it('falls back to the HINT with the strongest single photo', async () => {
    const { pickShowcase } = await import('../src/lib/rank');
    const idx = { objects: [o('a', 'HINT', 'comet', 5.4, 62000), o('b', 'HINT', 'comet', 4.4, 62000)], flash_events: [f('a', 61900, 3), f('b', 61900, 4), f('a', 61910, 2)] };
    const s = pickShowcase(idx);
    expect(s!.object.slug).toBe('b');
    expect(s!.sure).toBe(false);
  });
  it('picks 2025 YH5 from the real index', async () => {
    const { pickShowcase } = await import('../src/lib/rank');
    const fs = await import('node:fs');
    const path = new URL('../public/data/index.json', import.meta.url);
    if (!fs.existsSync(path)) return;
    const s = pickShowcase(JSON.parse(fs.readFileSync(path, 'utf8')));
    expect(s!.object.slug).toBe('2025yh5');
  });
});
