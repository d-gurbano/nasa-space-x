// FITS header parsing and the TAN + SIP sky-to-pixel transform of a SPHEREx level-2 frame.
// Checked against astropy in wcs.test.ts. Pixels are 0-based (FITS pixel minus 1).

export const BLOCK = 2880;
const CARD = 80;
const D2R = Math.PI / 180;

export type Header = Record<string, number | string | boolean>;

/** Parse 80-character header cards up to END. Returns null if END is not in the text yet. */
export function parseHeader(text: string): { header: Header; bytes: number } | null {
  const header: Header = {};
  for (let i = 0; i + CARD <= text.length; i += CARD) {
    const card = text.slice(i, i + CARD);
    const key = card.slice(0, 8).trim();
    if (key === 'END') return { header, bytes: Math.ceil((i + CARD) / BLOCK) * BLOCK };
    if (card[8] !== '=' || key === 'HIERARCH') continue;
    const raw = card.slice(10);
    if (raw.trimStart().startsWith("'")) {
      const m = raw.match(/'((?:[^']|'')*)'/);
      header[key] = m ? m[1].replace(/''/g, "'").trimEnd() : '';
    } else {
      const v = raw.split('/')[0].trim();
      header[key] = v === 'T' ? true : v === 'F' ? false : Number(v.replace(/D/i, 'E'));
    }
  }
  return null;
}

export interface ImageHdu {
  header: Header;
  /** byte offset of the first pixel in the file */
  dataOffset: number;
  nx: number;
  ny: number;
}

/** Find the IMAGE HDU (the first extension) in the first bytes of a level-2 file. Null = need more bytes. */
export function findImageHdu(bytes: Uint8Array): ImageHdu | null {
  const text = new TextDecoder('ascii').decode(bytes);
  const primary = parseHeader(text);
  if (!primary) return null;
  const ext = parseHeader(text.slice(primary.bytes));
  if (!ext) return null;
  const h = ext.header;
  if (h.XTENSION !== 'IMAGE' || h.BITPIX !== -32 || h.NAXIS !== 2) throw new Error('Not a float32 image extension');
  return { header: h, dataOffset: primary.bytes + ext.bytes, nx: h.NAXIS1 as number, ny: h.NAXIS2 as number };
}

export interface Wcs {
  crval: [number, number];
  /** sky (degrees) to 0-based pixel */
  world2pix(ra: number, dec: number): [number, number];
}

function sip(h: Header, name: string): number[][] | null {
  const order = h[`${name}_ORDER`];
  if (typeof order !== 'number') return null;
  const c: number[][] = [];
  for (let p = 0; p <= order; p++) {
    c.push([]);
    for (let q = 0; q <= order; q++) c[p].push(typeof h[`${name}_${p}_${q}`] === 'number' ? (h[`${name}_${p}_${q}`] as number) : 0);
  }
  return c;
}

function poly(c: number[][] | null, u: number, v: number): number {
  if (!c) return 0;
  let s = 0, up = 1;
  for (let p = 0; p < c.length; p++) {
    let vq = 1;
    for (let q = 0; q < c.length - p; q++) {
      s += c[p][q] * up * vq;
      vq *= v;
    }
    up *= u;
  }
  return s;
}

export function makeWcs(h: Header): Wcs {
  const num = (k: string, d: number) => (typeof h[k] === 'number' ? (h[k] as number) : d);
  if (!String(h.CTYPE1).startsWith('RA---TAN') || !String(h.CTYPE2).startsWith('DEC--TAN')) throw new Error('Unsupported projection ' + h.CTYPE1);
  const crpix1 = num('CRPIX1', 0), crpix2 = num('CRPIX2', 0);
  const ra0 = num('CRVAL1', 0) * D2R, dec0 = num('CRVAL2', 0) * D2R;
  // CD matrix, from CDi_j or PCi_j * CDELTi
  const hasCd = typeof h.CD1_1 === 'number';
  const d1 = hasCd ? 1 : num('CDELT1', 1), d2 = hasCd ? 1 : num('CDELT2', 1);
  const pre = hasCd ? 'CD' : 'PC';
  const cd11 = num(pre + '1_1', 1) * d1, cd12 = num(pre + '1_2', 0) * d1, cd21 = num(pre + '2_1', 0) * d2, cd22 = num(pre + '2_2', 1) * d2;
  const det = cd11 * cd22 - cd12 * cd21;
  const A = sip(h, 'A'), B = sip(h, 'B'), AP = sip(h, 'AP'), BP = sip(h, 'BP');
  const sin0 = Math.sin(dec0), cos0 = Math.cos(dec0);

  return {
    crval: [num('CRVAL1', 0), num('CRVAL2', 0)],
    world2pix(ra, dec) {
      // gnomonic projection onto the tangent plane, degrees
      const a = ra * D2R - ra0, d = dec * D2R;
      const sd = Math.sin(d), cdd = Math.cos(d), ca = Math.cos(a);
      const D = sin0 * sd + cos0 * cdd * ca;
      const xi = (cdd * Math.sin(a)) / D / D2R, eta = (cos0 * sd - sin0 * cdd * ca) / D / D2R;
      // undistorted offsets from CRPIX
      const U = (cd22 * xi - cd12 * eta) / det, V = (-cd21 * xi + cd11 * eta) / det;
      // SIP: U = u + A(u, v). Start from the inverse polynomial (or U), then polish on the forward one.
      let u = U + poly(AP, U, V), v = V + poly(BP, U, V);
      if (A || B) for (let k = 0; k < 4; k++) [u, v] = [U - poly(A, u, v), V - poly(B, u, v)];
      return [u + crpix1 - 1, v + crpix2 - 1];
    },
  };
}

/** Sky position at a tangent-plane offset (arcsec east, north) from a centre, all in degrees. */
export function offsetToSky(ra0: number, dec0: number, east: number, north: number): [number, number] {
  const x = (east / 3600) * D2R, y = (north / 3600) * D2R;
  const d0 = dec0 * D2R;
  const den = Math.cos(d0) - y * Math.sin(d0);
  const ra = ra0 + Math.atan2(x, den) / D2R;
  const dec = Math.atan2(Math.sin(d0) + y * Math.cos(d0), Math.hypot(x, den)) / D2R;
  return [((ra % 360) + 360) % 360, dec];
}

/** Tangent-plane offset (arcsec east, north) of a sky position from a centre. */
export function skyToOffset(ra0: number, dec0: number, ra: number, dec: number): [number, number] {
  const a = (ra - ra0) * D2R, d = dec * D2R, d0 = dec0 * D2R;
  const D = Math.sin(d0) * Math.sin(d) + Math.cos(d0) * Math.cos(d) * Math.cos(a);
  return [((Math.cos(d) * Math.sin(a)) / D / D2R) * 3600, ((Math.cos(d0) * Math.sin(d) - Math.sin(d0) * Math.cos(d) * Math.cos(a)) / D / D2R) * 3600];
}
