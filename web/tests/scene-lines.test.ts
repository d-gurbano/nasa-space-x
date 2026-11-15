// The drawn orbit lines against the drawn objects, on the real data in public/data:
// the selected object's close-up line through its body, and the GPU crowd dots on the CPU lines.
import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { basis, DEG, meanMotion, orbitPolyline, type Elements, type Vec3 } from '../src/lib/kepler';
import { cloudPosition, dotPosition, focusPath, orbitPath, type OrbitBody, type OrbitPath } from '../src/scene/orbits';

const DATA = 'public/data/';
const json = (f: string) => JSON.parse(readFileSync(DATA + f, 'utf8'));

function toSegment(p: Vec3, a: Vec3, b: Vec3): number {
  const ab = [b[0] - a[0], b[1] - a[1], b[2] - a[2]], ap = [p[0] - a[0], p[1] - a[1], p[2] - a[2]];
  const len2 = ab[0] ** 2 + ab[1] ** 2 + ab[2] ** 2;
  const t = len2 > 0 ? Math.min(1, Math.max(0, (ap[0] * ab[0] + ap[1] * ab[1] + ap[2] * ab[2]) / len2)) : 0;
  return Math.hypot(ap[0] - ab[0] * t, ap[1] - ab[1] * t, ap[2] - ab[2] * t);
}

/** World-space vertices of a path as the scene draws it: the float32 offsets added to the dot. */
const world = (path: OrbitPath): Vec3[] =>
  Array.from({ length: path.u.length }, (_, k) => [0, 1, 2].map((j) => path.origin[j] + path.rel[k * 3 + j]) as Vec3);

const toLine = (p: Vec3, pts: Vec3[]) => pts.slice(1).reduce((m, b, k) => Math.min(m, toSegment(p, pts[k], b)), Infinity);

function pageBody(slug: string): OrbitBody {
  const p = json(`objects/${slug}/object.json`);
  return { el: p.orbit, track: p.cloud?.before?.length ? { dates: p.cloud.dates_mjd, nominal: p.cloud.before.map((c: Vec3[]) => c[0]) } : undefined };
}

describe('close-up: the selected orbit runs through the body', () => {
  // the smallest close-up body is 1.2e-5 AU across (main.ts): the line must pass within 1% of that
  const TOL = 1.2e-7;
  for (const slug of ['2025yh5', '2025st20', '2024yr4']) {
    it(slug, () => {
      const body = pageBody(slug);
      for (const mjd of [60900.25, 61010.5, 61190]) {
        const path = focusPath(body, mjd);
        const at = dotPosition(body, mjd);
        const pts = world(path);
        expect(toLine(at, pts)).toBeLessThan(TOL);
        // dense next to the body, so the line stays straight and on it however far one zooms in
        const h = path.head;
        expect(Math.hypot(...([0, 1, 2].map((j) => pts[h + 1][j] - pts[h][j]) as Vec3))).toBeLessThan(1.2e-6);
        // the old full-orbit polyline (no track correction, uniform segments) can miss by more
        const old = orbitPolyline(body.el, 720, 40);
        expect(toLine(at, old)).toBeGreaterThanOrEqual(toLine(at, pts));
      }
    });
  }
});

describe('home map: GPU crowd dots sit on the CPU lines', () => {
  const meta = json('orbits.bin.json');
  const buf = readFileSync(DATA + 'orbits.bin');
  const d = new Float32Array(buf.buffer, buf.byteOffset, buf.byteLength / 4);
  const F = meta.fields.length, col = (n: string) => meta.fields.indexOf(n);
  const rows: [string, number][] = Object.entries(meta.slugs as Record<string, number>).filter(([, r]) => d[r * F + col('e')] < 0.995 && d[r * F + col('a')] > 0);
  // 20 objects, picked by a fixed seed
  let s = 7;
  const rnd = () => ((s = (s * 16807) % 2147483647) / 2147483647);
  const pick = Array.from({ length: 20 }, () => rows.splice(Math.floor(rnd() * rows.length), 1)[0]);

  for (const [slug, r] of pick) {
    it(slug, () => {
      const g = (n: string) => d[r * F + col(n)];
      const el: Elements = { a: g('a'), e: g('e'), i: g('i'), node: g('node'), peri: g('peri'), M: g('M'), epoch_mjd: meta.epoch_mjd };
      // exactly what AsteroidCloud uploads for this row
      const b = basis(el.i, el.node, el.peri);
      const orb = Float32Array.of(el.a, el.e, el.M * DEG, meanMotion(el.a));
      for (const mjd of [60800, 61200.5, 61720.75]) {
        const gpu = cloudPosition(orb, Float32Array.from(b.P), Float32Array.from(b.Q), mjd - meta.epoch_mjd);
        const line = world(orbitPath({ el }, mjd, 96));
        // a millionth of an AU (150 km): far below a pixel, even at the closest map zoom
        expect(toLine(gpu, line)).toBeLessThan(1e-6);
      }
    });
  }
});
