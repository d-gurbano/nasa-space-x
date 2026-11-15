import { describe, expect, it } from 'vitest';
import { oneSentence } from '../src/ui/panel-text';

describe('oneSentence', () => {
  it('keeps the claim and drops the numbers after the colon', () => {
    const t = 'Rewind found 2025 YH5 in SPHEREx photos taken 1-18 days before the first known observation (2025-12-20): S/N 34.4 in the sky-cleaned stack of 81 photos (no single photo shows it; only the stack does), on 8 separate days.';
    expect(oneSentence(t)).toBe('Rewind found 2025 YH5 in SPHEREx photos taken 1-18 days before the first known observation.');
  });
  it('keeps "a hint, not a find"', () => {
    const t = 'There is a signal where C/2026 Q1 should be (S/N 6.1), but not every test passes (too few photos are positive compared with fake paths; the signal rests on a single day), so this is a hint, not a find. 55% of the photos are positive.';
    expect(oneSentence(t)).toBe('There is a signal where C/2026 Q1 should be, but not every test passes, so this is a hint, not a find.');
  });
  it('keeps the "not earlier" caveat when the claim says so', () => {
    const t = 'SPHEREx saw C/2025 W2: S/N 11.4 in the stack. These photos are not earlier than the first known observation.';
    expect(oneSentence(t, 'seen in SPHEREx (not earlier than known observations)')).toBe('SPHEREx saw C/2025 W2. These photos are not earlier than the first known observation.');
  });
  it('handles empty text', () => {
    expect(oneSentence(null)).toBe('');
  });
});
