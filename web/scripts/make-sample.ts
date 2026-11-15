// Builds web/public/data-sample/ in the exact data-contract format, with "sample": true.
// Orbits are REAL (MPCORB, MPC NEA list, MPC comet list, JPL SBDB new-object list).
// Everything else (photos, detections, checks, clouds, spectra) is SYNTHETIC sample data.
// Run: node scripts/make-sample.ts   (Node 22+, type stripping)
import { mkdirSync, readFileSync, writeFileSync, rmSync, existsSync } from 'node:fs';
import { gunzipSync } from 'node:zlib';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { encodeGray } from './png.ts';
import {
  type Elements, type PlanetRow, type Vec3, DEG, meanMotion, positionAt, planetPosition, cometToElements, dist,
} from '../src/lib/kepler.ts';

const HERE = dirname(fileURLToPath(import.meta.url));
const MAIN = process.env.REWIND_MAIN ?? '/Users/rahmanbazarov/Data/programming/SpaceApps2026-Rewind';
const OUT = process.env.SAMPLE_OUT ?? join(HERE, '..', 'public', 'data-sample'); // SAMPLE_OUT: build somewhere else first
const EPOCH = 61200; // MJD 2026-06-09, the MPCORB common epoch K2669
const AU_KM = 149597870.7;
const LD_KM = 384400;
const TODAY = 61359; // 2026-11-15, the date this sample was built

