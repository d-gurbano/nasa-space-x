// The SPHEREx picture in the star card, with its controls beside it. Ways to look:
//  blink: the first pass and the last, back and forth, with the motion drawn beside the star;
//  passes: a flipbook of the pass pictures (all photos of one pass added up);
//  photos: a flipbook of single SPHEREx photos in time order, with the predicted spot ringed;
//  wavelength (WISE 0855): one photo per wavelength, invisible until about 4 µm.
import type { StarManifest } from '../../lib/types';
import { mjdFromIso, plainDate } from '../../lib/time';
import { icon } from '../../ui/components';
import { esc } from '../../ui/dom';
import { rel } from '../page';
import { passSpots } from '../stars/logic';

export type Mode = 'blink' | 'passes' | 'photos' | 'wave';
/** WISE 0855 is seen only beyond this wavelength (µm). */
export const SHOWS_FROM = 3.9;

/** A bar as long as one SPHEREx pixel, bottom left. */
function scaleBar(m: StarManifest): string {
  if (!m.image) return '';
  const w = m.image.spherex_pixel_arcsec / m.image.arcsec_per_png_px, y = m.image.size_px - 18;
  return `<g class="s3v-scale"><path d="M16,${y - 4}v8m0,-4h${w.toFixed(1)}m0,-4v8"/><text x="16" y="${y - 12}">1 SPHEREx pixel</text></g>`;
}

/** Ticks around a point, leaving the star itself clear. */
const cross = (p: [number, number], gap: number, len: number, cls: string) =>
  `<path class="${cls}" d="${[[1, 0], [-1, 0], [0, 1], [0, -1]].map(([x, y]) => `M${p[0] + x * gap},${p[1] + y * gap}l${x * len},${y * len}`).join('')}"/>`;

/** The motion from the first pass to the last: where it was, and an arrow to where it went. */
function motion(m: StarManifest): string {
  const spots = passSpots(m), a = spots[0], b = spots[spots.length - 1];
  if (!m.image || !a || !b) return '';
  const len = Math.hypot(b[0] - a[0], b[1] - a[1]);
  if (len < 12) return '';
  const ux = (b[0] - a[0]) / len, uy = (b[1] - a[1]) / len;
  const [nx, ny] = uy >= 0 ? [uy, -ux] : [-uy, ux];
  const off = 84, at = (p: [number, number], d: number, back = 0) => `${(p[0] + nx * d - ux * back).toFixed(1)},${(p[1] + ny * d - uy * back).toFixed(1)}`;
  const months = Math.round((mjdFromIso(m.seasons[m.seasons.length - 1].iso) - mjdFromIso(m.seasons[0].iso)) / 30.44);
  const mid: [number, number] = [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2], [tx, ty] = at(mid, off + 18).split(',');
  return `<g class="s3v-arrow">
    <text x="${tx}" y="${(+ty + 6).toFixed(1)}">${months >= 11 && months <= 13 ? '1 year' : `${months} months`}</text>
    ${cross(a, 30, 22, 's3v-then')}
    <path class="s3v-ext" d="M${at(a, 40)}L${at(a, off + 8)}M${at(b, 40)}L${at(b, off + 8)}"/>
    <path class="s3v-shaft" d="M${at(a, off)}L${at(b, off, 6)}"/>
    <path class="s3v-tip" d="M${at(b, off)}L${at(b, off - 7, 15)}L${at(b, off + 7, 15)}Z"/>
  </g>`;
}

export interface Viewer { el: HTMLElement; /** The column beside the picture; the card adds its own lines here. */ side: HTMLElement; stop(): void }

