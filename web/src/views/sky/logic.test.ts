import { describe, expect, it } from 'vitest';
import {
  apertureMean, cellsFor, diffGrey, framesAt, groupFrames, inPolygon, medianStack, parseCoords, parseWaveGrid, pickFrames, properMotion, resolveKey,
  sharedStretch, skyStats, spreadOrder, toGrey, trackMover, waveAt, type Frame, type Row, type SkyMeta,
} from './logic';

const meta: SkyMeta = {
  schema: 'rewind-skyindex-v1', releases: ['qr3', 'dr1'], n_frames: 2, cell_deg: 5,
  vers: ['l2b-v27-2026-214', 'l2b_retry-v27-2026-225'],
  key_patterns: { level2: '{release}/level2/{week}/{ver}/{det}/level2_{obs}D{det}_spx_{ver}.fits' },
};
const square = (ra: number, dec: number, half = 1.7) => [ra - half, dec - half, ra + half, dec - half, ra + half, dec + half, ra - half, dec + half];
const row = (key: string, mjd: number, det: number, ra = 133.8, dec = -7.2, release = 1): Row => [key, mjd, det, ra, dec, square(ra, dec), 4.4, 5.0, release];
const frame = (key: string, mjd: number, detector = 1): Frame => ({ key, mjd, detector, release: 'dr1', wlMin: 0.7, wlMax: 1.1, pass: 0, visit: 0 });

describe('position input', () => {
  it('reads degrees', () => {
    expect(parseCoords('133.7951 -7.2451')).toEqual({ ra: 133.7951, dec: -7.2451 });
    expect(parseCoords(' 133.7951, +7.2451 ')).toEqual({ ra: 133.7951, dec: 7.2451 });
  });
  it('reads hours and degrees with minutes and seconds', () => {
    const c = parseCoords('08 55 10.83 -07 14 42.5')!;
    expect(c.ra).toBeCloseTo(133.795125, 5);
    expect(c.dec).toBeCloseTo(-7.245139, 5);
    const d = parseCoords('17h57m48.5s +04d41m36s')!;
    expect(d.ra).toBeCloseTo(269.452083, 5);
    expect(d.dec).toBeCloseTo(4.693333, 5);
    expect(parseCoords('00:10:00 -00:30:00')!.dec).toBeCloseTo(-0.5, 9);
  });
  it('rejects what it cannot read', () => {
    for (const bad of ['', 'andromeda', '400 10', '10 95', '1 2 3', '08 70 00 -07 14 42']) expect(parseCoords(bad)).toBeNull();
  });
});

