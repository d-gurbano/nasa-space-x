import '@fontsource/geist-sans/400.css';
import '@fontsource/geist-sans/500.css';
import '@fontsource/geist-sans/600.css';
import '@fontsource/geist-sans/700.css';
import '@fontsource/geist-mono/400.css';
import '@fontsource/geist-mono/500.css';
import './styles/tokens.css';
import './styles/base.css';
import './styles/components.css';
import './styles/app.css';
import './styles/pages.css';

import { getJson, loadIndex, loadOrbits, loadPlanets, resolveRel, rowElements, type DataSource } from './lib/data';
import type { FlashEvent, ObjectPage } from './lib/types';
import { FlashFx } from './scene/flash';
import { eclToThree } from './scene/asteroids';
import { isValidElements } from './lib/kepler';
import { UncertaintyCloud } from './scene/cloud';
import { mountPhotoCard } from './ui/photocard';
import { ObjectPanel } from './ui/panel';
import { mountDock } from './ui/panel-dock';
import { ObjectFocus } from './scene/focus';
import { PageHost, makeCtx, type View } from './views/page';
import { detectivesView } from './views/detectives';
import { starsView } from './views/stars';
import { benchmarkView } from './views/benchmark';
import { scientistsView } from './views/scientists';
import { aboutView } from './views/about';
import { skyView } from './views/sky';
import { Scene, type Level, type RewindDot } from './scene/Scene';
import { mountTimebar } from './ui/timebar';
import { mountOpening } from './ui/opening';
import { mountTopbar } from './ui/topbar';
import { mountResults } from './ui/results';
import { isPre, mountMapUi } from './ui/mapui';
import { isKnown, knownSince, pickShowcase, rankObjects, tally } from './lib/rank';
import { guidedRewind, type Guided } from './guided';
import { runDemo } from './demo';
import { isPhone, reducedMotion, store } from './state';
import { esc, fmt } from './ui/dom';

const ui = document.getElementById('ui')!;
const canvas = document.getElementById('scene') as HTMLCanvasElement;
const labelRoot = document.getElementById('labels')!;

export const pages = new Map<string, Promise<ObjectPage>>();

