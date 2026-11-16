// Date helpers. MJD is UTC days since 1858-11-17.

export const MJD_UNIX_EPOCH = 40587;
const MONTHS = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC'];

export function mjdFromDate(d: Date): number {
  return d.getTime() / 86400000 + MJD_UNIX_EPOCH;
}

export function dateFromMjd(mjd: number): Date {
  return new Date((mjd - MJD_UNIX_EPOCH) * 86400000);
}

/** "2026-09-16" (UTC) to MJD at 00:00 UTC. */
export function mjdFromIso(iso: string): number {
  return mjdFromDate(new Date(iso.length <= 10 ? iso + 'T00:00:00Z' : iso));
}

export function isoFromMjd(mjd: number): string {
  return dateFromMjd(mjd).toISOString().slice(0, 10);
}

/** Big readout: "NOV 15, 2026". */
export function readoutFromMjd(mjd: number): string {
  const d = dateFromMjd(mjd);
  return `${MONTHS[d.getUTCMonth()]} ${String(d.getUTCDate()).padStart(2, '0')}, ${d.getUTCFullYear()}`;
}

/** Plain: "16 Sep 2026". */
export function plainDate(isoOrMjd: string | number): string {
  const d = typeof isoOrMjd === 'number' ? dateFromMjd(isoOrMjd) : new Date(isoOrMjd.slice(0, 10) + 'T00:00:00Z');
  const m = MONTHS[d.getUTCMonth()];
  return `${d.getUTCDate()} ${m[0]}${m.slice(1).toLowerCase()} ${d.getUTCFullYear()}`;
}

/** How far a date is from today, in plain words: "Today", "19 days ago", "in 1.5 years". */
export function relativeText(days: number): string {
  const n = Math.abs(days);
  if (n < 0.5) return 'Today';
  const amount =
    n < 45 ? `${Math.round(n)} ${Math.round(n) === 1 ? 'day' : 'days'}` : n < 365 ? `${Math.round(n / 30.44)} months` : `${(n / 365.25).toFixed(1)} years`;
  return days < 0 ? `${amount} ago` : `in ${amount}`;
}

/** Linear map between a time range and a 0..1 slider fraction (clamped). */
export function fracFromMjd(mjd: number, start: number, end: number): number {
  return Math.min(1, Math.max(0, (mjd - start) / (end - start)));
}

export function mjdFromFrac(f: number, start: number, end: number): number {
  return start + Math.min(1, Math.max(0, f)) * (end - start);
}

/** The viewer's local calendar date, as the MJD of that date at 00:00 UTC (so the UTC readouts show it). */
export function todayMjd(now = new Date()): number {
  return Date.UTC(now.getFullYear(), now.getMonth(), now.getDate()) / 86400000 + MJD_UNIX_EPOCH;
}
