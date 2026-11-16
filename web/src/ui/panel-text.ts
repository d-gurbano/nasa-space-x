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
