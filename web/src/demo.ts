// ?demo=1: the 28-second film we screen-record for the video. ?t=<seconds> jumps to a moment,
// ?guide=1 shows a REC-safe frame guide.
// The camera never goes closer than the orbit framing: small-scale things (the photo, the day
// photos, the uncertainty) are 2D overlays over the dimmed, slowly turning 3D map.
// Every frame is a pure function of t (see demo/timeline.ts), so a jump lands on the same picture.
import './styles/demo.css';
import type { ObjectPage } from './lib/types';
import type { Showcase } from './lib/rank';
import type { Scene } from './scene/Scene';
import type { UncertaintyCloud } from './scene/cloud';
import type { FlashFx } from './scene/flash';
import { loadIndex, resolveRel } from './lib/data';
import { orbitPolyline } from './lib/kepler';
import { mjdFromIso, plainDate } from './lib/time';
import { eclToThree } from './scene/asteroids';
import { el } from './ui/dom';
import { store } from './state';
import { DemoFx } from './demo/fx';
import {
  DURATION, MOON_KM, T, captionAt, captionHtml, demoFacts, millionKm, moons, mjdAt, orbitPose,
  poseAt, poseToCamera, ramp, shotAt, cubicOut, type CapId, type DemoFacts,
} from './demo/timeline';

