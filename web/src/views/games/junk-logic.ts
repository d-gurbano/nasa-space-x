// Real or junk?: the pure parts (the answer categories, round building, the AI line), kept apart so they can be tested.

export type Cat = 'asteroid' | 'trail' | 'cosmic' | 'ghost' | 'detector';

export interface JunkStamp {
  id: string;
  img: string;
  cat: Cat;
  /** the true label, as written in the answer key */
  label: string;
  obsid: string;
  det: string;
  snr?: number;
  /** the real-or-fake CNN's score for this exact stamp, or null if it was not run on it */
  ai: number | null;
}

export interface JunkData {
  ai_accuracy: number;
  ai_test_n: number;
  source: string;
  pool: JunkStamp[];
}

export const CATS: { id: Cat; name: string; key: string; say: string }[] = [
  { id: 'asteroid', name: 'Asteroid', key: '1', say: 'A real asteroid looks like a star in one image: a small round dot the size of the telescope’s blur. Only its motion between images gives it away.' },
  { id: 'trail', name: 'Satellite trail', key: '2', say: 'A satellite crosses the whole view during one exposure, so it leaves a long straight line.' },
  { id: 'cosmic', name: 'Cosmic ray', key: '3', say: 'A charged particle hits the detector and lights up one pixel, a short dash or a splash. It is sharper than a star and gone in the next image.' },
  { id: 'ghost', name: 'Ghost or halo', key: '4', say: 'Light from a bright star bounces inside the telescope and lands as a soft ring or blob away from the star.' },
  { id: 'detector', name: 'Detector effect', key: '5', say: 'The detector itself made this: an after-image of an earlier bright star (persistence), charge spilling from a saturated star (bloom), or an electronic echo (crosstalk).' },
];
export const CAT_NAME = Object.fromEntries(CATS.map((c) => [c.id, c.name])) as Record<Cat, string>;

export function shuffle<T>(a: T[], rand = Math.random): T[] {
  const b = [...a];
  for (let i = b.length - 1; i > 0; i--) {
    const j = Math.floor(rand() * (i + 1));
    [b[i], b[j]] = [b[j], b[i]];
  }
  return b;
}

/** n rounds: a few asteroids, at least one of every artifact kind, the rest at random, in random order. */
export function buildRounds(pool: JunkStamp[], n = 10, asteroids = 3, rand = Math.random): JunkStamp[] {
  const by = (c: Cat) => shuffle(pool.filter((s) => s.cat === c), rand);
  const pick: JunkStamp[] = by('asteroid').slice(0, asteroids);
  for (const c of CATS) if (c.id !== 'asteroid') pick.push(...by(c.id).slice(0, 1));
  const rest = shuffle(pool.filter((s) => s.cat !== 'asteroid' && !pick.includes(s)), rand);
  while (pick.length < n && rest.length) pick.push(rest.pop()!);
  return shuffle(pick.slice(0, n), rand);
}

/** What our real-or-fake AI said about this stamp, or that it never saw it. Never made up. */
export function aiLine(s: JunkStamp): string {
  if (s.ai == null) return 'Our AI was not run on this image.';
  const real = s.ai >= 0.5;
  return `Our real-or-fake AI scored this exact image ${s.ai.toFixed(2)} on a scale from 0 (junk) to 1 (real), so it called it ${real ? 'a real object' : 'junk'}. ${real === (s.cat === 'asteroid') ? 'That was right.' : 'That was wrong.'}`;
}

export const pct = (right: number, n: number) => (n ? Math.round((100 * right) / n) : 0);
