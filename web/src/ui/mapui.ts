// Small helpers on the 3D map: the layers panel, the cards for a dot or a planet under the
// pointer, the first-visit hint and the selected object's distance from Earth.
import { planetElements, planetPosition, type PlanetRow } from '../lib/kepler';
import { daysBefore, isKnown, tally } from '../lib/rank';
import type { IndexObject } from '../lib/types';
import { dotPosition, type Layer, type Scene, type Target } from '../scene/Scene';
import { isPhone, store } from '../state';
import { el, esc, fmt, plural } from './dom';
import { verdictWord } from './topbar';

const AU_KM = 149_597_870.7;

const KIND: Record<IndexObject['kind'], string> = {
  comet: 'Comet',
  neo: 'Near-Earth asteroid',
  mba: 'Main-belt asteroid',
  lost: 'Lost asteroid',
  famous: 'Well-known object',
};

const LAYER_ROWS: [Layer, string, string][] = [
  ['found', 'Found before discovery', 'var(--gold)'],
  ['searched', 'Searched', 'var(--blue-2)'],
  ['neo', 'Near-Earth', '#6badeb'],
  ['comet', 'Comets', '#b3e0f2'],
  ['mba', 'Main belt', '#4a8ccc'],
  ['planets', 'Planet orbits', 'var(--orbit)'],
];

const FACTS: Record<string, string> = {
  Mercury: 'Its day side reaches about 430 °C, yet craters at its poles hold ice.',
  Venus: 'It spins backwards, and one day there lasts longer than its year.',
  Earth: 'SPHEREx circles Earth and maps the whole sky every six months.',
  Mars: 'Its volcano Olympus Mons is about 22 km high, the tallest known.',
  Jupiter: 'Its gravity shapes the asteroid belt and bends the paths of many comets.',
  Saturn: 'It is less dense than water.',
  Uranus: 'It is tilted about 98 degrees, so it rolls around the Sun on its side.',
  Neptune: 'Its winds are the fastest known, about 2,000 km/h.',
};

const HINT_KEY = 'rewind-map-hint';

/** A find whose photos really are earlier than the moment anyone had the object. */
export function isPre(o: IndexObject): boolean {
  return o.verdict === 'FOUND' && !isKnown(o) && (daysBefore(o) ?? -1) >= 0;
}

const dist = (au: number) => `${au.toFixed(au < 10 ? 2 : 1)} AU`;
const mkm = (au: number) => `${fmt((au * AU_KM) / 1e6, au < 0.07 ? 1 : 0)} million km`;

export function mountMapUi(root: HTMLElement, scene: Scene, objects: IndexObject[], planets: PlanetRow[]) {
  const bySlug = new Map(objects.map((o) => [o.slug, o]));

  // ---------- cards under the pointer ----------
  scene.hoverCard = (t: Target) => {
    if (t.kind === 'planet') return `<strong>${esc(t.name)}</strong><span class="pk-type">Planet</span>`;
    const o = bySlug.get(t.slug);
    if (!o) return '';
    const days = daysBefore(o);
    const known = isKnown(o) && o.verdict === 'FOUND';
    return `<strong>${esc(o.name)}</strong><span class="pk-type">${KIND[o.kind] ?? 'Asteroid'}</span>
      <span class="pk-row"><span class="verdict-chip v-${o.verdict.toLowerCase()}">${known ? 'Known' : verdictWord(o.verdict)}</span>${isPre(o) && days! > 0 ? `<span class="pk-days mono">${plural(Math.round(days!), 'day')} earlier</span>` : ''}</span>`;
  };
  scene.planetCard = (name: string) => {
    const p = planets.find((x) => x.name === name);
    if (!p) return '';
    const el0 = planetElements(p, store.mjd), r = Math.hypot(...planetPosition(p, store.mjd));
    const years = Math.pow(el0.a, 1.5);
    const period = years < 2 ? `${fmt(years * 365.25)} days` : `${fmt(years, years < 20 ? 1 : 0)} years`;
    return `<strong>${esc(name)}</strong>
      <dl><dt>From the Sun</dt><dd class="mono">${dist(r)} <small>${mkm(r)}</small></dd><dt>One orbit</dt><dd class="mono">${period}</dd></dl>
      ${FACTS[name] ? `<p>${FACTS[name]}</p>` : ''}`;
  };

  // ---------- layers ----------
  const layers = el('section', { class: 'layers' + (isPhone ? ' collapsed' : ''), 'aria-label': 'Map layers' });
  layers.innerHTML = `<button class="ly-toggle" aria-expanded="${!isPhone}"><span class="kicker">Layers</span><i class="rs-caret"></i></button>
    <div class="ly-body">${LAYER_ROWS.map(([id, label, c]) => `<button role="switch" aria-checked="true" data-layer="${id}" style="--c:${c}"><i></i><span>${label}</span><b class="mono"></b></button>`).join('')}</div>`;
  root.appendChild(layers);
  const toggle = layers.querySelector('.ly-toggle') as HTMLButtonElement;
  toggle.addEventListener('click', () => toggle.setAttribute('aria-expanded', String(!layers.classList.toggle('collapsed'))));
  layers.querySelectorAll<HTMLButtonElement>('[data-layer]').forEach((b) =>
    b.addEventListener('click', () => {
      const on = b.getAttribute('aria-checked') !== 'true';
      b.setAttribute('aria-checked', String(on));
      scene.setLayer(b.dataset.layer as Layer, on);
    }),
  );
  /** Counts come from what is really drawn (call again once the dots are loaded); Rewind's own
   * counts come from index.json, the same as everywhere else on the site. */
  const t = tally(objects);
  const refresh = () => {
    const n = { ...scene.layerCounts(), found: t.before, searched: t.searched };
    layers.querySelectorAll<HTMLButtonElement>('[data-layer]').forEach((b) => ((b.lastElementChild as HTMLElement).textContent = fmt(n[b.dataset.layer as Layer])));
  };
  refresh();

  // ---------- first-visit hint ----------
  let seen = true;
  try {
    seen = !!localStorage.getItem(HINT_KEY);
  } catch {
    // no storage: skip the hint rather than show it on every visit
  }
  const hint = seen ? null : root.appendChild(el('p', { class: 'map-hint chip chip-gold' }, 'Click a glowing dot to open it'));
  const picked = () => {
    if (!hint?.isConnected || !store.selected) return;
    hint.remove();
    try {
      localStorage.setItem(HINT_KEY, '1');
    } catch {
      // fine
    }
  };

  // ---------- distance from Earth of the selected object, at the date shown ----------
  const away = root.appendChild(el('p', { class: 'earth-dist', hidden: '' }));
  const earth = planets.find((p) => p.name === 'Earth');
  let text = '';
  scene.addHook(() => {
    picked();
    const d = store.selected && earth ? scene.rewindDot(store.selected) : null;
    let t = '';
    if (d) {
      const a = dotPosition(d, store.mjd), b = planetPosition(earth!, store.mjd);
      const au = Math.hypot(a[0] - b[0], a[1] - b[1], a[2] - b[2]);
      t = `<small>From Earth on this date</small><strong class="mono">${au.toFixed(au < 10 ? 3 : 1)} AU</strong><small class="mono">${mkm(au)}</small>`;
    }
    if (t === text) return;
    text = t;
    away.hidden = !t;
    away.innerHTML = t;
  });

  return { refresh };
}
