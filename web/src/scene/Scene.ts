// The 3D solar system: Sun, planets, asteroid cloud, Rewind objects, labels, camera.
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { type Elements, type PlanetRow, orbitPolyline, planetElements, planetPosition } from '../lib/kepler';
import type { OrbitColumns } from '../lib/data';
import { AsteroidCloud, eclToThree } from './asteroids';
import { LabelLayer } from './labels';
import { DropLines, LINE_LOOK, OrbitLine } from './orbit-lines';
import { dotPosition, orbitPath, type Track } from './orbits';
import { PLANET_LOOK, planetMaterial, rewindMaterial, starField, sunSprite } from './sprites';
import { isPhone, reducedMotion, store } from '../state';

const ORBIT_GREY = 0x5d6470;
const EARTH_BLUE = 0x5fa8e0;
const GOLD = 0xf2b544;
// Rewind dots by verdict: [colour once the object is known, size in px]. Before that every dot is grey.
const TONE = { found: [GOLD, 5.5], hint: [0x8ec5f5, 4], faint: [0x6b7079, 2.6] } as const;

export { dotPosition, type Track } from './orbits';

export interface RewindDot {
  track?: Track;
  priority?: number; // label priority, 6..8 (FOUND highest); 0 = named only when selected or in a flash
  slug: string;
  name: string;
  el: Elements;
  knownMjd: number; // when anyone first had the object
  tone?: keyof typeof TONE; // found = gold, hint = blue, faint = small and grey
  comet?: boolean; // drawn with a short tail
  pre?: boolean; // found before anyone knew it: these have their own layer
}

/** What the layers panel can switch on and off. */
export const LAYERS = ['found', 'searched', 'neo', 'comet', 'mba', 'planets'] as const;
export type Layer = (typeof LAYERS)[number];

/** Something the pointer can pick: a Rewind object or a planet. The background dots are not pickable. */
export type Target = { kind: 'object'; slug: string } | { kind: 'planet'; name: string };

interface Hit {
  planet: boolean;
  k: number; // index into the Rewind objects or the planets
}

const PICK_PX = 12; // a pointer picks the nearest object within this many px
const TOUCH_PX = 22; // a fingertip is less exact

/** The three camera framings: the whole system, one object's orbit, and the object close up. */
export type Level = 'system' | 'orbit' | 'close';

interface Fly {
  t0: number;
  dur: number;
  fromTgt: THREE.Vector3;
  toTgt: THREE.Vector3;
  fromDir: THREE.Vector3;
  toDir: THREE.Vector3;
  fromDist: number;
  toDist: number;
  limits: [number, number];
}

const UP = new THREE.Vector3(0, 1, 0);
const cubic = (t: number) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);

export class Scene {
  readonly renderer: THREE.WebGLRenderer;
  readonly scene = new THREE.Scene();
  readonly camera: THREE.PerspectiveCamera;
  readonly controls: OrbitControls;
  readonly labels: LabelLayer;
  asteroids: AsteroidCloud | null = null;
  readonly pixelRatio: number;
  private planets: PlanetRow[] = [];
  private planetDots!: THREE.Points;
  private rewind: RewindDot[] = [];
  private rewindDots: THREE.Points | null = null;
  private planetOrbits: [THREE.LineBasicMaterial, number][] = []; // material and its full opacity
  private lines = new Map<number, OrbitLine>(); // orbit lines by Rewind object index
  private drops = new DropLines(64);
  readonly layers: Record<Layer, boolean> = { found: true, searched: true, neo: true, comet: true, mba: true, planets: true };
  private layerNow: Record<Layer, number> = { found: 1, searched: 1, neo: 1, comet: 1, mba: 1, planets: 1 };
  // picking: the pointer highlights the nearest pickable object, and a click selects only that one
  private pointer: { x: number; y: number } | null = null;
  private press: { x: number; y: number; moved: boolean } | null = null;
  private hover: Hit | null = null;
  private labelHover: Hit | null = null;
  private pinned = -1; // the planet whose card is open
  private pickEl: HTMLDivElement;
  private pinEl: HTMLDivElement;
  private pinHtml = '';
  /** HTML for the small card under the pointer, and for a planet's card. Set by the app. */
  hoverCard: ((t: Target) => string) | null = null;
  planetCard: ((name: string) => string) | null = null;
  private sun = sunSprite();
  private size: [number, number] = [1, 1];
  jsMs = 0;
  private fly: Fly | null = null;
  level: Level = 'system';
  onLevel: ((l: Level) => void) | null = null;
  private follow: (() => THREE.Vector3 | null) | null = null;
  private lastFollow = new THREE.Vector3();
  private hooks: ((dt: number) => void)[] = [];
  autoRotate = !reducedMotion;
  onPick: ((slug: string) => void) | null = null;

