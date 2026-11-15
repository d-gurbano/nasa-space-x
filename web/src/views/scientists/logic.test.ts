import { describe, expect, it } from 'vitest';
import { bytes, filterRows, gainRange, km, lead, snrBar, sortRows, splitContract, toCsv, type Row } from './logic';

const row = (name: string, verdict: Row['verdict'], snr: number | null, extra: Partial<Row> = {}): Row => ({
  slug: name.toLowerCase().replace(/[^a-z0-9]/g, ''), name, kind: 'neo', verdict, verdict_text: `${name}, "quoted"`,
  discovered: { mjd: 61000, iso: '2025-11-21', by: 'X', site: 'Y' }, first_spherex_hint: null,
  best_snr: snr as number, n_frames: 10, thumb: '', page: '', ...extra,
});

const rows = [
  row('2025 ST20', 'FOUND', 9.1, { days_before_first_known_obs: 14, first_known_obs_iso: '2025-09-27' }),
  row('C/2025 W2', 'FOUND', 11.4, { days_before_first_known_obs: null, first_known_obs_iso: '2025-10-26' }),
  row('433 Eros', 'FOUND', 110.9, { kind: 'famous' }),
  row('2025 VP', 'HINT', 15.6),
  row('2025 MQ91', 'NO_PHOTOS', null),
  row('2026 AB1', 'TOO_FAINT', 0.4),
];

describe('results table', () => {
  it('filters by verdict and by name, ignoring spaces and slashes', () => {
    expect(filterRows(rows, 'FOUND', '').length).toBe(3);
    expect(filterRows(rows, 'ALL', 'st20').map((o) => o.name)).toEqual(['2025 ST20']);
    expect(filterRows(rows, 'ALL', 'c/2025 w').map((o) => o.name)).toEqual(['C/2025 W2']);
    expect(filterRows(rows, 'HINT', 'st20')).toEqual([]);
  });

  it('ranks finds first and known objects after new finds', () => {
    expect(sortRows(rows, { key: 'verdict', dir: 1 }).map((o) => o.name)).toEqual(['C/2025 W2', '2025 ST20', '433 Eros', '2025 VP', '2026 AB1', '2025 MQ91']);
  });

  it('keeps empty values last in both directions', () => {
    expect(sortRows(rows, { key: 'snr', dir: -1 }).map((o) => o.name)).toEqual(['433 Eros', '2025 VP', 'C/2025 W2', '2025 ST20', '2026 AB1', '2025 MQ91']);
    expect(sortRows(rows, { key: 'snr', dir: 1 }).at(-1)!.name).toBe('2025 MQ91');
    expect(sortRows(rows, { key: 'lead', dir: -1 })[0].name).toBe('2025 ST20');
  });

  it('sorts names by number, not by character', () => {
    const names = sortRows([row('2025 YH5', 'HINT', 1), row('2025 YH10', 'HINT', 1), row('433 Eros', 'HINT', 1)], { key: 'name', dir: 1 }).map((o) => o.name);
    expect(names).toEqual(['433 Eros', '2025 YH5', '2025 YH10']);
  });

  it('says how a find compares with the first known observation, and nothing stronger', () => {
    expect(rows.map(lead)).toEqual(['14 d earlier', 'not earlier', 'known object', '', '', '']);
  });

  it('writes CSV with quoted text', () => {
    const csv = toCsv(rows.slice(0, 1)).split('\n');
    expect(csv[0].startsWith('name,slug,kind,verdict')).toBe(true);
    expect(csv[1]).toContain('2025 ST20,2025st20,neo,FOUND,9.1,10,2025-11-21,X,2025-09-27,14,,"2025 ST20, ""quoted"""');
  });
});

describe('contract and impact helpers', () => {
  it('splits the contract at its headings', () => {
    const parts = splitContract('# Title\nintro\n\n## 1. a.json\n{ "a": 1 }\n\n## 2. b.json\nline\nline 2\n');
    expect(parts).toEqual([{ title: '1. a.json', body: '{ "a": 1 }' }, { title: '2. b.json', body: 'line\nline 2' }]);
  });

  it('formats kilometres and the gain range', () => {
    expect(km(32462)).toBe('32,462');
    expect(km(2719821)).toBe('2.72M');
    expect(km(15967617)).toBe('16.0M');
    expect(km(176580398)).toBe('177M');
    expect(gainRange([1.07, 1.0, 1.01])).toBe('0 to 7%');
  });

  it('scales the S/N bar by square root and clamps empty or negative values', () => {
    expect(snrBar(100, 100)).toBe(100);
    expect(snrBar(25, 100)).toBe(50);
    expect(snrBar(-2.5, 100)).toBe(0);
    expect(snrBar(null, 100)).toBe(0);
    expect(snrBar(5, 0)).toBe(0);
  });

  it('formats file sizes', () => {
    expect(bytes(812)).toBe('812 B');
    expect(bytes(4723)).toBe('4.6 KB');
    expect(bytes(163047)).toBe('159 KB');
    expect(bytes(4464256)).toBe('4.3 MB');
    expect(bytes(66568570)).toBe('63 MB');
  });
});
