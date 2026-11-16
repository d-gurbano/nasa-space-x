import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { HIT_RATE, hitRows, LIVE } from '../src/views/findings';

const json = (f: string) => JSON.parse(readFileSync(join(__dirname, '..', 'public', 'data', f), 'utf8'));

describe('findings.ts matches the data files', () => {
  it('hit rate by type equals benchmark.json archive_search_hit_rate', () => {
    const hr = json('benchmark.json').archive_search_hit_rate;
    expect(hr.label).toBe('MEASURED');
    for (const k of ['comet', 'neo', 'lost'] as const) {
      expect(HIT_RATE[k].found).toBe(hr.by_type[k].found);
      expect(HIT_RATE[k].with_photos).toBe(hr.by_type[k].with_photos);
    }
    expect(hitRows(hr.by_type)).toEqual(hitRows());
    expect(hitRows()).toEqual([['Comets', '5 of 31', '16%'], ['Near-Earth asteroids', '3 of 201', '1.5%'], ['Lost objects', '0 of 11', '']]);
  });
  it('the live test equals index.json live_stats', () => {
    const ls = json('index.json').live_stats;
    for (const [k, v] of Object.entries(LIVE)) expect(String(ls[k]).slice(0, 10), k).toBe(String(v));
  });
});
