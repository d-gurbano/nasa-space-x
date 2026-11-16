// Name that rock: pure logic for Minor Planet Center provisional designations.
// An asteroid name like 2025 YH5 is year, half-month letter (Y = Dec 16-31), then the order in
// that half-month: second letter H = 8th, plus 25 for each cycle (5), so 8 + 5 x 25 = 133rd.
// Comets use a prefix (C/ long-period, P/ periodic) and a plain number for the order.

/** Half-month letters: A = Jan 1-15, B = Jan 16-31, ... Y = Dec 16-31. I is skipped, Z unused. */
export const HALF = 'ABCDEFGHJKLMNOPQRSTUVWXY';
/** Order letters: A = 1st ... Z = 25th, I skipped. */
export const ORDER = 'ABCDEFGHJKLMNOPQRSTUVWXYZ';
const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
const MON = MONTHS.map((m) => m.slice(0, 3));

export interface Parsed {
  prefix: string | null; // 'C', 'P', ... for comets
  year: number;
  half: number; // 0..23
  order: number; // 1-based order within the half-month
}

const RE = /^(?:([CPDXA])\/)?(\d{4}) ([A-HJ-Y])([A-HJ-Z])?(\d*)$/;

/** Parse a provisional designation. Returns null for numbered names (433 Eros) or 3I/ATLAS. */
export function parse(name: string): Parsed | null {
  const m = RE.exec(name.trim());
  if (!m) return null;
  const [, prefix, y, h, l, n] = m;
  const half = HALF.indexOf(h);
  if (prefix) {
    // comets: letter then a plain number, no second letter
    if (l || !n) return null;
    return { prefix, year: +y, half, order: +n };
  }
  if (!l) return null;
  return { prefix: null, year: +y, half, order: ORDER.indexOf(l) + 1 + 25 * (n ? +n : 0) };
}

/** Build a designation from its parts. */
export function build(p: Parsed): string {
  const h = HALF[p.half];
  if (p.prefix) return `${p.prefix}/${p.year} ${h}${p.order}`;
  const cycle = Math.floor((p.order - 1) / 25), l = ORDER[(p.order - 1) % 25];
  return `${p.year} ${h}${l}${cycle || ''}`;
}

/** The half-month index (0..23) of an ISO date like 2025-12-20. */
export function halfOf(iso: string): number {
  const [, mo, d] = iso.split('-').map(Number);
  return (mo - 1) * 2 + (d > 15 ? 1 : 0);
}

/** "December 16-31" for a half-month index. */
export function halfLabel(half: number, short = false): string {
  const mo = Math.floor(half / 2), names = short ? MON : MONTHS;
  const last = new Date(Date.UTC(2001, mo + 1, 0)).getUTCDate();
  return `${names[mo]} ${half % 2 ? `16-${last}` : '1-15'}`;
}

export const ordinal = (n: number) => {
  const s = n % 100 >= 11 && n % 100 <= 13 ? 'th' : (['th', 'st', 'nd', 'rd'][n % 10] ?? 'th');
  return `${n}${s}`;
};

/** How the order was worked out, in plain words. */
export function orderSum(name: string): string {
  const p = parse(name);
  if (!p) return '';
  if (p.prefix) return `the number ${p.order} means the ${ordinal(p.order)} comet in that half-month`;
  const m = RE.exec(name.trim())!, l = m[4], n = m[5] ? +m[5] : 0;
  const li = ORDER.indexOf(l) + 1;
  return n ? `${l} = ${li}, plus ${n} x 25 = ${li + 25 * n}` : `${l} = ${li}, no number, so ${li}`;
}

/** Normalise what the player typed: spaces, case, a missing space after the year. */
export function normalise(s: string): string {
  let t = s.toUpperCase().replace(/\s+/g, ' ').trim();
  t = t.replace(/^([CPDXA])\s*\/\s*/, '$1/');
  t = t.replace(/(\d{4})\s*([A-Z])/, '$1 $2');
  return t;
}

