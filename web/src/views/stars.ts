// Challenge stars: the Sun's neighbourhood in 3D, with the five NASA challenge targets at
// their real distances and a time slider that moves every star along its real space motion.
// Clicking a star (or the Sun) flies to a close-up and opens a compact card with three tabs:
// what SPHEREx saw (the blink and flipbook, the wavelength reveal for WISE 0855, the honest
// "too bright" story for the two bright ones), the facts, and the years-of-motion chart.
import '../styles/page-stars.css';
import type { StarManifest } from '../lib/types';
import { mjdFromIso, plainDate } from '../lib/time';
import { icon, stat, stats } from '../ui/components';
import { esc, fmt, plural, provenance } from '../ui/dom';
import { reducedMotion } from '../state';
import type { View, ViewCtx } from './page';
import { curveChart, sky, trackChart } from './stars/charts';
import { lightCurve, parseCsv, track } from './stars/logic';
import { closest, compare, PC_TO_LY, speeds, STARS, SUN, tempLabel, yearLabel, type Kind, type Star } from './stars3d/motion';
import { Neighbourhood } from './stars3d/scene';
import { viewer, type Mode } from './stars3d/viewer';

interface Target {
  extra: string;
  kind: 'mover' | 'cold' | 'bright';
  why: string;
  honest: string;
  tone: 'ok' | 'warn';
  /** Days between two maxima of a pulsating star, from the AAVSO catalogue. */
  period?: number;
}

// The honest notes come from the challenge-target analysis (data/05-test-targets/REPORT.md).
const TARGETS: Record<string, Target> = {
  barnard: {
    extra: 'barnard', kind: 'mover', tone: 'ok',
    why: 'The largest proper motion of any star (10.4″ per year, Gaia DR3): almost two SPHEREx pixels a year, so its motion is visible across the survey.',
    honest: 'Saturated in every SPHEREx image: its position is measured from the wings of the point-spread function.',
  },
  epsindib: {
    extra: 'eps_indi_b', kind: 'mover', tone: 'ok',
    why: 'A binary brown dwarf moving 4.7″ per year, less than one SPHEREx pixel (6.2″): a test of sub-pixel motion.',
    honest: 'The two brown dwarfs are too close for SPHEREx to separate, so they show as one dot.',
  },
  wise0855: {
    extra: 'wise0855', kind: 'cold', tone: 'warn',
    why: 'The coldest known brown dwarf. It shows up only at the longest wavelengths SPHEREx sees.',
    honest: 'In 2026 it passes about 6.6 arcsec from a brighter background star. That star blends into the measured motion and brightness, and causes the "detections" at short wavelengths.',
  },
  rwaur: {
    extra: 'rw_aur', kind: 'bright', tone: 'warn',
    why: 'A young star still wrapped in dust, with a brightness that keeps changing: a test of what to say when a target is too bright.',
    honest: 'Too bright for SPHEREx in most photos. The brightness changes we see are only indicative.',
  },
  rdra: {
    extra: 'r_dra', kind: 'bright', tone: 'warn', period: 246,
    why: 'A giant star that swells and fades every 246 days. Far too bright for SPHEREx to measure.',
    honest: 'Too bright for SPHEREx in most photos: the pictures show its glow, not a precise brightness or position.',
  },
};

const KIND: Record<Kind, string> = {
  sun: 'Our star', 'red dwarf': 'Red dwarf', 'brown dwarf': 'Brown dwarf', 'young variable star': 'Young variable star',
  'pulsating red giant': 'Pulsating red giant', context: 'Bright neighbour',
};
const hex = (c: number) => '#' + c.toString(16).padStart(6, '0');
const T0 = -10_000, T1 = 12_000, NOW = 2026;
const NEAREST = closest(STARS.find((s) => s.id === 'barnard')!);

interface Summary {
  n_frames?: number; n_passes?: number; n_saturated?: number; n_centroid_ok?: number;
  pred_shift_arcsec?: number; meas_shift_arcsec?: number; meas_shift_px?: number;
  first_pass?: string; last_pass?: string; decades_median_resid_arcsec?: number;
}

