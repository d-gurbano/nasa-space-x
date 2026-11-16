// Game rounds: the rounds.json format, and a synthetic sample (made in the browser, always
// labelled "sample") for when the real rounds are not there yet.
import { rng, type Frames } from './stack';

export interface GameRound {
  id: string;
  title: string;
  object?: string;
  slug?: string;
  /** 'guided' = a reveal round: no frames to shift, only ready-made stacks (wrong, close, exact). */
  mode?: string;
  stacks?: { label: string; png: string; snr: number }[];
  truth: { angle_deg: number; rate_px_per_hr: number; x?: number; y?: number };
  frames?: { png: string; dt_hr: number }[];
  grid?: { angles: number[]; rates: number[]; png_pattern: string };
  explain?: string;
  difficulty?: string;
  snr_truth?: number;
  snr_wrong_p95?: number;
  px_arcsec?: number;
}

export interface GameData {
  rounds: GameRound[];
  sample?: boolean;
}

/** A round with its frames already in memory (only the synthetic sample has these). */
export interface SampleRound extends GameRound {
  data: Frames;
}

const N = 64; // native pixels across
const UP = 4; // nearest-neighbour upscale, like the real rounds

function gauss(r: () => number): number {
  return Math.sqrt(-2 * Math.log(r() || 1e-12)) * Math.cos(2 * Math.PI * r());
}

/** One synthetic round: noise, a few badly subtracted stars, and a dot moving in a straight line. */
export function synthRound(seed: number, peak: number, nFrames: number, hours: number, travel: number): SampleRound {
  const r = rng(seed);
  const angle = Math.round(r() * 360);
  const dt = [0, ...Array.from({ length: nFrames - 1 }, () => r() * hours)].sort((a, b) => a - b);
  dt[dt.length - 1] = hours;
  const rate = (travel * UP) / hours; // output pixels per hour
  const a = (angle * Math.PI) / 180;
  const v = [Math.sin(a) * rate, -Math.cos(a) * rate];
  const mid = [N * UP * (0.35 + 0.3 * r()), N * UP * (0.35 + 0.3 * r())];
  const stars = Array.from({ length: 7 }, () => [r() * N, r() * N, 2 + r() * 6]);
  const W = N * UP;
  const px = dt.map((t) => {
    const small = new Float32Array(N * N);
    const ox = (mid[0] + v[0] * (t - hours / 2)) / UP, oy = (mid[1] + v[1] * (t - hours / 2)) / UP;
    for (let y = 0; y < N; y++)
      for (let x = 0; x < N; x++) {
        let s = gauss(r);
        const d2 = (x + 0.5 - ox) ** 2 + (y + 0.5 - oy) ** 2;
        s += peak * Math.exp(-d2 / (2 * 0.8 * 0.8));
        small[y * N + x] = s;
      }
    for (const [sx, sy, f] of stars) {
      const k = Math.floor(sy) * N + Math.floor(sx);
      small[k] += f * 0.25 * gauss(r); // what is left of a star after the static sky is taken away
    }
    const big = new Float32Array(W * W);
    for (let y = 0; y < W; y++) for (let x = 0; x < W; x++) big[y * W + x] = small[Math.floor(y / UP) * N + Math.floor(x / UP)];
    return big;
  });
  return {
    id: 's' + seed,
    title: '',
    truth: { angle_deg: angle, rate_px_per_hr: rate },
    data: { w: W, h: W, px, dt },
  };
}

export function sampleRounds(): SampleRound[] {
  const plan: [string, string, number, number, number, number][] = [
    ['A bright asteroid', 'You can already see it in every image. Stacking along its path makes it brighter.', 5, 10, 6, 30],
    ['A dimmer one', 'This one is fainter. You can still make out its trail if you look closely.', 2.6, 12, 6, 34],
    ['Faint and fast', 'It moves a long way between images, so the speed matters as much as the direction.', 1.8, 14, 5, 46],
    ['Barely there', 'You can hardly see it in any one image. Only the right motion brings it out.', 1.2, 18, 8, 26],
    ['Lost in the noise', 'No single image shows it. Rewind searches for objects this faint.', 0.9, 22, 8, 30],
    ['A faint find', 'Like 2025 YH5, it cannot be seen in any single image but is clear in the right stack.', 0.75, 24, 9, 28],
  ];
  return plan.map(([title, explain, peak, n, hours, travel], i) => ({
    ...synthRound(101 + i * 17, peak, n, hours, travel),
    title,
    explain,
    difficulty: ['easy', 'easy', 'medium', 'medium', 'hard', 'hard'][i],
  }));
}
