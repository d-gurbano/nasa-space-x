// Planetary defense desk: pure logic. Builds the rounds from our computed orbit numbers and scores a choice.

export type Action = 'archive' | 'nights' | 'wait';
export interface Scenario { sigma3_km_before: number; sigma3_km_after: number; factor: number; at_iso: string; n_mpc_obs: number; first_days_of_obs: number }
export interface Impact { days_before_first_known_obs: number; spherex_positions: number; at_discovery_scenario?: Scenario }

export type DefRound =
  | { kind: 'precovery'; name: string; slug: string; discovered: string; days: number; positions: number; before_km: number; after_km: number; factor: number; at_iso: string; n_obs: number; first_days: number; sentry: boolean | null }
  | { kind: 'apophis'; name: string; before_km: number; after_km: number; miss_km: number; today_km: number }
  | { kind: 'empty'; name: string; slug: string; discovered: string; n_frames: number; best_snr: number | null };

/** Apophis with only its 2004 observations, plus the real 15 March 2004 precovery (COMPUTED; see findings.ts). */
export const APOPHIS: DefRound = { kind: 'apophis', name: '(99942) Apophis, in 2004', before_km: 53000, after_km: 2100, miss_km: 46600, today_km: 38000 };

export const EARTH_KM = 6371, MOON_KM = 384400;

export function precoveryRound(name: string, slug: string, discovered: string, imp: Impact | null | undefined, sentry: boolean | null): DefRound | null {
  const s = imp?.at_discovery_scenario;
  if (!s) return null;
  return {
    kind: 'precovery', name, slug, discovered, days: imp!.days_before_first_known_obs, positions: imp!.spherex_positions,
    before_km: s.sigma3_km_before, after_km: s.sigma3_km_after, factor: s.factor, at_iso: s.at_iso,
    n_obs: s.n_mpc_obs, first_days: s.first_days_of_obs, sentry,
  };
}

/** The action that helps most first: old images when they hold the object, otherwise more telescope nights. */
export const best = (r: DefRound): Action => (r.kind === 'empty' ? 'nights' : 'archive');
export const score = (r: DefRound, a: Action) => (a === best(r) ? 10 : 0);

/** "16.0 million km", "53,000 km". */
export function fmtKm(km: number): string {
  if (km >= 1e6) return `${(km / 1e6).toFixed(1)} million km`;
  if (km >= 1e4) return `${(Math.round(km / 1000) * 1000).toLocaleString('en-US')} km`;
  return `${(Math.round(km / 100) * 100).toLocaleString('en-US')} km`;
}
