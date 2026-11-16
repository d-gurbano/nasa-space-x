// The ?demo=1 film as pure functions of time t (seconds): the shot list, the captions, the clock
// and the camera path. Everything the film says is read from the data (see demoFacts).
// Camera rule: never closer than the ORBIT framing (Sun, Earth's orbit and the object's orbit on screen).
import type { IndexObject, ObjectPage } from '../lib/types';
import { daysBefore, isKnown, tally } from '../lib/rank';
import { mjdFromIso, plainDate } from '../lib/time';

export const DURATION = 28;

export type ShotId = 'title' | 'discover' | 'rewind' | 'flash' | 'stack' | 'cloud' | 'map' | 'end';
export const SHOTS: { id: ShotId; from: number; to: number }[] = [
  { id: 'title', from: 0, to: 3.5 },
  { id: 'discover', from: 3.5, to: 8 },
  { id: 'rewind', from: 8, to: 9.8 },
  { id: 'flash', from: 9.8, to: 13 },
  { id: 'stack', from: 13, to: 17 },
  { id: 'cloud', from: 17, to: 22 },
  { id: 'map', from: 22, to: 26 },
  { id: 'end', from: 26, to: DURATION },
];

export const shotAt = (t: number): ShotId => (SHOTS.find((s) => t < s.to) ?? SHOTS[SHOTS.length - 1]).id;

// moments inside shots
export const T = {
  orbitIn: 7, // camera settled on the orbit framing
  flash: 9.8,
  daysFrom: 13.2, // first day photo lights up
  dayStep: 0.22,
  merge: 16.1, // day photos merge into the stack
  shrinkFrom: 19.2,
  shrinkTo: 20.2,
  orbitOut: 21.6, // start of the pull back to the whole map
  wide: 25,
};

export interface DemoFacts {
  slug: string;
  name: string;
  discoveredIso: string;
  hazardous: boolean;
  daysBefore: number; // days_before_first_known_obs
  earliestMjd: number; // the first SPHEREx photo before anyone knew
  stackFrames: number;
  snr: number | null;
  dayPngs: string[];
  cloud: { beforeKm: number; afterKm: number; factor: number; atIso: string; label: string } | null;
  searched: number;
  found: number;
  foundBefore: number;
  findSlugs: string[];
}

/** The documented at-discovery scenario (docs/IMPACT.md), used only if the object file has none. */
export const DOC_SCENARIO = { beforeKm: 3_500_000, afterKm: 1_100_000, factor: 3.2 };
export const MOON_KM = 384_400;

interface Scenario {
  sigma3_km_before?: number;
  sigma3_km_after?: number;
  factor?: number;
  at_iso?: string;
}

export function demoFacts(objects: IndexObject[], o: IndexObject, p: ObjectPage): DemoFacts {
  const t = tally(objects);
  // the engine writes more impact fields than the shared type names
  const imp = p.impact as { earliest_spherex_day_iso?: string; at_discovery_scenario?: Scenario | null } | null | undefined;
  const s = imp?.at_discovery_scenario;
  const before = s?.sigma3_km_before, after = s?.sigma3_km_after;
  const early = o.first_spherex_hint?.mjd ?? mjdFromIso(imp?.earliest_spherex_day_iso ?? o.discovered.iso);
  return {
    slug: o.slug,
    name: p.name ?? o.name,
    discoveredIso: o.discovered.iso,
    hazardous: !!(p.facts as { pha?: boolean } | undefined)?.pha,
    daysBefore: daysBefore(o) ?? Math.round(mjdFromIso(o.discovered.iso) - early),
    earliestMjd: early,
    stackFrames: p.spherex?.stack?.n_frames ?? 0,
    snr: p.spherex?.stack?.snr ?? o.best_snr ?? null,
    dayPngs: (p.spherex?.days ?? []).map((d) => d.png),
    cloud:
      before && after
        ? { beforeKm: before, afterKm: after, factor: s?.factor ?? before / after, atIso: s?.at_iso ?? '', label: 'computed: if run on discovery day' }
        : { ...DOC_SCENARIO, atIso: '', label: 'computed: if run on discovery day' },
    searched: t.searched,
    found: t.found,
    foundBefore: t.before,
    findSlugs: objects.filter((x) => x.verdict === 'FOUND' && !isKnown(x)).map((x) => x.slug),
  };
}

