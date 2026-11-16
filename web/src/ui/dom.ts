// Small DOM helpers.

export function el<K extends keyof HTMLElementTagNameMap>(tag: K, attrs: Record<string, string> = {}, text?: string): HTMLElementTagNameMap[K] {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
  if (text !== undefined) e.textContent = text;
  return e;
}

/** Escape text for use inside template-literal HTML. */
export function esc(s: unknown): string {
  return String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]!);
}

export function chipReal(source: string): string {
  return `<span class="chip chip-real">Real data · ${esc(source)}</span>`;
}

export function chipSample(): string {
  return `<span class="chip chip-sample">Sample data</span>`;
}

/** The right provenance chip for a piece of content. */
export function provenance(sample: boolean, source: string): string {
  return sample ? chipSample() : chipReal(source);
}

export function fmt(n: number, digits = 0): string {
  return n.toLocaleString('en-US', { maximumFractionDigits: digits, minimumFractionDigits: digits });
}

/** "1 day", "6 days". */
export function plural(n: number, word: string, many = word + 's'): string {
  return `${fmt(n)} ${Math.abs(n) === 1 ? word : many}`;
}

/** Fix "1 days" style grammar in text we did not write (engine labels). */
export function fixPlural(text: string): string {
  return text.replace(/(^|[^\d.])1 (day|photo|frame|night|year|month|week|path)s\b/g, (_m, pre: string, w: string) => `${pre}1 ${w}`);
}
