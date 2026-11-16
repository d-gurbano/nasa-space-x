// Charts for the Challenge targets page: plain SVG drawn to the width it is given, with one
// readout line under the plot that follows the pointer, a tap, or the arrow keys, and a
// table of the same numbers.
import { dateFromMjd, mjdFromDate, plainDate } from '../../lib/time';
import { table } from '../../ui/components';
import { esc, fmt, plural } from '../../ui/dom';
import { BANDS, niceStep, type LcMedian, type LcPoint, type Track } from './logic';

/** A dot the reader can point at: where it is in the plot (px) and what to say about it. */
interface Mark { x: number; y: number; say: string }
interface Drawn { svg: string; marks: Mark[]; height: number }

/**
 * Put a chart in `host`. It is redrawn to the host's width, and the mark nearest the
 * pointer (or stepped to with the arrow keys) is ringed and described in the line below.
 */
function chart(host: HTMLElement, label: string, legend: string, draw: (width: number) => Drawn, start: number): () => void {
  host.innerHTML = `<ul class="legend st-legend">${legend}</ul>
    <div class="st-plot" tabindex="0" role="group" aria-label="${esc(label)} Use the left and right arrow keys to step through the points."></div>
    <p class="st-read" aria-live="polite"></p>`;
  const plot = host.querySelector('.st-plot') as HTMLElement, read = host.querySelector('.st-read') as HTMLElement;
  let marks: Mark[] = [], on = start, width = 0;
  const pick = (k: number) => {
    on = Math.max(0, Math.min(marks.length - 1, k));
    const m = marks[on], ring = plot.querySelector('.st-on');
    if (!m || !ring) return;
    ring.setAttribute('cx', String(m.x));
    ring.setAttribute('cy', String(m.y));
    read.innerHTML = m.say;
  };
  const render = () => {
    const w = Math.round(plot.clientWidth);
    if (!w || w === width) return;
    width = w;
    const d = draw(w);
    marks = d.marks;
    plot.innerHTML = `<svg class="chart" width="${w}" height="${d.height}" viewBox="0 0 ${w} ${d.height}" aria-hidden="true">${d.svg}<circle class="st-on" r="10"/></svg>`;
    pick(on);
  };
  const nearest = (e: PointerEvent) => {
    const r = plot.getBoundingClientRect(), x = e.clientX - r.left, y = e.clientY - r.top;
    let best = 0, bd = Infinity;
    marks.forEach((m, k) => {
      const d = Math.hypot(m.x - x, (m.y - y) * 0.35); // mostly along the time axis
      if (d < bd) [bd, best] = [d, k];
    });
    pick(best);
  };
  plot.addEventListener('pointermove', nearest);
  plot.addEventListener('pointerdown', nearest);
  plot.addEventListener('keydown', (e) => {
    if (e.key !== 'ArrowRight' && e.key !== 'ArrowLeft') return;
    e.preventDefault();
    pick(on + (e.key === 'ArrowRight' ? 1 : -1));
  });
  const ro = new ResizeObserver(render);
  ro.observe(plot);
  render();
  return () => ro.disconnect();
}

const n1 = (v: number) => v.toFixed(1);
/** "19.2 arcmin" above 5 arcmin, else "136.9 arcsec". */
export const sky = (arcsec: number) => (arcsec >= 300 ? `${n1(arcsec / 60)} arcmin` : `${n1(arcsec)} arcsec`);
const when = (p: { first: number; last: number }) => (Math.floor(p.first) === Math.floor(p.last) ? `${Math.floor(p.first)}` : `${Math.floor(p.first)} to ${Math.floor(p.last)}`);

