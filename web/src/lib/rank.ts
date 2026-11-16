// Ordering of Rewind objects, the choice of the "best" flash for the guided demo, and the
// grouping of flash marks on the time bar.
import type { FlashEvent, IndexObject, SiteIndex } from './types';
import { mjdFromIso } from './time';

const ORDER: Record<string, number> = { FOUND: 0, HINT: 1, TOO_FAINT: 2, NO_PHOTOS: 3, PENDING: 4 };

/** Known objects (like Eros) are shown to demonstrate SPHEREx, not as finds before discovery. */
export function isKnown(o: Pick<IndexObject, 'kind'>): boolean {
  return o.kind === 'famous';
}

/** FOUND first (new finds before known objects), then HINT, TOO_FAINT, NO_PHOTOS; stronger signal first. */
export function rankObjects<T extends Pick<IndexObject, 'verdict' | 'kind' | 'best_snr' | 'name'>>(list: T[]): T[] {
  return [...list].sort(
    (a, b) =>
      (ORDER[a.verdict] ?? 9) - (ORDER[b.verdict] ?? 9) ||
      Number(isKnown(a)) - Number(isKnown(b)) ||
      (b.best_snr ?? -99) - (a.best_snr ?? -99) ||
      a.name.localeCompare(b.name),
  );
}

type Early = Pick<IndexObject, 'discovered' | 'first_spherex_hint' | 'first_known_obs_iso' | 'days_before_first_known_obs'>;

/** When anyone first had the object (MJD): the first known observation if the engine gives it, else the discovery date. */
export function knownSince(o: Pick<Early, 'discovered' | 'first_known_obs_iso'>): number {
  return o.first_known_obs_iso ? mjdFromIso(o.first_known_obs_iso) : o.discovered.mjd;
}

/** What "N days before" counts to, in the data's words. */
export function beforeWhat(o: Pick<Early, 'discovered' | 'first_known_obs_iso'>): string {
  return o.first_known_obs_iso && o.first_known_obs_iso.slice(0, 10) !== o.discovered.iso.slice(0, 10) ? 'the first known observation' : 'discovery';
}

/**
 * Days from the first SPHEREx photo to the moment anyone had the object; null when the photos
 * are not earlier. The engine's count to the first known observation wins when it is given:
 * photos taken after it are extra positions, not a find before discovery.
 */
export function daysBefore(o: Pick<Early, 'first_spherex_hint' | 'days_before_first_known_obs'>): number | null {
  if (o.days_before_first_known_obs !== undefined) return o.days_before_first_known_obs;
  return o.first_spherex_hint?.days_before_discovery ?? null;
}

/** A new find whose photos are not earlier than the first known observation (like C/2025 W2). */
export function seenNotEarlier(o: Pick<IndexObject, 'verdict' | 'kind' | 'first_spherex_hint' | 'days_before_first_known_obs'>): boolean {
  return o.verdict === 'FOUND' && !isKnown(o) && daysBefore(o) == null;
}

/** Counts for the results card and the opening. Known objects that SPHEREx sees are not finds. */
export function tally(objects: Pick<IndexObject, 'verdict' | 'kind' | 'first_spherex_hint' | 'days_before_first_known_obs'>[]) {
  const n = (f: (o: (typeof objects)[number]) => boolean) => objects.filter(f).length;
  const finds = objects.filter((o) => o.verdict === 'FOUND' && !isKnown(o));
  return {
    searched: objects.length,
    found: finds.length,
    // finds with a photo from before anyone had the object
    before: finds.filter((o) => (daysBefore(o) ?? -1) >= 0).length,
    // only say "before discovery" when every find really has such a photo
    allBefore: finds.every((o) => (daysBefore(o) ?? -1) >= 0),
    known: n((o) => o.verdict === 'FOUND' && isKnown(o)),
    hints: n((o) => o.verdict === 'HINT'),
    tooFaint: n((o) => o.verdict === 'TOO_FAINT'),
    noPhotos: n((o) => o.verdict === 'NO_PHOTOS'),
    pending: n((o) => o.verdict === 'PENDING'),
  };
}

/** SPHEREx photos read: the sum over the objects shown, so it never lags behind headline_stats. */
export function framesRead(objects: Pick<IndexObject, 'n_frames'>[]): number {
  return objects.reduce((s, o) => s + (o.n_frames ?? 0), 0);
}

/** "2 of them are potentially hazardous asteroids (...), per JPL." from the finds' object pages (facts.pha). */
export function phaLine(pages: ({ name: string; facts?: { pha?: boolean } | null } | null)[]): string {
  const names = pages.filter((p) => p?.facts?.pha).map((p) => p!.name);
  if (!names.length) return '';
  const what = names.length === 1 ? 'is a potentially hazardous asteroid' : 'are potentially hazardous asteroids';
  return `${names.length} of them ${what} (${names.join(', ')}), per JPL.`;
}

export interface Showcase {
  object: IndexObject;
  flash: FlashEvent;
  sure: boolean; // FOUND (true) or only a HINT (false)
  score: number; // S/N of that one photo
}

/**
 * The object for the guided rewind and the demo, chosen from index.json each time:
 * FOUND before HINT, never a known object, needs a SPHEREx photo from before anyone had it.
 * The object whose single best such photo has the highest S/N wins, and that photo is the flash:
 * a visitor sees one photo, so a clear one beats a strong stack of faint ones.
 */
export function pickShowcase(idx: Pick<SiteIndex, 'objects' | 'flash_events'>, prefer?: string | null): Showcase | null {
  const pre = (o: IndexObject) => idx.flash_events.filter((f) => f.slug === o.slug && f.before_first_known_obs !== false && f.mjd < knownSince(o));
  const best = (fs: FlashEvent[]) => fs.reduce((b, f) => ((f.snr ?? 0) > (b.snr ?? 0) ? f : b));
  for (const verdict of ['FOUND', 'HINT'] as const) {
    let cands = idx.objects.filter((o) => o.verdict === verdict && !isKnown(o) && pre(o).length);
    if (prefer && cands.some((o) => o.slug === prefer)) cands = cands.filter((o) => o.slug === prefer);
    if (!cands.length) continue;
    const scored = cands.map((o) => ({ o, flash: best(pre(o)) })).sort((a, b) => (b.flash.snr ?? 0) - (a.flash.snr ?? 0));
    const { o, flash } = scored[0];
    return { object: o, flash, sure: verdict === 'FOUND', score: flash.snr ?? 0 };
  }
  return null;
}

/** One mark on the time bar: photos first..last of the date-sorted list; best is the one it stands for. */
export interface Mark { first: number; last: number; best: number }

/**
 * Group date-sorted positions (px) into marks: a photo joins the mark before it while the
 * mark stays narrower than `gap`. `better(a, b)` says whether photo a should stand for the mark instead of b.
 */
export function clusterMarks(xs: number[], gap: number, better: (a: number, b: number) => boolean): Mark[] {
  const out: Mark[] = [];
  xs.forEach((x, k) => {
    const m = out[out.length - 1];
    if (m && x - xs[m.first] <= gap) {
      m.last = k;
      if (better(k, m.best)) m.best = k;
    } else out.push({ first: k, last: k, best: k });
  });
  return out;
}