export async function runDemo(o: {
  scene: Scene;
  cloud: UncertaintyCloud;
  flash: FlashFx;
  showcase: Showcase | null;
  page: (slug: string) => Promise<ObjectPage>;
  ui: HTMLElement;
}) {
  const { scene, flash, ui } = o;
  const params = new URLSearchParams(location.search);
  document.body.classList.add('demo', 'explored');
  flash.muted = true; // the film draws its own beam and card
  scene.autoRotate = false;
  scene.controls.enabled = false;
  store.setPlaying(false);

  const src = await loadIndex();
  const objects = src.index.objects;
  const want = params.get('flash') ?? '2025yh5';
  const obj = objects.find((x) => x.slug === want) ?? o.showcase?.object;
  if (!obj) return;
  const p = await o.page(obj.slug);
  const f = demoFacts(objects, obj, p);
  const url = (rel: string) => resolveRel(src.base + obj.page, rel);

  const root = el('div', { class: 'dm' });
  root.innerHTML = `
    <div class="dm-dim"></div><div class="dm-white"></div>
    <div class="dm-panel">
      <div class="dm-card">
        <div class="dm-card-kick"></div>
        <div class="dm-photo"><img class="dm-stack" alt=""><i class="dm-ring"></i></div>
        <div class="dm-days"></div>
        <div class="dm-card-foot"></div>
      </div>
      <div class="dm-info">${infoHtml(f)}</div>
    </div>
    <div class="dm-title"></div>
    <div class="dm-cap"></div>
    <div class="dm-end"><b>Rewind</b><span>Every discovery has a <em>past.</em></span><small>NASA SPHEREx data / NASA Space Apps 2026 / Team SpaceX</small></div>
    ${params.get('guide') === '1' ? '<div class="dm-guide"><i></i><i></i><span>REC-safe</span></div>' : ''}`;
  ui.appendChild(root);
  const $ = <E extends HTMLElement = HTMLElement>(s: string) => root.querySelector(s) as E;
  const [dim, white, panel, card, info, title, cap, end] = ['.dm-dim', '.dm-white', '.dm-panel', '.dm-card', '.dm-info', '.dm-title', '.dm-cap', '.dm-end'].map((s) => $(s));
  const stack = $<HTMLImageElement>('.dm-stack');
  stack.src = url(p.spherex.stack.png);
  const days = f.dayPngs.map((png) => {
    const im = el('img', { alt: '' });
    im.src = url(png);
    $('.dm-days').appendChild(im);
    return im;
  });
  const sd = p.spherex.days;
  $('.dm-card-kick').textContent = sd.length ? `NASA SPHEREx · ${plainDate(sd[0].iso)} to ${plainDate(sd[sd.length - 1].iso)}` : 'NASA SPHEREx';
  const foot = $('.dm-card-foot');
  const ring = $('.dm-ring');
  const blue = $<SVGCircleElement & HTMLElement>('.dm-c-blue'), gold = $<SVGCircleElement & HTMLElement>('.dm-c-gold');
  const [numA, numB] = [$('.dm-num-a'), $('.dm-num-b')];
  // wait for the pictures so the recording never shows a half-loaded card
  await Promise.all([stack, ...days].map((im) => im.decode().catch(() => undefined)));

  // the framings, from the data at discovery
  const disc = mjdFromIso(f.discoveredIso);
  const dot = scene.rewindDot(f.slug);
  const at = scene.rewindPositionAt(f.slug, disc);
  const pts: [number, number, number][] = [[0, 0, 0]];
  for (let k = 0; k < 24; k++) pts.push([Math.cos((k / 24) * Math.PI * 2), 0, Math.sin((k / 24) * Math.PI * 2)]);
  if (dot) for (const v of orbitPolyline(dot.el, 128, 4)) pts.push(eclToThree(v).toArray() as [number, number, number]);
  if (at) pts.push(at.toArray() as [number, number, number]);
  const [w0, h0] = scene.viewSize;
  const orbit = orbitPose(pts, at ? (at.toArray() as [number, number, number]) : [1, 0, 0], scene.camera.fov, w0 / h0);
  const fx = new DemoFx(scene, f.slug, f.findSlugs);

  const today = store.today;
  const start = Math.min(DURATION, Math.max(0, Number(params.get('t')) || 0));
  const t0 = performance.now() - start * 1000;
  let lastCap: CapId | null | undefined;
  let lastShift = -1;
  const on = (e: HTMLElement, v: boolean) => e.classList.contains('on') !== v && e.classList.toggle('on', v);

  scene.addHook(() => {
    const t = Math.min(DURATION + 2, (performance.now() - t0) / 1000);
    const shot = shotAt(t);
    // clock and camera
    store.setTime(mjdAt(t, today, disc, f.earliestMjd));
    const pose = poseAt(t, orbit);
    scene.controls.target.set(...pose.target);
    scene.camera.position.set(...poseToCamera(pose));
    const panelOn = t >= T.flash && t < T.orbitOut;
    const shift = panelOn ? Math.round(scene.viewSize[0] * 0.2) : 0;
    if (shift !== lastShift) scene.setViewShift((lastShift = shift), 0);

    // map extras
    fx.update(t, {
      orbit: ramp(t, 3.5, 5) * (1 - 0.5 * ramp(t, 22, 23)) * (1 - 0.5 * ramp(t, 26, 27)),
      beam: ramp(t, T.flash, T.flash + 0.2) * (1 - 0.6 * ramp(t, 12.6, 13.4)) * (1 - ramp(t, 21.4, 22)),
      beamGrow: ramp(t, T.flash, T.flash + 0.6, cubicOut),
      hero: ramp(t, 4, 5) * (1 - ramp(t, 22, 22.5)),
      finds: ramp(t, 22.4, 23.2) * (1 - 0.6 * ramp(t, 26, 26.6)),
    });
    dim.style.opacity = String(0.4 * ramp(t, T.flash, T.flash + 0.4) * (1 - ramp(t, 21.6, 22.4)) + 0.6 * ramp(t, 26, 26.6));
    white.style.opacity = t >= T.flash && t < T.flash + 0.6 ? String(0.32 * (1 - ramp(t, T.flash, T.flash + 0.6, cubicOut))) : '0';

    // the overlay panel: the photo card, then the uncertainty infographic
    on(panel, panelOn);
    on(card, t < 17);
    on(info, t >= 17);
    const lit = Math.max(0, Math.min(days.length, Math.floor((t - T.daysFrom) / T.dayStep) + 1));
    const merge = ramp(t, T.merge, T.merge + 0.5);
    if (shot === 'stack' || shot === 'cloud') {
      const tw = days[0] ? days[0].offsetWidth + 4 : 0, ph = stack.offsetHeight;
      days.forEach((im, i) => {
        im.classList.toggle('lit', i < lit);
        im.style.transform = `translate(${(days.length / 2 - 0.5 - i) * tw * merge}px, ${-ph * 0.5 * merge}px) scale(${1 - 0.7 * merge})`;
        im.style.opacity = shot === 'stack' ? String((i < lit ? 1 : 0.18) * (1 - merge)) : '0';
      });
    } else days.forEach((im) => (im.style.opacity = '0'));
    stack.style.opacity = shot === 'stack' ? String(Math.max(0.06 + 0.5 * (lit / Math.max(1, days.length)) ** 1.5, merge)) : '1';
    on(ring, (t >= T.flash + 0.5 && t < 13) || t >= T.merge + 0.4);
    const footText = shot === 'stack' ? 'No single photo shows it. Only the stack does.' : `${f.stackFrames} photos stacked${f.snr != null ? ` · S/N ${f.snr.toFixed(1)}` : ''}`;
    if (foot.textContent !== footText) foot.textContent = footText;
    if (f.cloud) {
      const r0 = 90, r1 = 90 * (f.cloud.afterKm / f.cloud.beforeKm);
      const s = ramp(t, T.shrinkFrom, T.shrinkTo);
      blue.setAttribute('r', String(r0 * ramp(t, 17.2, 18, cubicOut)));
      blue.style.opacity = String(1 - 0.75 * s);
      gold.setAttribute('r', String(r0 + (r1 - r0) * s));
      gold.style.opacity = String(Math.min(1, s * 3));
      on(numA, t >= 17.4);
      on(numB, t >= T.shrinkTo - 0.2);
      numA.classList.toggle('past', t >= T.shrinkTo - 0.2);
    }

    // one caption at a time
    const c = captionAt(t);
    if (c !== lastCap) {
      lastCap = c;
      const target = c === 'title' ? title : c === 'end' ? end : cap;
      for (const e of [title, cap, end]) if (e !== target) on(e, false);
      if (c && c !== 'end') {
        const html = captionHtml(c, f);
        // let the previous lower third fade out (300 ms) before the new words appear
        if (target === cap && cap.classList.contains('on')) {
          on(cap, false);
          setTimeout(() => lastCap === c && ((cap.innerHTML = html), on(cap, true)), 300);
        } else {
          target.innerHTML = html;
          on(target, true);
        }
      } else if (c === 'end') on(end, true);
      else on(cap, false);
    }
    if (c === 'rewind') {
      const d = cap.querySelector('.dm-date');
      if (d) d.textContent = plainDate(store.mjd);
    }
  });
}