describe('frame index', () => {
  it('names the cells around a position, with wrap in RA', () => {
    expect(cellsFor(133.7951, -7.2451)).toEqual(expect.arrayContaining(['r26_d16']));
    expect(cellsFor(133.7951, -7.2451).length).toBeLessThanOrEqual(9);
    expect(cellsFor(0.5, 0.5)).toEqual(expect.arrayContaining(['r71_d17', 'r0_d18', 'r71_d18', 'r0_d17']));
    // near a pole every RA cell of the last band can hold a covering frame
    expect(cellsFor(10, 89.5).filter((c) => c.endsWith('_d35')).length).toBe(72);
    expect(cellsFor(270, 66.56)).toEqual(expect.arrayContaining(['r52_d31', 'r55_d31']));
  });
  it('tests a position against a frame outline', () => {
    expect(inPolygon(133.8, -7.2, square(133.8, -7.2))).toBe(true);
    expect(inPolygon(136.0, -7.2, square(133.8, -7.2))).toBe(false);
    expect(inPolygon(0.2, 10, square(359.9, 10))).toBe(true); // across RA = 0
    expect(inPolygon(313.8, 7.2, square(133.8, -7.2))).toBe(false); // other side of the sky
  });
  it('rebuilds the archive key of a compact row', () => {
    expect(resolveKey(row('2025W26_2A_0354_1|0', 60850, 6), meta)).toBe('dr1/level2/2025W26_2A/l2b-v27-2026-214/6/level2_2025W26_2A_0354_1D6_spx_l2b-v27-2026-214.fits');
    expect(resolveKey(row('2026W31_2A_0217_1|1', 61250, 1, 0, 0, 0), meta)).toBe('qr3/level2/2026W31_2A/l2b_retry-v27-2026-225/1/level2_2026W31_2A_0217_1D1_spx_l2b_retry-v27-2026-225.fits');
    expect(resolveKey(row('qr3/level2/x/y/1/z.fits', 1, 1), meta)).toBe('qr3/level2/x/y/1/z.fits');
  });
  it('decodes the full index compact keys (each one answered HTTP 206 to a Range read on S3, 2026-11-15)', () => {
    // the groups used, copied from meta.json key_groups of the full index
    const groups: Record<number, [string, string, string]> = {
      0: ['dr1', '2025W17_4B', 'l2b-v27-2026-196'], 55: ['dr1', '2025W33_1B', 'l2b-v27-2026-227'], 57: ['dr1', '2025W33_2C', 'l2b-v27-2026-228'],
      59: ['dr1', '2025W34_1B', 'l2b-v27-2026-228'], 60: ['dr1', '2025W34_2B', 'l2b-v27-2026-229'], 246: ['qr3', '2026W34_1A', 'l2b-v27-2026-243'],
    };
    const full: SkyMeta = {
      schema: 'rewind-skyindex-v1', releases: ['qr3', 'dr1'], n_frames: 1628230, cell_deg: 5,
      key_patterns: { template: '{release}/level2/{week}/{proc}/{detector}/level2_{week}_{SEQ}D{detector}_spx_{proc}.fits' },
      key_groups: Object.assign([], groups),
    };
    const known: [string, number, string][] = [
      // cell r11_d22
      ['59/0278_1', 4, 'dr1/level2/2025W34_1B/l2b-v27-2026-228/4/level2_2025W34_1B_0278_1D4_spx_l2b-v27-2026-228.fits'],
      ['59/0278_1', 1, 'dr1/level2/2025W34_1B/l2b-v27-2026-228/1/level2_2025W34_1B_0278_1D1_spx_l2b-v27-2026-228.fits'],
      ['60/0111_2', 1, 'dr1/level2/2025W34_2B/l2b-v27-2026-229/1/level2_2025W34_2B_0111_2D1_spx_l2b-v27-2026-229.fits'],
      ['246/0209_1', 1, 'qr3/level2/2026W34_1A/l2b-v27-2026-243/1/level2_2026W34_1A_0209_1D1_spx_l2b-v27-2026-243.fits'],
      // cell r17_d5
      ['0/0004_1', 2, 'dr1/level2/2025W17_4B/l2b-v27-2026-196/2/level2_2025W17_4B_0004_1D2_spx_l2b-v27-2026-196.fits'],
      ['0/0025_4', 5, 'dr1/level2/2025W17_4B/l2b-v27-2026-196/5/level2_2025W17_4B_0025_4D5_spx_l2b-v27-2026-196.fits'],
      ['0/0374_1', 2, 'dr1/level2/2025W17_4B/l2b-v27-2026-196/2/level2_2025W17_4B_0374_1D2_spx_l2b-v27-2026-196.fits'],
      // cell r53_d18
      ['55/0310_1', 3, 'dr1/level2/2025W33_1B/l2b-v27-2026-227/3/level2_2025W33_1B_0310_1D3_spx_l2b-v27-2026-227.fits'],
      ['55/0310_2', 6, 'dr1/level2/2025W33_1B/l2b-v27-2026-227/6/level2_2025W33_1B_0310_2D6_spx_l2b-v27-2026-227.fits'],
      ['55/0310_4', 6, 'dr1/level2/2025W33_1B/l2b-v27-2026-227/6/level2_2025W33_1B_0310_4D6_spx_l2b-v27-2026-227.fits'],
      ['57/0321_1', 6, 'dr1/level2/2025W33_2C/l2b-v27-2026-228/6/level2_2025W33_2C_0321_1D6_spx_l2b-v27-2026-228.fits'],
    ];
    for (const [k, det, key] of known) expect(resolveKey(row(k, 60900, det), full)).toBe(key);
    // a compact row goes through framesAt like any other
    expect(framesAt(133.7951, -7.2451, [{ f: [row('59/0278_1', 60906.44, 4)] }], full)[0].key).toBe(known[0][2]);
  });
  it('finds the covering frames once each, oldest first', () => {
    const shard = { f: [row('b_2|0', 60900.2, 6), row('a_1|0', 60900.1, 5), row('far_3|0', 60900.3, 6, 150, 20)] };
    const got = framesAt(133.7951, -7.2451, [shard, shard], meta);
    expect(got.map((f) => f.detector)).toEqual([5, 6]);
    expect(got[0].release).toBe('dr1');
  });
  it('numbers visits and survey passes', () => {
    const f = groupFrames([frame('a', 60800), frame('b', 60800.01), frame('c', 60801), frame('d', 60985), frame('e', 60985.1)]);
    expect(f.map((x) => x.pass)).toEqual([0, 0, 0, 1, 1]);
    expect(f.map((x) => x.visit)).toEqual([0, 0, 1, 2, 2]);
    // a field that is watched all the time is cut into half-year passes
    const deep = groupFrames(Array.from({ length: 400 }, (_v, i) => frame('k' + i, 60800 + i)));
    expect(deep[399].pass).toBe(2);
  });
});

