// Object side panel (bottom sheet on phones): a clean info card. The first screen is the
// name, a one-line type, the verdict chip and one big number. Below it, five tabs:
// Photos (a still stack; the days are clickable, nothing plays on its own), Found? (the
// checks as a checklist), Future (next close pass and the Before / After uncertainty),
// Made of (the spectrum) and Story (the discovery).
import './panel.css';
import type { IndexObject, ObjectPage } from '../lib/types';
import { mjdFromIso, plainDate } from '../lib/time';
import { checkResults } from '../lib/checks';
import type { CheckKey } from '../lib/types';
import { simpleSpectrum, TYPE_PLAIN } from './panel-chart';
import { el, esc, fixPlural, fmt, plural, provenance } from './dom';
import { verdictWord } from './topbar';
import { beforeWhat, daysBefore, isKnown, seenNotEarlier } from '../lib/rank';
import { engineText, farText, oneSentence, shortDate } from './panel-text';
import type { Level } from '../scene/Scene';

const KIND: Record<string, string> = {
  neo: 'Near-Earth asteroid', mba: 'Main-belt asteroid', comet: 'Comet', lost: 'Lost asteroid', famous: 'Famous asteroid',
};

const icon = (d: string) => `<svg viewBox="0 0 16 16" aria-hidden="true">${d}</svg>`;
const TABS: [id: string, label: string, title: string, icon: string][] = [
  ['photos', 'Images', 'SPHEREx detections', icon('<rect x="2" y="3" width="12" height="10" rx="2"/><circle cx="6" cy="7" r="1.1"/><path d="m2.5 12 3.5-3 2.5 2 2-1.5 3 2.5"/>')],
  ['sure', 'Evidence', 'Detection tests', icon('<circle cx="8" cy="8" r="6"/><path d="m5.4 8.2 1.8 1.8 3.4-3.6"/>')],
  ['future', 'Orbit', 'Orbit uncertainty', icon('<path d="M2 12.5c2.5-6 7-8 11.5-7.5"/><path d="m11 2.6 2.8 2.3-2.3 2.6"/><circle cx="2.6" cy="12.6" r="0.9"/>')],
  ['made', 'Spectrum', 'Reflectance spectrum', icon('<path d="M8 2 13 7 8 14 3 7z"/><path d="M3 7h10"/>')],
  ['story', 'Discovery', 'Discovery circumstances', icon('<path d="M8 4.2C6.8 3.4 5 3.2 2.5 3.4v8.8c2.5-.2 4.3 0 5.5.8 1.2-.8 3-1 5.5-.8V3.4C11 3.2 9.2 3.4 8 4.2z"/><path d="M8 4.2V13"/>')],
];

const CK_ICON: Record<string, string> = {
  ok: icon('<path d="m3.5 8.4 3 3 6-6.6"/>'),
  warn: icon('<path d="M8 3.5v5.5"/><circle cx="8" cy="12" r="0.6"/>'),
  bad: icon('<path d="m4 4 8 8M12 4l-8 8"/>'),
  na: icon('<path d="M4 8h8"/>'),
};
const CK_WORD: Record<string, string> = { ok: 'Pass', warn: 'Weak', bad: 'Fail', na: 'Not done' };

/** Per-night detection threshold (engine: a night is positive at S/N ≥ 2). */
const DAY_SNR = 2;

export interface PanelHooks {
  sample: boolean;
  url: (slug: string, rel: string) => string; // resolve an image path from object.json
  onClose: () => void;
  onView: (level: Level) => void;
}

export class ObjectPanel {
  readonly root: HTMLElement;
  private body: HTMLElement;
  slug: string | null = null;

  constructor(parent: HTMLElement, private hooks: PanelHooks) {
    this.root = el('aside', { class: 'panel', 'aria-label': 'Object details', tabindex: '-1' });
    this.root.hidden = true;
    this.root.innerHTML = `<div class="pn-grab" aria-hidden="true"></div><button class="pn-close icon-btn" aria-label="Close panel">&times;</button><div class="pn-body op"></div>`;
    this.body = this.root.querySelector('.pn-body') as HTMLElement;
    parent.appendChild(this.root);
    (this.root.querySelector('.pn-close') as HTMLButtonElement).addEventListener('click', () => hooks.onClose());
    this.root.addEventListener('keydown', (e) => e.key === 'Escape' && hooks.onClose());
    this.initSheetDrag();
  }