/** Decades of motion: the prediction as a line, each telescope's photos as dots on it. */
export function trackChart(host: HTMLElement, t: Track, name: string): () => void {
  const pts = [...t.points].sort((a, b) => a.year - b.year);
  const top = Math.max(...t.line.map((p) => p[1]), ...pts.map((p) => p.moved));
  const k = top >= 300 ? 60 : 1, unit = top >= 300 ? 'arcmin' : 'arcsec';
  const y0 = pts[0].first, y1 = Math.max(pts[pts.length - 1].last, t.line[t.line.length - 1][0]), pad = (y1 - y0) * 0.04;
  const draw = (W: number): Drawn => {
    const H = 150, L = 40, R = 16, T = 34, B = 26; // compact: it lives in the star card
    const x = (yr: number) => L + ((yr - y0 + pad) / (y1 - y0 + 2 * pad)) * (W - L - R);
    const y = (v: number) => T + (1 - v / (top * 1.04)) * (H - T - B);
    const ys = niceStep(top / k, 4), xs = Math.max(1, niceStep(y1 - y0, W < 520 ? 4 : 7));
    let axis = '';
    for (let v = 0; v <= top / k; v += ys) axis += `<line class="grid" x1="${L}" x2="${W - R}" y1="${y(v * k)}" y2="${y(v * k)}"/><text x="${L - 8}" y="${y(v * k) + 4}" text-anchor="end">${v}</text>`;
    for (let yr = Math.ceil(y0 / xs) * xs; yr <= y1; yr += xs) axis += `<text x="${x(yr)}" y="${H - B + 18}" text-anchor="middle">${yr}</text>`;
    const first = pts[0], sx = pts.find((p) => p.spherex);
    // the first dot's label is lifted clear of the rising line
    const lift = Math.round(((H - T - B) / (W - L - R)) * 150) + 18;
    return {
      height: H,
      marks: pts.map((p) => ({
        x: x(p.year), y: y(p.moved),
        say: `<b>${when(p)}</b> ${esc(p.family)}${p.n > 1 ? `, ${p.spherex ? plural(p.n, 'pass', 'passes') : plural(p.n, 'image')}` : ''}: ${sky(p.moved)} from the start, ${n1(p.miss)} arcsec from the predicted spot.`,
      })),
      svg: `<g class="axis">${axis}</g>
        <text class="axis-label" x="0" y="12">Displacement since the first epoch (${unit})</text>
        <polyline class="st-line" points="${t.line.map((p) => `${x(p[0]).toFixed(1)},${y(p[1]).toFixed(1)}`).join(' ')}"/>
        ${pts.filter((p) => !p.spherex).map((p) => `<circle class="st-pt" cx="${x(p.year).toFixed(1)}" cy="${y(p.moved).toFixed(1)}" r="4"/>`).join('')}
        <line class="st-lead" x1="${x(first.year)}" x2="${x(first.year)}" y1="${y(first.moved) - 9}" y2="${y(first.moved) - lift + 6}"/>
        <text class="st-lab" x="${x(first.year) - 3}" y="${y(first.moved) - lift}">${Math.floor(first.year)}, ${esc(first.family)}</text>
        ${sx ? `<circle class="st-pt st-sx" cx="${x(sx.year).toFixed(1)}" cy="${y(sx.moved).toFixed(1)}" r="6.5"/><text class="st-lab" x="${x(sx.year) - 12}" y="${y(sx.moved) - 10}" text-anchor="end">SPHEREx</text>` : ''}`,
    };
  };
  return chart(
    host,
    `Chart: how far ${name} moved from ${Math.floor(y0)} to ${Math.floor(y1)}, and the residual of each measurement from the catalogue prediction.`,
    `<li><span class="lg-dot st-lg-old"></span>Older telescopes</li><li><span class="lg-dot st-lg-sx"></span>SPHEREx</li><li><span class="lg-line st-lg-pred"></span>Predicted from today's star catalogue</li>`,
    draw,
    pts.length - 1,
  );
}

export function trackTable(t: Track): string {
  return table(
    ['Survey', 'Year', 'Images', 'Displacement', 'Residual'],
    [...t.points].sort((a, b) => a.year - b.year).map((p) => [esc(p.family), when(p), String(p.n), sky(p.moved), `${n1(p.miss)} arcsec`]),
  );
}

const pct = (v: number) => (Math.round(v) ? `${fmt(Math.abs(v))}% ${v > 0 ? 'brighter' : 'fainter'} than usual` : 'the same as usual');
const month = (mjd: number) => plainDate(mjd).replace(/^\d+ /, '');

/**
 * Brightness over time: every photo as a small dot, the middle of each pass as a large one.
 * `passes` are the dates SPHEREx looked (MJD); `period` draws a bar that long, in days.
 */
