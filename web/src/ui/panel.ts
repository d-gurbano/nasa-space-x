// Object side panel (bottom sheet on phones): a clean info card. The first screen is the
// name, a one-line type, the verdict chip and one big number. Below it, five tabs:
// Photos (a still stack; the days are clickable, nothing plays on its own), Found? (the
// checks as a checklist), Future (next close pass and the Before / After uncertainty),
// Made of (the spectrum) and Story (the discovery).
import './panel.css';
import type { IndexObject, ObjectPage } from '../lib/types';
import { plainDate } from '../lib/time';
import { simpleSpectrum, TYPE_PLAIN } from './panel-chart';
import { el, esc, fixPlural, fmt, plural, provenance } from './dom';
import { verdictWord } from './topbar';
import { beforeWhat, daysBefore, isKnown } from '../lib/rank';
import { oneSentence } from './panel-text';
import type { Level } from '../scene/Scene';

const KIND: Record<string, string> = {
  neo: 'Near-Earth asteroid', mba: 'Main-belt asteroid', comet: 'Comet', lost: 'Lost asteroid', famous: 'Famous asteroid',
};

const icon = (d: string) => `<svg viewBox="0 0 16 16" aria-hidden="true">${d}</svg>`;
const TABS: [id: string, label: string, title: string, icon: string][] = [
  ['photos', 'Photos', 'What SPHEREx saw', icon('<rect x="2" y="3" width="12" height="10" rx="2"/><circle cx="6" cy="7" r="1.1"/><path d="m2.5 12 3.5-3 2.5 2 2-1.5 3 2.5"/>')],
  ['sure', 'Found?', 'How sure are we?', icon('<circle cx="8" cy="8" r="6"/><path d="m5.4 8.2 1.8 1.8 3.4-3.6"/>')],
  ['future', 'Future', 'Where is it going?', icon('<path d="M2 12.5c2.5-6 7-8 11.5-7.5"/><path d="m11 2.6 2.8 2.3-2.3 2.6"/><circle cx="2.6" cy="12.6" r="0.9"/>')],
  ['made', 'Made of', 'What is it made of?', icon('<path d="M8 2 13 7 8 14 3 7z"/><path d="M3 7h10"/>')],
  ['story', 'Story', 'How it was discovered', icon('<path d="M8 4.2C6.8 3.4 5 3.2 2.5 3.4v8.8c2.5-.2 4.3 0 5.5.8 1.2-.8 3-1 5.5-.8V3.4C11 3.2 9.2 3.4 8 4.2z"/><path d="M8 4.2V13"/>')],
];

