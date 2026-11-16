// Sky: the any-position SPHEREx time machine. Type a position; the page finds every public
// SPHEREx photo that covers it (static frame index), reads the pixels live from NASA's archive
// in a Web Worker, and shows them as a flipbook, per-pass stacks, a pass-minus-pass difference
// and a quick-look spectrum of any pixel. Nothing here is pre-rendered.
import '../styles/page-sky.css';
import { getJson } from '../lib/data';
import { plainDate } from '../lib/time';
import { chip, icon, iconButton, tabs } from '../ui/components';
import { esc, fmt, plural } from '../ui/dom';
import { reducedMotion } from '../state';
import {
  BUCKET_URL, PIXEL_ARCSEC, SIZES, apertureMean, cellsFor, diffGrey, formatCoords, framesAt, median, medianStack, parseCoords, parseWaveGrid,
  pickFrames, properMotion, sharedStretch, toGrey, trackMover, waveAt, type Frame, type Mover, type Row, type SkyMeta, type WaveGrid,
} from './sky/logic';
import { offsetToSky, skyToOffset } from './sky/wcs';
import type { LoadRequest, WorkerOut } from './sky/worker';
import type { View } from './page';

const INDEX = 'data/skyindex/';
const GRID = 128; // every cutout is resampled to this many pixels across
const BATCH = 40;
const PLAY_MS = 380;
const PASS_COLOURS = ['var(--blue-2)', 'var(--gold)', 'var(--ok)', 'var(--bad)', 'var(--ink-2)'];
const J2026 = 61041; // MJD of 2026-01-01

// The 5 challenge targets with catalogue proper motions (mas per year), and the 2 deep fields.
const TARGETS = [
  { id: 'wise0855', name: 'WISE 0855', what: 'The coldest known brown dwarf', ra: 133.783556, dec: -7.244052, pmra: -8123.7, pmdec: 673.2, epoch: 2015.3929, source: 'Kirkpatrick et al. 2021' },
  { id: 'barnard', name: "Barnard's Star", what: 'Largest proper motion of any star, 10.4″/yr', ra: 269.448503, dec: 4.73942, pmra: -801.551, pmdec: 10362.394, epoch: 2016, source: 'Gaia DR3' },
  { id: 'epsindib', name: 'Epsilon Indi B', what: 'Binary brown dwarf, 3.6 pc (11.8 light-years)', ra: 331.076453, dec: -56.793812, pmra: 3981.977, pmdec: -2466.832, epoch: 2016, source: 'Gaia DR3' },
  { id: 'rwaur', name: 'RW Aurigae', what: 'Young T Tauri binary with deep dimming events', ra: 76.956081, dec: 30.401205, pmra: 2.641, pmdec: -27.398, epoch: 2016, source: 'Gaia DR3' },
  { id: 'rdra', name: 'R Draconis', what: 'Mira variable (pulsating red giant), period ~246 d', ra: 248.167378, dec: 66.755007, pmra: -20.643, pmdec: 6.149, epoch: 2016, source: 'Gaia DR3' },
];
const FIELDS = [
  { id: 'nep', name: 'North ecliptic pole deep field', what: 'Imaged on almost every orbit', ra: 270, dec: 66.5607 },
  { id: 'sep', name: 'South ecliptic pole deep field', what: 'Imaged on almost every orbit', ra: 90, dec: -66.5607 },
];

interface Loaded { frame: Frame; data: Float32Array; noise: number; mjd: number; x: number; y: number; jac: [number, number, number, number] }
interface Result { ra: number; dec: number; size: number; all: Frame[]; loaded: Map<string, Loaded>; skipped: Map<string, 'edge' | 'error'>; bytes: number }
interface ObjectLite { spherex?: { frames?: { mjd: number; pred_ra: number; pred_dec: number; snr: number | null; used?: boolean }[] }; checks?: { orbit_fit?: { positions?: { mjd: number; ra: number; dec: number }[] } | null } }

// Kept between visits to the page: the index, the wavelength grids, the worker (it caches
// FITS headers) and every result already read.
let metaP: Promise<SkyMeta | null> | null = null;
const shards = new Map<string, Promise<{ f: Row[] } | null>>();
const grids = new Map<number, Promise<WaveGrid | null>>();
const results = new Map<string, Result>();
let worker: Worker | null = null;
let jobs = 0;