export function viewer(m: StarManifest, url: string, modes: Mode[], reduced: boolean): Viewer {
  const size = m.image?.size_px ?? 64, n = m.seasons.length;
  const frames = [...m.frames].sort((a, b) => a.mjd - b.mjd);
  // a few frames have no wavelength in the manifest (NaN, read as null)
  const waves = m.frames.filter((f) => Number.isFinite(f.wavelength_um)).sort((a, b) => a.wavelength_um - b.wavelength_um);
  const um = (f: { wavelength_um: number }) => (Number.isFinite(f.wavelength_um) ? `${f.wavelength_um.toFixed(2)} µm` : 'wavelength not recorded');
  const from = waves.findIndex((f) => f.wavelength_um >= SHOWS_FROM);
  const pass = (k: number) => rel(url, m.seasons[k].png);
  const LABEL: Record<Mode, string> = { blink: 'Before / after', passes: `${n} passes`, photos: `${frames.length} images`, wave: 'Wavelength' };
  let mode = modes[0], k = 0, timer = 0, playing = !reduced;

  const el = document.createElement('div');
  el.className = 's3v';
  el.innerHTML = `
    <figure class="s3v-stage">
      <img class="s3v-img" width="${size}" height="${size}" alt="">
      <svg class="s3v-over" viewBox="0 0 ${size} ${size}" aria-hidden="true"><g class="s3v-mode"></g><circle class="s3v-ring" r="26"/>${scaleBar(m)}</svg>
      <figcaption class="s3v-tag mono"></figcaption>
    </figure>
    <div class="s3v-side">
    <div class="s3v-bar">
      ${modes.length > 1 ? `<div class="seg s3v-modes" role="tablist" aria-label="How to look">${modes.map((x) => `<button type="button" role="tab" data-mode="${x}" aria-selected="${x === mode}">${LABEL[x]}</button>`).join('')}</div>` : ''}
      <button type="button" class="icon-btn s3v-play" aria-label="Pause"></button>
      <input class="s3v-range" type="range" min="0" value="0" aria-label="Image">
    </div>
    <p class="s3v-read" aria-live="polite"></p>
    </div>`;
  [...m.seasons.map((_, i) => pass(i)), ...frames.slice(0, 12).map((f) => rel(url, f.png))].forEach((s) => (new Image().src = s));

  const q = <T extends Element>(s: string) => el.querySelector(s) as T;
  const img = q<HTMLImageElement>('.s3v-img'), tag = q<HTMLElement>('.s3v-tag'), over = q<SVGGElement>('.s3v-mode');
  const ring = q<SVGCircleElement>('.s3v-ring'), range = q<HTMLInputElement>('.s3v-range'), play = q<HTMLButtonElement>('.s3v-play'), read = q<HTMLElement>('.s3v-read');
  const arrow = motion(m);

  const count = () => (mode === 'blink' ? 2 : mode === 'passes' ? n : mode === 'photos' ? frames.length : waves.length);
  const paint = () => {
    const kk = Math.min(k, count() - 1);
    ring.style.display = 'none';
    if (mode === 'blink') {
      const last = kk === 1;
      img.src = pass(last ? n - 1 : 0);
      img.alt = `${m.name}, SPHEREx pass of ${plainDate(m.seasons[last ? n - 1 : 0].iso)}`;
      tag.innerHTML = `<b>${last ? 'After' : 'Before'}</b> ${esc(plainDate(m.seasons[last ? n - 1 : 0].iso))}`;
      read.textContent = '';
    } else if (mode === 'passes') {
      img.src = pass(kk);
      img.alt = `${m.name}, stack of all SPHEREx images from the pass of ${plainDate(m.seasons[kk].iso)}`;
      tag.innerHTML = `<b>${kk + 1}/${n}</b> ${esc(plainDate(m.seasons[kk].iso))}`;
      read.textContent = 'Each frame is the stack of all images from one survey pass.';
    } else if (mode === 'photos') {
      const f = frames[kk];
      img.src = rel(url, f.png);
      img.alt = `${m.name}, one SPHEREx image, ${um(f)}, ${plainDate(f.iso)}`;
      tag.innerHTML = `<b>${kk + 1}/${frames.length}</b> ${esc(plainDate(f.iso))}`;
      ring.style.display = '';
      ring.setAttribute('cx', String(f.pred_xy[0]));
      ring.setAttribute('cy', String(f.pred_xy[1]));
      read.textContent = `${um(f)}. The ring marks the predicted spot.`;
    } else {
      const f = waves[kk], on = f.wavelength_um >= SHOWS_FROM;
      img.src = rel(url, f.png);
      img.alt = `${m.name} at ${f.wavelength_um.toFixed(2)} micrometres, ${plainDate(f.iso)}`;
      tag.innerHTML = `<b>${f.wavelength_um.toFixed(2)} µm</b> ${esc(plainDate(f.iso))}`;
      ring.style.display = '';
      ring.classList.toggle('on', on);
      ring.setAttribute('cx', String(f.pred_xy[0]));
      ring.setAttribute('cy', String(f.pred_xy[1]));
      read.innerHTML = on
        ? `<span class="chip chip-gold">It can show here</span> Beyond ${SHOWS_FROM} µm it glows faintly in the ring.${f.iso.startsWith('2026') ? ' In 2026 a background star can blend in.' : ''}`
        : `<span class="chip">Too cold to show</span> A source near the ring is the background star, not WISE 0855.`;
      range.setAttribute('aria-valuetext', `${f.wavelength_um.toFixed(2)} micrometres`);
    }
    over.innerHTML = mode === 'blink' ? arrow : '';
    range.value = String(kk);
  };
  const run = (on: boolean) => {
    clearInterval(timer);
    playing = on;
    timer = on ? window.setInterval(() => ((k = (k + 1) % count()), paint()), mode === 'blink' ? 700 : mode === 'passes' ? 420 : mode === 'photos' ? 260 : 220) : 0;
    play.innerHTML = icon(on ? 'pause' : 'play');
    play.setAttribute('aria-label', on ? 'Pause' : 'Play');
  };
  const setMode = (x: Mode) => {
    mode = x;
    el.dataset.mode = x;
    range.max = String(count() - 1);
    range.hidden = x === 'blink' || count() < 3;
    range.setAttribute('aria-label', x === 'wave' ? 'Wavelength of the image' : 'Image');
    el.querySelectorAll<HTMLElement>('[data-mode]').forEach((b) => b.setAttribute('aria-selected', String(b.dataset.mode === x)));
    // the wavelength reveal starts short and plays up to where WISE 0855 appears
    k = 0;
    paint();
    run(x !== 'wave' && !reduced);
    if (x === 'wave' && !reduced) sweep();
  };
  /** Glide the wavelength from the shortest to well inside the band where it shows, once. */
  let sweepRaf = 0;
  const sweep = () => {
    const end = from >= 0 ? from + Math.round((waves.length - 1 - from) * 0.6) : waves.length - 1, t0 = performance.now();
    const step = (now: number) => {
      const f = Math.min(1, (now - t0) / 2600);
      k = Math.round(end * (1 - (1 - f) ** 2));
      paint();
      sweepRaf = f < 1 && mode === 'wave' ? requestAnimationFrame(step) : 0;
    };
    sweepRaf = requestAnimationFrame(step);
  };
  el.querySelectorAll<HTMLButtonElement>('[data-mode]').forEach((b) => (b.onclick = () => setMode(b.dataset.mode as Mode)));
  play.onclick = () => {
    cancelAnimationFrame(sweepRaf);
    run(!playing);
  };
  range.oninput = () => {
    cancelAnimationFrame(sweepRaf);
    run(false);
    k = +range.value;
    paint();
  };
  setMode(mode);
  return {
    el,
    side: q<HTMLElement>('.s3v-side'),
    stop: () => {
      clearInterval(timer);
      cancelAnimationFrame(sweepRaf);
    },
  };
}