const CK_ICON: Record<string, string> = {
  ok: icon('<path d="m3.5 8.4 3 3 6-6.6"/>'),
  warn: icon('<path d="M8 3.5v5.5"/><circle cx="8" cy="12" r="0.6"/>'),
  bad: icon('<path d="m4 4 8 8M12 4l-8 8"/>'),
  na: icon('<path d="M4 8h8"/>'),
};
const CK_WORD: Record<string, string> = { ok: 'Pass', warn: 'Weak', bad: 'Fail', na: 'Not done' };

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
    this.body.innerHTML = `<header class="op-head"><div class="op-title"><h2 class="op-name">${esc(o.name)}</h2></div><p class="op-type">${esc(KIND[o.kind] ?? o.kind)}</p><p class="muted">Loading...</p></header>`;
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
        `<section class="op-pane" role="tabpanel" id="op-pane-${id}" aria-labelledby="op-tab-${id}"${k === 0 ? '' : ' hidden'}><h3 class="op-h">${title}</h3>${panes[id] || '<p class="muted">Nothing to show here for this object.</p>'}</section>`).join('')}</div>`;
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
      const when = beforeWhat(o) === 'discovery' ? 'Discovered' : 'First known observation';
      const date = o.first_known_obs_iso ?? o.discovered?.iso;
      num = fmt(days);
      what = `${days === 1 ? 'day' : 'days'} ${v === 'FOUND' ? 'before anyone else' : 'earlier, if it is real'}`;
      sub = `${v === 'FOUND' ? '' : 'A hint, not a sure find. '}${date ? `${when}: ${plainDate(date)}` : ''}`;
    } else if (v === 'FOUND') {
      num = fmt(stacked);
      what = `${stacked === 1 ? 'photo shows' : 'photos added together show'} it`;
      sub = known ? 'A known object. It shows what SPHEREx can see.' : claim && /not earlier/i.test(claim) ? 'Not earlier than the known observations.' : '';
    } else if (v === 'HINT') {
      num = fmt(photos);
      what = `${photos === 1 ? 'photo' : 'photos'} checked`;
      sub = 'A hint, not a sure find.';
    } else {
      num = fmt(photos);
      what = v === 'TOO_FAINT' ? `${photos === 1 ? 'photo' : 'photos'} searched` : v === 'NO_PHOTOS' ? 'photos of the right spot' : `${photos === 1 ? 'photo' : 'photos'} so far`;
      sub = v === 'TOO_FAINT' ? 'Nothing shows at the predicted spot.' : v === 'NO_PHOTOS' ? 'SPHEREx was not looking there at the right time.' : 'Not searched yet.';
    }
    const early = what.includes('before anyone');
    return `<header class="op-head">
      <div class="op-title"><h2 class="op-name">${esc(p.name ?? o.name)}</h2><span class="verdict-chip v-${v.toLowerCase()}">${known && v === 'FOUND' ? 'Seen' : verdictWord(v)}</span></div>
      <p class="op-type">${bits.map(esc).join(' <span aria-hidden="true">·</span> ')}</p>
      <div class="op-stat${v === 'FOUND' || v === 'HINT' ? ' op-stat-gold' : ''}">
        <span class="op-num">${num}</span>
        <p class="op-stat-text"><strong>${early ? '<span class="sr-only">Seen </span>' : ''}${esc(what)}</strong>${sub ? `<span>${esc(sub)}</span>` : ''}</p>
        ${hasPath ? `<button class="op-view" aria-pressed="false" title="Fly to the object, or back out to its whole orbit">${icon('<circle cx="7" cy="7" r="4.5"/><path d="M10.5 10.5 14 14"/>')}<span>Close-up</span></button>` : ''}
      </div>
    </header>`;
  }

  // ---------- Photos: a still picture; the days are clickable ----------
  private photoList(p: ObjectPage): { src: string; label: string; date: string; text: string; alt: string }[] {
    const sx = p.spherex;
    const days = (sx?.days ?? []).filter((d) => d.png);
    const items = days.map((d) => ({
      src: d.png, label: plainDate(d.iso).replace(/ \d{4}$/, ''), date: dateOr(d.iso),
      text: `${plural(d.n_frames, 'photo')}${d.snr != null ? `, S/N ${n1(d.snr)}` : ''}`,
      alt: `All ${d.n_frames} SPHEREx photos from ${dateOr(d.iso)} added together`,
    }));
    const st = sx?.stack;
    if (st?.png) {
      const n = st.n_frames ?? sx.frames.length;
      items.unshift({ src: st.png, label: 'All', date: `All ${plural(n, 'photo')} added together`, text: st.snr != null ? `S/N ${n1(st.snr)}` : '', alt: `All ${n} SPHEREx photos added together` });
    }
    if (items.length) return items;
    // no stacks: fall back to the single photos the engine kept a picture of
    const frames = (sx?.frames ?? []).filter((f) => f.png).slice(0, 24);
    return frames.map((f, i) => ({
      src: f.png!, label: String(i + 1), date: dateOr(f.iso),
      text: `${f.wavelength_um != null ? f.wavelength_um.toFixed(2) + ' µm' : ''}${f.snr != null ? `, S/N ${n1(f.snr)}` : ''}`,
      alt: `SPHEREx photo ${i + 1}, ${dateOr(f.iso)}`,
    }));
  }

  private photos(p: ObjectPage, sample: boolean): string {
    const items = this.photoList(p);
    if (!items.length) {
      const none = !(p.spherex?.frames?.length ?? 0);
      return `<p class="op-empty">${none ? `SPHEREx has no photos of the right spot at the right time${p.verdict === 'NO_PHOTOS' ? '' : ' yet'}.` : 'No picture was kept for these photos.'}</p>`;
    }
    const url = (rel: string) => esc(this.hooks.url(p.slug, rel));
    return `<div class="op-photo${items.length > 1 ? '' : ' op-photo-one'}">
        <figure class="stamp op-big"><img alt="" width="256" height="256"><span class="stamp-cross" aria-hidden="true"></span></figure>
        ${items.length > 1 ? `<div class="op-strip" role="listbox" aria-label="Pick a day">${items.map((x, i) =>
          `<button role="option" aria-selected="${i === 0}" aria-label="${esc(x.date)}" title="${esc(x.date)}"><img src="${url(x.src)}" alt="" loading="lazy" width="44" height="44"><span>${esc(x.label)}</span></button>`).join('')}</div>` : ''}
      </div>
      <p class="op-cap mono" aria-live="polite"></p>
      <p class="op-note">The object should sit in the gold circle.${items.length > 1 ? ' Pick a day to see it alone.' : ''} ${provenance(sample, 'NASA SPHEREx')}</p>`;
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
      cap.innerHTML = `<span class="gold">${esc(it.date)}</span>${it.text ? `<span title="S/N: how many times stronger the dot is than the random speckle. Above about 5 is convincing.">${esc(it.text)}</span>` : ''}`;
      buttons.forEach((b, i) => b.setAttribute('aria-selected', String(i === k)));
    };
    buttons.forEach((b, i) => b.addEventListener('click', () => show(i)));
    show(0);
  }

  // ---------- Found? the checks as a checklist ----------
  private sure(o: IndexObject, p: ObjectPage): string {
    const c = p.checks;
    const rows: [status: string, title: string, text: string][] = [];
    if (c && p.spherex?.frames?.length) {
      const ok = (k: keyof NonNullable<typeof c.passed>, fallback: boolean) => (c.passed?.[k] ?? fallback ? 'ok' : 'warn');
      const np = c.null_paths;
      if (np) rows.push([c.passed?.nulls === false ? 'bad' : np.n_exceeding === 0 ? 'ok' : np.n_exceeding <= 1 ? 'warn' : 'bad', 'Not random noise',
        `We also searched ${plural(np.n, 'made-up path')} next to the real one. ${np.n_exceeding === 0 ? 'None' : np.n_exceeding} showed a dot this strong.`]);
      if (c.per_day_positive) {
        const [pos, tot] = c.per_day_positive.split(' of ').map(Number);
        rows.push([ok('days', pos === tot), 'Seen day after day', `It shows up on ${c.per_day_positive} days when each day is checked alone.`]);
      }
      const ts = c.time_shift;
      if (ts?.snr?.length && ts.shifts_days?.length) {
        const atZero = ts.shifts_days[ts.snr.indexOf(Math.max(...ts.snr))] === 0;
        rows.push([ok('time_shift', atZero), 'Only at the right time', atZero
          ? 'The dot fades when we look a little too early or too late.'
          : 'The dot is not strongest at the right time, which is suspicious.']);
      }
      const ss = c.static_sky_subtracted?.snr ?? null;
      if (ss === null) rows.push(['na', 'Still there without the stars', 'No clean picture of the fixed sky to subtract for this object.']);
      else rows.push([ok('cleaned', ss >= 5), 'Still there without the stars', `With the fixed stars and galaxies removed, the dot is ${ss.toFixed(1)} times stronger than the noise.`]);
      const inj = c.injection;
      if (!inj || inj.limit_ab_mag == null || inj.recovered_fraction_at_object_mag == null) rows.push(['na', 'Bright enough to see here', 'Not measured for this object.']);
      else rows.push([ok('detectable', inj.recovered_fraction_at_object_mag >= 0.8), 'Bright enough to see here',
        `We planted fake dots this bright in the real photos and got ${Math.round(inj.recovered_fraction_at_object_mag * 100)}% of them back.`]);
      if (c.orbit_fit?.rms_arcsec_after != null && c.orbit_fit.rms_arcsec_before != null) rows.push([ok('orbit', true), 'Fits the orbit',
        `With ${plural(c.orbit_fit.new_points, 'new position')} added, the orbit still fits (${c.orbit_fit.rms_arcsec_after.toFixed(2)} arcsec, was ${c.orbit_fit.rms_arcsec_before.toFixed(2)}).`]);
      else rows.push(['na', 'Fits the orbit', 'The signal is too weak to add new positions to the orbit.']);
      if (c.clone_search?.n_clones != null && c.clone_search.false_alarm_rate != null) rows.push(['ok', 'Many possible paths searched',
        `The orbit is uncertain, so we searched ${fmt(c.clone_search.n_clones)} paths. About ${Math.round(c.clone_search.false_alarm_rate * 100)}% of such hits are false alarms.`]);
    }
    const line = oneSentence(fixPlural(p.verdict_text ?? ''), (p as ObjectPage & { claim?: string | null }).claim ?? o.claim);
    const full = fixPlural(p.verdict_text ?? '');
    const pass = rows.filter((r) => r[0] === 'ok').length;
    return `<p class="op-lead">${esc(line)}</p>
      ${rows.length ? `<p class="op-score mono">${pass} of ${rows.length} checks pass</p>
      <ul class="op-checks">${rows.map(([s, t, x]) => `<li class="ck-${s}"><span class="op-ck" role="img" aria-label="${CK_WORD[s]}" title="${CK_WORD[s]}">${CK_ICON[s]}</span><div><strong>${t}</strong><p>${x}</p></div></li>`).join('')}</ul>` : '<p class="muted">No photos, so there is nothing to check.</p>'}
      ${c?.real_or_fake_score != null ? `<p class="hint">AI helper: ${Math.round(c.real_or_fake_score * 100)} / 100 for "looks real". It only advises; the checks decide.</p>` : ''}
      ${full && full !== line ? `<details class="op-more"><summary>The full verdict, with numbers</summary><p>${esc(full)}</p></details>` : ''}`;
  }

  // ---------- Future: next close pass, Before / After uncertainty ----------
  private future(p: ObjectPage, hasPath: boolean): string {
    const ca = p.facts?.next_close_approach;
    let pass: string;
    if (ca && ca.dist_ld != null && ca.iso) {
      const ld = ca.dist_ld < 10 ? fmt(ca.dist_ld, 1) : fmt(Math.round(ca.dist_ld));
      pass = `<p class="op-big-line"><strong>${esc(plainDate(ca.iso))}</strong></p>
        <p>It passes <strong>${ld} Moon distances</strong> from Earth, about ${kmText(ca.dist_ld * 384400)}. ${p.facts.sentry ? 'It is on NASA\'s Sentry impact-monitoring list.' : 'It is not expected to hit Earth.'}</p>`;
    } else {
      pass = `<p>${p.facts?.neo ? 'No close pass by Earth is listed for it.' : 'Its orbit does not bring it near Earth.'}</p>`;
    }
    const c = p.cloud;
    const b = c?.before_sigma_km_at, a = c?.after_sigma_km_at;
    let unc: string;
    if (!c?.before?.length || b?.km == null) {
      unc = `<p class="muted">${hasPath ? 'No uncertainty estimate for this object yet.' : 'Its path is not in our data yet.'}</p>`;
    } else {
      const hasAfter = !!c.after && a?.km != null;
      const max = Math.max(b.km, hasAfter ? a!.km : 0);
      const row = (label: string, km: number, cls: string) => `<div class="op-unc-row ${cls}"><span>${label}</span><span class="op-bar"><i style="width:${Math.max(2, (km / max) * 100).toFixed(1)}%"></i></span><strong class="mono">± ${kmText(km)}</strong></div>`;
      let gain = 'Rewind has no new positions for it yet, so there is no "after".';
      if (hasAfter) {
        const ratio = b.km / a!.km, pct = Math.round((1 - a!.km / b.km) * 100);
        gain = ratio >= 1.5 ? `${fmt(ratio, 1)} times smaller with the positions Rewind found.` : pct >= 1 ? `${pct}% smaller with the positions Rewind found.` : 'About the same with the positions Rewind found.';
      }
      unc = `<div class="op-unc">${row('Before Rewind', b.km, 'unc-before')}${hasAfter ? row('After Rewind', a!.km, 'unc-after') : ''}</div>
        <p>${gain}</p>
        <p class="hint">Smaller is better. Switch Before / After under the 3D view to see the cloud of possible positions.</p>`;
    }
    return `<div class="op-block"><h4 class="op-k">Next close pass by Earth</h4>${pass}</div>
      <div class="op-block"><h4 class="op-k">How far off its predicted position could be${b?.iso ? `, by ${esc(plainDate(b.iso))}` : ''}</h4>${unc}</div>`;
  }

  // ---------- Made of: the spectrum, simplified ----------
  private made(p: ObjectPage, sample: boolean): string {
    const c = p.composition;
    if (!c?.points?.length) return `<p class="op-empty">Not enough light in the photos to tell what it is made of.</p>`;
    const plain = c.best_match ? TYPE_PLAIN[c.best_match.trim().charAt(0).toUpperCase()] : null;
    return `<p class="op-lead">${c.best_match
      ? `Closest to <strong>${esc(c.best_match)}-type</strong>${plain ? `: ${plain}` : ''}. <span class="chip">${esc(c.label ?? 'rough match')}</span>`
      : 'No clear match to a typical rock or ice type.'}</p>
      ${simpleSpectrum(c)}
      <p class="op-note">Rock and ice reflect infrared colours differently. ${provenance(sample, 'NASA SPHEREx')}</p>`;
  }

  // ---------- Story: the discovery in a few lines ----------
  private story(o: IndexObject, p: ObjectPage): string {
    const s = p.story;
    if (!s) return '';
    const when = s.discovered_iso ? `Found on <strong>${esc(plainDate(s.discovered_iso))}</strong>` : 'Found';
    const who = whoWhere(s.by, s.site);
    // the engine's story starts with the same discovery sentence; keep only what it adds
    const more = fixPlural(s.plain ?? '').split(/(?<=\.)\s+(?=[A-Z0-9])/).filter((x) => x && !/was discovered on/i.test(x)).slice(0, 2).join(' ');
    const sources = (s.sources ?? []).filter(Boolean);
    const credits = (p.credits ?? []).filter(Boolean);
    return `<p class="op-lead">${when}${who ? ' ' + who : ''}.</p>
      ${more ? `<p>${esc(more)}</p>` : ''}
      <dl class="op-facts">
        <div><dt>One trip around the Sun</dt><dd class="mono">${p.orbit?.period_yr != null && p.orbit.period_yr < 1e5 ? fmt(p.orbit.period_yr, 1) + ' years' : 'unknown'}</dd></div>
        <div><dt>Size</dt><dd class="mono">${p.facts?.diameter_km ? sizeText(p.facts.diameter_km) : 'unknown'}</dd></div>
        <div><dt>Orbit family</dt><dd class="mono">${esc(p.facts?.class ?? KIND[o.kind] ?? 'unknown')}</dd></div>
      </dl>
      ${sources.length ? `<p class="op-sources">Sources: ${sources.map((u, k) => `<a href="${esc(u)}" target="_blank" rel="noopener">${esc(hostOf(u))}${sources.length > 1 ? ' ' + (k + 1) : ''}</a>`).join(', ')}</p>` : ''}
      ${credits.length ? `<details class="op-more"><summary>Data credits</summary><p>${credits.map(esc).join('<br>')}</p></details>` : ''}`;
  }
}

/** "by the Euclid team (observatory code 273)" when the discoverer and the site are the same. */
function whoWhere(by: string | null | undefined, site: string | null | undefined): string {
  const m = site ? site.match(/^(.*?)\s*\((\w+)\)$/) : null;
  const siteName = m ? m[1] : site ?? '';
  if (by && siteName && by.trim().toLowerCase() === siteName.trim().toLowerCase()) {
    return `by the <strong>${esc(by)}</strong> team${m ? ` (observatory code ${esc(m[2])})` : ''}`;
  }
  if (by && site) return `by <strong>${esc(by)}</strong> at ${esc(site)}`;
  if (by) return `by <strong>${esc(by)}</strong>`;
  if (site) return `at ${esc(site)}`;
  return '';
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
