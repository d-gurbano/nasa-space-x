// Pure logic for the "Does it work?" page: what each test case counts as, the totals,
// and one plain sentence per case. No DOM here, so it can be tested.

export interface BenchCase {
  name: string;
  /** neo, comet or mba. */
  type?: string;
  hidden_until_iso?: string;
  truth: string;
  rewind_verdict: string;
  snr?: number | null;
  /** The same measurement at the true (JPL Horizons) position. */
  oracle_snr?: number | null;
  pos_err_arcsec?: number | null;
  V_pred?: number | null;
  V_true_median?: number | null;
  median_blind_minus_true_arcsec?: number | null;
  checks?: Record<string, boolean>;
  note?: string;
}

export interface BenchSummary {
  plain?: string;
  method?: string;
  label?: string;
  unusable_note?: string;
  pos_err_arcsec?: { n?: number; median?: number; p90?: number };
}

/** One brightness bin of the completeness curve (V magnitude from v_min to v_max). */
export interface CurveBin { v_min?: number; v_max?: number; n?: number; found?: number; found_or_hint?: number; seen_by_oracle?: number }

/** benchmark.json. v2 adds types, decoys, the curve and keeps the first test under v1; every field may be missing. */
export interface Bench {
  sample?: boolean;
  cases?: BenchCase[];
  decoys?: BenchCase[];
  completeness_curve?: CurveBin[];
  summary?: BenchSummary;
  v1?: { cases?: BenchCase[]; summary?: BenchSummary };
}

/** found / hint / missed are for objects SPHEREx really saw; quiet / false for the ones it did not. */
export type Outcome = 'found' | 'hint' | 'missed' | 'quiet' | 'false';

export function outcome(c: BenchCase): Outcome {
  const said = c.rewind_verdict === 'FOUND';
  if (c.truth !== 'seen') return said ? 'false' : 'quiet';
  return said ? 'found' : c.rewind_verdict === 'HINT' ? 'hint' : 'missed';
}

/** A case that could really be tested: the truth is known. (v2 lists cases with no usable test as "unknown".) */
export const usable = (c: BenchCase) => c.truth === 'seen' || c.truth === 'not seen';

/** Totals counted from the cases. (summary.missed in the v1 file also counts the hints.) */
export function tally(cases: BenchCase[]) {
  const n = { found: 0, hint: 0, missed: 0, quiet: 0, false: 0 };
  for (const c of cases) n[outcome(c)]++;
  return { ...n, total: cases.length, seen: n.found + n.hint + n.missed };
}

/** The one false-alarm sentence used on every page: "0 false alarms in 23 real cases and 22 empty-sky decoys". */
export function alarmLine(t: ReturnType<typeof tally>, decoys: ReturnType<typeof decoyTally>): string {
  const n = t.false + decoys.false;
  return `${n} false ${n === 1 ? 'alarm' : 'alarms'} in ${t.total} real ${t.total === 1 ? 'case' : 'cases'}${decoys.ran ? ` and ${decoys.ran} empty-sky ${decoys.ran === 1 ? 'decoy' : 'decoys'}` : ''}`;
}

/** The engine's method note, in plain words where it uses shorthand. */
export function methodText(s: string): string {
  return s.replace('missed excludes hints. Frames listed with MOST (full orbit).', "'Missed' doesn't count hints. Frame lists come from the MOST service using the full orbit.");
}

/** Empty-sky decoys: how many ran, and how many Rewind wrongly called a find. */
export function decoyTally(decoys: BenchCase[]) {
  const ran = decoys.filter((d) => d.rewind_verdict && d.rewind_verdict !== 'ERROR');
  return { ran: ran.length, false: ran.filter((d) => d.rewind_verdict === 'FOUND').length };
}

const mag = (c: BenchCase) => c.V_pred ?? c.V_true_median ?? 99;
const ORDER: Outcome[] = ['found', 'hint', 'missed', 'quiet', 'false'];

/** Found first, then hints, missed and not visible; brightest first inside each group. */
export function byOutcome(cases: BenchCase[]): BenchCase[] {
  return [...cases].sort((a, b) => ORDER.indexOf(outcome(a)) - ORDER.indexOf(outcome(b)) || mag(a) - mag(b));
}

/** Results per object type, in the order the types first appear. Cases without a type are left out. */
export function byType(cases: BenchCase[]) {
  const out = new Map<string, ReturnType<typeof tally>>();
  for (const type of new Set(cases.map((c) => c.type).filter((t): t is string => !!t))) out.set(type, tally(cases.filter((c) => c.type === type)));
  return out;
}