describe('which photos to read first', () => {
  it('spreads any prefix over the whole range', () => {
    expect(spreadOrder(8)).toEqual([4, 2, 6, 1, 3, 5, 7, 0]);
    expect([...spreadOrder(13)].sort((a, b) => a - b)).toEqual(Array.from({ length: 13 }, (_v, i) => i));
  });
  it('takes from every pass and band, skips what is taken, and honours the focus date', () => {
    const all = groupFrames([
      ...Array.from({ length: 30 }, (_v, i) => frame('p0_' + i, 60800 + i * 0.01, 1 + (i % 6))),
      ...Array.from({ length: 30 }, (_v, i) => frame('p1_' + i, 60990 + i * 0.01, 1 + (i % 6))),
    ]);
    const first = pickFrames(all, new Set(), 12);
    expect(first.length).toBe(12);
    expect(new Set(first.map((f) => `${f.pass}/${f.detector}`)).size).toBe(12);
    expect(first.map((f) => f.mjd)).toEqual([...first.map((f) => f.mjd)].sort((a, b) => a - b));
    const second = pickFrames(all, new Set(first.map((f) => f.key)), 100);
    expect(second.length).toBe(48);
    expect(second.some((f) => first.includes(f))).toBe(false);
    const focused = pickFrames(all, new Set(), 6, 60990);
    expect(focused.filter((f) => f.pass === 1).length).toBeGreaterThanOrEqual(2);
  });
});

describe('wavelength and motion', () => {
  it('reads nested and flat wavelength grids and interpolates', () => {
    const nested = parseWaveGrid({ xs: [0, 100], ys: [0, 100], wave_um: [[1, 1], [2, 2]] })!;
    expect(waveAt(nested, 50, 25)).toBeCloseTo(1.25, 9);
    expect(waveAt(nested, 50, 500)).toBeCloseTo(2, 9); // clamped at the edge
    const flat = parseWaveGrid({ nx: 2, naxis: [2040, 2040], wave: [1, 1, 2, 2] })!;
    expect(flat.xs).toEqual([509.5, 1529.5]);
    expect(waveAt(flat, 1019.5, 1019.5)).toBeCloseTo(1.5, 9);
    expect(parseWaveGrid({})).toBeNull();
    // the full index files: cwave_um blocks with one naxis number
    const blocks = parseWaveGrid({ n: 2, naxis: 2040, block_px: 1020, cwave_um: [[1, 2], [3, 4]] })!;
    expect(blocks.xs).toEqual([509.5, 1529.5]);
    expect(waveAt(blocks, 1019.5, 509.5)).toBeCloseTo(1.5, 9);
  });
  it('moves a star by its catalogue proper motion', () => {
    // WISE 0855: 8.1 arcsec per year to the west
    const at = properMotion(133.783556, -7.244052, -8123.7, 673.2, 2015.3929);
    const [ra, dec] = at(51544.5 + 365.25 * 26.3929); // 11 years later
    expect((ra - 133.783556) * 3600 * Math.cos((-7.244052 * Math.PI) / 180)).toBeCloseTo(-89.36, 1);
    expect((dec + 7.244052) * 3600).toBeCloseTo(7.41, 1);
  });
  it('follows a solar-system object between its photos only', () => {
    const at = trackMover([{ mjd: 100, ra: 10, dec: 0 }, { mjd: 100.5, ra: 11, dec: 1 }, { mjd: 300, ra: 50, dec: 5 }]);
    expect(at(100.25)).toEqual([10.5, 0.5]);
    expect(at(200)).toBeNull();
    expect(at(300.01)).toEqual([50, 5]);
  });
});

describe('pictures', () => {
  it('measures sky and noise, stacks by median and ignores missing pixels', () => {
    const { sky, noise } = skyStats(Float32Array.from([1, 2, 3, 4, 100, NaN]));
    expect(sky).toBe(3);
    expect(noise).toBeCloseTo(1.4826, 4);
    const stack = medianStack([Float32Array.from([1, NaN, NaN]), Float32Array.from([5, 2, NaN]), Float32Array.from([9, 4, NaN])]);
    expect([stack[0], stack[1]]).toEqual([5, 3]);
    expect(stack[2]).toBeNaN();
  });
  it('maps brightness to grey with one stretch, and differences around mid grey', () => {
    const s = sharedStretch([Float32Array.from([0, 0.1, -0.1, 50])], [0.1]);
    expect(toGrey(-1, s)).toBe(0);
    expect(toGrey(1e6, s)).toBe(255);
    expect(toGrey(0, s)).toBeGreaterThan(0);
    expect(toGrey(1, s)).toBeGreaterThan(toGrey(0.2, s));
    expect(toGrey(NaN, s)).toBe(0);
    expect([diffGrey(0, 1), diffGrey(5, 1), diffGrey(-5, 1), diffGrey(NaN, 1)]).toEqual([128, 255, 1, 128]);
  });
  it('averages the pixels inside a small circle', () => {
    const data = new Float32Array(16).fill(1);
    data[5] = 9; // pixel (1, 1)
    expect(apertureMean(data, 4, 1.5, 1.5, 0.6)).toBe(9);
    expect(apertureMean(data, 4, 1.5, 1.5, 1.2)).toBeCloseTo((9 + 4) / 5, 6);
    expect(apertureMean(new Float32Array(16).fill(NaN), 4, 2, 2, 1)).toBeNaN();
  });
});
