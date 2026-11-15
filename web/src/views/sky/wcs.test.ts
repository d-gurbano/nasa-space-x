import { describe, expect, it } from 'vitest';
import fixture from './fixtures/wcs.json';
import { findImageHdu, makeWcs, offsetToSky, parseHeader, skyToOffset } from './wcs';

describe('TAN + SIP world to pixel, against astropy', () => {
  for (const f of fixture.frames) {
    it(`matches astropy within 0.001 px: ${f.key.split('/').pop()}`, () => {
      const parsed = parseHeader(f.header)!;
      expect(parsed.header['MJD-AVG']).toBeCloseTo(f.mjd_avg, 6);
      expect(parsed.header.DETECTOR).toBe(f.detector);
      const wcs = makeWcs(parsed.header);
      for (const c of f.cases) {
        const [x, y] = wcs.world2pix(c.ra, c.dec);
        expect(Math.abs(x - c.x)).toBeLessThan(1e-3);
        expect(Math.abs(y - c.y)).toBeLessThan(1e-3);
      }
    });
  }

  it('finds the IMAGE extension and its data offset in raw bytes', () => {
    const f = fixture.frames[0];
    const pad = (s: string) => s.padEnd(Math.ceil(s.length / 2880) * 2880, ' ');
    const primary = pad(['SIMPLE  =                    T', 'BITPIX  =                    8', 'NAXIS   =                    0', 'END'].map((c) => c.padEnd(80, ' ')).join(''));
    const bytes = new TextEncoder().encode(primary + f.header);
    const hdu = findImageHdu(bytes)!;
    expect(hdu.dataOffset).toBe(f.data_offset);
    expect([hdu.nx, hdu.ny]).toEqual([2040, 2040]);
    // a header cut before END asks for more bytes
    expect(findImageHdu(bytes.slice(0, 8000))).toBeNull();
  });

  it('offsetToSky and skyToOffset are inverse, and east is +RA', () => {
    const [ra, dec] = offsetToSky(133.7951, -7.2451, 60, -45);
    expect(ra).toBeGreaterThan(133.7951);
    expect(dec).toBeLessThan(-7.2451);
    const [e, n] = skyToOffset(133.7951, -7.2451, ra, dec);
    expect(e).toBeCloseTo(60, 6);
    expect(n).toBeCloseTo(-45, 6);
    const [ra2] = offsetToSky(0.001, 80, -120, 0);
    expect(ra2).toBeGreaterThan(359);
  });
});
