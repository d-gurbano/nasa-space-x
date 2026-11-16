// "Made of" chart for the object panel, kept simple: the SPHEREx measurements as gold dots
// over the closest typical type as one clear line (the other types stay faint). The full
// chart and the table are on the For scientists page.
import type { ObjectPage } from '../lib/types';
import { esc } from './dom';

const W = 360, H = 168, L = 14, R = 14, T = 20, B = 34;

/** What each typical type is, in a few plain words. */
export const TYPE_PLAIN: Record<string, string> = {
  C: 'dark, carbon-rich rock',
  S: 'lighter, stony rock',
  D: 'very dark, reddish rock',
  X: 'grey rock, possibly rich in metal',
};

export function simpleSpectrum(c: ObjectPage['composition']): string {
  const pts = c.points;
  const templates = c.templates ?? [];
  const xmin = 0.7, xmax = 5.0;
  // scale to the values (not the error bars); long error bars are clipped
  const vals = [...pts.map((p) => p.value), ...templates.flatMap((t) => t.value)];
  const lo = Math.min(...vals), hi = Math.max(...vals), pad = Math.max(0.1, (hi - lo) * 0.25);
  const ymin = lo - pad, ymax = hi + pad;
  const x = (u: number) => L + ((u - xmin) / (xmax - xmin)) * (W - L - R);
  const y = (v: number) => T + (1 - (v - ymin) / (ymax - ymin)) * (H - T - B);
  const best = c.best_match?.toLowerCase();
  const isBest = (name: string) => !!best && name.toLowerCase().startsWith(best);
  const ticks = [1, 2, 3, 4, 5].map((u) => `<text x="${x(u)}" y="${H - B + 15}" text-anchor="middle">${u}</text>`).join('');
  const lines = templates
    .map((t) => `<path class="${isBest(t.name) ? 'sp-best' : 'sp-other'}" d="${t.um.map((u, k) => `${k ? 'L' : 'M'}${x(u).toFixed(1)},${y(t.value[k]).toFixed(1)}`).join('')}"><title>Typical ${esc(t.name)}-type</title></path>`)
    .join('');
  // a channel with S/N < 2 carries no colour information; it is drawn faded
  const weak = (p: { value: number; err: number }) => !(p.err > 0) || Math.abs(p.value) / p.err < 2;
  const dots = pts
    .map((p) => `<g class="sp-pt${weak(p) ? ' sp-weak' : ''}"><line x1="${x(p.um)}" x2="${x(p.um)}" y1="${y(p.value - p.err)}" y2="${y(p.value + p.err)}"/><circle cx="${x(p.um)}" cy="${y(p.value)}" r="4"><title>${p.um} µm: ${p.value} ± ${p.err}${weak(p) ? ' (S/N < 2)' : ''}</title></circle></g>`)
    .join('');
  return `<svg class="op-chart" viewBox="0 0 ${W} ${H}" role="img" aria-label="Relative reflectance in ${pts.length} SPHEREx spectral bins${c.best_match ? `, compared with a typical ${esc(c.best_match)}-type` : ''}">
    <defs><clipPath id="op-chart-clip"><rect x="${L}" y="${T}" width="${W - L - R}" height="${H - T - B}"/></clipPath></defs>
    <text x="${L}" y="12">relative reflectance (normalised below 1.3 µm) ↑</text>
    <line class="sp-axis" x1="${L}" x2="${W - R}" y1="${H - B}" y2="${H - B}"/>
    ${ticks}
    <text x="${(L + W - R) / 2}" y="${H - 3}" text-anchor="middle">wavelength (µm)</text>
    <g clip-path="url(#op-chart-clip)">${lines}${dots}</g>
  </svg>
  <ul class="op-legend">
    <li><span class="sp-k-dot"></span>SPHEREx, binned (faded: S/N &lt; 2)</li>
    ${c.best_match ? `<li><span class="sp-k-best"></span>Mean ${esc(c.best_match)}-type template</li>` : ''}
    ${templates.length > (c.best_match ? 1 : 0) ? `<li><span class="sp-k-other"></span>${c.best_match ? 'Other templates' : 'Taxonomic templates'}</li>` : ''}
  </ul>`;
}