const optional = <T>(url: string): Promise<T | null> => getJson<T>(url).catch(() => null);
const loadMeta = () => (metaP ??= optional<SkyMeta>(INDEX + 'meta.json').then((m) => (m?.schema?.startsWith('rewind-skyindex') ? m : null)));
// a big cell is split: the first file lists its part files in 'more', each with its own rows
const readCell = async (name: string): Promise<{ f: Row[] } | null> => {
  const first = await optional<{ f?: Row[]; more?: string[] }>(`${INDEX}cells/${name}.json`);
  if (!first) return null;
  const parts = await Promise.all((first.more ?? []).map((p) => optional<{ f?: Row[] }>(`${INDEX}cells/${p}`)));
  return { f: [first, ...parts].flatMap((s) => s?.f ?? []) };
};
const loadShard = (name: string) => shards.get(name) ?? shards.set(name, readCell(name)).get(name)!;
const loadGrid = (d: number) => grids.get(d) ?? grids.set(d, optional<Record<string, unknown>>(`${INDEX}detectors/D${d}_wave.json`).then((j) => (j ? parseWaveGrid(j) : null))).get(d)!;

function setUrl(q: { ra: number; dec: number; size: number; target?: string } | null) {
  const u = new URL(location.href);
  for (const k of ['ra', 'dec', 'size', 'target']) u.searchParams.delete(k);
  if (q) {
    u.searchParams.set('ra', q.ra.toFixed(5));
    u.searchParams.set('dec', q.dec.toFixed(5));
    u.searchParams.set('size', String(q.size));
    if (q.target) u.searchParams.set('target', q.target);
  }
  history.replaceState(null, '', u);
}

