import { describe, expect, it } from 'vitest';
import { APOPHIS, best, fmtKm, precoveryRound, score } from './defense-logic';

describe('defense', () => {
  it('reads the at-discovery scenario', () => {
    const r = precoveryRound('2025 ST20', '2025st20', '2025-09-27', {
      days_before_first_known_obs: 14, spherex_positions: 1,
      at_discovery_scenario: { sigma3_km_before: 15967617, sigma3_km_after: 2719821, factor: 5.9, at_iso: '2026-09-27', n_mpc_obs: 18, first_days_of_obs: 7 },
    }, false);
    expect(r?.kind).toBe('precovery');
    expect(r && 'factor' in r && r.factor).toBe(5.9);
    expect(precoveryRound('x', 'x', '', null, null)).toBeNull();
  });
  it('scores the action that helps most first', () => {
    expect(best(APOPHIS)).toBe('archive');
    expect(score(APOPHIS, 'wait')).toBe(0);
    const empty = { kind: 'empty' as const, name: 'x', slug: 'x', discovered: '', n_frames: 120, best_snr: 0.2 };
    expect(best(empty)).toBe('nights');
  });
  it('formats distances', () => {
    expect(fmtKm(15967617)).toBe('16.0 million km');
    expect(fmtKm(53000)).toBe('53,000 km');
    expect(fmtKm(2100)).toBe('2,100 km');
  });
});
