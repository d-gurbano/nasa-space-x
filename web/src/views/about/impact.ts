// Numbers for the About page, taken from index.json and from the "impact" block of each find's
// object page (COMPUTED by the engine). Nothing here is rounded up: weak fits are counted apart.
import type { IndexObject, ObjectPage } from '../../lib/types';

/** Fields the final engine run adds to index.json; they are not in the v1 types. */
export type Find = IndexObject & { days_before_first_known_obs?: number | null };

interface Scenario {
  first_days_of_obs?: number;
  spherex_positions_used?: number;
  sigma3_km_before?: number;
  sigma3_km_after?: number;
  factor?: number;
  converged?: boolean;
}
export type ImpactPage = Pick<ObjectPage, 'slug' | 'name'> & {
  facts?: { pha?: boolean } | null;
  impact?: { one_year_after_last_obs?: { factor?: number } | null; at_discovery_scenario?: Scenario | null } | null;
};

/** How many finds were seen before the first known observation anywhere, and by how many days. */
export function leadDays(finds: Find[]): { n: number; min: number; max: number } {
  const days = finds.map((o) => o.days_before_first_known_obs ?? 0).filter((d) => d > 0);
  return { n: days.length, min: Math.min(...days), max: Math.max(...days) };
}

export interface Gain { slug: string; name: string; factor: number; kmBefore: number; kmAfter: number; days: number; positions: number }
export interface ImpactSummary {
  /** Clear gains in the "right after discovery" scenario (2x or more, fit converged), best first. */
  top: Gain[];
  /** Smallest and largest factor among the other converged scenarios. */
  rest: [number, number] | null;
  /** Scenarios the engine could not fit well enough to trust. */
  weak: number;
  /** Smallest and largest gain today, in percent, with every known observation in the fit. */
  today: [number, number] | null;
}

export function summarize(pages: ImpactPage[]): ImpactSummary {
  const ok: Gain[] = [];
  let weak = 0;
  const pct: number[] = [];
  for (const p of pages) {
    const now = p.impact?.one_year_after_last_obs?.factor;
    if (Number.isFinite(now)) pct.push(Math.max(0, Math.round((now! - 1) * 100)));
    const s = p.impact?.at_discovery_scenario;
    if (!s) continue;
    if (s.converged !== true || !Number.isFinite(s.factor) || !Number.isFinite(s.sigma3_km_before) || !Number.isFinite(s.sigma3_km_after)) {
      weak++;
      continue;
    }
    ok.push({ slug: p.slug, name: p.name, factor: s.factor!, kmBefore: s.sigma3_km_before!, kmAfter: s.sigma3_km_after!, days: s.first_days_of_obs ?? 0, positions: s.spherex_positions_used ?? 0 });
  }
  ok.sort((a, b) => b.factor - a.factor);
  const top = ok.filter((g) => Math.round(g.factor) >= 2).slice(0, 2);
  const others = ok.slice(top.length).map((g) => g.factor);
  return {
    top,
    rest: others.length ? [Math.min(...others), Math.max(...others)] : null,
    weak,
    today: pct.length ? [Math.min(...pct), Math.max(...pct)] : null,
  };
}

/** "16 million km", "2.7 million km". */
export function millionKm(km: number): string {
  const m = km / 1e6;
  return `${m >= 10 ? Math.round(m) : m.toFixed(1)} million km`;
}
