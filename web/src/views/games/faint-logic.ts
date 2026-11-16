// Too faint?: pure logic. Picks a mix of real searched objects and scores a bet.

export type Verdict = 'FOUND' | 'HINT' | 'TOO_FAINT';
export type Bet = 'show' | 'faint';
export interface FaintObj {
  slug: string;
  name: string;
  kind: string;
  verdict: Verdict;
  pred_ab: number;
  n_frames: number;
  snr: number;
  limit_ab: number | null;
}

export const ROUNDS = 10;
const MIX: [Verdict, number][] = [['FOUND', 3], ['HINT', 3], ['TOO_FAINT', 4]];

function shuffle<T>(a: T[], rand: () => number): T[] {
  const b = [...a];
  for (let i = b.length - 1; i > 0; i--) {
    const j = Math.floor(rand() * (i + 1));
    [b[i], b[j]] = [b[j], b[i]];
  }
  return b;
}

/** 3 found, 3 hints and 4 too faint, in a random order; topped up from the rest if a group is short. */
export function pickRounds(all: FaintObj[], rand: () => number = Math.random): FaintObj[] {
  const out: FaintObj[] = [];
  for (const [v, n] of MIX) out.push(...shuffle(all.filter((o) => o.verdict === v), rand).slice(0, n));
  const rest = shuffle(all.filter((o) => !out.includes(o)), rand);
  while (out.length < ROUNDS && rest.length) out.push(rest.pop()!);
  return shuffle(out, rand);
}

/** 10 for the right bet. A hint is a weak signal below our detection bar, so either bet earns 5. */
export function score(bet: Bet, v: Verdict): number {
  if (v === 'HINT') return 5;
  return (v === 'FOUND') === (bet === 'show') ? 10 : 0;
}

/** Stacking N images lowers the noise by about √N, so the S/N of one image is about S/N(stack) / √N. */
export const perImage = (snr: number, n: number) => snr / Math.sqrt(Math.max(1, n));
