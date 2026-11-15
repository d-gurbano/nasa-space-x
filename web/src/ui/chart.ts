// "What it is made of": SPHEREx brightness by wavelength with error bars,
// plus a few class template curves. Plain SVG, with a table alternative.
import type { ObjectPage } from '../lib/types';
import { esc } from './dom';

const W = 360, H = 200, L = 40, R = 12, T = 12, B = 34;

export function compositionChart(c: ObjectPage['composition']): string {
  const pts = c.points;
  const xmin = 0.7, xmax = 5.0;
  // scale to the values (not the error bars), within a sane range; long error bars are clipped
  const vals = [...pts.map((p) => p.value), ...c.templates.flatMap((t) => t.value)];
  const ymin = Math.max(-1, Math.floor(Math.min(...vals) * 10) / 10 - 0.1), ymax = Math.min(6, Math.ceil(Math.max(...vals) * 10) / 10 + 0.1);
  const x = (u: number) => L + ((u - xmin) / (xmax - xmin)) * (W - L - R);
  const y = (v: number) => T + (1 - (v - ymin) / (ymax - ymin)) * (H - T - B);
  const best = c.best_match?.toLowerCase();
  const isBest = (name: string) => !!best && name.toLowerCase().startsWith(best);
  const xt = [1, 2, 3, 4, 5].map((u) => `<g><line x1="${x(u)}" x2="${x(u)}" y1="${H - B}" y2="${H - B + 4}"/><text x="${x(u)}" y="${H - B + 16}" text-anchor="middle">${u}</text></g>`).join('');
  const ys: number[] = [];
  const stepY = ymax - ymin > 3 ? 1 : 0.5;
  for (let v = Math.ceil(ymin / stepY) * stepY; v <= ymax; v += stepY) ys.push(v);
  const yt = ys.map((v) => `<g><line class="grid" x1="${L}" x2="${W - R}" y1="${y(v)}" y2="${y(v)}"/><text x="${L - 6}" y="${y(v) + 4}" text-anchor="end">${v.toFixed(1)}</text></g>`).join('');
  const lines = c.templates
    .map((t) => {
      const d = t.um.map((u, k) => `${k ? 'L' : 'M'}${x(u).toFixed(1)},${y(t.value[k]).toFixed(1)}`).join('');
      return `<path class="tpl ${isBest(t.name) ? 'tpl-best' : ''}" d="${d}"><title>${esc(t.name)}</title></path>`;
    })
    .join('');
  const dots = pts
    .map((p) => `<g class="pt"><line x1="${x(p.um)}" x2="${x(p.um)}" y1="${y(p.value - p.err)}" y2="${y(p.value + p.err)}"/><circle cx="${x(p.um)}" cy="${y(p.value)}" r="3.5"><title>${p.um} µm: ${p.value} +/- ${p.err}</title></circle></g>`)
    .join('');
  return `<svg class="chart" viewBox="0 0 ${W} ${H}" role="img" aria-label="Brightness of the object at ${pts.length} SPHEREx wavelengths compared with ${c.templates.length} asteroid and comet types">
    <g class="axis">${yt}${xt}<line x1="${L}" x2="${W - R}" y1="${H - B}" y2="${H - B}"/></g>
    <text class="axis-label" x="${(L + W - R) / 2}" y="${H - 2}" text-anchor="middle">wavelength (µm)</text>
    <defs><clipPath id="plot-clip"><rect x="${L}" y="${T}" width="${W - L - R}" height="${H - T - B}"/></clipPath></defs>
    <g clip-path="url(#plot-clip)">${lines}${dots}</g>
  </svg>
  <ul class="legend">
    <li><span class="lg-dot"></span>SPHEREx</li>
    ${c.templates.map((t) => `<li class="${isBest(t.name) ? 'lg-best' : ''}"><span class="lg-line"></span>${esc(t.name)}</li>`).join('')}
  </ul>`;
}

export function compositionTable(c: ObjectPage['composition']): string {
  return `<table class="data-table"><thead><tr><th>Wavelength (µm)</th><th>Relative brightness</th><th>Error (+/-)</th></tr></thead><tbody>
    ${c.points.map((p) => `<tr><td>${p.um.toFixed(2)}</td><td>${p.value.toFixed(3)}</td><td>${p.err.toFixed(3)}</td></tr>`).join('')}
  </tbody></table>`;
}
