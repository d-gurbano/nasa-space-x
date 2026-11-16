// The nine detection checks and four verdicts, defined once. Every page that counts or names a
// check (object panel, blind test, For scientists) reads this list, so the counts always agree.
// Keys and pass rules follow docs/DATA-CONTRACT.md and engine/rewind_engine/verdict.py.
import type { CheckKey } from './types';

export interface CheckDef {
  key: CheckKey;
  /** Short name, used as a list heading. */
  name: string;
  /** The pass rule, one sentence. */
  rule: string;
}

export const CHECKS: CheckDef[] = [
  { key: 'snr', name: 'Stack S/N ≥ 5', rule: 'The static-sky-subtracted stack has a null-calibrated S/N of 5 or more.' },
  { key: 'cleaned', name: 'Static sky subtracted', rule: 'A static-sky reference exists for at least 10 images.' },
  { key: 'nulls', name: 'Null-path test', rule: 'No offset (null) trajectory next to the predicted one (at least 12) is as strong.' },
  { key: 'time_shift', name: 'Time-shift test', rule: 'The S/N peaks at zero time shift and falls off on both sides.' },
  { key: 'days', name: 'Multi-night', rule: 'At least 2 nights are positive on their own (S/N ≥ 2).' },
  { key: 'detectable', name: 'Injection–recovery', rule: 'Synthetic sources planted at the predicted brightness are recovered at least 50% of the time.' },
  { key: 'sign_test', name: 'Sign test', rule: 'More single images are positive on the real path than on every null path, by 3σ or more (waived when single images already show the object).' },
  { key: 'not_one_day', name: 'Not one night', rule: 'The S/N stays at 3 or more with the best night removed.' },
  { key: 'orbit', name: 'Orbit consistency', rule: 'An orbit refit including the new positions stays good (not required for known objects).' },
];

export const N_CHECKS = CHECKS.length;

export const VERDICT_DEF: Record<string, string> = {
  FOUND: 'All nine checks pass. For a known control object this means "SPHEREx recorded it", not a precovery.',
  HINT: 'A signal is present (null-calibrated S/N ≥ 3, or ≥ 2 with two core checks passed) but not every check passes. Never upgraded.',
  TOO_FAINT: 'Nothing significant at the predicted position: injection–recovery puts the object below the local limit, or it was fainter than predicted.',
  NO_PHOTOS: 'SPHEREx did not image the predicted position during the searched window.',
};

/** Pass/fail per check, in the canonical order; checks missing from the file are left out. */
export function checkResults(passed: Partial<Record<CheckKey, boolean>> | undefined | null): { def: CheckDef; ok: boolean }[] {
  if (!passed) return [];
  return CHECKS.filter((d) => typeof passed[d.key] === 'boolean').map((def) => ({ def, ok: !!passed[def.key] }));
}