  constructor(private canvas: HTMLCanvasElement, labelRoot: HTMLElement) {
    this.pixelRatio = Math.min(window.devicePixelRatio || 1, isPhone ? 1.25 : 2);
    this.renderer = new THREE.WebGLRenderer({ canvas, antialias: !isPhone, logarithmicDepthBuffer: true, powerPreference: 'high-performance' });
    this.renderer.setPixelRatio(this.pixelRatio);
    this.renderer.setClearColor(0x030407, 1);
    this.camera = new THREE.PerspectiveCamera(45, 1, 1e-6, 1e5);
    this.camera.position.set(0, 2.6, 4.2);
    this.controls = new OrbitControls(this.camera, canvas);
    this.controls.enableDamping = true;
    this.controls.dampingFactor = 0.08;
    this.controls.minDistance = 0.00002;
    this.controls.maxDistance = 120;
    this.controls.zoomSpeed = 0.8;
    // never roll over the poles
    this.controls.minPolarAngle = 0.06;
    this.controls.maxPolarAngle = Math.PI - 0.06;
    this.controls.addEventListener('start', () => {
      this.autoRotate = false;
      // keep the flight's end limits, widened so the camera does not jump from where it is now
      if (this.fly) {
        const cur = this.camera.position.distanceTo(this.controls.target);
        this.setLimits([Math.min(this.fly.limits[0], cur), Math.max(this.fly.limits[1], cur)]);
      }
      this.fly = null;
    });
    this.labels = new LabelLayer(labelRoot);
    this.scene.add(starField(this.pixelRatio), this.drops.lines);
    this.addSun();
    this.pickEl = document.createElement('div');
    this.pickEl.className = 'pick';
    this.pickEl.innerHTML = '<i class="pick-ring"></i><div class="pick-card"></div>';
    this.pinEl = document.createElement('div');
    this.pinEl.className = 'pick pick-pin';
    this.pinEl.innerHTML = '<i class="pick-ring"></i><div class="pick-card planet-card" role="status"></div>';
    labelRoot.append(this.pinEl, this.pickEl);
    this.listen();
    window.addEventListener('resize', () => this.resize());
    this.resize();
  }

  private shift: [number, number] = [0, 0];
  private shiftNow: [number, number] = [0, 0];

  get viewSize(): [number, number] {
    return this.size;
  }

  private resize() {
    const w = this.canvas.clientWidth || window.innerWidth;
    const h = this.canvas.clientHeight || window.innerHeight;
    this.renderer.setSize(w, h, false);
    this.size = [w, h];
    this.camera.aspect = w / h;
    this.applyShift();
  }

  /** Move the centre of view by (dx, dy) px, e.g. to keep the target clear of a side panel. It eases there. */
  setViewShift(dx: number, dy: number) {
    this.shift = [dx, dy];
    if (reducedMotion) {
      this.shiftNow = [dx, dy];
      this.applyShift();
    }
  }

  private easeShift(dt: number) {
    const [a, b] = this.shiftNow, [x, y] = this.shift;
    if (a === x && b === y) return;
    const k = 1 - Math.exp(-dt * 7);
    this.shiftNow = [Math.abs(x - a) < 0.5 ? x : a + (x - a) * k, Math.abs(y - b) < 0.5 ? y : b + (y - b) * k];
    this.applyShift();
  }

  private applyShift() {
    const w = this.canvas.clientWidth || window.innerWidth;
    const h = this.canvas.clientHeight || window.innerHeight;
    const [dx, dy] = this.shiftNow;
    if (dx || dy) this.camera.setViewOffset(w, h, dx, dy, w, h);
    else this.camera.clearViewOffset();
    this.camera.updateProjectionMatrix();
  }

  private addSun() {
    this.scene.add(this.sun);
    this.labels.add({ id: 'sun', text: 'Sun', cls: 'label-planet', priority: 6, pos: (o) => o.set(0, 0, 0), pad: () => 8 });
  }