export const millionKm = (km: number) => `±${(km / 1e6).toFixed(1)} million km`;
export const moons = (km: number) => Math.max(1, Math.round(km / MOON_KM));

export type CapId = 'title' | 'discover' | 'rewind' | 'flash' | 'stack' | 'cloud' | 'sharper' | 'map' | 'end';
/** One caption at a time: [from, to) in seconds. Gaps let the 300 ms fade finish. */
export const CAPTIONS: { id: CapId; from: number; to: number }[] = [
  { id: 'title', from: 0.3, to: 3.3 },
  { id: 'discover', from: 3.8, to: 7.8 },
  { id: 'rewind', from: 8.0, to: 9.6 },
  { id: 'flash', from: 9.9, to: 12.8 },
  { id: 'stack', from: 13.1, to: 16.8 },
  { id: 'cloud', from: 17.1, to: 20.0 },
  { id: 'sharper', from: 20.3, to: 21.8 },
  { id: 'map', from: 22.4, to: 25.8 },
  { id: 'end', from: 26.2, to: Infinity },
];
export const captionAt = (t: number): CapId | null => CAPTIONS.find((c) => t >= c.from && t < c.to)?.id ?? null;

/** Caption HTML (text only from the data). */
export function captionHtml(id: CapId, f: DemoFacts): string {
  switch (id) {
    case 'title':
      return 'Every discovery has a <em>past.</em>';
    case 'discover':
      return `<span class="dm-kick">Discovery</span>${plainDate(f.discoveredIso)}: astronomers discover ${f.name}.${f.hazardous ? '<span class="dm-chip">Potentially hazardous</span>' : ''}`;
    case 'rewind':
      return `<span class="dm-kick">Rewind</span><span class="dm-date"></span>`;
    case 'flash':
      return `<span class="dm-kick">${plainDate(f.earliestMjd)}</span>NASA's SPHEREx had already imaged it. <em>${f.daysBefore} days earlier.</em>`;
    case 'stack':
      return `<span class="dm-kick">Shift-and-stack</span>${f.stackFrames} images, co-added along its path. <em>The signal appears.</em>`;
    case 'cloud':
      return `<span class="dm-kick">Orbit uncertainty</span>3σ position one year after discovery, from the first week of observations.`;
    case 'sharper':
      return `<span class="dm-big">${Math.round(f.cloud!.factor)}× smaller.</span><span class="dm-sub">with the SPHEREx precovery positions</span>`;
    case 'map':
      return `<span class="dm-stats"><span><b>${f.searched}</b> comets and asteroids searched.</span><span><b>${f.found}</b> FOUND in SPHEREx images.</span><span><b>${f.foundBefore}</b> before their first known observation.</span></span>`;
    case 'end':
      return '';
  }
}

// ---------- easing ----------
export const quint = (k: number) => (k < 0.5 ? 16 * k ** 5 : 1 - (-2 * k + 2) ** 5 / 2);
export const cubicOut = (k: number) => 1 - (1 - k) ** 3;
export const cubic = (k: number) => (k < 0.5 ? 4 * k ** 3 : 1 - (-2 * k + 2) ** 3 / 2);
export const clamp01 = (k: number) => Math.min(1, Math.max(0, k));
/** 0 before a, 1 after b, eased in between. */
export const ramp = (t: number, a: number, b: number, ease = quint) => ease(clamp01((t - a) / (b - a)));

/** The clock: today, fast rewind to discovery, faster rewind to the first photo, back to today. */
export function mjdAt(t: number, today: number, discovered: number, early: number): number {
  if (t < 3.5) return today - (3.5 - t) * 2;
  if (t < 8) return today + (discovered - today) * ramp(t, 3.5, 6.5);
  if (t < T.flash) return discovered + (early - discovered) * ramp(t, 8, 9.5, cubicOut);
  if (t < 22) return early;
  return early + (today - early) * ramp(t, 22, 24.5) + Math.max(0, t - 24.5) * 2;
}