  /** Phones: drag the grab handle to expand or collapse the bottom sheet. */
  private initSheetDrag() {
    const grab = this.root.querySelector('.pn-grab') as HTMLElement;
    let y0 = 0;
    grab.addEventListener('pointerdown', (e) => {
      y0 = e.clientY;
      grab.setPointerCapture(e.pointerId);
    });
    grab.addEventListener('pointerup', (e) => {
      const dy = e.clientY - y0;
      if (Math.abs(dy) < 6) this.root.classList.toggle('expanded');
      else this.root.classList.toggle('expanded', dy < 0);
    });
  }

  close() {
    this.slug = null;
    this.root.classList.remove('pn-in', 'expanded');
    setTimeout(() => !this.slug && (this.root.hidden = true), 300);
  }

  loading(o: IndexObject) {
    this.slug = o.slug;
    this.root.hidden = false;
    void this.root.offsetWidth;
    this.root.classList.add('pn-in');
    this.body.innerHTML = `<header class="op-head"><div class="pn-title"><h2 class="op-name">${esc(o.name)}</h2></div><p class="op-type">${esc(KIND[o.kind] ?? o.kind)}</p><p class="muted">Loading...</p></header>`;
  }

  fail(msg: string) {
    this.body.insertAdjacentHTML('beforeend', `<p class="warn op-fail">${esc(msg)}</p>`);
  }

  show(o: IndexObject, p: ObjectPage, hasPath = false) {
    if (this.slug !== o.slug) return;
    const sample = p.sample || this.hooks.sample;
    // each part is built on its own, so a missing optional field only blanks that part
    const safe = (name: string, f: () => string) => {
      try {
        return f();
      } catch (e) {
        console.warn(`panel section "${name}" skipped for ${p.slug}:`, e);
        return '';
      }
    };
    const panes: Record<string, string> = {
      photos: safe('photos', () => this.photos(p, sample)),
      sure: safe('sure', () => this.sure(o, p)),
      future: safe('future', () => this.future(p, hasPath)),
      made: safe('made', () => this.made(p, sample)),
      story: safe('story', () => this.story(o, p)),
    };
    this.body.innerHTML = `${safe('header', () => this.header(o, p, hasPath))}
      <div class="op-tabs" role="tablist" aria-label="About this object">${TABS.map(([id, label, , ico], k) =>
        `<button role="tab" id="op-tab-${id}" aria-controls="op-pane-${id}" aria-selected="${k === 0}" tabindex="${k === 0 ? 0 : -1}">${ico}<span>${label}</span></button>`).join('')}</div>
      <div class="op-panes">${TABS.map(([id, , title], k) =>
        `<section class="op-pane" role="tabpanel" id="op-pane-${id}" aria-labelledby="op-tab-${id}"${k === 0 ? '' : ' hidden'}><h3 class="op-h">${title}</h3>${panes[id] || '<p class="muted">No data for this object.</p>'}</section>`).join('')}</div>`;
    this.wireTabs();
    this.body.querySelector<HTMLButtonElement>('.op-view')?.addEventListener('click', () => this.hooks.onView(this.level === 'close' ? 'orbit' : 'close'));
    this.setLevel(this.level);
    try {
      this.wirePhotos(p);
    } catch (e) {
      console.warn(`panel photos failed for ${p.slug}:`, e);
    }
    this.root.focus({ preventScroll: true });
  }

  private wireTabs() {
    const tabs = [...this.body.querySelectorAll<HTMLButtonElement>('.op-tabs [role="tab"]')];
    const panes = this.body.querySelector('.op-panes') as HTMLElement;
    const pick = (t: HTMLButtonElement, focus = false) => {
      tabs.forEach((x) => {
        const on = x === t;
        x.setAttribute('aria-selected', String(on));
        x.tabIndex = on ? 0 : -1;
        (this.body.querySelector('#' + x.getAttribute('aria-controls')) as HTMLElement).hidden = !on;
      });
      panes.scrollTop = 0;
      if (focus) t.focus();
    };
    tabs.forEach((t, k) => {
      t.addEventListener('click', () => pick(t));
      t.addEventListener('keydown', (e) => {
        const d = e.key === 'ArrowRight' ? 1 : e.key === 'ArrowLeft' ? -1 : 0;
        if (!d) return;
        e.preventDefault();
        pick(tabs[(k + d + tabs.length) % tabs.length], true);
      });
    });
  }