/** A text file from public/extra, or null when it is not there (the dev server answers with the app page). */
async function text(path: string): Promise<string | null> {
  try {
    const r = await fetch(path);
    if (!r.ok) return null;
    const t = await r.text();
    return t.trimStart().startsWith('<') ? null : t;
  } catch {
    return null;
  }
}

function summaryOf(t: string | null): Summary | null {
  try {
    return t ? JSON.parse(t.replace(/\bNaN\b/g, 'null')) : null;
  } catch {
    return null;
  }
}

interface Loaded { m: StarManifest; url: string; sample: boolean; sum: Summary | null; pos: string | null; lc: string | null }
const cache = new Map<string, Promise<Loaded>>();
function load(ctx: ViewCtx, slug: string, t: Target): Promise<Loaded> {
  if (!cache.has(slug)) {
    const x = `extra/stars/${t.extra}`, bright = t.kind === 'bright';
    cache.set(slug, Promise.all([
      ctx.load<StarManifest>(`stars/${slug}/manifest.json`),
      text(`${x}_summary.json`),
      bright ? null : text(`${x}_decades_positions.csv`),
      bright ? text(`${x}_lightcurve.csv`) : null,
    ]).then(([{ data, url, sample }, s, pos, lc]) => ({ m: data, url, sample, sum: summaryOf(s), pos, lc })));
    cache.get(slug)!.catch(() => cache.delete(slug));
  }
  return cache.get(slug)!;
}

/** "Moved 10.4 arcsec in a year: 1.7 SPHEREx pixels." */
function moved(sum: Summary | null): { big: string; small: string } | null {
  if (sum?.meas_shift_arcsec == null || sum.meas_shift_px == null || !sum.first_pass || !sum.last_pass) return null;
  const months = Math.round((mjdFromIso(sum.last_pass) - mjdFromIso(sum.first_pass)) / 30.44);
  const span = months >= 11 && months <= 13 ? 'a year' : plural(months, 'month');
  return {
    big: `Moved ${sum.meas_shift_arcsec.toFixed(1)} arcsec in ${span}: ${sum.meas_shift_px.toFixed(1)} SPHEREx pixels.`,
    small: sum.pred_shift_arcsec != null ? `Predicted from the star catalogue: ${sum.pred_shift_arcsec.toFixed(1)} arcsec.` : '',
  };
}

type Tab = 'view' | 'facts' | 'motion';

const lightYears = (s: Star) => {
  const ly = s.dist * PC_TO_LY;
  return ly >= 100 ? fmt(Math.round(ly / 10) * 10) : ly.toFixed(1);
};

/** The Facts tab: four numbers and one line. Sizes and temperatures are published values. */
function facts(s: Star, why: string): string {
  const c = compare(s), sp = speeds(s);
  const wide = `${s.rsun >= 100 ? 'about ' : ''}${c.ratio >= 100 ? fmt(c.ratio) : c.ratio >= 10 ? c.ratio.toFixed(0) : c.ratio.toFixed(1)} ×`;
  return `${stats([
    s.kind === 'sun' ? stat('8.3 light-minutes', 'from Earth') : stat(`${lightYears(s)} light-years`, s.far ? 'away: not to scale on the map' : 'from the Sun'),
    stat(tempLabel(s.temp), s.kind === 'brown dwarf' ? 'in its clouds' : 'at the surface'),
    stat(wide, c.body === 'Sun' ? "the Sun's width" : "Jupiter's width"),
    ...(s.kind === 'sun' ? [] : [stat(`${sp.total.toFixed(0)} km/s`, s.rv == null ? 'across the sky' : 'through space')]),
  ], 's3c-stats')}
  <p class="s3c-why">${esc(why)}</p>
  <p class="s3c-foot">Size and temperature are published values, rounded. Rewind did not measure them.</p>`;
}

