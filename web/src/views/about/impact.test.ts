import { describe, expect, it } from 'vitest';
import { leadDays, millionKm, summarize, type Find, type ImpactPage } from './impact';

const page = (name: string, today: number | null, scenario: object | null): ImpactPage => ({
  slug: name.toLowerCase(),
  name,
  impact: { one_year_after_last_obs: today == null ? null : { factor: today }, at_discovery_scenario: scenario },
});
const fit = (factor: number, converged = true) => ({ first_days_of_obs: 7, spherex_positions_used: 1, sigma3_km_before: 15967617, sigma3_km_after: 2719821, factor, converged });

describe('about page numbers', () => {
  it('counts finds seen before the first known observation', () => {
    const finds = [{ days_before_first_known_obs: 14 }, { days_before_first_known_obs: 4 }, { days_before_first_known_obs: null }, {}] as Find[];
    expect(leadDays(finds)).toEqual({ n: 2, min: 4, max: 14 });
  });

  it('keeps clear gains apart from small and weak ones', () => {
    const s = summarize([
      page('A', 1.01, fit(5.9)),
      page('B', 1.07, fit(3.2)),
      page('C', 1.0, fit(1.5)),
      page('D', 1.01, fit(0.9)),
      page('E', 1.0, fit(1.3, false)),
      page('F', 1.0, { error: 'not finite' }),
      page('G', 1.01, null),
      { slug: 'h', name: 'H' },
    ]);
    expect(s.top.map((g) => g.name)).toEqual(['A', 'B']);
    expect(s.rest).toEqual([0.9, 1.5]);
    expect(s.weak).toBe(2);
    expect(s.today).toEqual([0, 7]);
  });

  it('says nothing when there is no impact data', () => {
    expect(summarize([{ slug: 'x', name: 'X' }])).toEqual({ top: [], rest: null, weak: 0, today: null });
  });

  it('writes distances in millions of km', () => {
    expect(millionKm(15967617)).toBe('16 million km');
    expect(millionKm(2719821)).toBe('2.7 million km');
  });
});