  /** The panel's view button follows the camera framing. */
  private level: Level = 'orbit';
  setLevel(l: Level) {
    this.level = l;
    const b = this.body.querySelector<HTMLButtonElement>('.op-view');
    if (!b) return;
    b.setAttribute('aria-pressed', String(l === 'close'));
    (b.querySelector('span') as HTMLElement).textContent = l === 'close' ? 'Whole orbit' : 'Close-up';
  }

  // ---------- first screen: name, type, verdict chip, one big number ----------
  private header(o: IndexObject, p: ObjectPage, hasPath: boolean): string {
    const v = p.verdict;
    const known = isKnown(p);
    const bits = [KIND[p.kind] ?? p.kind, p.facts?.pha ? 'Potentially hazardous' : '', p.orbit?.period_yr != null && p.orbit.period_yr < 1000 ? `${p.orbit.period_yr.toFixed(1)}-year orbit` : ''].filter(Boolean);
    const days = daysBefore(o);
    const claim = (p as ObjectPage & { claim?: string | null }).claim ?? o.claim;
    const photos = p.spherex?.frames?.length ?? o.n_frames ?? 0;
    const stacked = p.spherex?.stack?.n_frames ?? photos;
    let num: string, what: string, sub: string;
    if (!known && days !== null && days > 0 && (v === 'FOUND' || v === 'HINT')) {
      const ref = beforeWhat(o);
      const firstObs = o.first_known_obs_iso, disc = o.discovered?.iso;
      num = fmt(days);
      what = `${days === 1 ? 'day' : 'days'} before ${ref}${v === 'FOUND' ? '' : ', if real'}`;
      const dates = [
        firstObs ? `First known observation: ${plainDate(firstObs)}` : '',
        disc && (!firstObs || disc.slice(0, 10) !== firstObs.slice(0, 10)) ? `Discovered: ${plainDate(disc)}` : '',
      ].filter(Boolean).join(' · ');
      sub = `${v === 'FOUND' ? '' : 'HINT: not every detection test passed. '}${dates}`;
    } else if (v === 'FOUND') {
      num = fmt(stacked);
      what = `${stacked === 1 ? 'SPHEREx image' : 'SPHEREx images stacked'}`;
      sub = known ? 'Control object: known for years, run to show a clear SPHEREx detection. Not a precovery.' : claim && /not earlier/i.test(claim) ? 'Detected, but not earlier than the first known observation: extra positions, not a precovery.' : '';
    } else if (v === 'HINT') {
      num = fmt(photos);
      what = `${photos === 1 ? 'image' : 'images'} searched`;
      sub = 'HINT: a signal is present but not every detection test passes.';
    } else {
      num = fmt(photos);
      what = v === 'TOO_FAINT' ? `${photos === 1 ? 'image' : 'images'} searched` : v === 'NO_PHOTOS' ? 'SPHEREx images cover the predicted position' : `${photos === 1 ? 'image' : 'images'} so far`;
      sub = v === 'TOO_FAINT' ? 'No significant signal at the predicted position.' : v === 'NO_PHOTOS' ? 'SPHEREx did not image the predicted position in the searched window.' : 'Not searched yet.';
    }
    const early = !known && days !== null && days > 0 && (v === 'FOUND' || v === 'HINT');
    return `<header class="op-head">
      <div class="pn-title"><h2 class="op-name">${esc(p.name ?? o.name)}</h2>${seenNotEarlier(o) ? '<span class="verdict-chip v-seen">Detected, not earlier</span>' : `<span class="verdict-chip v-${v.toLowerCase()}">${known && v === 'FOUND' ? 'Control' : verdictWord(v)}</span>`}</div>
      <p class="op-type">${bits.map(esc).join(' <span aria-hidden="true">·</span> ')}</p>
      <div class="op-stat${v === 'FOUND' || v === 'HINT' ? ' op-stat-gold' : ''}">
        <span class="op-num">${num}</span>
        <p class="op-stat-text"><strong>${early ? '<span class="sr-only">Detected </span>' : ''}${esc(what)}</strong>${sub ? `<span>${esc(sub)}</span>` : ''}</p>
        ${hasPath ? `<button class="op-view" aria-pressed="false" title="Zoom the 3D view to the object, or out to its whole orbit">${icon('<circle cx="7" cy="7" r="4.5"/><path d="M10.5 10.5 14 14"/>')}<span>Close-up</span></button>` : ''}
      </div>
    </header>`;
  }