/** Old page addresses, kept working: rewrites the hash in place (no extra history entry). */
const RENAMED: Record<string, string> = { detectives: 'games', stars: 'targets', benchmark: 'blind-test', scientists: 'methods' };
function legacyHash() {
  const old = location.hash.match(/^#\/([\w-]+)$/)?.[1];
  if (old && RENAMED[old]) history.replaceState(null, '', '#/' + RENAMED[old]);
}

const VIEWS: Record<string, [string, string, View]> = {
  sky: ['Sky images', 'SPHEREx images of any position, queried live', skyView],
  games: ['Games', 'The pipeline, one step at a time', detectivesView],
  targets: ['Test targets', 'Stars and brown dwarfs named in the challenge', starsView],
  'blind-test': ['Blind test', 'Recovering known objects without their later observations', benchmarkView],
  methods: ['Methods', 'Pipeline, full results, checks, downloads', scientistsView],
  about: ['About Rewind', 'Team / credits / AI use', aboutView],
};
export let source: DataSource;
const NAMED = 10; // Rewind objects that carry a name in the 3D view; with the planets that is about 20 labels

export function pageUrl(slug: string): string {
  const o = source.index.objects.find((x) => x.slug === slug)!;
  return resolveRel(source.base + 'index.json', o.page);
}

export function loadPage(slug: string): Promise<ObjectPage> {
  if (!pages.has(slug)) pages.set(slug, getJson<ObjectPage>(pageUrl(slug)));
  return pages.get(slug)!;
}

async function boot() {
  try {
    source = await loadIndex();
  } catch (e) {
    ui.innerHTML = `<p class="fatal" role="alert"><strong>No data to show yet</strong>Rewind could not find its data files (data/index.json or data-sample/index.json). If you are running the site yourself, run <code>npm run sync-data</code> or rebuild the sample with <code>npm run sample</code>, then reload. <span class="muted">(${esc(e)})</span></p>`;
    return;
  }
  document.body.classList.toggle('is-sample', source.sample);
  const idx = source.index;

  let scene: Scene;
  try {
    scene = new Scene(canvas, labelRoot);
  } catch {
    noWebgl();
    return;
  }
  const planets = await loadPlanets(source.base);
  scene.setPlanets(planets.planets);
  (window as unknown as { __rewind: unknown }).__rewind = { scene, store }; // for debugging and perf checks
  if (new URLSearchParams(location.search).get('fps') === '1') fpsMeter(scene);
  scene.start();
  document.body.classList.add('scene-ready');

  const select = (slug: string) => {
    location.hash = '#/object/' + slug;
  };
  scene.onPick = select;

  const topbar = mountTopbar(ui, idx.objects, source.sample, select);
  mountResults(ui, idx, source.sample, select);
  const mapUi = mountMapUi(ui, scene, idx.objects, planets.planets);
  const objectOf = (slug: string) => idx.objects.find((o) => o.slug === slug);
  const photoUrl = (f: FlashEvent) => resolveRel(source.base + 'index.json', f.photo);
  const timebar = mountTimebar(ui, idx.flash_events, { objectOf, photoUrl, onPin: (f) => pinFlash(f) });
  // keep scene labels out of the top bar and the time bar
  const safe = () => {
    document.documentElement.style.setProperty('--tb-h', timebar.offsetHeight - 16 + 'px');
    scene.labels.setSafeArea(topbar.getBoundingClientRect().bottom, (timebar.querySelector('.tb-grid') as HTMLElement).getBoundingClientRect().top - 8);
  };
  safe();
  window.addEventListener('resize', safe);

  // A dot starts on the orbit from the shared table. Once the object's page is read it moves to the
  // page's orbit, corrected to the engine's nominal path (first clone per date), so it sits inside its cloud.
  const dots = new Map<string, RewindDot>();
  const refine = async (slug: string) => {
    const d = dots.get(slug), p = d && (await loadPage(slug).catch(() => null));
    if (!d || !p || !isValidElements(p.orbit)) return;
    d.el = { ...p.orbit };
    if (p.cloud?.before?.length) d.track = { dates: p.cloud.dates_mjd, nominal: p.cloud.before.map((c) => c[0]) };
  };
  let heavy: Promise<void> | null = null;
  const loadHeavy = () =>
    (heavy ??= (async () => {
      const orbits = await loadOrbits(source.base);
      // a Rewind object is drawn once, as its own dot, not a second time in the crowd
      scene.setAsteroids(orbits, new Set(idx.objects.map((o) => orbits.slugs[o.slug]).filter((r) => r !== undefined)));
      document.body.classList.add('dots-ready');
      // every searched object is a dot, placed from the shared orbit table: there can be hundreds,
      // so their pages (about 100 KB each) are read only when needed. Only the strongest get a name.
      const named = new Set(rankObjects(idx.objects).slice(0, NAMED).map((o) => o.slug));
      const list = await Promise.all(
        idx.objects.map(async (o): Promise<RewindDot | null> => {
          const row = orbits.slugs[o.slug];
          // an object missing from the table can still get its orbit from its page
          const el = row !== undefined ? rowElements(orbits, row) : await loadPage(o.slug).then((p) => (isValidElements(p.orbit) ? { ...p.orbit } : null), () => null);
          if (!el || !isValidElements(el)) return null;
          const priority = !named.has(o.slug) ? 0 : o.verdict === 'FOUND' ? (isKnown(o) ? 7.5 : 8) : o.verdict === 'HINT' ? 7 : 6;
          // comets (C/, P/ and interstellar I/ names) get a short tail
          const comet = o.kind === 'comet' || /^\d*[CPI]\//.test(o.name);
          const tone = o.verdict === 'FOUND' ? 'found' : o.verdict === 'HINT' ? 'hint' : 'faint';
          return { slug: o.slug, name: o.name, knownMjd: knownSince(o), el, priority, comet, tone, pre: isPre(o) };
        }),
      );
      for (const d of list) if (d) dots.set(d.slug, d);
      scene.setRewindObjects([...dots.values()]);
      mapUi.refresh();
      // the finds get their exact path right away (their pages are read for the showcase anyway)
      await Promise.all(idx.objects.filter((o) => o.verdict === 'FOUND').map((o) => refine(o.slug)));
    })());
  const deepLink = /^#\/.+/.test(location.hash);
  if (!isPhone || deepLink) loadHeavy();

  let demo = 0;
  // ---------- flash, photo card, object panel, cloud ----------
  const card = mountPhotoCard(ui, {
    sample: source.sample,
    objectOf,
    photoUrl,
    page: loadPage,
    onOpen: select,
    onHide: () => (scene.labels.focus = null),
  });
  // the object in the photo is the one in focus: its label shows "Before first known obs."
  const flash = new FlashFx(scene, idx.flash_events, (f) => {
    scene.labels.focus = 'obj-' + f.slug;
    card.show(f);
    refine(f.slug); // the photo card reads the page anyway
  });
  // with many photos, only the finds flash on their own while the clock runs; every photo is still on the time bar
  const finds = new Set(idx.objects.filter((o) => o.verdict === 'FOUND').map((o) => o.slug));
  if (finds.size) flash.auto = finds;
  const cloud = new UncertaintyCloud(scene);
  const focus = new ObjectFocus(scene);
  // the three framings: the whole system (closes the object), its orbit, and the close-up
  const view = (l: Level) => {
    const slug = store.selected;
    if (l === 'system' || !slug) location.hash = '#/';
    else if (l === 'close') scene.frameClose(slug, focus.radius);
    else scene.frameOrbit(slug);
  };
  const panel = new ObjectPanel(ui, {
    sample: source.sample,
    url: (slug, rel) => resolveRel(pageUrl(slug), rel),
    onClose: () => (location.hash = '#/'),
    onView: view,
  });
  const dock = mountDock(ui, { onView: view, onCloud: (m) => cloud.setMode(m) });
  // fewer names the closer we get: the close-up keeps only Earth, SPHEREx and the Sun (the panel names the object)
  scene.onLevel = (l) => {
    panel.setLevel(l);
    dock.setLevel(l);
    const sel = 'obj-' + store.selected;
    scene.labels.filter =
      l === 'system' ? null
      : l === 'orbit' ? (id) => !id.startsWith('obj-') || id === sel
      : (id) => id.startsWith('focus-') || id === 'planet-Earth' || id === 'spherex' || id === 'sun';
  };
  const pinFlash = (f: FlashEvent) => {
    store.setPlaying(false);
    store.setTime(f.mjd);
    flash.trigger(f);
  };

  const openObject = async (slug: string) => {
    const o = objectOf(slug);
    if (!o) return;
    store.selected = slug;
    document.body.classList.add('obj-open');
    dismissOpening();
    card.hide();
    panel.loading(o);
    await loadHeavy();
    await refine(slug);
    if (store.selected !== slug) return;
    scene.highlight(slug, false);
    panelShift();
    const page0 = await loadPage(slug).catch(() => null);
    if (store.selected !== slug) return;
    // the body is drawn hugely enlarged; its size follows the cloud so the close-up shows both
    const spread = page0 ? cloud.extentAt(page0, store.mjd) : 0;
    focus.radius = spread > 0 ? Math.min(2.5e-4, Math.max(1.2e-5, spread * 0.15)) : 1.5e-4;
    // always the whole orbit first, never empty space
    const framed = scene.frameOrbit(slug);
    if (!framed) {
      // no orbit: look at where SPHEREx saw it, if we know that
      const f = idx.flash_events.find((x) => x.slug === slug);
      if (f) scene.flyTo(eclToThree(f.object_xyz_au), 1.5);
    }
    try {
      const p = await loadPage(slug);
      if (store.selected !== slug) return;
      panel.show(o, p, framed);
      cloud.show(p);
      cloud.setMode('before');
      if (framed) focus.show(slug, p, !!dots.get(slug)?.comet, focus.radius);
      dock.show(p, framed);
      scene.onLevel?.(scene.level);
    } catch {
      panel.fail('Could not load the details for this object.');
    }
  };
  const closeObject = () => {
    if (!store.selected) return;
    store.selected = null;
    document.body.classList.remove('obj-open');
    panel.close();
    cloud.show(null);
    focus.hide();
    dock.hide();
    scene.highlight(null);
    scene.setViewShift(0, 0);
    scene.stopFollow();
    scene.frameSystem();
  };
  // keep the selected object in the part of the screen the panel does not cover
  const panelShift = () => {
    if (!store.selected) return;
    const phone = window.matchMedia('(max-width: 720px)').matches;
    if (phone) scene.setViewShift(0, Math.round(window.innerHeight * 0.22));
    else scene.setViewShift(Math.round((panel.root.offsetWidth || 440) / 2), 0);
  };
  window.addEventListener('resize', panelShift);
  const dismissOpening = () => {
    document.body.classList.add('explored');
    document.body.classList.remove('hero');
    ui.querySelectorAll('.opening, .captions').forEach((e) => e.remove());
    cancelAnimationFrame(demo);
  };
  const host = new PageHost(ui, makeCtx(source));
  const route = () => {
    legacyHash();
    const m = location.hash.match(/^#\/object\/(.+)$/);
    const v = location.hash.match(/^#\/([\w-]+)$/)?.[1];
    if (v && VIEWS[v]) {
      dismissOpening();
      closeObject();
      if (host.current !== v) host.open(v, ...VIEWS[v]);
      return;
    }
    host.close();
    if (m) openObject(decodeURIComponent(m[1]));
    else closeObject();
  };
  window.addEventListener('hashchange', route);
  window.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && store.selected) location.hash = '#/';
  });

  // the photo first-time visitors are shown: strongest find before discovery (?flash=<slug> overrides)
  const params = new URLSearchParams(location.search);
  // chosen fresh from index.json: FOUND before HINT, highest null-scaled S/N, never a known object
  const showcase = pickShowcase(idx, loadPage, params.get('flash'));
  if (params.get('demo') === '1') {
    await loadHeavy();
    runDemo({ scene, cloud, flash, showcase: await showcase, page: loadPage, ui });
    return;
  }
  if (deepLink) {
    document.body.classList.add('explored');
    route();
    return;
  }
  let tour: Guided | null = null;
  let tourAsked = false;
  const startTour = async () => {
    if (tourAsked) return;
    tourAsked = true;
    const sc = await showcase;
    if (tour || !sc) return;
    tour = guidedRewind(scene, flash, sc.flash);
  };
  // only claim "SPHEREx saw it" in the opening if at least one new object is a sure find
  const t = tally(idx.objects);
  mountOpening(ui, {
    stats: [
      [String(t.before), t.before === 1 ? 'precovery: detected before its first known observation' : 'precoveries: detected before their first known observation', true],
      [String(t.searched), 'asteroids and comets searched'],
      [fmt(idx.headline_stats.frames_read), 'SPHEREx images analysed'],
    ],
    lastCaption: t.before ? undefined : 'Highlighted: an earlier SPHEREx image of the same field.',
    start: loadHeavy,
    onCaption: (i) => {
      cancelAnimationFrame(demo);
      if (reducedMotion) return;
      if (i === 1) {
        // a gentle rewind of about eight months
        const from = store.mjd, to = from - 240, t0 = performance.now();
        const step = () => {
          const k = Math.min(1, (performance.now() - t0) / 3200);
          store.setTime(from + (to - from) * (1 - Math.pow(1 - k, 3)));
          if (k < 1) demo = requestAnimationFrame(step);
        };
        demo = requestAnimationFrame(step);
      } else if (i === 2) {
        startTour();
      }
    },
    onDone: () => {
      cancelAnimationFrame(demo);
      document.body.classList.add('explored');
      // after Skip or the last caption, make sure the visitor sees one flash without touching anything
      startTour();
    },
  });
}

