// Pure helpers for the For scientists page: the results table (filter, sort, CSV),
// the orbit-impact numbers and the split of DATA-CONTRACT.md into sections.
import type { IndexObject, Verdict } from '../../lib/types';
import { isKnown, rankObjects } from '../../lib/rank';

/** An index.json row, with the fields the engine adds for finds checked against the first known observation. */
export type Row = IndexObject & {
  first_known_obs_iso?: string | null;
  days_before_first_known_obs?: number | null;
  arc_days_before?: number | null;
  arc_days_after?: number | null;
  claim?: string | null;
};

export type SortKey = 'name' | 'kind' | 'verdict' | 'snr' | 'frames' | 'discovered' | 'lead';
export interface Sort { key: SortKey; dir: 1 | -1 }

const key = (s: string) => s.toLowerCase().replace(/[^a-z0-9]/g, '');

/** A results-table tab: a verdict, all rows, or the known objects run as controls. */
export type Tab = Verdict | 'ALL' | 'KNOWN';

/** FOUND means a new find, the same count as the rest of the site; known controls have their own tab. */
export function inTab(o: Row, tab: Tab): boolean {
  if (tab === 'ALL') return true;
  if (tab === 'KNOWN') return o.verdict === 'FOUND' && isKnown(o);
  if (tab === 'FOUND') return o.verdict === 'FOUND' && !isKnown(o);
  return o.verdict === tab;
}

/** A new find whose SPHEREx photos are not earlier than the first known observation. */
export function notEarlier(o: Row): boolean {
  return o.verdict === 'FOUND' && !isKnown(o) && !((o.days_before_first_known_obs ?? 0) > 0);
}

/** Rows of one tab whose name or slug contains the search text; spaces and "/" do not matter. */
export function filterRows(rows: Row[], tab: Tab, q: string): Row[] {
  const k = key(q);
  return rows.filter((o) => inTab(o, tab) && (!k || key(o.name).includes(k) || o.slug.includes(k)));
}

/** "verdict" is the site's own ranking (finds first, stronger signal first). Empty values always go last. */
export function sortRows(rows: Row[], s: Sort): Row[] {
  if (s.key === 'verdict') {
    const ranked = rankObjects(rows);
    return s.dir === 1 ? ranked : ranked.reverse();
  }
  const val = (o: Row): number | string | null =>
    s.key === 'name' ? o.name
    : s.key === 'kind' ? o.kind
    : s.key === 'snr' ? o.best_snr ?? null
    : s.key === 'frames' ? o.n_frames ?? null
    : s.key === 'discovered' ? o.discovered?.mjd ?? null
    : o.days_before_first_known_obs ?? null;
  const byName = (a: Row, b: Row) => a.name.localeCompare(b.name, 'en', { numeric: true });
  return [...rows].sort((a, b) => {
    const x = val(a);
    const y = val(b);
    if (x === null || y === null) return Number(x === null) - Number(y === null) || byName(a, b);
    const d = typeof x === 'string' ? x.localeCompare(y as string, 'en', { numeric: true }) : x - (y as number);
    return d * s.dir || byName(a, b);
  });
}

/** How a find compares with the first known observation anywhere. Empty for everything that is not FOUND. */
export function lead(o: Row): string {
  if (o.verdict !== 'FOUND') return '';
  if (isKnown(o)) return 'known object';
  const d = o.days_before_first_known_obs;
  if (d != null && d > 0) return `${d} d earlier`;
  return o.first_known_obs_iso ? 'not earlier' : '';
}

const CSV_HEAD = ['name', 'slug', 'kind', 'verdict', 'best_snr', 'n_frames', 'discovered_iso', 'discovered_by', 'first_known_obs_iso', 'days_before_first_known_obs', 'claim', 'verdict_text'];

export function toCsv(rows: Row[]): string {
  const cell = (v: unknown) => {
    const s = String(v ?? '');
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  const line = (o: Row) => [o.name, o.slug, o.kind, o.verdict, o.best_snr, o.n_frames, o.discovered?.iso, o.discovered?.by, o.first_known_obs_iso, o.days_before_first_known_obs, o.claim, o.verdict_text];
  return [CSV_HEAD, ...rows.map(line)].map((r) => r.map(cell).join(',')).join('\n') + '\n';
}

/** DATA-CONTRACT.md cut at its "## " headings. The text before the first heading is dropped. */
export function splitContract(md: string): { title: string; body: string }[] {
  return md.split(/^## /m).slice(1).map((s) => {
    const i = s.indexOf('\n');
    return i < 0 ? { title: s.trim(), body: '' } : { title: s.slice(0, i).trim(), body: s.slice(i + 1).trim() };
  });
}

/** Kilometres for a table cell: full digits below a million, "2.72M" style above. */
export function km(n: number): string {
  if (n < 1e6) return Math.round(n).toLocaleString('en-US');
  const m = n / 1e6;
  return m.toFixed(m >= 100 ? 0 : m >= 10 ? 1 : 2) + 'M';
}

/** Width in percent of an S/N bar on a square-root scale, so that 5 and 110 both stay readable.
 *  Negative and missing values give 0; the maximum fills the bar. */
export function snrBar(snr: number | null | undefined, max: number): number {
  if (snr == null || !Number.isFinite(snr) || snr <= 0 || !(max > 0)) return 0;
  return Math.min(100, Math.sqrt(snr / max) * 100);
}

/** "4.3 MB", "159 KB", "812 B": a file size in binary units, as a browser shows it. */
export function bytes(n: number): string {
  if (n < 1024) return `${n} B`;
  const kb = n / 1024;
  if (kb < 1024) return `${kb < 10 ? kb.toFixed(1) : Math.round(kb)} KB`;
  const mb = kb / 1024;
  return `${mb < 10 ? mb.toFixed(1) : Math.round(mb)} MB`;
}

/** "0 to 7%": the spread of today's improvement over a set of before/after factors. */
export function gainRange(factors: number[]): string {
  const pct = factors.map((f) => Math.round((f - 1) * 100));
  const lo = Math.min(...pct);
  const hi = Math.max(...pct);
  return lo === hi ? `${lo}%` : `${lo} to ${hi}%`;
}