  // ---------- Photos: a still picture; the days are clickable ----------
  private photoList(p: ObjectPage): { src: string; label: string; date: string; text: string; alt: string; dim?: boolean }[] {
    const sx = p.spherex;
    const days = (sx?.days ?? []).filter((d) => d.png);
    // show the year on the strip when the nights span more than one year (e.g. a lone night months earlier)
    const years = new Set(days.map((d) => d.iso.slice(0, 4)));
    const ref = p.first_known_obs_iso ? mjdFromIso(p.first_known_obs_iso) : null;
    const items = days.map((d) => {
      const detected = d.snr != null && d.snr >= DAY_SNR;
      const lead = ref != null ? Math.floor(ref - mjdFromIso(d.iso)) : null;
      const when = lead != null && lead >= 1 ? `, ${plural(lead, 'day')} before first known obs.` : '';
      return {
        src: d.png, label: years.size > 1 ? shortDate(plainDate(d.iso)) : plainDate(d.iso).replace(/ \d{4}$/, ''), date: dateOr(d.iso),
        text: `${plural(d.n_frames, 'image')} stacked${d.snr != null ? `, S/N ${n1(d.snr)}` : ''}${d.snr != null && !detected ? ` (below ${DAY_SNR}: no detection this night)` : ''}${when}`,
        alt: `Shift-and-stack of ${d.n_frames} SPHEREx images from ${dateOr(d.iso)}`,
        dim: d.snr != null && !detected,
      };
    });
    const st = sx?.stack;
    if (st?.png) {
      const n = st.n_frames ?? sx.frames.length;
      items.unshift({ src: st.png, label: 'All', date: `Shift-and-stack of ${plural(n, 'image')}, all nights`, text: st.snr != null ? `S/N ${n1(st.snr)}` : '', alt: `Shift-and-stack of all ${n} SPHEREx images`, dim: false });
    }
    if (items.length) return items;
    // no stacks: fall back to the single photos the engine kept a picture of
    const frames = (sx?.frames ?? []).filter((f) => f.png).slice(0, 24);
    return frames.map((f, i) => ({
      src: f.png!, label: String(i + 1), date: dateOr(f.iso),
      text: `${f.wavelength_um != null ? f.wavelength_um.toFixed(2) + ' µm' : ''}${f.snr != null ? `, S/N ${n1(f.snr)}` : ''}`,
      alt: `SPHEREx image ${i + 1}, ${dateOr(f.iso)}`,
    }));
  }

  private photos(p: ObjectPage, sample: boolean): string {
    const items = this.photoList(p);
    if (!items.length) {
      const none = !(p.spherex?.frames?.length ?? 0);
      return `<p class="op-empty">${none ? `No SPHEREx image covers the predicted position in the searched window${p.verdict === 'NO_PHOTOS' ? '' : ' yet'}.` : 'No cutout was saved for these images.'}</p>`;
    }
    const url = (rel: string) => esc(this.hooks.url(p.slug, rel));
    return `<div class="op-photo${items.length > 1 ? '' : ' op-photo-one'}">
        <figure class="stamp op-big"><img alt="" width="256" height="256"><span class="stamp-cross" aria-hidden="true"></span></figure>
        ${items.length > 1 ? `<div class="op-strip" role="listbox" aria-label="Select a night">${items.map((x, i) =>
          `<button role="option" aria-selected="${i === 0}" aria-label="${esc(x.date)}${x.dim ? ', no detection' : ''}" title="${esc(x.date)}${x.dim ? ' (no detection)' : ''}"${x.dim ? ' class="op-nodet"' : ''}><img src="${url(x.src)}" alt="" loading="lazy" width="44" height="44"><span>${esc(x.label)}</span></button>`).join('')}</div>` : ''}
      </div>
      <p class="op-cap mono" aria-live="polite"></p>
      <p class="op-note">Circle: predicted position.${items.length > 1 ? ` Select a night to see that night's stack; faded nights are below S/N ${DAY_SNR}.` : ''} ${provenance(sample, 'NASA SPHEREx')}</p>`;
  }

