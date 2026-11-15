import { describe, expect, it } from 'vitest';
import { fixPlural, plural } from '../src/ui/dom';

describe('grammar', () => {
  it('pluralizes', () => {
    expect(plural(1, 'day')).toBe('1 day');
    expect(plural(6, 'day')).toBe('6 days');
    expect(plural(0, 'photo')).toBe('0 photos');
  });
  it('fixes "1 days" in engine text without touching 11 or 2.1', () => {
    expect(fixPlural('SPHEREx photo, 1 days before discovery')).toBe('SPHEREx photo, 1 day before discovery');
    expect(fixPlural('11 days before')).toBe('11 days before');
    expect(fixPlural('2.1 days')).toBe('2.1 days');
    expect(fixPlural('1 days')).toBe('1 day');
  });
});