export interface NameObj {
  slug: string;
  name: string;
  kind: string;
  iso: string; // discovery date in our data (first known observation)
}

export type Round =
  | { mode: 'read'; obj: NameObj; p: Parsed; agrees: boolean }
  | { mode: 'build'; obj: NameObj; p: Parsed };

const shuffle = <T>(a: T[], rnd: () => number) => {
  const b = [...a];
  for (let i = b.length - 1; i > 0; i--) {
    const j = Math.floor(rnd() * (i + 1));
    [b[i], b[j]] = [b[j], b[i]];
  }
  return b;
};

/** Does the listed discovery date fall in the half-month (and year) the name says? */
export const agrees = (o: NameObj, p: Parsed) => +o.iso.slice(0, 4) === p.year && halfOf(o.iso) === p.half;

/**
 * Eight rounds, read and build alternating. 2025 YH5 opens if present. One read round is a
 * name whose listed date and letter disagree, when we have one, and each mode gets a comet.
 * Build rounds only use objects whose date and name agree, so the date given is a fair clue.
 */
export function pickRounds(objs: NameObj[], n = 8, rnd: () => number = Math.random): Round[] {
  const ok = objs.map((o) => ({ o, p: parse(o.name) })).filter((x): x is { o: NameObj; p: Parsed } => !!x.p);
  const pool = shuffle(ok, rnd);
  const used = new Set<string>();
  const take = (f: (x: { o: NameObj; p: Parsed }) => boolean) => {
    const x = pool.find((y) => !used.has(y.o.slug) && f(y));
    if (x) used.add(x.o.slug);
    return x;
  };
  const nRead = Math.ceil(n / 2), nBuild = n - nRead;
  const read = [take((x) => x.o.name === '2025 YH5'), take((x) => !agrees(x.o, x.p)), take((x) => !!x.p.prefix)];
  while (read.filter(Boolean).length < nRead) {
    const x = take((y) => !y.p.prefix);
    if (!x) break;
    read.push(x);
  }
  const build = [take((x) => !!x.p.prefix && agrees(x.o, x.p))];
  while (build.filter(Boolean).length < nBuild) {
    const x = take((y) => agrees(y.o, y.p) && !y.p.prefix);
    if (!x) break;
    build.push(x);
  }
  const r = read.filter((x) => !!x).slice(0, nRead);
  const first = r[0]?.o.name === '2025 YH5' ? [r[0]] : [];
  const reads = [...first, ...shuffle(r.slice(first.length), rnd)];
  const builds = shuffle(build.filter((x) => !!x), rnd).slice(0, nBuild);
  const out: Round[] = [];
  for (let i = 0; i < Math.max(reads.length, builds.length); i++) {
    if (reads[i]) out.push({ mode: 'read', obj: reads[i]!.o, p: reads[i]!.p, agrees: agrees(reads[i]!.o, reads[i]!.p) });
    if (builds[i]) out.push({ mode: 'build', obj: builds[i]!.o, p: builds[i]!.p });
  }
  return out;
}

/** Read round: 5 points for the half-month, 5 for the order. */
export function scoreRead(p: Parsed, half: number, order: number) {
  const h = half === p.half, o = order === p.order;
  return { half: h, order: o, points: (h ? 5 : 0) + (o ? 5 : 0) };
}

/** Build round: 5 points for year and half-month letter, 5 for the order part. */
export function scoreBuild(truth: string, typed: string) {
  const t = parse(truth)!, g = parse(normalise(typed));
  if (!g) return { valid: false, half: false, order: false, points: 0 };
  const half = g.year === t.year && g.half === t.half && g.prefix === t.prefix;
  const order = g.order === t.order;
  return { valid: true, half, order, points: (half ? 5 : 0) + (order ? 5 : 0) };
}