  private wirePhotos(p: ObjectPage) {
    const img = this.body.querySelector('.op-big img') as HTMLImageElement | null;
    if (!img) return;
    const cap = this.body.querySelector('.op-cap') as HTMLElement;
    const items = this.photoList(p);
    const buttons = [...this.body.querySelectorAll<HTMLButtonElement>('.op-strip button')];
    const show = (k: number) => {
      const it = items[k];
      img.src = this.hooks.url(p.slug, it.src);
      img.alt = it.alt;
      cap.innerHTML = `<span class="gold">${esc(it.date)}</span>${it.text ? `<span title="S/N: stack flux divided by the scatter of the same stack along offset (null) paths. The detection threshold is 5 for the full stack and 2 for a single night.">${esc(it.text)}</span>` : ''}`;
      buttons.forEach((b, i) => b.setAttribute('aria-selected', String(i === k)));
    };
    buttons.forEach((b, i) => b.addEventListener('click', () => show(i)));
    show(0);
  }

  // ---------- Evidence: the engine's nine checks, each with the number behind it ----------
  private sure(o: IndexObject, p: ObjectPage): string {
    const c = p.checks;
    const rows: [status: string, title: string, text: string][] = [];
    if (c && p.spherex?.frames?.length) {
      for (const { def, ok } of checkResults(c.passed)) rows.push([ok ? 'ok' : 'bad', def.name, checkDetail(def.key, p) || def.rule]);
    }
    const cs = c?.clone_search;
    const cloneLine = cs?.n_clones != null && cs.false_alarm_rate != null
      ? `<p class="hint">Orbit-uncertainty search: ${fmt(cs.n_clones)} orbit clones stacked; false-alarm probability ${farText(cs.false_alarm_rate, cs.n_null_trials)}. Informational, not one of the nine checks.</p>`
      : '';
    const line = oneSentence(engineText(fixPlural(p.verdict_text ?? '')), (p as ObjectPage & { claim?: string | null }).claim ?? o.claim);
    const full = engineText(fixPlural(p.verdict_text ?? ''));
    const pass = rows.filter((r) => r[0] === 'ok').length;
    return `<p class="op-lead">${esc(line)}</p>
      ${rows.length ? `<p class="op-score mono">${pass} of ${rows.length} checks pass</p>
      <ul class="op-checks">${rows.map(([s, t, x]) => `<li class="ck-${s}"><span class="op-ck" role="img" aria-label="${CK_WORD[s]}" title="${CK_WORD[s]}">${CK_ICON[s]}</span><div><strong>${esc(t)}</strong><p>${esc(x)}</p></div></li>`).join('')}</ul>` : '<p class="muted">No SPHEREx images, so there is nothing to test.</p>'}
      ${cloneLine}
      ${c?.real_or_fake_score != null ? `<p class="hint">CNN real-or-artifact score: ${Math.round(c.real_or_fake_score * 100)} / 100. Advisory only; no verdict rule uses it.</p>` : ''}
      ${full && full !== line ? `<details class="op-more"><summary>Engine verdict text</summary><p>${esc(full)}</p></details>` : ''}`;
  }

