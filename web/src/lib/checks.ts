// The nine detection checks and four verdicts, defined once. Every page that counts or names a
// check (object panel, blind test, Methods) reads this list, so the counts always agree.
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
  { key: 'nulls', name: 'Null-path test', rule: 'None of the offset (null) trajectories around the predicted one (at least 12) is as strong.' },
  { key: 'time_shift', name: 'Time-shift test', rule: 'The S/N peaks at zero time shift and falls off on both sides.' },
  { key: 'days', name: 'Multi-day', rule: 'At least 2 days are positive on their own (S/N ≥ 2).' },
  { key: 'detectable', name: 'Injection–recovery', rule: 'Synthetic sources planted at the predicted brightness are recovered at least 50% of the time.' },
  { key: 'sign_test', name: 'Sign test', rule: 'More single images are positive on the real path than on every null path, by 3σ or more (waived when single images already show the object).' },
  { key: 'not_one_day', name: 'Not one day', rule: 'The S/N stays at 3 or more with the best day removed.' },
  { key: 'orbit', name: 'Orbit consistency', rule: 'An orbit refit that includes the new positions is still a good fit (not required for known objects).' },
];

export const N_CHECKS = CHECKS.length;

export const VERDICT_DEF: Record<string, string> = {
  FOUND: 'All nine checks pass. For a control object this means SPHEREx recorded it. It is not a precovery.',
  HINT: 'A signal is present (null-calibrated S/N ≥ 3, or ≥ 2 with two core checks passed) but not every check passes. A HINT is never upgraded to FOUND.',
  TOO_FAINT: 'There is no significant signal at the predicted position. Either injection–recovery puts the object below the local limit, or it was fainter than predicted.',
  NO_PHOTOS: 'SPHEREx did not image the predicted position in the period we searched.',
};

/** Pass/fail per check, in the canonical order; checks missing from the file are left out. */
export function checkResults(passed: Partial<Record<CheckKey, boolean>> | undefined | null): { def: CheckDef; ok: boolean }[] {
  if (!passed) return [];
  return CHECKS.filter((d) => typeof passed[d.key] === 'boolean').map((def) => ({ def, ok: !!passed[def.key] }));
}