export const skyView: View = async (body, ctx) => {
  const meta = await loadMeta();
  const finds = ctx.source.sample ? [] : ctx.source.index.objects.filter((o) => o.verdict === 'FOUND');
  // a place to try, as a card: a button that loads it live, or (with no index yet) a link to its ready-made page
  const spot = (t: { id: string; name: string; what: string }, thumb: boolean) => {
    const inner = `<span class="sky-thumb">${thumb ? `<img src="${esc(ctx.source.base)}stars/${t.id}/stack.png" alt="" loading="lazy">` : ''}</span><span class="sky-card-name">${esc(t.name)}</span><span class="sky-card-what">${esc(t.what)}</span>`;
    return `<li>${meta ? `<button type="button" class="sky-card" data-preset="${t.id}">${inner}</button>` : `<a class="sky-card" href="#/stars">${inner}</a>`}</li>`;
  };
  const soon = !meta
    ? 'Until then, these targets open with images already processed by Rewind.'
    : meta.partial
      ? `For now it covers these spots${meta.n_shortlist_paths ? ` and the paths of ${fmt(meta.n_shortlist_paths)} comets and asteroids` : ''}.`
      : '';
  body.innerHTML = `
    <p class="sky-lead">Enter coordinates (ICRS). Rewind queries the IRSA SPHEREx image index live, cuts out every image that covers the position, and plays them in time order.</p>
    <form class="sky-form" novalidate>
      <label class="sky-field"><span class="kicker">Position (RA Dec)</span>
        <input class="sky-input mono" name="pos" type="text" inputmode="text" autocomplete="off" spellcheck="false" placeholder="133.7595 -7.2421  or  08 55 02.3 -07 14 31" aria-describedby="sky-err"></label>
      <div class="sky-field"><span class="kicker">Patch width</span>
        <div class="seg sky-size" role="radiogroup" aria-label="Patch width in arcseconds">${SIZES.map((s) => `<button type="button" role="radio" data-size="${s}" aria-checked="false" aria-selected="false">${s}"</button>`).join('')}</div></div>
      <button class="btn btn-primary sky-go" type="submit">Show this field${icon('arrow')}</button>
    </form>
    <p class="sky-err warn" id="sky-err" role="alert" hidden></p>
    <section class="sky-presets" aria-label="Example fields">
      ${soon ? `<div class="sky-soon"><i aria-hidden="true"></i><p><b>Full-sky index arriving soon</b><span>${esc(soon)}</span></p></div>` : '<p class="kicker">Try</p>'}
      <ul class="sky-cards">${TARGETS.map((t) => spot(t, true)).join('')}${meta ? FIELDS.map((t) => spot(t, false)).join('') : ''}</ul>
      ${meta ? `<div class="sky-more">
        ${finds.length ? `<select class="chip sky-finds" aria-label="A Rewind find, where SPHEREx saw it"><option value="">A Rewind find...</option>${finds.map((o) => `<option value="${esc(o.slug)}">${esc(o.name)}</option>`).join('')}</select>` : ''}
        <button class="chip chip-gold sky-lucky">Random spot</button>
      </div>` : ''}
    </section>
    <div class="sky-out" aria-live="polite"></div>`;
  // a missing thumbnail leaves the plain star-field tile
  body.querySelectorAll<HTMLImageElement>('.sky-thumb img').forEach((img) => img.addEventListener('error', () => img.remove()));

  const form = body.querySelector('.sky-form') as HTMLFormElement;
  const input = body.querySelector('.sky-input') as HTMLInputElement;
  const err = body.querySelector('.sky-err') as HTMLElement;
  const out = body.querySelector('.sky-out') as HTMLElement;
  const sizeBtns = [...body.querySelectorAll<HTMLButtonElement>('.sky-size button')];
  let size = 120;
  let timer = 0;
  let alive = true;
  let job = 0;
  const setSize = (s: number) => {
    size = SIZES.includes(s) ? s : 120;
    sizeBtns.forEach((b) => ['aria-selected', 'aria-checked'].forEach((a) => b.setAttribute(a, String(+b.dataset.size! === size))));
  };
  const fail = (msg: string) => {
    err.textContent = msg;
    err.hidden = !msg;
  };
  const stopPlay = () => {
    clearInterval(timer);
    timer = 0;
  };

  // no index on the server yet: the form waits, the cards lead to the ready-made star pages
  if (!meta) {
    form.classList.add('sky-wait');
    form.querySelectorAll('input, button').forEach((e) => ((e as HTMLInputElement).disabled = true));
    return;
  }
  const coverage = meta.partial
    ? `Our index is partial for now: it covers ${(meta.areas ?? []).length ? 'the 5 challenge targets, the 2 deep fields and ' : ''}the paths of ${meta.n_shortlist_paths ?? 'the'} shortlisted comets and asteroids (${fmt(meta.n_frames)} images).`
    : `The index lists ${fmt(meta.n_frames)} public SPHEREx Level 2 images over the whole sky.`;

  // ---------- one request ----------
  const show = async (ra: number, dec: number, o: { target?: string; mover?: Mover; focusMjd?: number; name?: string } = {}) => {
    stopPlay();
    worker?.postMessage({ type: 'cancel' });
    fail('');
    const my = (job = ++jobs);
    input.value = formatCoords(ra, dec);
    setUrl({ ra, dec, size, target: o.target });
    out.innerHTML = `<p class="sky-status mono">Querying which SPHEREx images cover this position...</p>`;
    const cells = await Promise.all(cellsFor(ra, dec, meta.cell_deg).map(loadShard));
    if (!alive || my !== job) return;
    const found = cells.filter((c): c is { f: Row[] } => !!c);
    const cacheKey = `${ra.toFixed(5)},${dec.toFixed(5)},${size}`;
    const res: Result = results.get(cacheKey) ?? { ra, dec, size, all: framesAt(ra, dec, found, meta), loaded: new Map(), skipped: new Map(), bytes: 0 };
    results.set(cacheKey, res);
    if (!res.all.length) {
      const partial = !!meta.partial;
      out.innerHTML = `<div class="sky-empty card card-pad">
        <p class="kicker">${esc(formatCoords(ra, dec))}</p>
        <h2 class="sky-empty-title">${partial ? 'This position is not in our index yet' : 'No SPHEREx images here'}</h2>
        <p>${partial ? esc(coverage) + ' SPHEREx may have imaged this position; our partial index cannot look it up yet.' : 'No image in the public SPHEREx releases (' + esc(meta.releases.join(', ').toUpperCase()) + ') covers this position.'}</p>
        <p><button class="btn btn-s sky-lucky">Take me to a covered spot${icon('arrow')}</button></p></div>`;
    } else renderViewer(res, o, my);
    out.scrollIntoView({ behavior: reducedMotion ? 'auto' : 'smooth', block: 'start' });
  };

  const renderViewer = (res: Result, o: { mover?: Mover; focusMjd?: number; name?: string }, my: number) => {
    const all = res.all;
    const nPass = all[all.length - 1].pass + 1, nVisit = all[all.length - 1].visit + 1;
    const releases = [...new Set(all.map((f) => f.release.toUpperCase()))].join(' + ');
    const scale = res.size / GRID; // arcsec per grid pixel
    out.innerHTML = `
      <div class="sky-facts">
        <span class="chip chip-real">Real data · NASA SPHEREx, read live from IRSA</span>
        <span class="sky-count mono">${esc(o.name ? o.name + ': ' : '')}${plural(all.length, 'image')} of this field, ${plural(nVisit, 'visit')}, ${plural(nPass, 'survey pass', 'survey passes')}, ${esc(releases)}</span>
      </div>
      <div class="sky-progress" role="status"><div class="sky-bar"><i></i></div><p class="mono"></p></div>
      <div class="sky-grid">
        <div class="sky-left">
          ${tabs([{ id: 'flip', label: 'Flipbook' }, { id: 'seasons', label: 'Seasons' }, { id: 'diff', label: 'Difference' }], 'flip', 'sky-tabs')}
          <figure class="sky-frame" tabindex="0" aria-label="SPHEREx images of this field. Arrow keys step through the images, space plays, click picks a pixel for the spectrum.">
            <canvas width="${GRID}" height="${GRID}"></canvas>
            <span class="sky-ring sky-pick" aria-hidden="true"></span>
            <span class="sky-ring sky-pred" aria-hidden="true" hidden></span>
            <span class="sky-scale mono" aria-hidden="true" style="width:${(30 / res.size) * 100}%">30"</span>
            <span class="sky-compass mono" aria-hidden="true">N up, E left</span>
          </figure>
          <p class="sky-cap mono"></p>
          <div class="sky-scrub">
            ${iconButton('prev', 'Previous image', 'sky-prev')}
            <button class="icon-btn tip sky-play" aria-label="Play" data-tip="Play or pause">${icon('play')}</button>
            ${iconButton('next', 'Next image', 'sky-next')}
            <input class="sky-range" type="range" min="0" max="0" value="0" aria-label="Image number">
          </div>
          <div class="sky-opts">
            <label class="chip sky-toggle"><input type="checkbox" class="sky-same"> Same wavelength only<span class="sky-band"></span></label>
            ${o.mover ? `<label class="chip sky-toggle"><input type="checkbox" class="sky-predon" checked> ${esc(o.mover.label)}</label>` : ''}
            <span class="sky-diffsel" hidden><select class="chip sky-a" aria-label="Earlier pass"></select><span class="mono">minus</span><select class="chip sky-b" aria-label="Later pass"></select></span>
          </div>
          <p class="hint sky-modehint"></p>
        </div>
        <div class="sky-right">
          <div class="card card-pad sky-spec">
            <p class="kicker">Spectrum of the ringed pixel</p>
            <div class="sky-chart"></div>
            <p class="hint">${chip('Quick look, not calibrated photometry', 'chip-gold')} SPHEREx's linear variable filters put each position at a different wavelength in each exposure, so every image adds one spectral point. Value: mean surface brightness within 6 arcsec of the ring, minus the median of the same cutout. Click or tap the image to move the ring.</p>
          </div>
          <p class="hint">Each cutout has its median background subtracted, and all cutouts share one stretch. SPHEREx pixels are ${PIXEL_ARCSEC} arcsec, so point sources are only a few pixels across. Dark blue marks pixels with no data, such as the overexposed core of a very bright star. ${esc(coverage)}</p>
          <button class="btn btn-s sky-more" hidden></button>
        </div>
      </div>`;
    const q = <T extends HTMLElement>(s: string) => out.querySelector(s) as T;
    const canvas = q<HTMLCanvasElement>('canvas'), g = canvas.getContext('2d')!;
    const frameEl = q('.sky-frame'), cap = q('.sky-cap'), range = q<HTMLInputElement>('.sky-range'), play = q<HTMLButtonElement>('.sky-play');
    const pick = q('.sky-pick'), pred = q('.sky-pred'), bar = q('.sky-bar i'), prog = q('.sky-progress p'), more = q<HTMLButtonElement>('.sky-more');
    const same = q<HTMLInputElement>('.sky-same'), predOn = out.querySelector('.sky-predon') as HTMLInputElement | null;
    const selA = q<HTMLSelectElement>('.sky-a'), selB = q<HTMLSelectElement>('.sky-b'), modeHint = q('.sky-modehint'), chart = q('.sky-chart');
    const image = g.createImageData(GRID, GRID);
    let mode: 'flip' | 'seasons' | 'diff' = 'flip';
    let band = 0; // detector number when "same colour only" is on
    let lastShown: Loaded | undefined;
    let spot: [number, number] = [GRID / 2, GRID / 2]; // grid pixel of the spectrum ring
    let pending = 0, t0 = 0, batchBytes = 0, batchRead = 0;
    const waves = new Map<number, WaveGrid | null>();

    const shown = () => [...res.loaded.values()].filter((l) => !band || l.frame.detector === band).sort((a, b) => a.mjd - b.mjd);
    const passes = () => {
      const by = new Map<number, Loaded[]>();
      for (const l of shown()) by.set(l.frame.pass, [...(by.get(l.frame.pass) ?? []), l]);
      return [...by.entries()].sort((a, b) => a[0] - b[0]).map(([pass, list]) => ({ pass, list, stack: medianStack(list.map((l) => l.data)), from: list[0].mjd, to: list[list.length - 1].mjd }));
    };
    const waveOf = (l: Loaded, gx = GRID / 2, gy = GRID / 2): number => {
      const grid = waves.get(l.frame.detector);
      const east = (GRID / 2 - gx) * scale, north = (GRID / 2 - gy) * scale;
      return grid ? waveAt(grid, l.x + l.jac[0] * east + l.jac[1] * north, l.y + l.jac[2] * east + l.jac[3] * north) : (l.frame.wlMin + l.frame.wlMax) / 2;
    };
    const place = (el: HTMLElement, radec: [number, number] | null) => {
      const off = radec && skyToOffset(res.ra, res.dec, radec[0], radec[1]);
      const x = off ? 50 - (off[0] / res.size) * 100 : -1, y = off ? 50 - (off[1] / res.size) * 100 : -1;
      el.hidden = !(x >= 0 && x <= 100 && y >= 0 && y <= 100);
      el.style.left = x + '%';
      el.style.top = y + '%';
    };
    const paint = (data: Float32Array, grey: (v: number) => number) => {
      for (let i = 0; i < data.length; i++) {
        const v = grey(data[i]);
        image.data[4 * i] = image.data[4 * i + 1] = image.data[4 * i + 2] = v;
        image.data[4 * i + 3] = 255;
        // no data (masked or saturated pixel): dark blue, so it is not read as black sky
        if (!Number.isFinite(data[i])) image.data.set([22, 36, 60], 4 * i);
      }
      g.putImageData(image, 0, 0);
    };

    const draw = () => {
      const list = shown();
      const stretch = sharedStretch(list.map((l) => l.data), list.map((l) => l.noise));
      const i = Math.min(+range.value, +range.max);
      let mjd: number | null = null;
      pred.hidden = true;
      if (!list.length) {
        cap.textContent = pending ? '' : 'No image could be shown for this position.';
        return;
      }
      if (mode === 'flip') {
        const l = (lastShown = list[i]);
        paint(l.data, (v) => toGrey(v, stretch));
        mjd = l.mjd;
        cap.innerHTML = `<span class="sky-date">${esc(plainDate(l.mjd))}</span>${chip(waveOf(l).toFixed(2) + ' µm', 'chip-blue')}<span>image ${i + 1} of ${list.length}</span><span>pass ${l.frame.pass + 1}</span>`;
      } else if (mode === 'seasons') {
        const p = passes()[i];
        paint(p.stack, (v) => toGrey(v, stretch));
        mjd = (p.from + p.to) / 2;
        cap.innerHTML = `<span class="sky-date">Pass ${p.pass + 1}</span><span>${esc(plainDate(p.from))} to ${esc(plainDate(p.to))}</span><span>${plural(p.list.length, 'image')} median-stacked</span>`;
      } else {
        const ps = passes();
        const a = ps.find((p) => p.pass === +selA.value), b = ps.find((p) => p.pass === +selB.value);
        if (!a || !b || a === b) {
          g.fillStyle = '#808080';
          g.fillRect(0, 0, GRID, GRID);
          cap.textContent = ps.length < 2 ? 'Only one pass is loaded here, so there is nothing to compare yet.' : 'Pick two different passes.';
          return;
        }
        const diff = b.stack.map((v, k) => v - a.stack[k]);
        const noise = 1.4826 * median(diff.map(Math.abs)) || 1e-6;
        paint(diff, (v) => diffGrey(v, 8 * noise));
        mjd = (b.from + b.to) / 2;
        cap.innerHTML = `<span class="sky-date">Pass ${b.pass + 1} minus pass ${a.pass + 1}</span><span>${plural(b.list.length, 'image')} minus ${plural(a.list.length, 'image')}</span>`;
      }
      if (o.mover && predOn?.checked && mjd !== null) place(pred, o.mover.at(mjd));
    };

    const spectrum = () => {
      const pts = [...res.loaded.values()]
        .map((l) => ({ um: waveOf(l, spot[0], spot[1]), v: apertureMean(l.data, GRID, spot[0], spot[1], PIXEL_ARCSEC / scale), noise: l.noise, pass: l.frame.pass, mjd: l.mjd }))
        .filter((p) => Number.isFinite(p.v));
      if (!pts.length) {
        chart.innerHTML = `<p class="empty">${pending ? 'Waiting for the first images...' : 'No data at this pixel.'}</p>`;
        return;
      }
      const W = 420, H = 230, L = 62, R = 10, T = 10, B = 36;
      const vs = pts.map((p) => p.v).sort((a, b) => a - b);
      const lo = Math.min(0, vs[Math.floor(vs.length * 0.02)]), hi = Math.max(vs[Math.min(vs.length - 1, Math.ceil(vs.length * 0.98))], lo + 1e-6);
      const y0 = lo - (hi - lo) * 0.08, y1 = hi + (hi - lo) * 0.12;
      const x = (u: number) => L + ((u - 0.7) / 4.4) * (W - L - R), y = (v: number) => T + (1 - (Math.min(y1, Math.max(y0, v)) - y0) / (y1 - y0)) * (H - T - B);
      const digits = y1 - y0 < 0.5 ? 3 : y1 - y0 < 5 ? 2 : 1;
      const yt = [0, 1, 2, 3, 4].map((k) => y0 + ((y1 - y0) * k) / 4).map((v) => `<line class="grid" x1="${L}" x2="${W - R}" y1="${y(v)}" y2="${y(v)}"/><text x="${L - 6}" y="${y(v) + 3}" text-anchor="end">${v.toFixed(digits)}</text>`).join('');
      const xt = [1, 2, 3, 4, 5].map((u) => `<line x1="${x(u)}" x2="${x(u)}" y1="${H - B}" y2="${H - B + 4}"/><text x="${x(u)}" y="${H - B + 16}" text-anchor="middle">${u}</text>`).join('');
      const zero = y0 < 0 && y1 > 0 ? `<line class="zero" x1="${L}" x2="${W - R}" y1="${y(0)}" y2="${y(0)}"/>` : '';
      const dots = pts.map((p) => `<g style="color:${PASS_COLOURS[p.pass % PASS_COLOURS.length]}"><line x1="${x(p.um).toFixed(1)}" x2="${x(p.um).toFixed(1)}" y1="${y(p.v - p.noise).toFixed(1)}" y2="${y(p.v + p.noise).toFixed(1)}"/><circle cx="${x(p.um).toFixed(1)}" cy="${y(p.v).toFixed(1)}" r="3"><title>${p.um.toFixed(2)} µm: ${p.v.toFixed(3)} MJy/sr, ${plainDate(p.mjd)}</title></circle></g>`).join('');
      const used = [...new Set(pts.map((p) => p.pass))].sort();
      const [east, north] = [(GRID / 2 - spot[0]) * scale, (GRID / 2 - spot[1]) * scale];
      const [sra, sdec] = offsetToSky(res.ra, res.dec, east, north);
      chart.innerHTML = `<svg class="sky-svg" viewBox="0 0 ${W} ${H}" role="img" aria-label="Brightness of the ringed pixel at ${pts.length} wavelengths between 0.7 and 5 micrometres">
          <g class="axis">${yt}${xt}${zero}<line x1="${L}" x2="${W - R}" y1="${H - B}" y2="${H - B}"/></g>
          <text class="axis-label" x="${(L + W - R) / 2}" y="${H - 3}" text-anchor="middle">wavelength (µm)</text>
          <text class="axis-label" transform="translate(9 ${(T + H - B) / 2}) rotate(-90)" text-anchor="middle">brightness (MJy/sr)</text>
          <g class="pts">${dots}</g></svg>
        <p class="sky-legend mono">${used.map((p) => `<span style="color:${PASS_COLOURS[p % PASS_COLOURS.length]}"><i></i>pass ${p + 1}</span>`).join('')}<span>bars: pixel noise</span><span>at ${esc(formatCoords(sra, sdec))}</span></p>`;
    };

    const refresh = () => {
      const n = mode === 'flip' ? shown().length : mode === 'seasons' ? passes().length : 1;
      range.max = String(Math.max(0, n - 1));
      if (+range.value > +range.max) range.value = range.max;
      q('.sky-scrub').classList.toggle('dim', mode === 'diff' || n < 2);
      q('.sky-diffsel').hidden = mode !== 'diff';
      if (mode === 'diff') {
        const ps = passes(), keepA = selA.value, keepB = selB.value;
        const opts = ps.map((p) => `<option value="${p.pass}">Pass ${p.pass + 1} (${esc(plainDate(p.from))})</option>`).join('');
        selA.innerHTML = selB.innerHTML = opts;
        selA.value = ps.some((p) => String(p.pass) === keepA) ? keepA : String(ps[0]?.pass ?? 0);
        selB.value = ps.some((p) => String(p.pass) === keepB) && keepB !== selA.value ? keepB : String(ps[ps.length - 1]?.pass ?? 0);
      }
      modeHint.textContent = mode === 'flip'
        ? 'Images in time order. Fixed sources stay put; anything that shifts between images is moving. Brightness also changes because each image samples a different wavelength.'
        : mode === 'seasons'
          ? 'Median stack of all loaded images from one survey pass. SPHEREx revisits each position about every 6 months.'
          : 'Difference image: later pass minus earlier pass. Grey means no change; a moving source appears as a negative (earlier position) next to a positive (later position).';
      play.innerHTML = icon(timer ? 'pause' : 'play');
      play.setAttribute('aria-label', timer ? 'Pause' : 'Play');
      draw();
    };
    const step = (d: number) => {
      const n = +range.max + 1;
      range.value = String((+range.value + d + n) % n);
      draw();
    };
    const toggle = (on = !timer) => {
      stopPlay();
      if (on && +range.max > 0) timer = window.setInterval(() => step(1), mode === 'flip' ? (reducedMotion ? 1100 : PLAY_MS) : 900);
      refresh();
    };

    const progress = () => {
      const left = res.all.length - res.loaded.size - res.skipped.size;
      bar.style.width = (batchRead ? ((batchRead - pending) / batchRead) * 100 : 100) + '%';
      const edge = [...res.skipped.values()].filter((r) => r === 'edge').length, bad = res.skipped.size - edge;
      if (pending) prog.textContent = `Reading image ${batchRead - pending + 1} of ${batchRead} from IRSA...`;
      else {
        const took = t0 ? `Read ${plural(batchRead, 'image')} in ${((performance.now() - t0) / 1000).toFixed(1)} s (${(batchBytes / 1e6).toFixed(1)} MB from IRSA). ` : '';
        prog.textContent = `${took}Showing ${res.loaded.size} of ${res.all.length}.${edge ? ` ${plural(edge, 'image')} skipped: the position falls on the detector edge.` : ''}${bad ? ` ${plural(bad, 'image')} could not be read from IRSA.` : ''}`;
        if (bad && !res.loaded.size) prog.innerHTML = `<span class="warn">Could not reach NASA's archive (nasa-irsa-spherex on AWS). Check the connection and try again.</span>`;
      }
      out.querySelector('.sky-progress')!.classList.toggle('done', !pending);
      more.hidden = !!pending || left <= 0;
      more.textContent = `Load ${Math.min(BATCH, left)} more (${fmt(left)} left)`;
    };

    const load = () => {
      const next = pickFrames(res.all, new Set([...res.loaded.keys(), ...res.skipped.keys()]), BATCH, o.focusMjd);
      if (!next.length) return progress();
      worker ??= new Worker(new URL('./sky/worker.ts', import.meta.url), { type: 'module' });
      pending = batchRead = next.length;
      batchBytes = 0;
      t0 = performance.now();
      const byKey = new Map(next.map((f) => [f.key, f]));
      worker.onmessage = (ev: MessageEvent<WorkerOut>) => {
        const m = ev.data;
        if (!alive || m.job !== my || my !== job) return;
        if (m.type === 'done') {
          pending = 0;
          progress();
          // start at the first photo, or at the moment a find was seen
          const list = shown(), focus = o.focusMjd;
          range.value = String(focus === undefined || mode !== 'flip' ? 0 : list.reduce((best, l, i) => (Math.abs(l.mjd - focus) < Math.abs(list[best].mjd - focus) ? i : best), 0));
          toggle(!reducedMotion && mode === 'flip' && focus === undefined);
          return;
        }
        const f = byKey.get(m.key)!;
        pending = Math.max(1, pending - 1);
        if (m.ok) {
          res.loaded.set(m.key, { frame: f, data: m.data, noise: m.noise, mjd: m.mjd, x: m.x, y: m.y, jac: m.jac });
          res.bytes += m.bytes;
          batchBytes += m.bytes;
          if (!waves.has(f.detector)) {
            waves.set(f.detector, null);
            loadGrid(f.detector).then((grid) => {
              waves.set(f.detector, grid);
              if (alive && my === job) (draw(), spectrum());
            });
          }
        } else {
          res.skipped.set(m.key, m.reason);
          if (m.reason === 'error') console.warn(`Sky: could not read ${BUCKET_URL}${m.key}: ${m.message}`);
        }
        // while reading, show the newest photo so the page feels alive
        if (m.ok && !timer && mode === 'flip') {
          range.max = String(shown().length - 1);
          range.value = String(shown().findIndex((l) => l.frame.key === m.key));
        }
        progress();
        refresh();
        spectrum();
      };
      worker.onerror = () => {
        pending = 0;
        prog.innerHTML = `<span class="warn">The image reader could not start in this browser.</span>`;
      };
      const req: LoadRequest = { type: 'load', job: my, base: BUCKET_URL, keys: next.map((f) => f.key), ra: res.ra, dec: res.dec, size: res.size, n: GRID };
      worker.postMessage(req);
      progress();
    };

    out.querySelector('.sky-tabs')!.addEventListener('click', (e) => {
      const b = (e.target as HTMLElement).closest('button');
      if (!b) return;
      stopPlay();
      mode = b.dataset.tab as typeof mode;
      out.querySelectorAll('.sky-tabs button').forEach((x) => x.setAttribute('aria-selected', String(x === b)));
      range.value = '0';
      refresh();
    });
    range.oninput = () => (stopPlay(), refresh());
    play.onclick = () => toggle();
    q('.sky-prev').onclick = () => (stopPlay(), step(-1), refresh());
    q('.sky-next').onclick = () => (stopPlay(), step(1), refresh());
    same.onchange = () => {
      const cur = lastShown ?? shown()[0];
      band = same.checked ? (cur?.frame.detector ?? 0) : 0;
      q('.sky-band').textContent = band && cur ? ` (band ${band}, ${cur.frame.wlMin.toFixed(1)} to ${cur.frame.wlMax.toFixed(1)} µm)` : '';
      range.value = mode === 'flip' ? String(Math.max(0, shown().indexOf(cur))) : '0';
      refresh();
    };
    if (predOn) predOn.onchange = draw;
    selA.onchange = selB.onchange = draw;
    more.onclick = () => (stopPlay(), load());
    frameEl.addEventListener('keydown', (e) => {
      if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') (stopPlay(), step(e.key === 'ArrowLeft' ? -1 : 1), refresh());
      else if (e.key === ' ') toggle();
      else return;
      e.preventDefault();
    });
    frameEl.addEventListener('click', (e) => {
      const r = canvas.getBoundingClientRect();
      spot = [((e.clientX - r.left) / r.width) * GRID, ((e.clientY - r.top) / r.height) * GRID];
      pick.style.left = (spot[0] / GRID) * 100 + '%';
      pick.style.top = (spot[1] / GRID) * 100 + '%';
      spectrum();
    });
    pick.style.width = pred.style.width = Math.max(7, ((2.4 * PIXEL_ARCSEC) / res.size) * 100) + '%';

    refresh();
    spectrum();
    if (res.loaded.size) progress();
    else load();
    if (res.loaded.size && !reducedMotion) toggle(true);
  };

  // ---------- inputs ----------
  const preset = async (id: string) => {
    const t = TARGETS.find((x) => x.id === id);
    if (t) {
      const at = properMotion(t.ra, t.dec, t.pmra, t.pmdec, t.epoch);
      const [ra, dec] = at(J2026);
      return show(ra, dec, { target: id, name: t.name, mover: { at, label: 'Predicted spot' } });
    }
    const f = FIELDS.find((x) => x.id === id);
    if (f) return show(f.ra, f.dec, { target: id, name: f.name });
    const o = finds.find((x) => x.slug === id);
    if (!o) return false;
    out.innerHTML = `<p class="sky-status mono">Looking up where SPHEREx saw ${esc(o.name)}...</p>`;
    try {
      const { data } = await ctx.load<ObjectLite>(o.page);
      const frames = (data.spherex?.frames ?? []).filter((f) => Number.isFinite(f.pred_ra) && Number.isFinite(f.pred_dec));
      const best = data.checks?.orbit_fit?.positions?.[0] ?? [...frames].sort((a, b) => (b.snr ?? -9) - (a.snr ?? -9)).map((f) => ({ mjd: f.mjd, ra: f.pred_ra, dec: f.pred_dec }))[0];
      if (!best) throw new Error('no position');
      const at = trackMover(frames.map((f) => ({ mjd: f.mjd, ra: f.pred_ra, dec: f.pred_dec })));
      const here = at(best.mjd) ?? [best.ra, best.dec];
      return show(here[0], here[1], { target: id, name: `${o.name}, where it was on ${plainDate(best.mjd)}`, focusMjd: best.mjd, mover: { at, label: 'Predicted spot' } });
    } catch {
      fail(`Could not load the position of ${o.name}.`);
    }
  };
  const lucky = async () => {
    fail('');
    for (let tries = 0; tries < 12; tries++) {
      const name = meta.cells?.length ? meta.cells[Math.floor(Math.random() * meta.cells.length)] : cellsFor(Math.random() * 360, (Math.asin(2 * Math.random() - 1) * 180) / Math.PI, meta.cell_deg, 0)[0];
      const rows = (await loadShard(name))?.f;
      if (!rows?.length) continue;
      const row = rows[Math.floor(Math.random() * rows.length)];
      // a point well inside that photo: its centre, moved by up to half a degree
      const [ra, dec] = offsetToSky(row[3], row[4], (Math.random() - 0.5) * 3600, (Math.random() - 0.5) * 3600);
      return show(ra, dec, { name: 'A random covered spot' });
    }
    fail('Could not find a covered spot. Try again.');
  };

  form.addEventListener('submit', (e) => {
    e.preventDefault();
    const c = parseCoords(input.value);
    if (!c) return fail('Could not read that position. Use degrees (133.7595 -7.2421) or hours and degrees (08 55 02.3 -07 14 31).');
    show(c.ra, c.dec);
  });
  sizeBtns.forEach((b) => b.addEventListener('click', () => {
    setSize(+b.dataset.size!);
    const p = new URLSearchParams(location.search);
    if (p.has('ra')) start(p);
  }));
  body.addEventListener('click', (e) => {
    const t = e.target as HTMLElement;
    const p = t.closest<HTMLElement>('[data-preset]');
    if (p) preset(p.dataset.preset!);
    else if (t.closest('.sky-lucky')) lucky();
  });
  body.querySelector('.sky-finds')?.addEventListener('change', (e) => {
    const s = e.target as HTMLSelectElement;
    if (s.value) preset(s.value);
    s.value = '';
  });

  // ---------- URL state: ?ra=&dec=&size= (and target= for a named preset) ----------
  const start = async (p: URLSearchParams) => {
    const ra = Number(p.get('ra')), dec = Number(p.get('dec')), target = p.get('target');
    if (target && (await preset(target)) !== false) return;
    if (p.has('ra') && p.has('dec') && ra >= 0 && ra < 360 && Math.abs(dec) <= 90) show(ra, dec);
  };
  const p = new URLSearchParams(location.search);
  setSize(Number(p.get('size')) || 120);
  if (p.has('ra') || p.has('target')) start(p);
  else out.innerHTML = `<p class="sky-idle hint">${meta.partial ? '' : esc(coverage) + ' '}Positions are RA and Dec in degrees (J2000), or RA in hours with minutes and seconds.</p>`;

  return () => {
    alive = false;
    stopPlay();
    worker?.postMessage({ type: 'cancel' });
    setUrl(null);
  };
};