  // ---------- Future: next close pass, Before / After uncertainty ----------
  private future(p: ObjectPage, hasPath: boolean): string {
    const ca = p.facts?.next_close_approach;
    let pass: string;
    if (ca && ca.dist_ld != null && ca.iso) {
      const ld = ca.dist_ld < 10 ? fmt(ca.dist_ld, 1) : fmt(Math.round(ca.dist_ld));
      pass = `<p class="op-big-line"><strong>${esc(plainDate(ca.iso))}</strong></p>
        <p>Nominal distance <strong>${ld} lunar distances</strong> (${kmText(ca.dist_ld * 384400)}), JPL SBDB. ${p.facts.sentry ? 'Listed on JPL Sentry (impact monitoring).' : 'Not on the JPL Sentry impact-risk list.'}</p>`;
    } else {
      pass = `<p>${p.facts?.neo ? 'No close approach to Earth is listed in JPL SBDB.' : 'Not a near-Earth object: its orbit does not come close to Earth\'s.'}</p>`;
    }
    // One number, one definition: the 3σ largest-axis uncertainty one year after the last
    // observation (the same figure as the Methods table). The 3D cloud's own 1σ value is
    // only the fallback, and is labelled as such.
    const yr = p.impact?.one_year_after_last_obs;
    const disc = p.impact?.at_discovery_scenario;
    const c = p.cloud;
    let unc: string, heading = 'Positional uncertainty';
    const row = (label: string, km: number, max: number, cls: string) => `<div class="op-unc-row ${cls}"><span>${label}</span><span class="op-bar"><i style="width:${Math.max(2, (km / max) * 100).toFixed(1)}%"></i></span><strong class="mono">${kmText(km)}</strong></div>`;
    const change = (before: number, after: number) => {
      const r = before / after;
      if (r >= 1.05) return `×${fmt(r, r >= 10 ? 0 : 1)} smaller with the SPHEREx positions.`;
      if (r <= 0.95) return `×${fmt(1 / r, 1)} larger with the SPHEREx positions. A formal uncertainty can grow when a new position pulls the least-squares solution; non-gravitational forces (comets) are not modelled.`;
      return 'No meaningful change (within 5%): the existing follow-up arc already constrains the orbit.';
    };
    if (yr && yr.sigma3_km_before != null && yr.sigma3_km_after != null) {
      heading = `3σ positional uncertainty on ${plainDate(yr.iso)} (1 year after the last observation)`;
      const max = Math.max(yr.sigma3_km_before, yr.sigma3_km_after);
      const atDisc = disc && disc.factor != null && disc.converged !== false
        ? `<p>At-discovery scenario (MPC observations of the first 7 days only): adding the SPHEREx positions ${disc.sigma3_km_before != null && disc.sigma3_km_after != null ? `takes the 1-year 3σ uncertainty from ${kmText(disc.sigma3_km_before)} to ${kmText(disc.sigma3_km_after)} (factor ×${disc.factor.toFixed(disc.factor >= 2 ? 1 : 2)}; above 1 means smaller)` : `changes the 1-year 3σ uncertainty by a factor ×${disc.factor.toFixed(disc.factor >= 2 ? 1 : 2)} (above 1 means smaller)`}.</p>`
        : disc?.error || disc?.converged === false
          ? '<p class="hint">At-discovery scenario: the short-arc fit was too weak to sample, so no number is given.</p>'
          : '';
      unc = `<div class="op-unc">${row('MPC observations only', yr.sigma3_km_before, max, 'unc-before')}${row('+ SPHEREx positions', yr.sigma3_km_after, max, 'unc-after')}</div>
        <p>${change(yr.sigma3_km_before, yr.sigma3_km_after)}</p>${atDisc}
        <p class="hint">Largest axis of the 3σ cloud from covariance clones of kete least-squares fits (gravity only). The Before / After control under the 3D view shows a 1σ cloud.</p>`;
    } else if (c?.before?.length && c.before_sigma_km_at?.km != null) {
      const b = c.before_sigma_km_at, a = c.after_sigma_km_at;
      const hasAfter = !!c.after && a?.km != null;
      heading = `1σ positional uncertainty on ${plainDate(b.iso)}`;
      const max = Math.max(b.km, hasAfter ? a!.km : 0);
      unc = `<div class="op-unc">${row('MPC observations only', b.km, max, 'unc-before')}${hasAfter ? row('+ SPHEREx positions', a!.km, max, 'unc-after') : ''}</div>
        <p>${hasAfter ? change(b.km, a!.km) : 'No SPHEREx positions were added to the fit for this object.'}</p>
        <p class="hint">Largest axis of the 1σ clone cloud (gravity only). Switch Before / After under the 3D view to see it.</p>`;
    } else {
      unc = `<p class="muted">${hasPath ? 'No uncertainty estimate for this object.' : 'No orbit for this object in the data set.'}</p>`;
    }
    return `<div class="op-block"><h4 class="op-k">Next close approach to Earth</h4>${pass}</div>
      <div class="op-block"><h4 class="op-k">${esc(heading)}</h4>${unc}</div>`;
  }