  setPlanets(planets: PlanetRow[]) {
    this.planets = planets;
    const mjd = store.mjd;
    planets.forEach((p) => {
      const isEarth = p.name === 'Earth';
      const pts = orbitPolyline(planetElements(p, mjd), 720).map((v) => eclToThree(v));
      const mat = new THREE.LineBasicMaterial({ color: isEarth ? EARTH_BLUE : ORBIT_GREY, transparent: true, opacity: isEarth ? 0.75 : 0.42, depthWrite: false });
      this.planetOrbits.push([mat, mat.opacity]);
      this.scene.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts), mat));
      const idx = planets.indexOf(p);
      const look = PLANET_LOOK[p.name];
      const at = new THREE.Vector3();
      const where = (o: THREE.Vector3) => o.fromArray(this.planetDots.geometry.attributes.position.array as Float32Array, idx * 3);
      this.labels.add({
        id: 'planet-' + p.name,
        text: isEarth ? 'Earth' : p.name,
        cls: isEarth ? 'label-planet label-earth' : 'label-planet',
        priority: isEarth ? 9 : 5 - idx * 0.1,
        pos: where,
        // keep the name clear of the sphere (and the ring), which grow when the camera is close
        pad: () => (look ? (look.px / 2) * THREE.MathUtils.clamp(1.2 / this.camera.position.distanceTo(where(at)), 1, 2.6) * (look.ring ? 2.2 : 1) - 3 : 0),
        onClick: () => this.pin(this.pinned === idx ? -1 : idx),
        onHover: (on) => this.overLabel({ planet: true, k: idx }, on),
      });
    });
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(planets.length * 3), 3));
    const col = new Float32Array(planets.length * 3), look = new Float32Array(planets.length * 3);
    planets.forEach((p, k) => {
      const l = PLANET_LOOK[p.name] ?? { color: 0xc9ccd2, px: 7 };
      const c = new THREE.Color(l.color);
      col.set([c.r, c.g, c.b], k * 3);
      look.set([l.px, l.ring ? 1 : 0, l.bands ?? 0], k * 3);
    });
    g.setAttribute('color', new THREE.BufferAttribute(col, 3));
    g.setAttribute('look', new THREE.BufferAttribute(look, 3));
    this.planetDots = new THREE.Points(g, planetMaterial(this.pixelRatio));
    this.planetDots.frustumCulled = false;
    this.scene.add(this.planetDots);
    this.addSpherex();
  }

  /** SPHEREx sits in low Earth orbit, so it is drawn at Earth with a short leader line. */
  private addSpherex() {
    this.labels.add({ id: 'spherex', text: 'SPHEREx', cls: 'label-spherex', priority: 8.9, offset: [-34, -30], pos: (o) => this.earthPosition(o) });
  }

  earthPosition(out = new THREE.Vector3()): THREE.Vector3 {
    const e = this.planets.find((p) => p.name === 'Earth');
    return e ? eclToThree(planetPosition(e, store.mjd), out) : out.set(1, 0, 0);
  }

  /** `skip`: rows of the table that are drawn as Rewind dots instead. */
  setAsteroids(orb: OrbitColumns, skip?: Set<number>) {
    this.asteroids = new AsteroidCloud(orb, this.pixelRatio, skip);
    this.scene.add(this.asteroids.points);
  }

  setRewindObjects(list: RewindDot[]) {
    this.rewind = list;
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(list.length * 3), 3));
    g.setAttribute('color', new THREE.BufferAttribute(new Float32Array(list.length * 3), 3));
    g.setAttribute('size', new THREE.BufferAttribute(Float32Array.from(list, (o) => TONE[o.tone ?? 'found'][1]), 1));
    g.setAttribute('tail', new THREE.BufferAttribute(Float32Array.from(list, (o) => (o.comet ? 1 : 0)), 1));
    g.setAttribute('fade', new THREE.BufferAttribute(new Float32Array(list.length).fill(1), 1));
    this.rewindDots = new THREE.Points(g, rewindMaterial(this.pixelRatio));
    this.rewindDots.frustumCulled = false;
    this.rewindDots.renderOrder = 2;
    this.scene.add(this.rewindDots);
    // an object missing from the table's name index may still be in the crowd: draw it once
    this.asteroids?.hideNear(list.map((o) => eclToThree(dotPosition(o, store.mjd)).toArray()), store.mjd);
    list.forEach((o, k) => {
      this.labels.add({
        id: 'obj-' + o.slug,
        text: o.name,
        cls: 'label-rewind',
        priority: o.priority ?? 7,
        sub: () => (store.mjd < o.knownMjd ? 'Nobody knew it yet' : null),
        pos: (out) => out.fromArray(g.attributes.position.array as Float32Array, k * 3),
        onClick: () => this.onPick?.(o.slug),
        onHover: (on) => this.overLabel({ planet: false, k }, on),
        visible: () => this.layers[o.pre ? 'found' : 'searched'],
      });
    });
  }

  /** Direction to look at an object's along-track cloud side-on (orbit normal, tilted towards the Sun side). */
  sideView(slug: string): THREE.Vector3 | null {
    const o = this.rewind.find((r) => r.slug === slug);
    if (!o) return null;
    const a = eclToThree(dotPosition(o, store.mjd)), b = eclToThree(dotPosition(o, store.mjd + 5));
    const v = b.clone().sub(a).normalize();
    const n = a.clone().cross(v).normalize();
    if (n.y < 0) n.negate();
    return n.multiplyScalar(0.85).add(a.clone().normalize().multiplyScalar(-0.35)).normalize();
  }

  rewindPosition(slug: string, out = new THREE.Vector3()): THREE.Vector3 | null {
    return this.rewindPositionAt(slug, store.mjd, out);
  }

  rewindPositionAt(slug: string, mjd: number, out = new THREE.Vector3()): THREE.Vector3 | null {
    const o = this.rewindDot(slug);
    return o ? eclToThree(dotPosition(o, mjd), out) : null;
  }

  rewindDot(slug: string): RewindDot | undefined {
    return this.rewind.find((r) => r.slug === slug);
  }

  /** Put one object in front: its name wins and the crowd of dots dims. (Its orbit is drawn by the object focus.) */
  highlight(slug: string | null, _showOrbit = true) {
    this.rewind.forEach((o) => {
      this.labels.setPriority('obj-' + o.slug, o.slug === slug ? 12 : slug ? Math.min(4, o.priority ?? 7) : o.priority ?? 7);
      this.labels.setClass('obj-' + o.slug, 'selected', o.slug === slug);
    });
    if (this.asteroids) this.asteroids.material.uniforms.uDim.value = slug ? 1 : 0;
  }

  // ---------- layers ----------
  setLayer(layer: Layer, on: boolean) {
    this.layers[layer] = on;
  }

  /** How many things each layer holds, for the layers panel. */
  layerCounts(): Record<Layer, number> {
    const found = this.rewind.filter((o) => o.pre).length;
    const g = this.asteroids?.groups ?? { neo: 0, mba: 0, comet: 0 };
    return { found, searched: this.rewind.length - found, neo: g.neo, comet: g.comet, mba: g.mba, planets: this.planets.length };
  }

  private easeLayers(k: number) {
    for (const l of LAYERS) {
      const to = this.layers[l] ? 1 : 0, d = to - this.layerNow[l];
      this.layerNow[l] = Math.abs(d) < 0.004 ? to : this.layerNow[l] + d * k;
    }
    const n = this.layerNow;
    this.asteroids?.material.uniforms.uGroup.value.set(n.neo, n.mba, n.comet);
    for (const [m, full] of this.planetOrbits) {
      m.opacity = full * n.planets;
      m.visible = n.planets > 0.004;
    }
  }

  // ---------- picking ----------
  private listen() {
    const c = this.canvas;
    const at = (e: PointerEvent) => {
      const r = c.getBoundingClientRect();
      return { x: e.clientX - r.left, y: e.clientY - r.top };
    };
    c.addEventListener('pointerdown', (e) => {
      if (e.isPrimary && e.button === 0) this.press = { ...at(e), moved: false };
    });
    c.addEventListener('pointermove', (e) => {
      const p = at(e);
      // past a few px it is a drag: it turns the view and never selects
      if (this.press && Math.hypot(p.x - this.press.x, p.y - this.press.y) > (e.pointerType === 'mouse' ? 5 : 10)) this.press.moved = true;
      this.pointer = e.pointerType === 'mouse' ? p : null;
    });
    c.addEventListener('pointerup', (e) => {
      const press = this.press;
      this.press = null;
      if (!press || press.moved || !e.isPrimary) return;
      const hit = this.nearest(press.x, press.y, e.pointerType === 'mouse' ? PICK_PX : TOUCH_PX);
      // empty space: nothing is selected, and an open planet card closes
      if (!hit || hit.planet) this.pin(hit && hit.k !== this.pinned ? hit.k : -1);
      else {
        this.pin(-1);
        this.onPick?.(this.rewind[hit.k].slug);
      }
    });
    c.addEventListener('pointercancel', () => (this.press = null));
    c.addEventListener('pointerleave', () => (this.pointer = null));
    window.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') this.pin(-1);
    });
  }

  private overLabel(h: Hit, on: boolean) {
    if (on) this.labelHover = h;
    else if (this.labelHover?.planet === h.planet && this.labelHover.k === h.k) this.labelHover = null;
  }

  /** Open a planet's card (-1 closes it). */
  private pin(k: number) {
    this.pinned = k;
    this.pinHtml = '';
    this.pinEl.classList.toggle('on', k >= 0);
  }

  private planetPx(k: number, at: THREE.Vector3): number {
    const look = PLANET_LOOK[this.planets[k].name];
    return (look?.px ?? 7) * THREE.MathUtils.clamp(1.2 / this.camera.position.distanceTo(at), 1, 2.6);
  }

  private v = new THREE.Vector3();
  private at = new THREE.Vector3();

  /** Screen position (px) of a world point, or null when it is behind the camera. */
  private toScreen(p: THREE.Vector3): [number, number] | null {
    this.v.copy(p).project(this.camera);
    return this.v.z > 1 ? null : [(this.v.x * 0.5 + 0.5) * this.size[0], (-this.v.y * 0.5 + 0.5) * this.size[1]];
  }

  private hitPosition(h: Hit, out: THREE.Vector3): THREE.Vector3 {
    const dots = h.planet ? this.planetDots : this.rewindDots!;
    return out.fromArray(dots.geometry.attributes.position.array as Float32Array, h.k * 3);
  }

  /** The nearest pickable object within `reach` px of a screen point: Rewind objects and planets only. */
  private nearest(x: number, y: number, reach: number): Hit | null {
    if (this.level === 'close') return null;
    let best = reach, hit: Hit | null = null;
    const fade = this.rewindDots?.geometry.attributes.fade.array as Float32Array | undefined;
    this.rewind.forEach((o, k) => {
      if (fade![k] < 0.5 || o.slug === store.selected) return;
      const s = this.toScreen(this.hitPosition({ planet: false, k }, this.at));
      if (!s) return;
      // a find wins a near tie with a fainter neighbour
      const d = Math.hypot(s[0] - x, s[1] - y) - (o.pre ? 3 : 0);
      if (d < best) {
        best = d;
        hit = { planet: false, k };
      }
    });
    if (this.planetDots) {
      this.planets.forEach((_p, k) => {
        const s = this.toScreen(this.hitPosition({ planet: true, k }, this.at));
        if (!s) return;
        // anywhere on the planet's disc counts; a dot right under the pointer still wins
        const d = Math.max(0, Math.hypot(s[0] - x, s[1] - y) - this.planetPx(k, this.at) / 2) + 2;
        if (d < best) {
          best = d;
          hit = { planet: true, k };
        }
      });
    }
    return hit;
  }

  private place(el: HTMLElement, h: Hit): boolean {
    const p = this.hitPosition(h, this.at);
    const s = this.toScreen(p);
    if (!s) return false;
    const [w, hgt] = this.size;
    const d = h.planet ? this.planetPx(h.k, p) + 14 : 24;
    el.style.transform = `translate3d(${s[0].toFixed(1)}px, ${s[1].toFixed(1)}px, 0)`;
    el.style.setProperty('--d', d.toFixed(0) + 'px');
    // keep the card on screen: nudge it sideways near the edges, flip it above near the bottom
    el.style.setProperty('--dx', (Math.min(w - 136, Math.max(136, s[0])) - s[0]).toFixed(0) + 'px');
    el.classList.toggle('up', s[1] > hgt * 0.6);
    return true;
  }

  private updatePick() {
    let h: Hit | null = null;
    if (this.pointer && !this.press?.moved) h = this.nearest(this.pointer.x, this.pointer.y, PICK_PX);
    h ??= this.level === 'close' ? null : this.labelHover;
    // the planet whose card is open needs no second card
    if (h?.planet && h.k === this.pinned) h = null;
    if (h?.planet !== this.hover?.planet || h?.k !== this.hover?.k) {
      this.hover = h;
      this.canvas.style.cursor = h ? 'pointer' : '';
      if (h) {
        const o = this.rewind[h.k];
        (this.pickEl.lastElementChild as HTMLElement).innerHTML = this.hoverCard?.(h.planet ? { kind: 'planet', name: this.planets[h.k].name } : { kind: 'object', slug: o.slug }) ?? '';
        this.pickEl.classList.toggle('pick-gold', !h.planet && (o.tone ?? 'found') === 'found');
      }
    }
    this.pickEl.classList.toggle('on', !!h && this.place(this.pickEl, h));
    if (this.pinned >= 0 && this.place(this.pinEl, { planet: true, k: this.pinned })) {
      const html = this.planetCard?.(this.planets[this.pinned].name) ?? '';
      if (html !== this.pinHtml) (this.pinEl.lastElementChild as HTMLElement).innerHTML = this.pinHtml = html;
    }
  }

  // ---------- orbit lines of Rewind objects ----------
  /**
   * Finds keep a gold line and hints a short blue trail; any object's whole orbit lights up under
   * the pointer. A line appears once the object is known, like its colour. Each line is rebuilt
   * around the dot whenever the dot moves, from the same propagation.
   */
  private updateLines(k: number) {
    const mjd = store.mjd, sel = store.selected, close = this.level === 'close';
    const hov = this.hover && !this.hover.planet ? this.hover.k : -1;
    const fade = this.rewindDots!.geometry.attributes.fade.array as Float32Array;
    const drops: { at: THREE.Vector3; color: THREE.Color; amount: number }[] = [];
    this.rewind.forEach((o, i) => {
      const tone = o.tone ?? 'found', look = LINE_LOOK[tone], on = i === hov;
      let line = this.lines.get(i);
      if (!line) {
        if (!on && !look.rest[0]) return;
        line = new OrbitLine(look);
        this.lines.set(i, line);
        this.scene.add(line.line);
      }
      // an open object has its own glowing orbit; the other lines step back
      const amount = close || o.slug === sel ? 0 : on ? 1 : mjd < o.knownMjd ? 0 : fade[i] * (sel ? 0.3 : 1);
      line.ease(on, amount, k);
      if (!line.line.visible) {
        if (!look.rest[0] && !on) {
          this.scene.remove(line.line);
          line.dispose();
          this.lines.delete(i);
        }
        return;
      }
      if (line.mjd !== mjd || line.src !== o.el) {
        line.set(orbitPath(o, mjd, tone === 'found' ? 192 : 96));
        line.mjd = mjd;
        line.src = o.el;
      }
      if (tone === 'found' || on) drops.push({ at: line.line.position, color: line.color, amount: Math.min(1, line.gain) });
    });
    this.drops.set(drops);
  }

  /**
   * Ease the camera to look at a target from a given distance. The flight turns around the
   * target and changes distance on a log scale, so big zooms feel even and the view never flips.
   * Zooming in, the aim settles first and the dive follows; zooming out, the reverse.
   */
  flyTo(target: THREE.Vector3, distance: number, follow: (() => THREE.Vector3 | null) | null = null, viewDir?: THREE.Vector3, limits: [number, number] = [0.00002, 120]) {
    this.autoRotate = false;
    const dir = viewDir ? viewDir.clone().normalize() : this.camera.position.clone().sub(this.controls.target).normalize();
    if (!viewDir && dir.y < 0.25) dir.y = 0.35;
    dir.normalize();
    this.follow = follow;
    const p = follow?.();
    if (p) this.lastFollow.copy(p);
    const off = this.camera.position.clone().sub(this.controls.target);
    if (reducedMotion) {
      this.controls.target.copy(target);
      this.camera.position.copy(target).addScaledVector(dir, distance);
      this.setLimits(limits);
      return;
    }
    // the controls must not clamp the camera mid-flight
    this.controls.minDistance = Math.min(limits[0], off.length(), distance) * 0.5;
    this.controls.maxDistance = Math.max(limits[1], off.length(), distance) * 2;
    const ratio = Math.abs(Math.log(Math.max(1e-12, distance) / Math.max(1e-12, off.length())));
    this.fly = {
      t0: performance.now(),
      dur: Math.min(2000, 1200 + ratio * 60),
      fromTgt: this.controls.target.clone(),
      toTgt: target.clone(),
      fromDir: off.clone().normalize(),
      toDir: dir,
      fromDist: off.length(),
      toDist: distance,
      limits,
    };
  }

  private setLimits([lo, hi]: [number, number]) {
    this.controls.minDistance = lo;
    this.controls.maxDistance = hi;
  }

  private setLevel(l: Level) {
    if (this.level === l) return;
    this.level = l;
    this.onLevel?.(l);
  }

  /** Camera distance that fits points in view, looking at `target` from direction `dir`. */
  fitFrom(target: THREE.Vector3, dir: THREE.Vector3, points: THREE.Vector3[], fill = 0.82): number {
    const f = dir.clone().normalize();
    const right = new THREE.Vector3().crossVectors(Math.abs(f.y) > 0.98 ? new THREE.Vector3(1, 0, 0) : UP, f).normalize();
    const up = new THREE.Vector3().crossVectors(f, right);
    const [w, h] = this.size;
    const tanV = Math.tan(THREE.MathUtils.degToRad(this.camera.fov / 2));
    // only the part of the screen the panel does not cover counts
    const tx = tanV * this.camera.aspect * Math.max(0.3, (w - 2 * Math.abs(this.shift[0])) / w) * fill;
    const ty = tanV * Math.max(0.3, (h - 2 * Math.abs(this.shift[1])) / h) * fill * 0.86;
    const q = new THREE.Vector3();
    let d = 0;
    for (const p of points) {
      q.copy(p).sub(target);
      const z = q.dot(f);
      d = Math.max(d, z + Math.abs(q.dot(right)) / tx, z + Math.abs(q.dot(up)) / ty);
    }
    return d;
  }

  /** The whole solar system, as on the home page. */
  frameSystem() {
    this.setLevel('system');
    this.flyTo(new THREE.Vector3(0, 0, 0), 5, null, undefined, [0.15, 60]);
  }

  /**
   * One object's whole orbit with Earth's orbit and the Sun, seen from about 35 degrees above
   * the planets' plane, turned so the object sits on the near side.
   */
  frameOrbit(slug: string) {
    const o = this.rewindDot(slug);
    const at = this.rewindPosition(slug);
    if (!o || !at) return false;
    // far-out comets: frame the inner part of the orbit, not hundreds of AU
    const cap = Math.max(5.5, at.length() * 1.6);
    const pts = orbitPolyline(o.el, 256, cap).map((v) => eclToThree(v)).filter((p) => p.length() <= cap);
    for (let k = 0; k < 24; k++) pts.push(new THREE.Vector3(Math.cos((k / 24) * Math.PI * 2), 0, Math.sin((k / 24) * Math.PI * 2)));
    pts.push(new THREE.Vector3(), at.clone());
    const box = new THREE.Box3().setFromPoints(pts);
    const target = box.getCenter(new THREE.Vector3());
    target.y *= 0.5;
    const az = Math.atan2(at.z - target.z, at.x - target.x) + 0.45;
    const el = THREE.MathUtils.degToRad(35);
    const dir = new THREE.Vector3(Math.cos(el) * Math.cos(az), Math.sin(el), Math.cos(el) * Math.sin(az));
    const d = this.fitFrom(target, dir, pts);
    this.setLevel('orbit');
    this.flyTo(target, d, null, dir, [d * 0.3, d * 4]);
    return true;
  }

  /**
   * The object large in the middle, lit from the side by the Sun, with Earth behind it:
   * the camera sits between the Sun side and the far side from Earth.
   */
  frameClose(slug: string, radius: number) {
    const at = this.rewindPosition(slug);
    if (!at) return false;
    const toSun = at.clone().negate().normalize();
    const fromEarth = at.clone().sub(this.earthPosition()).normalize();
    const dir = toSun.multiplyScalar(0.55).add(fromEarth.multiplyScalar(0.75)).add(new THREE.Vector3(0, 0.28, 0));
    if (dir.lengthSq() < 1e-6) dir.set(0, 1, 1);
    dir.normalize();
    // turn a little around the Sun line so the Sun lights the body from the side (a 3/4 phase)
    dir.applyAxisAngle(UP, 0.5).normalize();
    const tmp = new THREE.Vector3();
    this.setLevel('close');
    this.flyTo(at, radius * 7, () => this.rewindPosition(slug, tmp), dir, [radius * 2.2, 6]);
    return true;
  }

  /** Distance at which a set of points spans `fraction` of the screen (fuller axis), keeping the view direction. */
  fitDistance(points: THREE.Vector3[], fraction: number): number | null {
    if (points.length < 2) return null;
    const d = this.camera.position.distanceTo(this.controls.target);
    const v = new THREE.Vector3();
    let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity;
    for (const p of points) {
      v.copy(p).project(this.camera);
      x0 = Math.min(x0, v.x);
      x1 = Math.max(x1, v.x);
      y0 = Math.min(y0, v.y);
      y1 = Math.max(y1, v.y);
    }
    // fraction of the screen the points cover, along whichever axis is fuller
    const size = Math.max((x1 - x0) / 2, (y1 - y0) / 2);
    return size > 0 ? (d * size) / fraction : null;
  }

  stopFollow() {
    this.follow = null;
  }

  addHook(fn: (dt: number) => void) {
    this.hooks.push(fn);
  }

  private updateBodies(ease: number) {
    const mjd = store.mjd;
    if (this.planetDots) {
      const a = this.planetDots.geometry.attributes.position as THREE.BufferAttribute;
      const v = new THREE.Vector3();
      this.planets.forEach((p, k) => {
        eclToThree(planetPosition(p, mjd), v);
        a.setXYZ(k, v.x, v.y, v.z);
      });
      a.needsUpdate = true;
    }
    if (this.rewindDots) {
      const a = this.rewindDots.geometry.attributes.position as THREE.BufferAttribute;
      const c = this.rewindDots.geometry.attributes.color as THREE.BufferAttribute;
      const f = this.rewindDots.geometry.attributes.fade as THREE.BufferAttribute;
      const v = new THREE.Vector3();
      const col = new THREE.Color();
      this.rewind.forEach((o, k) => {
        eclToThree(dotPosition(o, mjd), v);
        a.setXYZ(k, v.x, v.y, v.z);
        const tone = o.tone ?? 'found';
        col.set(mjd < o.knownMjd && tone !== 'faint' ? 0x777a80 : TONE[tone][0]);
        c.setXYZ(k, col.r, col.g, col.b);
        f.setX(k, this.layerNow[o.pre ? 'found' : 'searched']);
      });
      a.needsUpdate = true;
      c.needsUpdate = true;
      f.needsUpdate = true;
      this.updateLines(ease);
    }
    this.asteroids?.setTime(mjd, performance.now() / 1000);
    // the Sun's glow keeps a minimum size on screen, however far out the camera is
    this.sun.scale.setScalar(Math.max(0.5, this.camera.position.length() * 0.17));
  }

  start() {
    let last = performance.now();
    const loop = () => {
      const now = performance.now();
      const dt = Math.min(0.1, (now - last) / 1000);
      last = now;
      if (store.playing) store.setTime(store.mjd + store.speed * dt);
      this.easeShift(dt);
      const ease = reducedMotion ? 1 : 1 - Math.exp(-dt * 9);
      this.easeLayers(ease);
      this.updateBodies(ease);
      for (const h of this.hooks) h(dt);
      if (this.fly) {
        const f = this.fly;
        const t = Math.min(1, (performance.now() - f.t0) / f.dur);
        const k = cubic(t);
        // if following a moving object, aim at where it is now
        if (this.follow) {
          const p = this.follow();
          if (p) {
            f.toTgt.copy(p);
            this.lastFollow.copy(p); // so a grab mid-flight keeps following from here, without a jump
          }
        }
        const zoomIn = f.toDist < f.fromDist * 0.5, zoomOut = f.toDist > f.fromDist * 2;
        const kt = zoomIn ? cubic(Math.min(1, t / 0.62)) : zoomOut ? cubic(Math.max(0, (t - 0.38) / 0.62)) : k;
        this.controls.target.lerpVectors(f.fromTgt, f.toTgt, kt);
        const q = new THREE.Quaternion().setFromUnitVectors(f.fromDir, f.toDir);
        const dir = f.fromDir.clone().applyQuaternion(new THREE.Quaternion().slerp(q, k));
        const dist = Math.exp(Math.log(f.fromDist) + (Math.log(f.toDist) - Math.log(f.fromDist)) * k);
        this.camera.position.copy(this.controls.target).addScaledVector(dir, dist);
        if (t >= 1) {
          this.fly = null;
          this.setLimits(f.limits);
          if (this.follow) this.lastFollow.copy(this.follow() ?? f.toTgt);
        }
      } else if (this.follow) {
        const p = this.follow();
        if (p) {
          const d = p.clone().sub(this.lastFollow);
          this.camera.position.add(d);
          this.controls.target.add(d);
          this.lastFollow.copy(p);
        }
      }
      if (this.autoRotate) {
        const ang = dt * 0.03;
        const off = this.camera.position.clone().sub(this.controls.target);
        off.applyAxisAngle(new THREE.Vector3(0, 1, 0), ang);
        this.camera.position.copy(this.controls.target).add(off);
      }
      this.controls.update();
      this.renderer.render(this.scene, this.camera);
      this.labels.update(this.camera, this.size[0], this.size[1]);
      this.updatePick();
      // JS time per frame (smoothed), shown by the ?fps=1 meter
      this.jsMs = this.jsMs * 0.95 + (performance.now() - now) * 0.05;
      requestAnimationFrame(loop);
    };
    requestAnimationFrame(loop);
  }
}