export const starsView: View = async (body, ctx) => {
  const off: (() => void)[] = [];
  let tabOff: (() => void)[] = [];
  let token = 0, selected: string | null = null, year = NOW;

  body.innerHTML = `
    <div class="s3">
      <div class="s3-stage">
        <div class="s3-intro">
          <p class="s3-lead">The five targets named in the NASA challenge: three stars and two brown dwarfs (one of them a binary). <b>Select one.</b></p>
          <ul class="s3-legend">
            ${(['red dwarf', 'brown dwarf', 'young variable star', 'pulsating red giant'] as Kind[]).map((k) => `<li><i style="--c: ${hex(STARS.find((s) => s.kind === k)!.color)}"></i>${KIND[k]}</li>`).join('')}
            <li><i class="s3-lg-trace"></i>Tap a star to see its path</li>
          </ul>
        </div>
        <div class="s3-moment" role="status" hidden>
          <p class="mono">Closest approach, around the year ${esc(yearLabel(Math.round(NEAREST.year / 50) * 50))}</p>
          <p class="s3-moment-big">Barnard's Star passes the Sun at <b>${(NEAREST.dist * PC_TO_LY).toFixed(1)} light-years</b></p>
        </div>
        <section class="s3-card" aria-label="Star details" hidden>
          <header class="s3c-head">
            <div class="s3c-id"></div>
            <div class="seg s3c-tabs" role="tablist" aria-label="What to show"></div>
            <button type="button" class="s3c-close" aria-label="Close">&times;</button>
          </header>
          <div class="s3c-body" role="tabpanel"></div>
        </section>
        <div class="s3-zoom">
          <button type="button" class="icon-btn" data-zoom="0.8" aria-label="Zoom in">+</button>
          <button type="button" class="icon-btn" data-zoom="1.25" aria-label="Zoom out">&minus;</button>
          <p class="s3-zoom-hint">${matchMedia('(pointer: coarse)').matches ? 'Pinch to zoom' : 'Click the map, then scroll to zoom'}</p>
        </div>
        <div class="s3-time">
          <button type="button" class="icon-btn s3-play" aria-label="Play through time">${icon('play')}</button>
          <div class="s3-year"><b class="s3-year-n">${NOW}</b><span class="s3-year-rel mono">Today</span></div>
          <div class="s3-track">
            <input class="s3-range" type="range" min="${T0}" max="${T1}" step="1" value="${NOW}" aria-label="Year">
            <button type="button" class="s3-mark s3-mark-now" style="--at: ${((NOW - T0) / (T1 - T0)).toFixed(4)}" data-year="${NOW}" aria-label="Back to today"><span>Today</span></button>
            <button type="button" class="s3-mark s3-mark-gold" style="--at: ${((NEAREST.year - T0) / (T1 - T0)).toFixed(4)}" data-year="${Math.round(NEAREST.year)}" aria-label="Jump to Barnard's Star at its closest"><span>Closest pass</span></button>
          </div>
        </div>
      </div>
    </div>`;
  const q = <T extends HTMLElement>(s: string) => body.querySelector(s) as T;
  const stage = q('.s3-stage'), card = q('.s3-card'), cid = q('.s3c-id'), ctabs = q('.s3c-tabs'), cbody = q('.s3c-body'), range = q<HTMLInputElement>('.s3-range');
  const yearN = q('.s3-year-n'), yearRel = q('.s3-year-rel'), moment = q('.s3-moment'), play = q<HTMLButtonElement>('.s3-play');

  let scene: Neighbourhood | null = null;
  try {
    scene = new Neighbourhood(stage, { onPick: (id) => pick(id), reduced: reducedMotion });
    off.push(() => scene?.dispose());
  } catch {
    stage.classList.add('s3-flat');
    stage.insertAdjacentHTML('afterbegin', `<div class="s3-fallback"><p>The 3D view could not start in this browser. The stars:</p>${STARS.filter((s) => s.slug).map((s) => `<button type="button" class="chip" data-id="${s.id}">${esc(s.name)}</button>`).join('')}</div>`);
    stage.querySelectorAll<HTMLButtonElement>('.s3-fallback button').forEach((b) => (b.onclick = () => pick(b.dataset.id!)));
  }

  // ---------- fit and zoom ----------
  // the map fills the window below the header, so the time bar is always in view
  const fit = () => {
    const page = body.closest<HTMLElement>('.page');
    if (!page) return;
    const top = stage.getBoundingClientRect().top - page.getBoundingClientRect().top + page.scrollTop;
    stage.style.height = `${Math.max(420, page.clientHeight - top - 16)}px`;
    insets();
  };
  fit();
  requestAnimationFrame(fit);
  void document.fonts?.ready.then(fit);
  window.addEventListener('resize', fit);
  off.push(() => window.removeEventListener('resize', fit));
  // the wheel scrolls the page until the map is clicked (or Ctrl/Cmd is held); pinch always zooms
  const onWheel = (e: WheelEvent) => {
    if (!stage.classList.contains('s3-armed') && !e.ctrlKey && !e.metaKey) e.stopPropagation();
  };
  stage.addEventListener('wheel', onWheel, { capture: true });
  stage.addEventListener('pointerdown', (e) => {
    if ((e.target as Element).closest('.s3-canvas')) stage.classList.add('s3-armed');
  });
  stage.addEventListener('pointerleave', () => stage.classList.remove('s3-armed'));
  stage.querySelectorAll<HTMLButtonElement>('[data-zoom]').forEach((b) => (b.onclick = () => scene?.zoom(+b.dataset.zoom!)));
  if (!scene) q('.s3-zoom').hidden = true;

  // ---------- time ----------
  const setYear = (y: number) => {
    year = Math.max(T0, Math.min(T1, y));
    range.value = String(Math.round(year));
    range.setAttribute('aria-valuetext', yearLabel(year));
    yearN.textContent = yearLabel(year);
    const d = Math.round(year - NOW);
    yearRel.textContent = Math.abs(d) < 5 ? 'Today' : d > 0 ? `${fmt(d)} years from now` : `${fmt(-d)} years ago`;
    const near = Math.max(0, 1 - Math.abs(year - NEAREST.year) / 600);
    moment.hidden = near <= 0;
    stage.classList.toggle('s3-near', near > 0);
    scene?.setYear(year);
    scene?.setGlow(near);
    scene?.setLink(near > 0 ? 'barnard' : null);
  };
  let playRaf = 0, tween = 0;
  const stopPlay = () => {
    cancelAnimationFrame(playRaf);
    playRaf = 0;
    play.innerHTML = icon('play');
    play.setAttribute('aria-label', 'Play through time');
  };
  const startPlay = () => {
    cancelAnimationFrame(tween);
    if (year >= T1 - 1) setYear(T0);
    play.innerHTML = icon('pause');
    play.setAttribute('aria-label', 'Pause');
    let last = performance.now();
    const step = (now: number) => {
      const dt = Math.min(0.05, (now - last) / 1000);
      last = now;
      // slow down through the closest approach, so the moment can be seen
      const slow = 0.18 + 0.82 * Math.min(1, Math.abs(year - NEAREST.year) / 1800);
      setYear(year + dt * 1500 * slow);
      if (year >= T1) return stopPlay();
      playRaf = requestAnimationFrame(step);
    };
    playRaf = requestAnimationFrame(step);
  };
  /** Glide to a year. */
  const goTo = (y: number) => {
    stopPlay();
    cancelAnimationFrame(tween);
    if (reducedMotion) return setYear(y);
    const a = year, t0 = performance.now(), dur = 900 + Math.min(1400, Math.abs(y - a) / 8);
    const step = (now: number) => {
      const f = Math.min(1, (now - t0) / dur), e = 1 - (1 - f) ** 3;
      setYear(a + (y - a) * e);
      if (f < 1) tween = requestAnimationFrame(step);
    };
    tween = requestAnimationFrame(step);
  };
  play.onclick = () => (playRaf ? stopPlay() : startPlay());
  range.oninput = () => {
    stopPlay();
    cancelAnimationFrame(tween);
    setYear(+range.value);
  };
  body.querySelectorAll<HTMLButtonElement>('.s3-mark').forEach((b) => (b.onclick = () => goTo(+b.dataset.year!)));
  off.push(() => {
    stopPlay();
    cancelAnimationFrame(tween);
  });

  // ---------- the card ----------
  const clearTab = () => {
    tabOff.forEach((f) => f());
    tabOff = [];
  };
  const closeCard = () => {
    clearTab();
    selected = null;
    token++;
    stage.classList.remove('s3-open');
    card.hidden = true;
    insets();
    scene?.focus(null);
  };
  /** Keep the star in the open part of the view, above the card. */
  // with no card, the time bar's room: this lifts the map a little above it
  function insets() {
    const below = (el: HTMLElement) => Math.max(0, stage.getBoundingClientRect().bottom - el.getBoundingClientRect().top);
    scene?.setInset(0, card.hidden ? below(q('.s3-time')) : below(card));
  }

  async function pick(id: string | null) {
    if (!id) return selected ? closeCard() : undefined;
    const s = id === 'sun' ? SUN : STARS.find((x) => x.id === id);
    if (!s || id === selected) return;
    clearTab();
    selected = id;
    const my = ++token;
    scene?.focus(id);
    stage.classList.add('s3-open');
    card.hidden = false;
    requestAnimationFrame(insets);

    const t = s.slug ? TARGETS[s.slug] : null, c = compare(s);
    const size = s.id === 'wise0855' ? `${c.line}, cold as the North Pole` : c.line;
    cid.innerHTML = `<i style="--c: ${hex(s.color)}"></i><h2 class="s3c-name">${esc(s.name)}</h2>
      <p class="s3c-meta"><span class="mono">${esc(KIND[s.kind])}</span><span class="s3c-size">${esc(size)}</span></p>`;
    const why = t?.why ?? (s.kind === 'sun' ? 'The centre of this map. Every distance here is measured from it.' : 'A bright neighbour of the Sun, shown for scale. Not a challenge target.');
    const names: [Tab, string][] = t ? [['view', 'SPHEREx view'], ['facts', 'Facts'], ['motion', t.kind === 'bright' ? 'Brightness' : 'Motion']] : [['facts', 'Facts']];
    ctabs.hidden = names.length < 2;
    ctabs.innerHTML = names.map(([k, label]) => `<button type="button" role="tab" data-tab="${k}">${label}</button>`).join('');

    let d: Loaded | null = null;
    const show = (tab: Tab) => {
      clearTab();
      ctabs.querySelectorAll<HTMLElement>('[data-tab]').forEach((b) => b.setAttribute('aria-selected', String(b.dataset.tab === tab)));
      cbody.scrollTop = 0;
      cbody.dataset.tab = tab;
      if (tab === 'facts' || !t) return void (cbody.innerHTML = facts(s, why));
      if (!d) return void (cbody.innerHTML = '<div class="s3c-load"><span></span></div>');
      const { m, url, sample, sum } = d;
      if (tab === 'view') {
        const modes: Mode[] = t.kind === 'cold' ? ['wave', 'blink', 'photos'] : t.kind === 'bright' ? ['passes', 'photos'] : ['blink', 'photos'];
        const v = viewer(m, url, modes, reducedMotion);
        tabOff.push(v.stop);
        const mv = t.kind === 'bright' ? null : moved(sum);
        const sat = t.kind === 'bright' && sum?.n_saturated != null && sum.n_frames ? [sum.n_saturated, sum.n_frames] : null;
        v.side.insertAdjacentHTML('beforeend', `
          ${mv ? `<p class="s3c-big">${esc(mv.big)}</p><p class="s3c-small">${esc(mv.small)}</p>` : ''}
          ${sat ? `<p class="s3c-big"><b>${fmt(sat[0])} of ${fmt(sat[1])}</b> photos are saturated: too bright to measure.</p>
            <div class="st-meter" role="img" aria-label="${sat[0]} of ${sat[1]} photos are saturated"><span style="width: ${((sat[0] / sat[1]) * 100).toFixed(1)}%"></span></div>` : ''}
          <p class="s3c-note s3c-note-${t.tone}"><b>${t.tone === 'warn' ? 'Caveat' : 'How well it worked'}</b>${esc(t.honest)}</p>
          ${provenance(sample, 'NASA SPHEREx')}`);
        cbody.replaceChildren(v.el);
        return;
      }
      // the third tab: years of motion, or the brightness of the two bright stars
      const path = d.pos ? track(parseCsv(d.pos)) : null, lc = d.lc ? lightCurve(parseCsv(d.lc)) : null;
      if (path) {
        const pts = [...path.points].sort((a, b) => a.year - b.year), first = pts[0], last = pts[pts.length - 1];
        cbody.innerHTML = `<div class="s3c-chart">
          <div class="s3c-chart-say">
            <p class="s3c-big"><b>${Math.round(last.last - first.first)} years</b> of motion, in real photos back to ${Math.floor(first.first)}.</p>
            <p class="s3c-small">Moved ${sky(last.moved)}${sum?.decades_median_resid_arcsec != null ? `. A typical photo is ${sum.decades_median_resid_arcsec.toFixed(1)} arcsec from the prediction` : ''}.</p>
            <p class="s3c-small"><a href="extra/stars/${t.extra}_decades_positions.csv" download>Download the table (CSV)</a></p>
          </div>
          <div class="st-chart" data-chart></div>
        </div>`;
        tabOff.push(trackChart(cbody.querySelector<HTMLElement>('[data-chart]')!, path, m.name));
      } else if (lc?.points.length) {
        const days = lc.points.map((p) => p.mjd);
        cbody.innerHTML = `<div class="s3c-chart">
          <div class="s3c-chart-say">
            <p class="s3c-big">Brightness, as a <b>hint</b> only.</p>
            <p class="s3c-small">${t.period
              ? `Only ${plural(lc.points.length, 'photo')} gave a reading, between ${plainDate(Math.min(...days))} and ${plainDate(Math.max(...days))}: too little to show the ${t.period}-day pulse, which is known from other telescopes (AAVSO).`
              : 'Small dots are single photos, large dots the middle of one pass, against the usual brightness of the star.'}</p>
            <p class="s3c-small"><a href="extra/stars/${t.extra}_lightcurve.csv" download>Download the table (CSV)</a></p>
          </div>
          <div class="st-chart" data-chart></div>
        </div>`;
        tabOff.push(curveChart(cbody.querySelector<HTMLElement>('[data-chart]')!, lc, m.seasons.map((x) => mjdFromIso(x.iso)), m.name, t.period));
      } else cbody.innerHTML = '<p class="s3c-small">No chart for this star.</p>';
    };
    ctabs.querySelectorAll<HTMLButtonElement>('[data-tab]').forEach((b) => (b.onclick = () => show(b.dataset.tab as Tab)));
    show(names[0][0]);
    if (!t || !s.slug) return;
    try {
      d = await load(ctx, s.slug, t);
    } catch (e) {
      if (my === token) cbody.innerHTML = `<p class="warn">Could not load this star: ${esc(e)}</p>`;
      return;
    }
    if (my === token) show((cbody.dataset.tab as Tab) ?? 'view');
  }

  q('.s3c-close').onclick = closeCard;
  const onKey = (e: KeyboardEvent) => {
    if (e.key === 'Escape' && selected) closeCard();
  };
  document.addEventListener('keydown', onKey);
  const ro = new ResizeObserver(() => selected && insets());
  ro.observe(card);
  off.push(() => {
    document.removeEventListener('keydown', onKey);
    ro.disconnect();
  });
  setYear(NOW);

  return () => {
    token++;
    clearTab();
    off.forEach((f) => f());
  };
};