  // ---------- Made of: the spectrum, simplified ----------
  private made(p: ObjectPage, sample: boolean): string {
    const c = p.composition;
    if (!c?.points?.length) return `<p class="op-empty">Too little flux in the SPHEREx images for a spectrum.</p>`;
    // a taxonomic match needs at least 3 channels measured at S/N ≥ 2
    const strong = c.points.filter((x) => x.err > 0 && Math.abs(x.value) / x.err >= 2).length;
    const usable = strong >= 3;
    const plain = usable && c.best_match ? TYPE_PLAIN[c.best_match.trim().charAt(0).toUpperCase()] : null;
    const lead = !usable
      ? `Too noisy to classify: only ${strong} of ${c.points.length} spectral bins have S/N ≥ 2.`
      : c.best_match
        ? `Closest template: <strong>${esc(c.best_match)}-type</strong>${plain ? ` (${plain})` : ''}. <span class="chip">${esc(c.label ?? 'rough match')}</span>`
        : 'No template fits better than the others.';
    return `<p class="op-lead">${lead}</p>
      ${simpleSpectrum(c)}
      <p class="op-note">Relative reflectance = measured flux divided by the flux expected for a solar-coloured source, normalised below 1.3 µm. Beyond about 3.5 µm, thermal emission adds to reflected light for near-Earth objects, so templates are least reliable there. ${provenance(sample, 'NASA SPHEREx')}</p>`;
  }

  // ---------- Story: the discovery in a few lines ----------
  private story(o: IndexObject, p: ObjectPage): string {
    const s = p.story;
    if (!s) return '';
    const when = s.discovered_iso ? `Discovered <strong>${esc(plainDate(s.discovered_iso))}</strong>` : 'Discovered';
    const who = whoWhere(s.by, s.site);
    // the engine's story repeats the discovery sentence (with "Mt." inside the site name, so it
    // cannot be split on full stops); drop it and the boilerplate that follows
    const more = engineText(fixPlural(s.plain ?? ''))
      .replace(/^.*?\bwas discovered on \S+(?: by .*?\(\w+\))?\.\s*/, '')
      .replace(/^Rewind searched SPHEREx (?:photos|images) taken before that date[^.]*\.\s*/, '')
      .trim();
    const firstObs = p.first_known_obs_iso ?? o.first_known_obs_iso;
    const obsLine = firstObs && s.discovered_iso && firstObs.slice(0, 10) < s.discovered_iso.slice(0, 10)
      ? `<p>Earliest observation on record at the Minor Planet Center: <strong>${esc(plainDate(firstObs))}</strong>, earlier than the discovery date because earlier observations were linked to the object afterwards. Rewind's lead times are counted from this earlier date.</p>`
      : '';
    const sources = (s.sources ?? []).filter(Boolean);
    const credits = (p.credits ?? []).filter(Boolean);
    return `<p class="op-lead">${when}${who ? ' ' + who : ''}.</p>
      ${obsLine}
      ${more ? `<p>${esc(more)}</p>` : ''}
      <dl class="op-facts">
        <div><dt>Orbital period</dt><dd class="mono">${p.orbit?.period_yr != null && p.orbit.period_yr < 1e5 ? fmt(p.orbit.period_yr, 1) + ' years' : 'unknown'}</dd></div>
        <div><dt>Size</dt><dd class="mono">${p.facts?.diameter_km ? sizeText(p.facts.diameter_km) : 'unknown'}</dd></div>
        <div><dt>Orbit family</dt><dd class="mono">${esc(p.facts?.class ?? KIND[o.kind] ?? 'unknown')}</dd></div>
      </dl>
      ${sources.length ? `<p class="op-sources">Sources: ${sources.map((u, k) => `<a href="${esc(u)}" target="_blank" rel="noopener">${esc(hostOf(u))}${sources.length > 1 ? ' ' + (k + 1) : ''}</a>`).join(', ')}</p>` : ''}
      ${credits.length ? `<details class="op-more"><summary>Data credits</summary><p>${credits.map(esc).join('<br>')}</p></details>` : ''}`;
  }
}

