import { describe, expect, it } from 'vitest';
import { declutter, PAD } from './declutter';

describe('declutter', () => {
  it('keeps labels that do not touch beside their star, on the right', () => {
    expect(declutter([{ x: 0, y: 0, w: 50, h: 20, rank: 1 }, { x: 200, y: 0, w: 50, h: 20, rank: 0 }])).toEqual([
      { dx: PAD, dy: 0, lead: false },
      { dx: PAD, dy: 0, lead: false },
    ]);
  });

  it('moves the lower-ranked of two overlapping labels to the left side first', () => {
    const out = declutter([{ x: 0, y: 100, w: 60, h: 20, rank: 0 }, { x: 10, y: 102, w: 60, h: 20, rank: 5 }]);
    expect(out[1]).toEqual({ dx: PAD, dy: 0, lead: false });
    expect(out[0]!.dx).toBe(-PAD - 60);
  });

  it('does not cover another star, and draws a leader when it moves a row', () => {
    // a star just right of the first, and one just left: both sides of the natural row are blocked
    const out = declutter([{ x: 100, y: 100, w: 40, h: 20, rank: 0 }], [[100, 100], [130, 100], [70, 100]]);
    expect(out[0]!.dy).not.toBe(0);
    expect(out[0]!.lead).toBe(true);
  });

  it('hides a fixed label instead of moving it', () => {
    const out = declutter([{ x: 0, y: 100, w: 60, h: 20, rank: 9 }, { x: 0, y: 100, w: 60, h: 20, rank: 0, fixed: true }]);
    expect(out[1]).toBeNull();
  });

  it('hides a label when every nearby spot is taken', () => {
    const stack = [-2, -1, 0, 1, 2].map((r, i) => ({ x: -60, y: 100 + r * 22, w: 200, h: 20, rank: 10 + i, fixed: true }));
    const out = declutter([...stack, { x: 0, y: 100, w: 60, h: 20, rank: 0 }]);
    expect(out[5]).toBeNull();
  });
});
