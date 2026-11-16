// Loads site data. Prefers real engine output in data/, falls back to data-sample/.
import type { PlanetsFile, SiteIndex } from './types';
import type { PlanetRow } from './kepler';

export type Fetcher = (url: string) => Promise<Response>;

export interface DataSource {
  base: string; // URL of the folder, ending in '/'
  sample: boolean;
  index: SiteIndex;
}

/** Resolve a path given relative to the JSON file that names it. */
export function resolveRel(jsonUrl: string, rel: string): string {
  const abs = new URL(jsonUrl, 'http://x/');
  const out = new URL(rel, abs);
  // Keep relative-looking output when the input was relative (works under any sub-path).
  return jsonUrl.startsWith('http') ? out.href : out.pathname.replace(/^\//, '');
}

async function tryJson<T>(fetcher: Fetcher, url: string): Promise<T | null> {
  try {
    const r = await fetcher(url);
    if (!r.ok) return null;
    const text = await r.text();
    // Dev servers answer missing files with index.html, so check before parsing.
    if (!text.trimStart().startsWith('{')) return null;
    // Python's json writes NaN / Infinity, which JSON.parse rejects; treat them as null
    return JSON.parse(text.replace(/(?<=[:\[,]\s*)-?(NaN|Infinity)(?=\s*[,\]}])/g, 'null')) as T;
  } catch {
    return null;
  }
}

export async function loadIndex(fetcher: Fetcher = fetch, candidates = ['data/', 'data-sample/']): Promise<DataSource> {
  for (const base of candidates) {
    const index = await tryJson<SiteIndex>(fetcher, base + 'index.json');
    if (index && typeof index.schema === 'string' && index.schema.startsWith('rewind-site')) {
      return { base, sample: !!index.sample || base.includes('sample'), index };
    }
  }
  throw new Error('No site data was found in ' + candidates.join(' or '));
}

export async function getJson<T>(url: string, fetcher: Fetcher = fetch): Promise<T> {
  const v = await tryJson<T>(fetcher, url);
  if (!v) throw new Error('Could not load ' + url);
  return v;
}

export interface OrbitColumns {
  count: number;
  epoch_mjd: number;
  fields: string[];
  data: Float32Array; // row-major, count * fields.length
  col: (name: string) => number; // field index or -1
  slugs: Record<string, number>; // optional map slug -> row, for objects in Rewind
}

/** Load orbits.bin (fast path) or orbits.json. */
export async function loadOrbits(base: string, fetcher: Fetcher = fetch): Promise<OrbitColumns> {
  const meta = await tryJson<{ rows: number; fields: string[]; epoch_mjd?: number; slugs?: Record<string, number> }>(fetcher, base + 'orbits.bin.json');
  if (meta) {
    try {
      const r = await fetcher(base + 'orbits.bin');
      if (r.ok) {
        const buf = await r.arrayBuffer();
        const data = new Float32Array(buf);
        if (data.length === meta.rows * meta.fields.length) {
          let epoch = meta.epoch_mjd;
          if (epoch === undefined) {
            const js = await tryJson<{ epoch_mjd: number }>(fetcher, base + 'orbits.json');
            epoch = js?.epoch_mjd ?? 61200;
          }
          return columns(meta.rows, epoch, meta.fields, data, meta.slugs);
        }
      }
    } catch {
      /* fall through to JSON */
    }
  }
  const js = await getJson<{ epoch_mjd: number; fields: string[]; rows: number[][]; slugs?: Record<string, number> }>(base + 'orbits.json', fetcher);
  const F = js.fields.length;
  const data = new Float32Array(js.rows.length * F);
  js.rows.forEach((row, r) => data.set(row.slice(0, F), r * F));
  return columns(js.rows.length, js.epoch_mjd, js.fields, data, js.slugs);
}

function columns(count: number, epoch_mjd: number, fields: string[], data: Float32Array, slugs: Record<string, number> = {}): OrbitColumns {
  return { count, epoch_mjd, fields, data, col: (n) => fields.indexOf(n), slugs };
}

/** Elements of one orbits row (used when an object page has no orbit of its own). */
export function rowElements(orb: OrbitColumns, row: number) {
  const F = orb.fields.length;
  const g = (n: string) => orb.data[row * F + orb.col(n)];
  return { a: g('a'), e: g('e'), i: g('i'), node: g('node'), peri: g('peri'), M: g('M'), epoch_mjd: orb.epoch_mjd };
}

/** Accepts both our flat rows (a, a_rate, ...) and the engine's JPL-style rows (I, long_peri, long_node, rates{}). */
export function normalizePlanet(r: Record<string, any>): PlanetRow {
  const rate = (k: string, alt: string) => r[k + '_rate'] ?? r.rates?.[k] ?? r.rates?.[alt] ?? 0;
  return {
    name: r.name,
    a: r.a, a_rate: rate('a', 'a'),
    e: r.e, e_rate: rate('e', 'e'),
    i: r.i ?? r.I, i_rate: r.i_rate ?? r.rates?.I ?? r.rates?.i ?? 0,
    L: r.L, L_rate: rate('L', 'L'),
    varpi: r.varpi ?? r.long_peri, varpi_rate: r.varpi_rate ?? r.rates?.long_peri ?? r.rates?.varpi ?? 0,
    node: r.node ?? r.long_node, node_rate: r.node_rate ?? r.rates?.long_node ?? r.rates?.node ?? 0,
  };
}

export async function loadPlanets(base: string, fetcher: Fetcher = fetch): Promise<PlanetsFile> {
  const p = await tryJson<PlanetsFile>(fetcher, base + 'planets.json');
  if (p?.planets?.length) {
    const planets = p.planets.map((r) => normalizePlanet(r as unknown as Record<string, unknown>));
    if (planets.every((x) => Number.isFinite(x.a) && Number.isFinite(x.L) && Number.isFinite(x.varpi) && Number.isFinite(x.node))) return { ...p, planets };
  }
  // Real data may not have planets yet; the sample copy is always there.
  return getJson<PlanetsFile>('data-sample/planets.json', fetcher);
}