/** How far Rewind's position was from the true one, for every case that has a measurement, smallest first. */
export function posErrors(cases: BenchCase[]): number[] {
  return cases.map((c) => c.pos_err_arcsec).filter((v): v is number => typeof v === 'number' && Number.isFinite(v)).sort((a, b) => a - b);
}

export function median(sorted: number[]): number | null {
  if (!sorted.length) return null;
  const m = sorted.length >> 1;
  return sorted.length % 2 ? sorted[m] : (sorted[m - 1] + sorted[m]) / 2;
}

/** The curve as bar heights: share found and share hint in each brightness bin, out of the objects
 *  SPHEREx could see (seen_by_oracle when given, as in the headline). Empty bins are dropped. */
export function curveBars(curve: CurveBin[]) {
  const seen = (b: CurveBin) => b.seen_by_oracle ?? b.n ?? 0;
  return curve.filter((b) => seen(b) > 0).map((b) => {
    const n = seen(b), found = Math.min(n, b.found ?? 0), hint = Math.max(0, Math.min(n, b.found_or_hint ?? found) - found);
    return { label: !b.v_min ? `under ${b.v_max}` : `${b.v_min} to ${b.v_max}`, n, found, hint };
  });
}

const VERDICT: Record<string, string> = { FOUND: 'Found', HINT: 'Hint', TOO_FAINT: 'Too faint', NO_PHOTOS: 'No photos' };
export const said = (c: BenchCase) => VERDICT[c.rewind_verdict] ?? c.rewind_verdict;

// Why a check failed, in plain words. The check rules are in the engine's docs/RESULTS.md.
const FAILED: Record<string, string> = {
  snr: 'the signal is below the line of S/N 5',
  cleaned: 'the fixed sky could not be cleaned well enough',
  nulls: 'a fake path nearby gave a signal just as strong',
  time_shift: 'the signal is not strongest at the right time',
  days: 'it shows on fewer than 2 separate days',
  detectable: 'at this brightness it should be too faint to see here',
  sign_test: 'too few single photos show it',
  not_one_day: 'the signal depends on one day alone',
  orbit: 'the new positions do not fit the orbit',
};

export function failedChecks(c: BenchCase): string[] {
  return Object.entries(c.checks ?? {}).filter(([k, ok]) => !ok && FAILED[k]).map(([k]) => FAILED[k]);
}

const sn = (v: number | null | undefined, tail: string) => (typeof v === 'number' ? ` (S/N ${v.toFixed(1)}${tail})` : '');

/** One plain sentence about a case. It never says more than the verdict in the file. */
export function explain(c: BenchCase): string {
  switch (outcome(c)) {
    case 'found':
      return `Rewind found it blind${c.pos_err_arcsec ? `, ${c.pos_err_arcsec.toFixed(1)} arcsec from its true position` : ''}.`;
    case 'hint': {
      const why = failedChecks(c);
      const s = why.length ? why.join(', and ') : 'not every check passed';
      return `${s[0].toUpperCase()}${s.slice(1)}.`;
    }
    case 'missed':
      return `SPHEREx did record it${sn(c.oracle_snr, ' at the true position')}, but on Rewind's rough early path the signal was too weak. Rewind said ${said(c)} and did not guess.`;
    case 'quiet':
      return `SPHEREx did not see this one clearly${sn(c.oracle_snr, ' at the true position, under the line of 5')}. Rewind said ${said(c)}, not Found.`;
    case 'false':
      return 'Rewind said Found, but SPHEREx did not really see it. This is a false alarm.';
  }
}

/** The key of a case in the orbit table: "(2525) O'Steen" -> "2525", "217P/LINEAR" -> "217p", "C/2025 L2 (ATLAS)" -> "c2025l2". */
export function orbitKey(name: string): string {
  const num = /^\((\d+)\)/.exec(name);
  if (num) return num[1];
  const periodic = /^(\d+P)\//i.exec(name);
  if (periodic) return periodic[1].toLowerCase();
  return name.replace(/\(.*?\)/g, '').replace(/[\s/]/g, '').toLowerCase();
}

/** Bar length (0..1) for a signal-to-noise ratio on a log scale, so S/N 3 and S/N 120 both read. */
export const snrBar = (snr: number | null | undefined, max = 150) => (typeof snr === 'number' && snr > 0 ? Math.min(1, Math.log10(1 + snr) / Math.log10(1 + max)) : 0);