/** The uncertainty infographic, drawn to scale with Earth and the Moon's orbit. */
function infoHtml(f: DemoFacts): string {
  const c = f.cloud;
  if (!c) return '';
  const moon = 90 * (MOON_KM / c.beforeKm);
  const at = c.atIso ? ` on ${plainDate(c.atIso)}` : '';
  return `
    <div class="dm-card-kick">Where ${f.name} could be${at}</div>
    <div class="dm-info-body">
      <svg viewBox="-100 -100 200 222" aria-hidden="true">
        <defs><radialGradient id="dmBlue"><stop offset="0" stop-color="#6aa8ff" stop-opacity=".55"/><stop offset="1" stop-color="#6aa8ff" stop-opacity=".12"/></radialGradient></defs>
        <circle class="dm-c-blue" r="0" fill="url(#dmBlue)" stroke="#8cbcff" stroke-width=".8"/>
        <circle class="dm-c-gold" r="90" fill="rgba(255,195,90,.28)" stroke="#ffc35a" stroke-width="1.4"/>
        <circle r="1.8" fill="#fff"/>
        <g transform="translate(-86 108)">
          <circle r="${moon.toFixed(2)}" fill="none" stroke="#fff" stroke-opacity=".8" stroke-width=".6" stroke-dasharray="1.6 1.6"/>
          <circle r="1.6" fill="#9fd0ff"/>
          <text x="${(moon + 4).toFixed(1)}" y="2" class="dm-svg-label">Earth and the Moon's orbit, same scale</text>
        </g>
      </svg>
      <div class="dm-nums">
        <div class="dm-num dm-num-a"><small>On discovery day</small><b>${millionKm(c.beforeKm)}</b><span>about ${moons(c.beforeKm)} Earth-Moon distances</span></div>
        <div class="dm-num dm-num-b gold"><small>With SPHEREx's older photos</small><b>${millionKm(c.afterKm)}</b><span>about ${moons(c.afterKm)} Earth-Moon distances</span></div>
      </div>
    </div>
    <div class="dm-card-foot">${c.label}</div>`;
}