// ---------- helpers ----------
function rng(seed: number) {
  let s = seed >>> 0;
  const next = () => {
    s = (s + 0x6d2b79f5) >>> 0;
    let t = s;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
  const gauss = () => Math.sqrt(-2 * Math.log(next() + 1e-12)) * Math.cos(2 * Math.PI * next());
  return { next, gauss };
}
const R = rng(20261115);
const r3 = (v: Vec3): Vec3 => v.map((x) => +x.toFixed(5)) as Vec3;
const iso = (mjd: number) => new Date((mjd - 40587) * 86400000).toISOString().slice(0, 10);
const mjdOf = (s: string) => Date.parse(s.slice(0, 10) + 'T00:00:00Z') / 86400000 + 40587;
function writeJson(rel: string, obj: unknown, pretty = true) {
  const p = join(OUT, rel);
  mkdirSync(dirname(p), { recursive: true });
  writeFileSync(p, JSON.stringify(obj, null, pretty ? 1 : 0));
}
function writePng(rel: string, w: number, h: number, px: Uint8Array) {
  const p = join(OUT, rel);
  mkdirSync(dirname(p), { recursive: true });
  writeFileSync(p, encodeGray(w, h, px));
}

function parseCsv(text: string): Record<string, string>[] {
  const lines = text.split('\n').filter(Boolean);
  const split = (l: string) => {
    const out: string[] = [];
    let cur = '', q = false;
    for (const ch of l) {
      if (ch === '"') q = !q;
      else if (ch === ',' && !q) { out.push(cur); cur = ''; }
      else cur += ch;
    }
    out.push(cur);
    return out;
  };
  const head = split(lines[0]);
  return lines.slice(1).map((l) => {
    const v = split(l);
    return Object.fromEntries(head.map((h, i) => [h, v[i] ?? '']));
  });
}

// MPC packed epoch like K2669 -> MJD
function unpackEpoch(p: string): number {
  const cent = { I: 1800, J: 1900, K: 2000 }[p[0] as 'I' | 'J' | 'K'] ?? 2000;
  const yr = cent + parseInt(p.slice(1, 3), 10);
  const val = (c: string) => (c <= '9' ? +c : c.charCodeAt(0) - 55);
  return Date.UTC(yr, val(p[3]) - 1, val(p[4])) / 86400000 + 40587;
}

interface Row { a: number; e: number; i: number; node: number; peri: number; M: number; H: number; flag: number; key: string }

function mpcLine(l: string): (Row & { hex: number }) | null {
  if (l.length < 160) return null;
  const a = +l.slice(92, 103), e = +l.slice(70, 79);
  if (!(a > 0) || !(e >= 0 && e < 1)) return null;
  let M = +l.slice(26, 35);
  const ep = unpackEpoch(l.slice(20, 25).trim());
  if (Math.abs(ep - EPOCH) > 0.5) M = (M + (meanMotion(a) * (EPOCH - ep)) / DEG) % 360;
  const readable = l.slice(166, 194).trim();
  const num = readable.match(/^\((\d+)\)/);
  return {
    a, e, i: +l.slice(59, 68), node: +l.slice(48, 57), peri: +l.slice(37, 46), M: (M + 360) % 360,
    H: +l.slice(8, 13) || 18, flag: 0, key: num ? num[1] : readable, hex: parseInt(l.slice(161, 165), 16) || 0,
  };
}

// ---------- 1. orbits ----------
console.log('reading orbit sources from', MAIN);
const D = join(MAIN, 'data');
const newCsv = parseCsv(readFileSync(join(D, '01-targets/clean/new_objects_since_2025-04-01.csv'), 'utf8'));
const byKey = new Map<string, Row>();
const newInfo = new Map<string, Record<string, string>>();
for (const r of newCsv) {
  const a = +r.a, e = +r.e;
  if (!(a > 0) || !(e < 1)) continue;
  const ep = +r.epoch - 2400000.5;
  let M = +r.ma;
  if (Math.abs(ep - EPOCH) > 0.5) M = (M + (meanMotion(a) * (EPOCH - ep)) / DEG) % 360;
  let flag = 4;
  if (r.neo === 'Y') flag |= 1;
  if (r.pha === 'Y') flag |= 2;
  byKey.set(r.pdes, { a, e, i: +r.i, node: +r.om, peri: +r.w, M: (M + 360) % 360, H: +r.H || 20, flag, key: r.pdes });
  newInfo.set(r.pdes, r);
}
// keep every new NEO, thin the new main-belt objects
const newRows = [...byKey.values()];
const keepNew = new Set(newRows.filter((r) => r.flag & 1 || R.next() < 0.1).map((r) => r.key));
for (const k of [...byKey.keys()]) if (!keepNew.has(k)) byKey.delete(k);
console.log('new objects kept', byKey.size);

const nea = readFileSync(join(D, '02-orbits/mpc/NEA.txt'), 'utf8').split('\n');
const neaByKey = new Map<string, Row>();
for (const l of nea) {
  const r = mpcLine(l);
  if (!r) continue;
  r.flag = 1 | (r.hex & 0x8000 ? 2 : 0);
  neaByKey.set(r.key, r);
  if (!byKey.has(r.key)) byKey.set(r.key, r);
}
console.log('after NEAs', byKey.size);

const mpcorb = gunzipSync(readFileSync(join(D, '02-orbits/mpc/MPCORB.DAT.gz'))).toString('latin1').split('\n');
let mba = 0;
for (let k = 43; k < mpcorb.length; k++) {
  if (R.next() > 0.02) continue;
  const r = mpcLine(mpcorb[k]);
  if (!r || r.a < 1.7 || r.a > 5.6 || byKey.has(r.key)) continue;
  byKey.set(r.key, r);
  mba++;
}
console.log('main-belt sample', mba);

const cometLines = readFileSync(join(D, '02-orbits/mpc/CometEls.txt'), 'utf8').split('\n');
const comets = new Map<string, Row & { tp: number }>();
for (const l of cometLines) {
  if (l.length < 100) continue;
  const tp = Date.UTC(+l.slice(14, 18), +l.slice(19, 21) - 1, 1) / 86400000 + 40587 + (+l.slice(22, 29) - 1);
  const q = +l.slice(30, 39), e = +l.slice(41, 49);
  const el = cometToElements(q, e, +l.slice(71, 79), +l.slice(61, 69), +l.slice(51, 59), tp, EPOCH);
  const name = l.slice(102, 158).trim();
  if (!el || e > 0.985 || el.a > 120) continue;
  const row = { ...el, H: +l.slice(91, 95) || 12, flag: 8, key: name, tp };
  comets.set(name, row);
  byKey.set('comet:' + name, row);
}
console.log('comets', comets.size, 'total rows', byKey.size);

// ---------- 2. showcase objects (real orbits, synthetic Rewind results) ----------
type Verdict = 'FOUND' | 'HINT' | 'TOO_FAINT' | 'NO_PHOTOS' | 'PENDING';
interface Show {
  slug: string; name: string; kind: 'comet' | 'neo' | 'mba' | 'lost' | 'famous'; verdict: Verdict;
  row: Row; disc: { mjd: number; by: string; site: string }; flashDaysBefore: number | null; flashMjd?: number;
  snr: number; flashLabel?: string; sigmaBeforeDeg: number; story: string; sources: string[]; cls: string | null;
  diameter: number | null; albedo: number | null; sentry?: boolean;
}
function needRow(k: string): Row {
  const r = byKey.get(k) ?? neaByKey.get(k);
  if (!r) throw new Error('missing orbit for ' + k);
  return r;
}
function discOf(k: string, fallbackIso: string) {
  const r = newInfo.get(k);
  const isoStr = r?.disc_date_best || r?.first_obs || fallbackIso;
  return mjdOf(isoStr);
}
const lostJson = JSON.parse(readFileSync(join(D, '02-orbits/sbdb/1988_RH9.json'), 'utf8'));
const lel = Object.fromEntries(lostJson.orbit.elements.map((x: { name: string; value: string }) => [x.name, +x.value]));
const lostEp = +lostJson.orbit.epoch - 2400000.5;
const lostRow: Row = {
  a: lel.a, e: lel.e, i: lel.i, node: lel.om, peri: lel.w,
  M: ((lel.ma + (meanMotion(lel.a) * (EPOCH - lostEp)) / DEG) % 360 + 360) % 360, H: 17.5, flag: 0, key: '1988 RH9',
};
byKey.set('1988 RH9', lostRow);

const SHOW: Show[] = [
  { slug: '2026kc3', name: '2026 KC3', kind: 'neo', verdict: 'FOUND', row: needRow('2026 KC3'),
    disc: { mjd: discOf('2026 KC3', '2026-05-20'), by: 'Catalina Sky Survey', site: 'Mount Lemmon, Arizona' },
    flashDaysBefore: 38, snr: 9.4, sigmaBeforeDeg: 0.35, cls: 'S', diameter: 0.6, albedo: null,
    story: 'A near-Earth asteroid about the size of a few city blocks. It was first reported in May 2026. In this sample, SPHEREx had already photographed it weeks earlier, while nobody was looking for it.',
    sources: ['https://ssd.jpl.nasa.gov/tools/sbdb_lookup.html#/?sstr=2026%20KC3', 'https://minorplanetcenter.net/db_search/show_object?object_id=2026+KC3'] },
  { slug: '2026rd39', name: '2026 RD39', kind: 'neo', verdict: 'FOUND', row: needRow('2026 RD39'),
    disc: { mjd: discOf('2026 RD39', '2026-09-05'), by: 'ATLAS', site: 'Haleakala, Hawaii' },
    flashDaysBefore: 60, snr: 7.2, sigmaBeforeDeg: 0.6, cls: 'C', diameter: 0.15, albedo: null,
    story: 'A small near-Earth asteroid found in September 2026. Its orbit was based on only a few weeks of watching. One older photo two months earlier stretches that arc a lot.',
    sources: ['https://ssd.jpl.nasa.gov/tools/sbdb_lookup.html#/?sstr=2026%20RD39'] },
  { slug: '2026mm', name: '2026 MM', kind: 'neo', verdict: 'HINT', row: needRow('2026 MM'),
    disc: { mjd: discOf('2026 MM', '2026-06-20'), by: 'Pan-STARRS', site: 'Haleakala, Hawaii' },
    flashDaysBefore: 21, snr: 4.1, sigmaBeforeDeg: 0.3, cls: null, diameter: null, albedo: null,
    story: 'A near-Earth asteroid found in June 2026. There is a faint spot in the right place in older SPHEREx photos, but it is not strong enough to be sure.',
    sources: ['https://ssd.jpl.nasa.gov/tools/sbdb_lookup.html#/?sstr=2026%20MM'] },
  { slug: 'c2026j1', name: 'C/2026 J1 (PANSTARRS)', kind: 'comet', verdict: 'FOUND', row: comets.get('C/2026 J1 (PANSTARRS)')!,
    disc: { mjd: mjdOf('2026-05-08'), by: 'Pan-STARRS', site: 'Haleakala, Hawaii' },
    flashDaysBefore: 95, snr: 12.5, sigmaBeforeDeg: 0.25, cls: 'comet', diameter: null, albedo: null,
    story: 'A comet found in May 2026 by the Pan-STARRS telescope in Hawaii. Comets glow in infrared, which is where SPHEREx looks, so it shows up clearly in photos from months before.',
    sources: ['https://minorplanetcenter.net/iau/Ephemerides/Comets/Soft00Cmt.txt'] },
  { slug: 'c2026m5', name: 'C/2026 M5 (PANSTARRS)', kind: 'comet', verdict: 'TOO_FAINT', row: comets.get('C/2026 M5 (PANSTARRS)')!,
    disc: { mjd: mjdOf('2026-06-22'), by: 'Pan-STARRS', site: 'Haleakala, Hawaii' },
    flashDaysBefore: null, snr: 1.2, sigmaBeforeDeg: 0.4, cls: 'comet', diameter: null, albedo: null,
    story: 'A comet found in June 2026. SPHEREx did point at the right part of the sky, but the comet was still too far from the Sun to glow enough.',
    sources: ['https://minorplanetcenter.net/iau/Ephemerides/Comets/Soft00Cmt.txt'] },
  { slug: '1988rh9', name: '1988 RH9', kind: 'lost', verdict: 'HINT', row: lostRow,
    disc: { mjd: mjdOf('1988-09-01'), by: 'Palomar', site: 'Palomar Mountain, California' },
    flashDaysBefore: null, flashMjd: mjdOf('2025-10-03'), snr: 4.6, sigmaBeforeDeg: 9, cls: null, diameter: null, albedo: null,
    flashLabel: 'SPHEREx photo of a lost asteroid',
    story: 'Seen for only 11 nights in 1988, then lost. Nobody knows exactly where it is now. A faint spot in a 2025 SPHEREx photo lines up with one of its possible paths.',
    sources: ['https://ssd.jpl.nasa.gov/tools/sbdb_lookup.html#/?sstr=1988%20RH9'] },
  { slug: 'apophis', name: '(99942) Apophis', kind: 'famous', verdict: 'FOUND', row: needRow('99942'),
    disc: { mjd: mjdOf('2004-06-19'), by: 'R. Tucker, D. Tholen, F. Bernardi', site: 'Kitt Peak, Arizona' },
    flashDaysBefore: null, flashMjd: mjdOf('2025-12-11'), snr: 15.8, sigmaBeforeDeg: 0.02, cls: 'S', diameter: 0.34, albedo: 0.35, sentry: false,
    flashLabel: 'SPHEREx photo of a famous asteroid',
    story: 'Found in 2004 and briefly the most worrying asteroid known. Older photos from before its discovery ruled out an impact. It will pass very close to Earth on 13 April 2029.',
    sources: ['https://ssd.jpl.nasa.gov/tools/sbdb_lookup.html#/?sstr=99942', 'https://science.nasa.gov/solar-system/asteroids/apophis/'] },
  { slug: '2024yr4', name: '2024 YR4', kind: 'famous', verdict: 'NO_PHOTOS', row: needRow('2024 YR4'),
    disc: { mjd: mjdOf('2024-12-27'), by: 'ATLAS', site: 'Rio Hurtado, Chile' },
    flashDaysBefore: null, snr: 0, sigmaBeforeDeg: 0.05, cls: null, diameter: 0.06, albedo: null,
    story: 'Found in December 2024, it briefly had a small chance of hitting Earth in 2032. SPHEREx started its survey in 2025, after the asteroid had faded from view, so there are no SPHEREx photos to search.',
    sources: ['https://ssd.jpl.nasa.gov/tools/sbdb_lookup.html#/?sstr=2024%20YR4', 'https://science.nasa.gov/solar-system/asteroids/2024-yr4/'] },
];
for (const s of SHOW) s.row.flag |= 16;

// write orbits
const rows = [...byKey.values()];
const outRows = rows.map((r) => [+r.a.toFixed(6), +r.e.toFixed(6), +r.i.toFixed(4), +r.node.toFixed(4), +r.peri.toFixed(4), +r.M.toFixed(4), +r.H.toFixed(1), r.flag]);
if (existsSync(OUT)) rmSync(OUT, { recursive: true });
mkdirSync(OUT, { recursive: true });
const fields = ['a', 'e', 'i', 'node', 'peri', 'M', 'H', 'flag'];
writeJson('orbits.json', {
  schema: 'rewind-orbits-v1', sample: true, epoch_mjd: EPOCH, fields,
  flag_bits: { '1': 'neo', '2': 'pha', '4': 'new_since_2025', '8': 'comet', '16': 'in_rewind' },
  note: 'Sample: real orbits from MPCORB, MPC NEA list, MPC comet list and JPL SBDB, thinned at random. in_rewind flags are sample.',
  rows: outRows,
}, false);
const bin = new Float32Array(outRows.length * fields.length);
outRows.forEach((r, k) => bin.set(r, k * fields.length));
writeFileSync(join(OUT, 'orbits.bin'), Buffer.from(bin.buffer));
writeJson('orbits.bin.json', { rows: outRows.length, fields, epoch_mjd: EPOCH, dtype: 'float32', order: 'row-major', sample: true });
console.log('orbits rows', outRows.length);

// ---------- 3. planets (JPL approximate positions of the planets, 1800-2050 table) ----------
const P = (name: string, v: number[]): PlanetRow => ({
  name, a: v[0], a_rate: v[1], e: v[2], e_rate: v[3], i: v[4], i_rate: v[5], L: v[6], L_rate: v[7],
  varpi: v[8], varpi_rate: v[9], node: v[10], node_rate: v[11],
});
const planets = [
  P('Mercury', [0.38709927, 0.00000037, 0.20563593, 0.00001906, 7.00497902, -0.00594749, 252.2503235, 149472.67411175, 77.45779628, 0.16047689, 48.33076593, -0.12534081]),
  P('Venus', [0.72333566, 0.0000039, 0.00677672, -0.00004107, 3.39467605, -0.0007889, 181.9790995, 58517.81538729, 131.60246718, 0.00268329, 76.67984255, -0.27769418]),
  P('Earth', [1.00000261, 0.00000562, 0.01671123, -0.00004392, -0.00001531, -0.01294668, 100.46457166, 35999.37244981, 102.93768193, 0.32327364, 0, 0]),
  P('Mars', [1.52371034, 0.00001847, 0.0933941, 0.00007882, 1.84969142, -0.00813131, -4.55343205, 19140.30268499, -23.94362959, 0.44441088, 49.55953891, -0.29257343]),
  P('Jupiter', [5.202887, -0.00011607, 0.04838624, -0.00013253, 1.30439695, -0.00183714, 34.39644051, 3034.74612775, 14.72847983, 0.21252668, 100.47390909, 0.20469106]),
  P('Saturn', [9.53667594, -0.0012506, 0.05386179, -0.00050991, 2.48599187, 0.00193609, 49.95424423, 1222.49362201, 92.59887831, -0.41897216, 113.66242448, -0.28867794]),
  P('Uranus', [19.18916464, -0.00196176, 0.04725744, -0.00004397, 0.77263783, -0.00242939, 313.23810451, 428.48202785, 170.9542763, 0.40805281, 74.01692503, 0.04240589]),
  P('Neptune', [30.06992276, 0.00026291, 0.00859048, 0.00005105, 1.77004347, 0.00035372, -55.12002969, 218.45945325, 44.96476227, -0.32241464, 131.78422574, -0.00508664]),
];
writeJson('planets.json', {
  schema: 'rewind-planets-v1', sample: true,
  source: 'JPL Solar System Dynamics, Approximate Positions of the Planets (E.M. Standish), Table 1, valid 1800-2050. Earth row is the Earth-Moon barycenter.',
  url: 'https://ssd.jpl.nasa.gov/planets/approx_pos.html',
  units: 'AU and degrees; *_rate per Julian century from J2000',
  planets,
});
const earth = planets[2];
const earthAt = (mjd: number) => planetPosition(earth, mjd);

// ---------- 4. synthetic stamps ----------
const S = 64; // stamp size (px). Browser upscales with nearest-neighbour.
interface Star { x: number; y: number; f: number }
function starField(seed: number, n = 26): Star[] {
  const g = rng(seed);
  return Array.from({ length: n }, () => ({ x: g.next() * S * 2 - S / 2, y: g.next() * S * 2 - S / 2, f: 3 + 120 * Math.pow(g.next(), 4) }));
}
function render(stars: Star[], dx: number, dy: number, dots: { x: number; y: number; f: number }[], seed: number): Float32Array {
  const g = rng(seed);
  const img = new Float32Array(S * S);
  const psf = 0.9;
  for (let k = 0; k < img.length; k++) img[k] = g.gauss();
  const add = (cx: number, cy: number, f: number) => {
    const x0 = Math.max(0, Math.floor(cx - 4)), x1 = Math.min(S - 1, Math.ceil(cx + 4));
    const y0 = Math.max(0, Math.floor(cy - 4)), y1 = Math.min(S - 1, Math.ceil(cy + 4));
    for (let y = y0; y <= y1; y++) for (let x = x0; x <= x1; x++)
      img[y * S + x] += (f / (2 * Math.PI * psf * psf)) * Math.exp(-((x - cx) ** 2 + (y - cy) ** 2) / (2 * psf * psf));
  };
  for (const s of stars) add(s.x + dx, s.y + dy, s.f);
  for (const d of dots) add(d.x, d.y, d.f);
  return img;
}
// One shared asinh stretch for everything of an object.
function toPng(img: Float32Array): Uint8Array {
  const out = new Uint8Array(img.length);
  const lo = -2.5, hi = Math.asinh(60 / 3);
  for (let k = 0; k < img.length; k++) {
    const v = (Math.asinh(img[k] / 3) - Math.asinh(lo / 3)) / (hi - Math.asinh(lo / 3));
    out[k] = Math.max(0, Math.min(255, Math.round(255 * Math.pow(Math.max(0, v), 0.9))));
  }
  return out;
}
function mean(imgs: Float32Array[]): Float32Array {
  const o = new Float32Array(S * S);
  for (const im of imgs) for (let k = 0; k < o.length; k++) o[k] += im[k] / imgs.length;
  // keep the noise level of one frame so the shared stretch still works, but scale signal up
  for (let k = 0; k < o.length; k++) o[k] *= Math.sqrt(imgs.length);
  return o;
}
function median(imgs: Float32Array[]): Float32Array {
  const o = new Float32Array(S * S);
  const tmp = new Array(imgs.length);
  for (let k = 0; k < o.length; k++) {
    for (let j = 0; j < imgs.length; j++) tmp[j] = imgs[j][k];
    tmp.sort((a: number, b: number) => a - b);
    o[k] = tmp[tmp.length >> 1] * Math.sqrt(imgs.length) * 0.8;
  }
  return o;
}

// ecliptic -> equatorial RA/Dec of the object as seen from Earth
const OBL = 23.4392911 * DEG;
function radec(obj: Vec3, obs: Vec3): [number, number] {
  const x = obj[0] - obs[0], y0 = obj[1] - obs[1], z0 = obj[2] - obs[2];
  const y = y0 * Math.cos(OBL) - z0 * Math.sin(OBL), z = y0 * Math.sin(OBL) + z0 * Math.cos(OBL);
  const ra = ((Math.atan2(y, x) / DEG) + 360) % 360;
  return [+ra.toFixed(5), +(Math.atan2(z, Math.hypot(x, y)) / DEG).toFixed(5)];
}

const toEl = (r: Row): Elements => ({ a: r.a, e: r.e, i: r.i, node: r.node, peri: r.peri, M: r.M, epoch_mjd: EPOCH });

// ---------- 5. object pages ----------
const BANDS = [0.75, 0.93, 1.11, 1.33, 1.64, 1.98, 2.42, 2.94, 3.52, 3.95, 4.45, 4.92];
const TEMPLATES = [
  { name: 'S type (stony)', um: [0.75, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0], value: [0.97, 0.93, 1.05, 1.1, 1.06, 1.17, 1.22, 1.27, 1.33, 1.42, 1.55] },
  { name: 'C type (dark, carbon rich)', um: [0.75, 1.0, 1.25, 1.5, 2.0, 2.5, 2.8, 3.0, 3.5, 4.0, 4.5, 5.0], value: [0.99, 1.0, 1.01, 1.02, 1.03, 1.04, 0.95, 0.93, 1.02, 1.06, 1.12, 1.22] },
  { name: 'D type (very red)', um: [0.75, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0], value: [0.88, 1.0, 1.2, 1.36, 1.5, 1.62, 1.74, 1.86, 1.98, 2.1] },
  { name: 'Comet (dust, ice, gas)', um: [0.75, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.26, 4.5, 5.0], value: [0.95, 1.0, 1.08, 1.14, 1.18, 1.05, 1.24, 1.3, 1.85, 1.38, 1.45] },
];
const interp = (xs: number[], ys: number[], x: number) => {
  for (let k = 1; k < xs.length; k++) if (x <= xs[k]) return ys[k - 1] + ((ys[k] - ys[k - 1]) * (x - xs[k - 1])) / (xs[k] - xs[k - 1]);
  return ys[ys.length - 1];
};

function closeApproach(el: Elements): { iso: string; dist_ld: number } | null {
  let best = Infinity, bestT = 0;
  for (let t = TODAY; t < TODAY + 365.25 * 15; t += 0.5) {
    const d = dist(positionAt(el, t), earthAt(t));
    if (d < best) { best = d; bestT = t; }
  }
  for (let t = bestT - 1; t < bestT + 1; t += 0.01) {
    const d = dist(positionAt(el, t), earthAt(t));
    if (d < best) { best = d; bestT = t; }
  }
  if (best > 0.2) return null;
  return { iso: iso(bestT), dist_ld: +((best * AU_KM) / LD_KM).toFixed(1) };
}

function cloud(el: Elements, sigmaDeg: number, shrink: number | null, seed: number) {
  const g = rng(seed);
  const dates = Array.from({ length: 16 }, (_, k) => TODAY - 120 + k * 90);
  const N = 160;
  const clones = Array.from({ length: N }, () => ({ dM: g.gauss(), da: g.gauss(), di: g.gauss(), dn: g.gauss() }));
  const make = (s: number) => dates.map((t) => clones.map((c) => r3(positionAt({
    ...el, M: el.M + c.dM * s, a: el.a * (1 + c.da * s * 0.0004), i: el.i + c.di * s * 0.05, node: el.node + c.dn * s * 0.05,
  }, t))));
  const spread = (pts: Vec3[][]) => {
    const last = pts[pts.length - 1];
    const m: Vec3 = [0, 0, 0];
    for (const p of last) for (let j = 0; j < 3; j++) m[j] += p[j] / last.length;
    return Math.sqrt(last.reduce((s, p) => s + dist(p, m) ** 2, 0) / last.length) * AU_KM;
  };
  const before = make(sigmaDeg);
  const after = shrink ? make(sigmaDeg / shrink) : null;
  return {
    dates_mjd: dates, before, after,
    before_sigma_km_at: { iso: iso(dates[dates.length - 1]), km: Math.round(spread(before)) },
    after_sigma_km_at: after ? { iso: iso(dates[dates.length - 1]), km: Math.round(spread(after)) } : null,
    note: 'Sample: clones drawn from made-up uncertainties around the real orbit. after = with the Rewind positions added; null if nothing measured.',
  };
}

const index = {
  schema: 'rewind-site-v1', generated: new Date().toISOString(), sample: true,
  headline_stats: { objects_searched: SHOW.length, found: 0, hints: 0, too_faint: 0, frames_read: 0 },
  benchmark: 'benchmark.json',
  objects: [] as unknown[], flash_events: [] as unknown[],
};

SHOW.forEach((s, si) => {
  const el = toEl(s.row);
  const base = `objects/${s.slug}/`;
  const flashMjd = s.flashMjd ?? (s.flashDaysBefore ? s.disc.mjd - s.flashDaysBefore : s.verdict === 'TOO_FAINT' ? s.disc.mjd - 70 : null);
  const g = rng(1000 + si);
  const stars = starField(77 + si);
  const frames: unknown[] = [], spx: Vec3[] = [], imgs: Float32Array[] = [], dayImgs: Float32Array[][] = [];
  const days: unknown[] = [];
  const hasPhotos = s.verdict !== 'NO_PHOTOS';
  if (hasPhotos && flashMjd) {
    const perFrame = s.verdict === 'TOO_FAINT' ? 1.0 : (s.snr / Math.sqrt(16)) * 4.5;
    let n = 0;
    for (let d = 0; d < 4; d++) {
      const dayMjd = flashMjd + d * 1.0 + (d > 1 ? 0.5 : 0);
      dayImgs.push([]);
      for (let k = 0; k < 4; k++, n++) {
        const t = dayMjd + k * 0.06;
        const obj = positionAt(el, t), obs = earthAt(t);
        const [ra, dec] = radec(obj, obs);
        // star field drifts past the object-centered stamp
        const img = render(stars, -(t - flashMjd) * 9, -(t - flashMjd) * 4, [{ x: S / 2 - 0.5, y: S / 2 - 0.5, f: perFrame * (0.8 + 0.4 * g.next()) }], 5000 + si * 100 + n);
        imgs.push(img);
        dayImgs[d].push(img);
        const png = `frames/f${String(n).padStart(3, '0')}.png`;
        writePng(base + png, S, S, toPng(img));
        const flux = +(perFrame * 1.7).toFixed(2), ferr = 1.7;
        frames.push({
          key: `sample-${s.slug}-${n}`, mjd: +t.toFixed(5), iso: iso(t), detector: 1 + (n % 6), wavelength_um: BANDS[(n * 5) % BANDS.length],
          pred_ra: ra, pred_dec: dec, sigma_px: +(0.4 + g.next() * 1.5).toFixed(2), flux_ujy: flux, flux_err: ferr,
          snr: +(flux / ferr + g.gauss() * 0.4).toFixed(2), flags: 0, used: g.next() > 0.08, png,
        });
        spx.push(r3(obs));
      }
      writePng(base + `days/d${d}.png`, S, S, toPng(mean(dayImgs[d])));
      days.push({ iso: iso(dayMjd), n_frames: 4, snr: +(s.snr / 2 + g.gauss() * 0.5).toFixed(1), png: `days/d${d}.png` });
    }
    writePng(base + 'stack.png', S, S, toPng(mean(imgs)));
    writePng(base + 'stack_median.png', S, S, toPng(median(imgs)));
    writePng(base + 'thumb.png', S, S, toPng(mean(imgs)));
    writePng(base + 'flash_01.png', S, S, toPng(mean(dayImgs[0])));
    writePng(base + 'quiz.png', S, S, toPng(mean(imgs)));
  } else {
    const img = render(stars, 0, 0, [], 9000 + si);
    writePng(base + 'thumb.png', S, S, toPng(img));
    writePng(base + 'quiz.png', S, S, toPng(img));
  }
  const isNeo = s.kind === 'neo' || (s.row.flag & 1) === 1;
  const ca = isNeo ? closeApproach(el) : null;
  const q = el.a * (1 - el.e), Q = el.a * (1 + el.e);
  const found = s.verdict === 'FOUND', hint = s.verdict === 'HINT';
  const comp = s.cls && hasPhotos && (found || hint) ? (() => {
    const t = TEMPLATES.find((x) => x.name.toLowerCase().startsWith(s.cls === 'comet' ? 'comet' : s.cls!.toLowerCase()))!;
    return BANDS.map((um) => {
      const err = +(0.04 + 0.5 / s.snr).toFixed(3);
      return { um, value: +(interp(t.um, t.value, um) + g.gauss() * err * 0.7).toFixed(3), err };
    });
  })() : [];
  const page = {
    schema: 'rewind-object-v1', slug: s.slug, name: s.name, kind: s.kind, verdict: s.verdict,
    verdict_text: verdictText(s), sample: true,
    story: { discovered_iso: iso(s.disc.mjd), by: s.disc.by, site: s.disc.site, plain: s.story, sources: s.sources },
    facts: {
      H: s.row.H, diameter_km: s.diameter, albedo: s.albedo, class: s.cls === 'comet' ? null : s.cls,
      neo: isNeo, pha: (s.row.flag & 2) === 2, sentry: !!s.sentry, moid_au: isNeo ? +Math.max(0.0005, (ca ? ca.dist_ld * LD_KM / AU_KM : 0.05)).toFixed(4) : null,
      next_close_approach: s.slug === 'apophis' ? { iso: '2029-04-13', dist_ld: 0.1 } : ca,
    },
    orbit: { epoch_mjd: EPOCH, a: s.row.a, e: s.row.e, i: s.row.i, node: s.row.node, peri: s.row.peri, M: s.row.M, q: +q.toFixed(5), Q: +Q.toFixed(5), period_yr: +Math.pow(el.a, 1.5).toFixed(3) },
    cloud: cloud(el, s.sigmaBeforeDeg, found ? 25 : hint ? 4 : null, 300 + si),
    spherex: {
      frames, days,
      stack: { png: 'stack.png', png_median: 'stack_median.png', snr: s.snr, ab_mag: +(19.5 + (10 - s.snr) * 0.15).toFixed(2), n_frames: frames.length },
      spherex_xyz_au_at_frames: spx,
    },
    checks: {
      null_paths: { n: 24, snr_mean: 0.1, snr_std: 1.0, n_exceeding: found ? 0 : hint ? 1 : 3 },
      time_shift: { shifts_days: [-2, -1, -0.5, 0, 0.5, 1, 2], snr: [0.3, 0.8, 2.6, s.snr, 2.4, 0.5, -0.2].map((v) => +v.toFixed(1)) },
      per_day_positive: found ? '4 of 4' : hint ? '3 of 4' : '1 of 4',
      static_sky_subtracted: { snr: +(s.snr * 0.92).toFixed(1) },
      injection: { limit_ab_mag: 20.8, recovered_fraction_at_object_mag: found ? 0.94 : hint ? 0.55 : 0.12 },
      orbit_fit: found ? { rms_arcsec_before: 0.48, rms_arcsec_after: 0.51, new_points: frames.length } : null,
      trail_px: +(g.next() * 1.5).toFixed(2),
      clone_search: s.kind === 'lost' ? { n_clones: 2000, false_alarm_rate: 0.03 } : null,
      real_or_fake_score: found ? 0.93 : hint ? 0.61 : null,
    },
    composition: { points: comp, templates: TEMPLATES, best_match: comp.length ? (s.cls === 'comet' ? 'Comet' : s.cls) : null, label: 'rough match' },
    quiz: { image: 'quiz.png', answer_xy: [S / 2, S / 2], answer_text: found ? 'Yes. The dot in the middle is the asteroid, exactly where its orbit says it should be.' : hint ? 'Maybe. There is a faint bump in the middle, but noise could do that too.' : 'No. Nothing stands out from the noise at the predicted spot.' },
    shape_model: null,
    credits: ['Sample data generated by the Rewind team for testing', 'Orbit: ' + (s.kind === 'comet' ? 'Minor Planet Center comet elements' : 'Minor Planet Center / JPL SBDB')],
  };
  writeJson(base + 'object.json', page);
  if (found) index.headline_stats.found++;
  if (hint) index.headline_stats.hints++;
  if (s.verdict === 'TOO_FAINT') index.headline_stats.too_faint++;
  index.headline_stats.frames_read += frames.length;
  const days_before = s.flashDaysBefore && (found || hint) ? s.flashDaysBefore : null;
  index.objects.push({
    slug: s.slug, name: s.name, kind: s.kind, verdict: s.verdict, verdict_text: page.verdict_text,
    discovered: { mjd: s.disc.mjd, iso: iso(s.disc.mjd), by: s.disc.by, site: s.disc.site },
    first_spherex_hint: days_before && flashMjd ? { mjd: flashMjd, iso: iso(flashMjd), days_before_discovery: days_before } : null,
    best_snr: s.snr, n_frames: frames.length, thumb: base + 'thumb.png', page: base + 'object.json',
  });
  if ((found || hint) && flashMjd) {
    index.flash_events.push({
      slug: s.slug, mjd: flashMjd, iso: iso(flashMjd), photo: base + 'flash_01.png',
      spherex_xyz_au: r3(earthAt(flashMjd)), object_xyz_au: r3(positionAt(el, flashMjd)),
      label: s.flashLabel ?? `SPHEREx photo, ${s.flashDaysBefore} days before discovery`,
    });
  }
});

function verdictText(s: Show): string {
  switch (s.verdict) {
    case 'FOUND': return s.kind === 'famous' ? 'Clearly seen in SPHEREx photos, right where its orbit predicts.' : `Clearly seen in SPHEREx photos ${s.flashDaysBefore} days before anyone found it.`;
    case 'HINT': return 'A faint spot in the right place, but not strong enough to be sure.';
    case 'TOO_FAINT': return 'SPHEREx looked at the right spot, but the object was too faint to see.';
    case 'NO_PHOTOS': return 'SPHEREx never photographed the right spot at the right time.';
    default: return 'Not searched yet.';
  }
}
writeJson('index.json', index);

// ---------- 6. benchmark ----------
const bcases = [
  ['2025 MA12', 'seen', 'FOUND', 8.1, 1.9], ['2025 OK3', 'seen', 'FOUND', 11.4, 1.2], ['2025 QP', 'seen', 'HINT', 4.2, 3.8],
  ['2025 RS9', 'seen', 'FOUND', 6.7, 2.4], ['2025 TJ', 'not seen', 'TOO_FAINT', 1.1, 0], ['2025 UQ1', 'seen', 'TOO_FAINT', 2.3, 0],
  ['2025 VB4', 'not seen', 'TOO_FAINT', 0.4, 0], ['2026 AF', 'seen', 'FOUND', 9.9, 1.5], ['2026 CE2', 'not seen', 'HINT', 4.0, 5.1],
  ['2026 DM', 'seen', 'FOUND', 13.2, 0.9], ['2026 FT1', 'not seen', 'TOO_FAINT', 0.8, 0], ['2026 GN', 'seen', 'HINT', 4.6, 2.9],
] as const;
const cases = bcases.map(([name, truth, v, snr, pe], k) => ({ name, hidden_until_iso: iso(60900 + k * 30), truth, rewind_verdict: v, snr, pos_err_arcsec: pe }));
const seen = cases.filter((c) => c.truth === 'seen');
const nFound = seen.filter((c) => c.rewind_verdict === 'FOUND').length;
const fa = cases.filter((c) => c.truth === 'not seen' && c.rewind_verdict === 'FOUND').length;
writeJson('benchmark.json', {
  sample: true, cases,
  summary: { n: cases.length, found: nFound, missed: seen.length - nFound, false_alarms: fa, plain: `Rewind found ${nFound} of ${seen.length} known cases, with ${fa} false alarms (sample numbers)` },
});

// ---------- 7. challenge stars ----------
const STARS = [
  ['barnard', "Barnard's Star", 269.452, 4.693, -802.8, 10362.5, 'Moves 10.4 arcsec per year, about 1.7 pixels per year'],
  ['wise0855', 'WISE 0855-0714', 133.786, -7.244, -8123.7, 673.4, 'Moves 8.1 arcsec per year, about 1.3 pixels per year'],
  ['epsindib', 'Epsilon Indi B', 330.84, -56.79, 3961.4, -2538.3, 'Moves 4.7 arcsec per year, about 0.8 pixels per year'],
  ['rwaur', 'RW Aurigae', 76.956, 30.401, 3.9, -26.3, 'Barely moves. Watch its brightness change instead'],
  ['rdra', 'R Draconis', 246.97, 66.75, -6.6, 16.6, 'Barely moves. A pulsating star that changes brightness over months'],
] as const;
STARS.forEach(([slug, name, ra, dec, pmra, pmdec, cap], k) => {
  const stars = starField(400 + k, 22);
  const pxPerYr = Math.hypot(pmra, pmdec) / 1000 / 6.2;
  const ang = Math.atan2(pmdec, pmra);
  const frames: unknown[] = [], seasons: unknown[] = [];
  const imgs: Float32Array[] = [];
  const t0 = mjdOf('2025-05-01');
  for (let n = 0; n < 12; n++) {
    const t = t0 + n * 45 + (n % 2) * 3;
    const yr = (t - t0) / 365.25;
    // magnify motion x4 in the sample so it is visible over 1.5 years
    const x = S / 2 - Math.cos(ang) * pxPerYr * yr * 4, y = S / 2 - Math.sin(ang) * pxPerYr * yr * 4;
    const varAmp = slug === 'rdra' || slug === 'rwaur' ? 1 + 0.6 * Math.sin(n * 0.9) : 1;
    const img = render(stars, 0, 0, [{ x, y, f: 260 * varAmp }], 7000 + k * 50 + n);
    imgs.push(img);
    const png = `frames/f${String(n).padStart(2, '0')}.png`;
    writePng(`stars/${slug}/${png}`, S, S, toPng(img));
    frames.push({ iso: iso(t), mjd: t, wavelength_um: BANDS[(n * 7) % BANDS.length], png, pred_xy: [+x.toFixed(2), +y.toFixed(2)] });
  }
  for (let ss = 0; ss < 3; ss++) {
    writePng(`stars/${slug}/seasons/s${ss}.png`, S, S, toPng(mean(imgs.slice(ss * 4, ss * 4 + 4))));
    seasons.push({ iso: iso(t0 + ss * 180), png: `seasons/s${ss}.png` });
  }
  writePng(`stars/${slug}/stack.png`, S, S, toPng(mean(imgs)));
  writeJson(`stars/${slug}/manifest.json`, {
    sample: true, slug, name, ra, dec, pm: { ra_mas_yr: pmra, dec_mas_yr: pmdec }, seasons, frames,
    stack: { png: 'stack.png', snr: 140 }, motion_caption: cap,
    note: 'Sample: synthetic noise images. Real SPHEREx cutouts replace these when the engine runs. Motion is exaggerated 4 times in this sample.',
  });
});

// ---------- 8. detectives (rounds.json v2: 5 photos of one fixed patch, the mover's place in each) ----------
const truths = ['planted', 'known', 'empty', 'planted', 'known', 'empty', 'planted', 'empty', 'known', 'planted', 'empty', 'known'] as const;
const explain = {
  known: 'The dot that moves is a known asteroid: it crossed a few pixels while the stars stayed put.',
  planted: 'A trick: we added a fake moving dot to the photos. Rewind plants fakes like this to measure how faint it can see.',
  empty: "Nothing moves here: the dots are stars that stay put. 'Nothing' is the right answer.",
};
const rounds = truths.map((truth, k) => {
  const stars = starField(900 + k, 30);
  const g = rng(1200 + k);
  const id = `r${String(k + 1).padStart(2, '0')}`;
  const x0 = 14 + g.next() * 30, y0 = 18 + g.next() * 28, vx = 2 + g.next() * 2.5, vy = -2 + g.next() * 4;
  const f = 20 - k + g.next() * 6; // later rounds are fainter
  const frames = [0, 1, 2, 3, 4].map((n) => {
    const dots = truth === 'empty' ? [] : [{ x: x0 + vx * n, y: y0 + vy * n, f }];
    writePng(`detectives/${id}_${n}.png`, S, S, toPng(render(stars, 0, 0, dots, 8000 + k * 10 + n)));
    return { png: `${id}_${n}.png`, iso: new Date((61300 + k + n * 0.13 - 40587) * 86400000).toISOString().slice(0, 19), wavelength_um: +(0.8 + g.next() * 4).toFixed(2) };
  });
  const track_xy = truth === 'empty' ? null : frames.map((_, n) => [+(x0 + vx * n).toFixed(1), +(y0 + vy * n).toFixed(1)]);
  return { id, truth, frames, track_xy, tolerance_px: 6, explain: explain[truth], difficulty: k < 4 ? 'easy' : k < 8 ? 'medium' : 'hard', reveal_after_answer: true };
});
writeJson('detectives/rounds.json', {
  schema: 'rewind-detectives-v2', version: 2, sample: true,
  real_rounds_note: "No 'real' rounds: every Rewind find is visible only in stacks of many photos, so a person could not see it move.",
  rounds,
});

console.log('sample written to', OUT);
