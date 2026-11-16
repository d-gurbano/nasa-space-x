import { describe, expect, it } from 'vitest';
import { agrees, build, halfLabel, halfOf, normalise, orderSum, parse, pickRounds, scoreBuild, scoreRead, type NameObj } from './name-logic';

describe('name logic', () => {
  it('parses asteroid designations with the I skipped', () => {
    expect(parse('2025 YH5')).toEqual({ prefix: null, year: 2025, half: 23, order: 8 + 5 * 25 });
    expect(parse('2026 GU')).toEqual({ prefix: null, year: 2026, half: 6, order: 20 });
    expect(parse('2026 BZ')!.order).toBe(25);
    expect(parse('2026 BA1')!.order).toBe(26);
    expect(parse('2026 BI')).toBeNull();
    expect(parse('433 Eros')).toBeNull();
    expect(parse('3I/ATLAS')).toBeNull();
  });
  it('parses comets', () => {
    expect(parse('C/2026 N1')).toEqual({ prefix: 'C', year: 2026, half: 12, order: 1 });
    expect(parse('P/2025 Y2')).toEqual({ prefix: 'P', year: 2025, half: 23, order: 2 });
  });
  it('builds back what it parses', () => {
    for (const n of ['2025 YH5', '2026 GU', '2026 BZ', '2026 BA1', '2026 RO10', 'C/2026 N1', 'P/2026 R3']) expect(build(parse(n)!)).toBe(n);
  });
  it('maps dates to half-months', () => {
    expect(halfOf('2025-12-20')).toBe(23);
    expect(halfOf('2026-01-15')).toBe(0);
    expect(halfOf('2026-01-16')).toBe(1);
    expect(halfLabel(23)).toBe('December 16-31');
    expect(halfLabel(3)).toBe('February 16-28');
  });
  it('explains the order', () => {
    expect(orderSum('2025 YH5')).toBe('H = 8, plus 5 x 25 = 133');
    expect(orderSum('2026 GU')).toBe('U = 20, no number, so 20');
  });
  it('normalises typing', () => {
    expect(normalise(' 2025yh5 ')).toBe('2025 YH5');
    expect(normalise('c / 2026 n1')).toBe('C/2026 N1');
  });
  it('scores both modes', () => {
    const p = parse('2025 YH5')!;
    expect(scoreRead(p, 23, 133).points).toBe(10);
    expect(scoreRead(p, 23, 149)).toMatchObject({ half: true, order: false, points: 5 });
    expect(scoreBuild('2025 YH5', '2025 yh5').points).toBe(10);
    expect(scoreBuild('2025 YH5', '2025 YJ5')).toMatchObject({ half: true, order: false });
    expect(scoreBuild('C/2026 N1', 'P/2026 N1').half).toBe(false);
    expect(scoreBuild('2025 YH5', 'nonsense').valid).toBe(false);
  });
  it('checks names against discovery dates', () => {
    const o = (name: string, iso: string): NameObj => ({ slug: name, name, kind: 'neo', iso });
    expect(agrees(o('2025 YH5', '2025-12-20'), parse('2025 YH5')!)).toBe(true);
    expect(agrees(o('2026 HA3', '2026-04-09'), parse('2026 HA3')!)).toBe(false);
  });
  it('picks eight alternating rounds with a lagged name and comets', () => {
    const objs: NameObj[] = [
      { slug: 'a', name: '2025 YH5', kind: 'neo', iso: '2025-12-20' },
      { slug: 'b', name: '2026 HA3', kind: 'lost', iso: '2026-04-09' },
      { slug: 'c', name: 'C/2026 N1', kind: 'comet', iso: '2026-07-14' },
      { slug: 'd', name: 'P/2025 Y2', kind: 'comet', iso: '2025-12-21' },
      { slug: 'x', name: '433 Eros', kind: 'famous', iso: '1898-08-13' },
      ...Array.from({ length: 12 }, (_, i) => ({ slug: `n${i}`, name: `2026 B${'ABCDEFGHJKLM'[i]}3`, kind: 'neo', iso: '2026-01-19' })),
    ];
    const r = pickRounds(objs, 8, () => 0.3);
    expect(r).toHaveLength(8);
    expect(r.map((x) => x.mode)).toEqual(['read', 'build', 'read', 'build', 'read', 'build', 'read', 'build']);
    expect(r[0].obj.name).toBe('2025 YH5');
    expect(r.some((x) => x.mode === 'read' && !x.agrees)).toBe(true);
    expect(r.some((x) => x.mode === 'build' && x.p.prefix)).toBe(true);
    expect(r.every((x) => x.mode === 'read' || agrees(x.obj, x.p))).toBe(true);
    expect(new Set(r.map((x) => x.obj.slug)).size).toBe(8);
  });
});