export function curveChart(host: HTMLElement, lc: { points: LcPoint[]; medians: LcMedian[] }, passes: number[], name: string, period?: number): () => void {
  const mags = lc.points.map((p) => Math.abs(p.pct)).sort((a, b) => a - b);
  const lim = (mags[Math.floor(0.98 * (mags.length - 1))] ?? 0) > 38 ? 100 : 50;
  const days = [...passes, ...lc.points.map((p) => p.mjd)];
  const x0 = Math.min(...days) - 20, x1 = Math.max(...days) + 20;
  const out = lc.points.filter((p) => Math.abs(p.pct) > lim).length;
  const bands = ([0, 1] as const).filter((b) => lc.medians.some((m) => m.band === b));
  const draw = (W: number): Drawn => {
    const H = 150, L = 46, R = 16, T = 26, B = 36;
    const x = (d: number) => L + ((d - x0) / (x1 - x0)) * (W - L - R);
    const y = (v: number) => T + (1 - (v + lim) / (2 * lim)) * (H - T - B);
    let axis = '';
    for (const v of [-lim, -lim / 2, 0, lim / 2, lim]) axis += `<line class="${v ? 'grid' : 'zero'}" x1="${L}" x2="${W - R}" y1="${y(v)}" y2="${y(v)}"/><text x="${L - 8}" y="${y(v) + 4}" text-anchor="end">${v > 0 ? '+' : ''}${v}%</text>`;
    const months = (x1 - x0) / 30.44, step = [1, 2, 3, 6, 12].find((s) => months / s <= (W < 520 ? 4 : 7)) ?? 12;
    const d = dateFromMjd(x0);
    d.setUTCDate(1);
    d.setUTCHours(0, 0, 0, 0);
    for (d.setUTCMonth(d.getUTCMonth() + 1); mjdFromDate(d) < x1; d.setUTCMonth(d.getUTCMonth() + 1)) {
      if (d.getUTCMonth() % step === 0 && x(mjdFromDate(d)) < W - 28) axis += `<text x="${x(mjdFromDate(d))}" y="${H - B + 28}" text-anchor="middle">${month(mjdFromDate(d))}</text>`;
    }
    const ticks = passes.map((p) => `<line class="lc-pass" x1="${x(p).toFixed(1)}" x2="${x(p).toFixed(1)}" y1="${H - B}" y2="${H - B + 8}"/>`).join('');
    const dots = lc.points
      .filter((p) => Math.abs(p.pct) <= lim)
      .map((p) => `<circle class="lc-pt lc-b${p.band}${p.saturated ? ' lc-sat' : ''}" cx="${x(p.mjd).toFixed(1)}" cy="${y(p.pct).toFixed(1)}" r="2.5"/>`)
      .join('');
    const lines = bands
      .map((b) => {
        const ms = lc.medians.filter((m) => m.band === b);
        // the label sits in the gap between the first two passes: above the upper line, below the lower one
        const mid = (o: number) => lc.medians.filter((m) => m.band === o).slice(0, 2).reduce((s, m, _, a) => s + m.pct / a.length, 0);
        const up = bands.every((o) => mid(o) <= mid(b));
        const lx = ms.length > 1 ? (x(ms[0].mjd) + x(ms[1].mjd)) / 2 : x(ms[0].mjd) + 14;
        const ly = ms.length > 1 ? y(mid(b)) + (up ? -10 : 18) : y(ms[0].pct) + 4;
        return `${ms.length > 1 ? `<polyline class="lc-line lc-b${b}" points="${ms.map((m) => `${x(m.mjd).toFixed(1)},${y(m.pct).toFixed(1)}`).join(' ')}"/>` : ''}
          ${ms.map((m) => `<circle class="lc-md lc-b${b}" cx="${x(m.mjd).toFixed(1)}" cy="${y(m.pct).toFixed(1)}" r="5.5"/>`).join('')}
          <text class="st-lab" x="${lx}" y="${ly}"${ms.length > 1 ? ' text-anchor="middle"' : ''}>${BANDS[b]}</text>`;
      })
      .join('');
    const bar = period
      ? `<g class="lc-period"><path d="M${x(x0 + 20)},${T + 2}v10m0,-5H${x(x0 + 20 + period)}m0,-5v10"/><text class="st-lab" x="${x(x0 + 20) + 8}" y="${T + 26}">One pulse: ${fmt(period)} days</text></g>`
      : '';
    return {
      height: H,
      marks: lc.medians.map((m) => ({ x: x(m.mjd), y: y(m.pct), say: `<b>${month(m.mjd)}</b>, ${BANDS[m.band]}: ${pct(m.pct)} (median of ${plural(m.n, 'image')}).` })),
      svg: `<g class="axis">${axis}</g>${ticks}
        <text class="axis-label" x="0" y="12">Compared with the star's usual brightness</text>
        ${bar}${dots}${lines}`,
    };
  };
  return chart(
    host,
    `Chart: brightness of ${name} in each SPHEREx image, relative to its median.`,
    `${bands.map((b) => `<li><span class="lg-dot lc-lg${b}"></span>${BANDS[b]}, middle of a pass</li>`).join('')}
     <li><span class="lg-dot lc-lg-sat"></span>Single image, saturated</li>
     ${lc.points.some((p) => !p.saturated) ? '<li><span class="lg-dot lc-lg-ok"></span>Single image, unsaturated</li>' : ''}
     <li><span class="lg-tick"></span>SPHEREx observed</li>
     ${out ? `<li>${plural(out, 'image')} beyond ${lim}% ${out === 1 ? 'is' : 'are'} not drawn</li>` : ''}`,
    draw,
    Math.max(0, lc.medians.filter((m) => m.band === bands[0]).length - 1),
  );
}

export function curveTable(lc: { medians: LcMedian[] }): string {
  return table(
    ['Wavelengths', 'Pass', 'Images', 'Relative to median'],
    lc.medians.map((m) => [BANDS[m.band], month(m.mjd), String(m.n), pct(m.pct)]),
  );
}
