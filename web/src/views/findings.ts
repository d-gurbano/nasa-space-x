// Real findings from our runs, shared by About, Scientists and the object panel.
// The hit rates and the live test come from data files (benchmark.json, index.json) and
// tests/findings.test.ts checks these copies against them; the validation notes come from the run logs.

export type Label = 'MEASURED' | 'COMPUTED' | 'VERIFIED';

export interface TypeRate { searched?: number; with_photos: number; found: number; found_rate?: number }
export type HitRates = Partial<Record<'comet' | 'neo' | 'lost', TypeRate>>;

/** benchmark.json archive_search_hit_rate.by_type, as of the final run */
export const HIT_RATE: Required<HitRates> = {
  comet: { with_photos: 31, found: 5 },
  neo: { with_photos: 201, found: 3 },
  lost: { with_photos: 11, found: 0 },
};
export const HIT_RATE_LABEL: Label = 'MEASURED';
export const HIT_RATE_PLAIN = 'We found comets more often than asteroids. In these images the comets were predicted brighter (median AB 20.7) than the small near-Earth asteroids (21.5), and most of those asteroids were too faint for SPHEREx before their first known observation.';

const TYPE_WORD: [keyof HitRates, string][] = [['comet', 'Comets'], ['neo', 'Near-Earth asteroids'], ['lost', 'Lost objects']];
const pct = (r: TypeRate) => {
  const p = (100 * r.found) / r.with_photos;
  return p >= 10 || p === 0 ? `${Math.round(p)}%` : `${p.toFixed(1)}%`;
};

/** One row per type: [label, "5 of 31", "16%"]; from the loaded data when given, else the copy above */
export function hitRows(data?: HitRates | null): [string, string, string][] {
  return TYPE_WORD.map(([k, word]) => {
    const r = data?.[k]?.with_photos ? data[k]! : HIT_RATE[k];
    return [word, `${r.found} of ${r.with_photos}`, r.found ? pct(r) : ''];
  });
}

/** index.json live_stats of the 2026-11-15 run (docs/LIVE.md in the engine) */
export const LIVE = {
  run_iso: '2026-11-15', since_first_obs: '2026-11-01',
  candidates: 455, screened: 296, with_public_photos: 204, searched: 12, too_faint: 12,
  newest_public_frame: '2026-10-04', min_days_before_first_obs: 27,
};
export const LIVE_LABEL: Label = 'MEASURED';
export const LIVE_TEXT = `On 15 Nov 2026 we ran Rewind on the ${LIVE.candidates} objects first seen since 1 Nov. We screened ${LIVE.screened} of them, and ${LIVE.with_public_photos} had public SPHEREx images. We measured the ${LIVE.searched} most promising with every check. All ${LIVE.too_faint} were too faint. The newest public SPHEREx images were from 4 Oct 2026, at least ${LIVE.min_days_before_first_obs} days before these objects were first seen, when they were fainter.`;
export const LIVE_PLAIN = 'What limits the search today is the age of the public data, about six weeks behind. If Rewind ran on SPHEREx images as they arrive, it could search for each new object soon after it is announced.';

/** How the method was checked: [title, label, short line, detail] */
export const VALIDATION: [string, Label, string, string][] = [
  ['Photometry', 'MEASURED', 'The measured brightness matched the prediction to -0.11 ± 0.14 mag.',
    'We tested this on the known asteroid (1000) Piazzia in 23 images at 0.75-2.4 µm. It was brighter at the longer wavelengths, as expected from the asteroid\'s own heat.'],
  ['Positions', 'MEASURED', 'The kete position engine matched JPL Horizons to 0.003-0.011 arcsec.',
    'We compute positions as seen from SPHEREx itself. Using the Earth\'s centre instead lost 24% of the signal on a main-belt asteroid. It would put near-Earth asteroids 9-90 arcsec off.'],
  ['Orbit tool, on Apophis', 'COMPUTED', 'One precovery reduced the 2029 miss-distance uncertainty about 25 times.',
    'Using only the 2004 observations of Apophis, we added its real 15 March 2004 precovery. The uncertainty fell from about ±53,000 km to about ±2,100 km. The miss distance from the 2004 data (46,600 km) is still about 4 sigma above today\'s JPL value (38,000 km).'],
  ['NEOWISE cross-check', 'MEASURED', 'We searched older NEOWISE images for three objects and found one hint and no detections.',
    'The lost asteroid 2015 SA has a possible single NEOWISE detection (W2 S/N about 4) 3 days before its first known observation. We count it as a hint, not a detection. The NEOWISE images did not support C/2026 C1 or C/2026 H2.'],
  ['Satellite trails', 'MEASURED', 'Starlink satellites cannot cross SPHEREx images.',
    'The headers of 610 frames place SPHEREx at 632-668 km, above the highest Starlink shells (at most about 577 km). The trails we see come from higher satellites and debris.'],
];

/** Short words for the panel's colour chip; only types the data actually matched */
export const COLOUR_WORD: Record<string, string> = { C: 'dark carbon', S: 'rocky' };