// ---------- camera ----------
export interface Pose {
  target: [number, number, number];
  az: number; // radians around +y, 0 = +x
  el: number; // radians above the planets' plane
  dist: number;
}

export const SYSTEM: Pose = { target: [0, 0, 0], az: Math.PI / 2, el: (30 * Math.PI) / 180, dist: 5.2 };
export const WIDE: Pose = { target: [0, 0, 0], az: Math.PI / 2, el: (40 * Math.PI) / 180, dist: 6.4 };
/** Smallest allowed distance: the frame is always at least ~3 AU tall at fov 45. */
export const MIN_DIST = 3.4;

/** Orbit framing: fit a bounding sphere of the given points (AU, three.js axes), from 35 degrees up. */
export function orbitPose(points: [number, number, number][], obj: [number, number, number], fovDeg: number, aspect: number): Pose {
  let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity, z0 = Infinity, z1 = -Infinity;
  for (const [x, y, z] of points) {
    x0 = Math.min(x0, x); x1 = Math.max(x1, x);
    y0 = Math.min(y0, y); y1 = Math.max(y1, y);
    z0 = Math.min(z0, z); z1 = Math.max(z1, z);
  }
  const c: [number, number, number] = [(x0 + x1) / 2, ((y0 + y1) / 2) * 0.5, (z0 + z1) / 2];
  let r = 0;
  for (const [x, y, z] of points) r = Math.max(r, Math.hypot(x - c[0], y - c[1], z - c[2]));
  const half = (fovDeg * Math.PI) / 360;
  const fit = Math.min(half, Math.atan(Math.tan(half) * aspect));
  // a little smaller than the sphere fit: seen from 35 degrees up, the flat orbits look shorter
  const dist = Math.max(MIN_DIST, (r / Math.sin(fit)) * 0.82);
  return { target: c, az: Math.atan2(obj[2] - c[2], obj[0] - c[0]) + 0.45, el: (35 * Math.PI) / 180, dist };
}

const lerp = (a: number, b: number, k: number) => a + (b - a) * k;
const angLerp = (a: number, b: number, k: number) => {
  let d = (b - a) % (Math.PI * 2);
  if (d > Math.PI) d -= Math.PI * 2;
  if (d < -Math.PI) d += Math.PI * 2;
  return a + d * k;
};
function mix(a: Pose, b: Pose, k: number): Pose {
  return {
    target: [lerp(a.target[0], b.target[0], k), lerp(a.target[1], b.target[1], k), lerp(a.target[2], b.target[2], k)],
    az: angLerp(a.az, b.az, k),
    el: lerp(a.el, b.el, k),
    dist: Math.exp(lerp(Math.log(a.dist), Math.log(b.dist), k)),
  };
}

/** Camera pose at t: eased dollies between system, orbit and wide framings, plus a slow constant orbit. */
export function poseAt(t: number, orbit: Pose): Pose {
  let p: Pose;
  if (t < 3.5) p = SYSTEM;
  else if (t < T.orbitIn) p = mix(SYSTEM, orbit, ramp(t, 3.5, T.orbitIn, cubic));
  else if (t < T.orbitOut) p = orbit;
  else p = mix(orbit, WIDE, ramp(t, T.orbitOut, T.wide, cubic));
  return {
    ...p,
    az: p.az - 0.028 * t, // never still: a slow turn around the Sun
    el: p.el + 0.05 * Math.sin((t / DURATION) * Math.PI * 2),
  };
}

export const poseToCamera = (p: Pose): [number, number, number] => [
  p.target[0] + p.dist * Math.cos(p.el) * Math.cos(p.az),
  p.target[1] + p.dist * Math.sin(p.el),
  p.target[2] + p.dist * Math.cos(p.el) * Math.sin(p.az),
];
