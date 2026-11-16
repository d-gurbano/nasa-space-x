// Plain-text helpers for the object panel (pure, so they are unit tested).

/**
 * The engine's verdict in one short sentence: its first sentence, without the bracketed
 * numbers and without the detail after a colon. When the claim says the photos are not
 * earlier than the known observations, that sentence is kept too, so nothing reads stronger
 * than the data. The full text stays in "How sure are we?".
 */
export function oneSentence(text: string | null | undefined, claim?: string | null): string {
  let t = (text ?? '').trim();
  for (let k = 0; k < 4; k++) {
    const next = t.replace(/\s*\([^()]*\)/g, '');
    if (next === t) break;
    t = next;
  }
  const sentences = t.split(/(?<=\.)\s+(?=[A-Z0-9])/);
  const cut = (s: string) => {
    const c = s.indexOf(': ');
    const out = (c > 0 ? s.slice(0, c) : s).trim().replace(/[.,;]+$/, '');
    return out ? out + '.' : '';
  };
  let first = cut(sentences[0] ?? '');
  if (claim && /not earlier/i.test(claim)) {
    const caveat = sentences.find((s) => /not earlier/i.test(s));
    if (caveat && cut(caveat) !== first) first += ' ' + cut(caveat);
  }
  return first;
}

const fmtInt = (n: number) => Math.round(n).toLocaleString('en-US');

/** A false-alarm probability as a count of null trials, never rounded to "about 0%". */
export function farText(rate: number, trials?: number | null): string {
  if (!(rate > 0)) return trials ? `0 in ${fmtInt(trials)} null trials` : '0 in the null trials';
  if (trials) return `${fmtInt(rate * trials)} in ${fmtInt(trials)} null trials (${(rate * 100).toPrecision(2)}%)`;
  return `${(rate * 100).toPrecision(2)}%`;
}

/** "26 Dec 2025" -> "26 Dec '25": a compact date that keeps the year. */
export function shortDate(plain: string): string {
  return plain.replace(/ \d{2}(\d{2})$/, " '$1");
}

// Older engine runs wrote casual sentences ("Rewind found X in SPHEREx photos", "a fake path is as
// bright"). The engine now writes the wording below; until every data set is regenerated, text from
// the files is passed through this map so all pages read the same. Text that already uses the new
// wording passes through unchanged.
const ENGINE_REWRITES: [RegExp, string][] = [
  [/^SPHEREx saw (.+?) \(a known object, not a precovery\): the cleaned stack of (\d+) photos gives S\/N ([\d.]+), and every control test agrees\./,
    'SPHEREx detected $1 (control object, not a precovery): null-calibrated S/N $3 in the static-sky-subtracted stack of $2 images, and every check passes.'],
  [/^Rewind found (.+?) in SPHEREx photos/, 'Rewind detected $1 in SPHEREx images'],
  [/^SPHEREx saw /, 'SPHEREx detected '],
  [/\bS\/N ([\d.]+) in the sky-cleaned stack of (\d+) photos/g, 'null-calibrated S/N $1 in the static-sky-subtracted stack of $2 images'],
  [/ \(no single photo shows it; only the stack does\)/g, ' (below the noise in every single image; detected only in the stack)'],
  [/, on (\d+) separate days, and the orbit still fits with the new positions\./g, ', positive on $1 separate nights, and the orbit refit with the new positions stays consistent.'],
  [/There is a signal where (.+?) should be \(S\/N/g, 'A signal is present at the predicted position of $1 (S/N'],
  [/but not every test passes/g, 'but not every check passes'],
  [/so this is a hint, not a find\./g, 'so this is a HINT, not a detection.'],
  [/the stack is not strong enough/g, 'stack S/N below 5'],
  [/a fake path is as bright/g, 'a null trajectory reached the same S/N'],
  [/the signal does not peak at the right time/g, 'S/N does not peak at zero time shift'],
  [/it is not seen on 2 separate days/g, 'positive on fewer than 2 nights'],
  [/the object should be below our limit/g, 'predicted magnitude below the injection-recovery limit'],
  [/the sky could not be cleaned/g, 'no usable static-sky reference'],
  [/the new positions do not fit the orbit well/g, 'new positions inconsistent with the orbit'],
  [/too few photos are positive compared with fake paths/g, 'sign test failed (too few positive single images)'],
  [/the signal rests on a single day/g, 'signal depends on a single night'],
  [/These photos are not earlier than the first known observation \(([^)]+)\): they add extra positions, not a precovery\./g,
    'These images are not earlier than the first known observation ($1): they add positions, not a precovery.'],
  [/^SPHEREx did not photograph (.+?) in the time we searched\./, 'No SPHEREx image covers the predicted position of $1 in the searched window.'],
  [/Nothing shows at the predicted spot of/g, 'No significant signal at the predicted position of'],
  [/ was too faint for SPHEREx here: our tests can only find objects brighter than about AB/g, ' was below the SPHEREx detection limit at this position: injection-recovery puts the local 50% limit at about AB'],
  [/ was too faint for SPHEREx here\./g, ' was below the SPHEREx detection limit at this position.'],
  [/The photos are in a crowded Milky Way field, which makes faint sources harder to separate from stars\./g, 'The images lie in a crowded Galactic field, where faint sources are harder to separate from stars.'],
  [/^Rewind found (\d+) of (\d+) known objects that were visible in SPHEREx before the pretend discovery date \((\d+) more were hints, (\d+) missed\), with (\d+) false alarms in/,
    'With the observed arc truncated, Rewind recovered $1 of $2 known objects that were detectable in SPHEREx before the truncation date ($3 more were HINT, $4 missed), with $5 false FOUNDs in'],
  [/Rewind searched SPHEREx photos taken before that date to see if the space telescope had caught it earlier\./g, 'Rewind searched SPHEREx images taken before that date for precovery detections.'],
  [/\bphotos\b/g, 'images'],
  [/\bphoto\b/g, 'image'],
];

/** Engine-written text in the site's current wording (see ENGINE_REWRITES). */
export function engineText(text: string | null | undefined): string {
  let t = text ?? '';
  for (const [re, to] of ENGINE_REWRITES) t = t.replace(re, to);
  return t;
}
