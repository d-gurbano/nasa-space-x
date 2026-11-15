// Ordering of Rewind objects, the choice of the "best" flash for the guided demo, and the
// grouping of flash marks on the time bar.
import type { FlashEvent, IndexObject, ObjectPage, SiteIndex } from './types';
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

/** Stack S/N measured against the fake-path (null) distribution: (S/N - null mean) / null spread. */
export function nullScaledSnr(o: Pick<IndexObject, 'best_snr'>, p: Pick<ObjectPage, 'checks' | 'spherex'> | null): number {
  const snr = p?.spherex?.stack?.snr ?? o.best_snr ?? -Infinity;
  const np = p?.checks?.null_paths;
  if (!np || !Number.isFinite(np.snr_mean) || !(np.snr_std > 0)) return snr;
  return (snr - np.snr_mean) / np.snr_std;
}

export interface Showcase {
  object: IndexObject;
  flash: FlashEvent;
  sure: boolean; // FOUND (true) or only a HINT (false)
  score: number;
}

/**
 * The object for the guided rewind and the demo, chosen from index.json each time:
 * FOUND before HINT, never a known object, needs a SPHEREx photo from before anyone had it,
 * highest null-scaled S/N wins. Its strongest such photo is the flash to show.
 */
export async function pickShowcase(
  idx: Pick<SiteIndex, 'objects' | 'flash_events'>,
  page: (slug: string) => Promise<ObjectPage>,
  prefer?: string | null,
): Promise<Showcase | null> {
  const pre = (o: IndexObject) => idx.flash_events.filter((f) => f.slug === o.slug && f.before_first_known_obs !== false && f.mjd < knownSince(o));
  for (const verdict of ['FOUND', 'HINT'] as const) {
    let cands = idx.objects.filter((o) => o.verdict === verdict && !isKnown(o) && pre(o).length);
    if (prefer && cands.some((o) => o.slug === prefer)) cands = cands.filter((o) => o.slug === prefer);
    if (!cands.length) continue;
    const scored = await Promise.all(
      cands.map(async (o) => ({ o, score: nullScaledSnr(o, await page(o.slug).catch(() => null)) })),
    );
    scored.sort((a, b) => b.score - a.score);
    const best = scored[0];
    const flash = pre(best.o).reduce((b, f) => ((f.snr ?? 0) > (b.snr ?? 0) ? f : b));
    return { object: best.o, flash, sure: verdict === 'FOUND', score: best.score };
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
