import { describe, expect, it } from 'vitest';
import { mpcDate, mpcLine, packDesignation } from '../src/lib/mpc';

describe('MPC 80-column', () => {
  it('packs designations', () => {
    expect(packDesignation('2025 OZ')).toBe('     K25O00Z');
    expect(packDesignation('2026 RD39')).toBe('     K26R39D');
    expect(packDesignation('2007 TA418')).toBe('     K07Tf8A');
    expect(packDesignation('C/2026 S1')).toBe('    CK26S010');
    expect(packDesignation('433')).toBe('00433       ');
    expect(packDesignation('(99942) Apophis')).toBe('99942       ');
  });
  it('formats dates', () => {
    expect(mpcDate(61293.5)).toBe('2026 09 10.500000');
  });
  it('writes exactly 80 columns with fields in place', () => {
    const l = mpcLine({ name: '2025 OZ', mjd: 61293.25, ra: 273.892767, dec: 64.772567, mag: 19.4, band: 'V', code: 'XXX' });
    expect(l.length).toBe(80);
    expect(l.slice(15, 32)).toBe('2026 09 10.250000');
    expect(l.slice(32, 44)).toBe('18 15 34.264');
    expect(l.slice(44, 56)).toBe('+64 46 21.24');
    expect(l.slice(65, 71)).toBe(' 19.4V');
    expect(l.slice(77, 80)).toBe('XXX');
  });
});
