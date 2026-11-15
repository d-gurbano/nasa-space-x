import { describe, expect, it } from 'vitest';
import { readFileSync, existsSync } from 'node:fs';
import { join } from 'node:path';
import { loadIndex, loadOrbits, resolveRel, type Fetcher } from '../src/lib/data';

const PUB = join(__dirname, '..', 'public');

// Serves files from public/, like the dev server: missing files return index.html with 200.
function fakeFetch(missing: string[] = []): Fetcher {
  return async (url: string) => {
    const p = join(PUB, url);
    if (missing.some((m) => url.startsWith(m)) || !existsSync(p)) return new Response('<!doctype html><html></html>', { status: 200 });
    return new Response(readFileSync(p));
  };
}

describe('data loading', () => {
  it('falls back to data-sample when data/ is missing (even if the server answers with HTML)', async () => {
    const src = await loadIndex(fakeFetch(['data/']));
    expect(src.base).toBe('data-sample/');
    expect(src.sample).toBe(true);
    expect(src.index.schema).toBe('rewind-site-v1');
    expect(src.index.objects.length).toBeGreaterThan(0);
  });
  it('resolves paths relative to the JSON file', () => {
    expect(resolveRel('data-sample/index.json', 'objects/x/object.json')).toBe('data-sample/objects/x/object.json');
    expect(resolveRel('data-sample/objects/x/object.json', 'frames/f0.png')).toBe('data-sample/objects/x/frames/f0.png');
  });
  it('loads the binary orbits and matches the JSON rows', async () => {
    const bin = await loadOrbits('data-sample/', fakeFetch());
    const js = await loadOrbits('data-sample/', fakeFetch(['data-sample/orbits.bin']));
    expect(bin.count).toBe(js.count);
    expect(bin.count).toBeGreaterThan(50000);
    expect(bin.fields).toEqual(['a', 'e', 'i', 'node', 'peri', 'M', 'H', 'flag']);
    for (const k of [0, 1234, bin.count - 1]) {
      for (let f = 0; f < 8; f++) expect(bin.data[k * 8 + f]).toBeCloseTo(js.data[k * 8 + f], 4);
    }
  });
  it('every sample file is marked sample', () => {
    const idx = JSON.parse(readFileSync(join(PUB, 'data-sample/index.json'), 'utf8'));
    expect(idx.sample).toBe(true);
    for (const o of idx.objects) expect(JSON.parse(readFileSync(join(PUB, 'data-sample', o.page), 'utf8')).sample).toBe(true);
  });
});

describe('planets', () => {
  it('normalizes the engine JPL-style rows and our flat rows to the same values', async () => {
    const { normalizePlanet } = await import('../src/lib/data');
    const jpl = { name: 'Mercury', a: 0.38709927, e: 0.20563593, I: 7.00497902, L: 252.2503235, long_peri: 77.45779628, long_node: 48.33076593,
      rates: { a: 3.7e-7, e: 1.906e-5, I: -0.00594749, L: 149472.67411175, long_peri: 0.16047689, long_node: -0.12534081 } };
    const flat = { name: 'Mercury', a: 0.38709927, a_rate: 3.7e-7, e: 0.20563593, e_rate: 1.906e-5, i: 7.00497902, i_rate: -0.00594749,
      L: 252.2503235, L_rate: 149472.67411175, varpi: 77.45779628, varpi_rate: 0.16047689, node: 48.33076593, node_rate: -0.12534081 };
    expect(normalizePlanet(jpl)).toEqual(normalizePlanet(flat));
  });
});
