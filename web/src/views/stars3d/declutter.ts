// Label collision handling for the star map: the most important label is placed first, beside
// its star on the right. A label that would cover one already placed, or another star, tries
// the left side, then a row up or down pushed a little further out (the scene then draws a
// short leader line back to its star), and is hidden when no nearby spot is free.

export interface LabelBox {
  x: number; // the star on screen, px
  y: number;
  w: number;
  h: number;
  rank: number; // higher is placed first
  /** Only its natural spot, right of the point: hidden rather than moved (ring distance tags). */
  fixed?: boolean;
}

/** Where a label goes: its left edge and vertical centre, relative to its star. */
export interface Spot { dx: number; dy: number; lead: boolean }

/** Gap between a star and its label, px. */
export const PAD = 12;
const SPOTS: [side: 1 | -1, row: number][] = [[1, 0], [-1, 0], [1, -1], [1, 1], [-1, -1], [-1, 1], [1, -2], [1, 2], [-1, -2], [-1, 2]];

/** For each box, its spot, or null when it should be hidden. Same order as the input. `dots` are star points labels must not cover. */
export function declutter(boxes: LabelBox[], dots: [number, number][] = [], gap = 2): (Spot | null)[] {
  const out: (Spot | null)[] = boxes.map(() => null);
  const placed: [number, number, number, number][] = dots.map(([x, y]) => [x - 4, y - 4, x + 4, y + 4]);
  const order = boxes.map((_, i) => i).sort((a, b) => boxes[b].rank - boxes[a].rank);
  for (const i of order) {
    const b = boxes[i];
    for (const [side, row] of b.fixed ? SPOTS.slice(0, 1) : SPOTS) {
      const off = PAD + Math.abs(row) * 10, dx = side > 0 ? off : -off - b.w, dy = row * (b.h + gap);
      const l = b.x + dx, t = b.y + dy - b.h / 2, r = l + b.w, bt = t + b.h;
      if (placed.some(([pl, pt, pr, pb]) => l < pr + gap && r + gap > pl && t < pb + gap && bt + gap > pt)) continue;
      placed.push([l, t, r, bt]);
      out[i] = { dx, dy, lead: row !== 0 };
      break;
    }
  }
  return out;
}