/** "by Mt. Lemmon Survey (MPC code G96)": the site is dropped when it only repeats the discoverer. */
function whoWhere(by: string | null | undefined, site: string | null | undefined): string {
  const m = site ? site.match(/^(.*?)\s*\((\w+)\)$/) : null;
  const siteName = (m ? m[1] : site ?? '').trim();
  const code = m ? ` (MPC code ${esc(m[2])})` : '';
  const b = (by ?? '').trim();
  if (b && siteName && siteName.toLowerCase().includes(b.toLowerCase())) return `by <strong>${esc(b)}</strong>${code}`;
  if (b && siteName) return `by <strong>${esc(b)}</strong> at ${esc(siteName)}${code}`;
  if (b) return `by <strong>${esc(b)}</strong>`;
  if (siteName) return `at ${esc(siteName)}${code}`;
  return '';
}

/** The measured number behind one check, in one sentence; '' when the file lacks it. */
function checkDetail(k: CheckKey, p: ObjectPage): string {
  const c = p.checks;
  switch (k) {
    case 'snr': {
      const v = p.spherex?.stack?.snr;
      return v != null ? `Null-calibrated S/N ${v.toFixed(1)} in the stack of ${plural(p.spherex.stack.n_frames, 'image')} (threshold 5).` : '';
    }
    case 'cleaned': {
      const ss = c.static_sky_subtracted?.snr;
      return ss != null ? `After subtracting a static-sky reference built from other SPHEREx images of the field: S/N ${ss.toFixed(1)}.` : '';
    }
    case 'nulls': {
      const np = c.null_paths;
      return np ? `${np.n_exceeding} of ${np.n} offset (null) trajectories reached the target S/N; null stacks average S/N ${np.snr_mean.toFixed(1)} ± ${np.snr_std.toFixed(1)}.` : '';
    }
    case 'time_shift': {
      const ts = c.time_shift;
      if (!ts?.snr?.length || ts.shifts_days.length < 2) return '';
      const at = ts.shifts_days[ts.snr.indexOf(Math.max(...ts.snr))];
      const step = Math.abs(ts.shifts_days[1] - ts.shifts_days[0]) * 24;
      return `Re-stacked with the ephemeris shifted in time (steps of ${step.toFixed(2)} h): S/N peaks at Δt = ${at === 0 ? '0' : (at * 24).toFixed(2) + ' h'}.`;
    }
    case 'days':
      return c.per_day_positive ? `Positive (S/N ≥ ${DAY_SNR}) on ${c.per_day_positive} nights when each night is stacked alone.` : '';
    case 'detectable': {
      const inj = c.injection;
      return inj?.recovered_fraction_at_object_mag != null
        ? `Synthetic sources at the predicted magnitude: ${Math.round(inj.recovered_fraction_at_object_mag * 100)}% recovered${inj.limit_ab_mag != null ? `; 50% completeness limit AB ${inj.limit_ab_mag.toFixed(1)}` : ''}.`
        : '';
    }
    case 'sign_test': {
      const fp = c.frac_positive;
      return fp ? `${Math.round(fp.target * 100)}% of single images positive on the predicted path, vs ${Math.round(fp.null_mean * 100)} ± ${Math.round(fp.null_std * 100)}% on null paths (highest ${Math.round(fp.null_max * 100)}%).` : '';
    }
    case 'not_one_day':
      return '';
    case 'orbit': {
      const f = c.orbit_fit;
      return f?.rms_arcsec_after != null && f.rms_arcsec_before != null
        ? `Refit with ${plural(f.new_points, 'SPHEREx position')}: RMS ${f.rms_arcsec_after.toFixed(2)}″ (was ${f.rms_arcsec_before.toFixed(2)}″).`
        : '';
    }
  }
}

function dateOr(iso: string | null | undefined): string {
  return iso ? plainDate(iso) : 'date n/a';
}

function n1(v: number | null | undefined): string {
  return v === null || v === undefined ? 'n/a' : v.toFixed(1);
}
function hostOf(u: string) {
  try {
    return new URL(u).hostname.replace(/^www\./, '');
  } catch {
    return u;
  }
}
export function kmText(km: number): string {
  if (km >= 1e6) return `${fmt(km / 1e6, km >= 1e7 ? 0 : 1)} million km`;
  return `${fmt(Math.round(km / (km > 1e4 ? 1000 : 1)) * (km > 1e4 ? 1000 : 1))} km`;
}
function sizeText(d: number) {
  return d >= 1 ? `${d.toFixed(1)} km` : `${Math.round(d * 1000)} m`;
}
