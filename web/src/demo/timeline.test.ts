import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import type { IndexObject, ObjectPage, SiteIndex } from '../lib/types';
import { CAPTIONS, DURATION, MIN_DIST, SHOTS, captionAt, captionHtml, demoFacts, mjdAt, orbitPose, poseAt, poseToCamera } from './timeline';

const data = (p: string) => JSON.parse(readFileSync(new URL('../../public/data/' + p, import.meta.url), 'utf8'));
const idx: SiteIndex = data('index.json');
const yh5 = idx.objects.find((o) => o.slug === '2025yh5') as IndexObject;
const page: ObjectPage = data('objects/2025yh5/object.json');
const text = (html: string) => html.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ');

describe('demo schedule', () => {
  it('shots tile 0..28 s with no gaps', () => {
    expect(SHOTS[0].from).toBe(0);
    expect(SHOTS.at(-1)!.to).toBe(DURATION);
    expect(DURATION).toBe(28);
    for (let i = 1; i < SHOTS.length; i++) expect(SHOTS[i].from).toBe(SHOTS[i - 1].to);
  });

  it('shows one caption at a time, with room for the 300 ms fade', () => {
    for (let i = 1; i < CAPTIONS.length; i++) expect(CAPTIONS[i].from - CAPTIONS[i - 1].to).toBeGreaterThanOrEqual(0.2);
    expect(captionAt(1)).toBe('title');
    expect(captionAt(10.5)).toBe('flash');
    expect(captionAt(27)).toBe('end');
  });

  it('never brings the camera closer than the orbit framing, and never snaps', () => {
    const orbit = orbitPose([[0, 0, 0], [1, 0, 0], [-1, 0, 0], [0, 0, 1.6], [0, 0, -1]], [0, 0, 1.6], 45, 16 / 9);
    let prev = poseToCamera(poseAt(0, orbit));
    for (let t = 0; t <= DURATION; t += 1 / 60) {
      const p = poseAt(t, orbit);
      expect(p.dist).toBeGreaterThanOrEqual(Math.min(orbit.dist, MIN_DIST) - 1e-9);
      const c = poseToCamera(p);
      expect(Math.hypot(c[0] - prev[0], c[1] - prev[1], c[2] - prev[2])).toBeLessThan(0.08); // per frame at 60 fps
      prev = c;
    }
  });

  it('the clock rewinds to the first SPHEREx photo for the flash', () => {
    const f = demoFacts(idx.objects, yh5, page);
    expect(mjdAt(11, 61360, 61029, f.earliestMjd)).toBe(f.earliestMjd);
    expect(mjdAt(5, 61360, 61029, f.earliestMjd)).toBeLessThan(61360);
  });
});

describe('demo numbers come from the data', () => {
  const f = demoFacts(idx.objects, yh5, page);

  it('reads days, photo count and counts', () => {
    expect(f.daysBefore).toBe(yh5.days_before_first_known_obs);
    expect(f.stackFrames).toBe(page.spherex.stack.n_frames);
    expect(f.dayPngs).toHaveLength(page.spherex.days.length);
    expect(f.searched).toBe(idx.objects.length);
    expect(text(captionHtml('flash', f))).toContain(`${f.daysBefore} days before its first known observation`);
    expect(text(captionHtml('stack', f))).toContain(`${f.stackFrames} images`);
    const map = text(captionHtml('map', f));
    for (const n of [f.searched, f.found, f.foundBefore]) expect(map).toContain(String(n));
  });

  it('uses the at-discovery scenario from object.json', () => {
    const s = (page.impact as any).at_discovery_scenario;
    expect(f.cloud!.beforeKm).toBe(s.sigma3_km_before);
    expect(f.cloud!.afterKm).toBe(s.sigma3_km_after);
    expect(text(captionHtml('sharper', f))).toContain(`${Math.round(s.factor)}× smaller`);
  });

  it('follows the data when it changes, nothing is hard-coded', () => {
    const o = { ...yh5, days_before_first_known_obs: 12 };
    const p = { ...page, impact: { at_discovery_scenario: { sigma3_km_before: 4e6, sigma3_km_after: 1e6, factor: 4 } } } as unknown as ObjectPage;
    const g = demoFacts(idx.objects.slice(0, 50), o, p);
    expect(text(captionHtml('flash', g))).toContain('12 days before its first known observation');
    expect(text(captionHtml('sharper', g))).toContain('4× smaller');
    expect(g.searched).toBe(50);
  });

  it('has no em dashes in any caption', () => {
    for (const c of CAPTIONS) expect(captionHtml(c.id, f)).not.toMatch(/—/);
  });
});