/** ?fps=1: frame rate, JS time per frame and dot count, for checking performance on a real GPU. */
function fpsMeter(scene: Scene) {
  const m = document.createElement('div');
  m.className = 'fps mono';
  document.body.appendChild(m);
  let frames = 0, t0 = performance.now();
  const gl = scene.renderer.getContext();
  const ext = gl.getExtension('WEBGL_debug_renderer_info');
  const gpu = ext ? String(gl.getParameter(ext.UNMASKED_RENDERER_WEBGL)).replace(/^ANGLE \((.*)\)$/, '$1').slice(0, 48) : 'unknown GPU';
  const tick = () => {
    frames++;
    const t = performance.now();
    if (t - t0 >= 1000) {
      m.textContent = `${Math.round((frames * 1000) / (t - t0))} fps / JS ${scene.jsMs.toFixed(1)} ms / ${scene.asteroids?.count ?? 0} dots / ${innerWidth}x${innerHeight} / ${gpu}`;
      frames = 0;
      t0 = t;
    }
    requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
}

// Without WebGL the 3D view is gone, but the pages (Games, Test targets, ...) still work.
function noWebgl() {
  document.body.classList.add('scene-ready', 'explored', 'no-webgl');
  mountTopbar(ui, source.index.objects, source.sample, () => {});
  ui.insertAdjacentHTML('beforeend', `<p class="fatal" role="alert"><strong>The 3D view could not start</strong>This browser or device could not start WebGL, which Rewind needs for the 3D solar system. Try another browser, or turn on hardware acceleration. The other pages still work: <a href="#/sky">Sky images</a>, <a href="#/games">Games</a>, <a href="#/targets">Test targets</a>, <a href="#/blind-test">Blind test</a>, <a href="#/methods">Methods</a>, <a href="#/about">About</a>.</p>`);
  const host = new PageHost(ui, makeCtx(source));
  const route = () => {
    legacyHash();
    const v = location.hash.match(/^#\/([\w-]+)$/)?.[1];
    if (v && VIEWS[v]) host.open(v, ...VIEWS[v]);
    else host.close();
  };
  window.addEventListener('hashchange', route);
  route();
}

boot();
