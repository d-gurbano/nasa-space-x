// The Sun's neighbourhood in 3D: the Sun at the centre, the challenge stars and a few bright
// neighbours at their real distances (1 unit = 1 parsec). Every star is a soft light in its own
// colour. Picking a star flies in to a close-up, with the Sun or Jupiter drawn beside it for size,
// and draws one thin trace of its path across the time slider, with a mark where it is today. The two far stars
// sit on a ring that is not to scale. Star sizes on the map are symbols, not to scale.
// Labels are HTML on top of the canvas, so they stay sharp and can be focused and clicked.
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { compare, FAR_RING, NEAR_LIMIT, scenePos, STARS, SUN, type Kind, type Star } from './motion';
import { declutter, PAD, type LabelBox } from './declutter';

const PATH: [number, number] = [-10_000, 12_000];
/** The overview direction; its distance is set so the far ring fits the view. */
const HOME_DIR = new THREE.Vector3(5.2, 4.4, 9.6).normalize();
const FOV = 48;
/** Sphere radius on the map (pc), by kind: a symbol, since real stars would be far too small to see. */
const RADIUS: Record<Kind, number> = { sun: 0.13, 'red dwarf': 0.09, 'brown dwarf': 0.075, 'young variable star': 0.1, 'pulsating red giant': 0.13, context: 0.07 };
/** In the close-up the camera sits this many star radii away. */
const CLOSE = 7.5;
const CMP_COLOR = { Sun: SUN.color, Jupiter: 0xe0b080 };
/** The trace runs from 0 to 1 over the slider; it fades out over this much at each end. */
const FADE = 0.3;
const TODAY = 2026;

/** A soft round glow, white so each sprite can tint it. */
function glowTexture(): THREE.Texture {
  const c = document.createElement('canvas');
  c.width = c.height = 128;
  const g = c.getContext('2d')!, r = g.createRadialGradient(64, 64, 0, 64, 64, 64);
  r.addColorStop(0, 'rgba(255,255,255,1)');
  r.addColorStop(0.12, 'rgba(255,255,255,0.85)');
  r.addColorStop(0.32, 'rgba(255,255,255,0.28)');
  r.addColorStop(0.62, 'rgba(255,255,255,0.07)');
  r.addColorStop(1, 'rgba(255,255,255,0)');
  g.fillStyle = r;
  g.fillRect(0, 0, 128, 128);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}

/** The corona: bright at the star's edge (a quarter of the way out), then a long soft fall. */
function coronaTexture(): THREE.Texture {
  const c = document.createElement('canvas');
  c.width = c.height = 256;
  const g = c.getContext('2d')!, r = g.createRadialGradient(128, 128, 0, 128, 128, 128);
  for (const [at, a] of [[0, 1], [0.25, 0.85], [0.3, 0.5], [0.4, 0.22], [0.58, 0.08], [0.8, 0.02], [1, 0]]) r.addColorStop(at, `rgba(255,255,255,${a})`);
  g.fillStyle = r;
  g.fillRect(0, 0, 256, 256);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}

const STAR_VERT = `
varying vec3 vObj; varying vec3 vN; varying vec3 vView;
void main() {
  vObj = position;
  vN = normalize(normalMatrix * normal);
  vec4 mv = modelViewMatrix * vec4(position, 1.0);
  vView = -mv.xyz;
  gl_Position = projectionMatrix * mv;
}`;
// limb darkening, a hot centre, and a slow shimmer: granules on stars, cloud bands on brown dwarfs
const STAR_FRAG = `
uniform vec3 uColor; uniform float uTime; uniform float uBands; uniform float uBright;
varying vec3 vObj; varying vec3 vN; varying vec3 vView;
float hash(vec3 p) { p = fract(p * 0.3183099 + 0.1); p *= 17.0; return fract(p.x * p.y * p.z * (p.x + p.y + p.z)); }
float noise(vec3 x) {
  vec3 i = floor(x), f = fract(x); f = f * f * (3.0 - 2.0 * f);
  return mix(mix(mix(hash(i), hash(i + vec3(1, 0, 0)), f.x), mix(hash(i + vec3(0, 1, 0)), hash(i + vec3(1, 1, 0)), f.x), f.y),
             mix(mix(hash(i + vec3(0, 0, 1)), hash(i + vec3(1, 0, 1)), f.x), mix(hash(i + vec3(0, 1, 1)), hash(i + vec3(1, 1, 1)), f.x), f.y), f.z);
}
void main() {
  float mu = clamp(dot(normalize(vN), normalize(vView)), 0.0, 1.0);
  vec3 p = normalize(vObj);
  float grain = noise(p * 7.0 + vec3(0.0, uTime * 0.14, 0.0)) * 0.6 + noise(p * 17.0 - vec3(uTime * 0.22, 0.0, 0.0)) * 0.4;
  float band = 0.5 + 0.5 * sin(p.y * 13.0 + noise(p * 3.0 + vec3(uTime * 0.04, 0.0, 0.0)) * 3.0);
  float tex = mix(grain, band * 0.75 + grain * 0.25, uBands);
  vec3 hot = mix(uColor, vec3(1.0), 0.6);
  vec3 col = mix(uColor * 0.5, hot, clamp(tex * 0.55 + 0.6 * pow(mu, 1.6), 0.0, 1.0));
  col *= (1.0 - 0.7 * (1.0 - pow(mu, 0.6))) * uBright;
  gl_FragColor = vec4(col, 1.0);
  #include <colorspace_fragment>
}`;

const additive = (map: THREE.Texture, color: number, opacity = 1) =>
  new THREE.SpriteMaterial({ map, color, opacity, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending });

interface Body {
  star: Star;
  ball: THREE.Mesh<THREE.SphereGeometry, THREE.ShaderMaterial>;
  corona: THREE.Sprite;
  spark: THREE.Sprite; // the bright point seen from far away; fades as the sphere grows on screen
  stalk?: THREE.Line;
  foot?: THREE.Mesh;
  label: HTMLButtonElement;
  pos: THREE.Vector3;
  base: number;
  r: number; // radius drawn this frame
  grow: number; // 0 on the map, 1 in the close-up
  lead?: HTMLElement; // leader line, when the label had to slide off its star
  w?: number; // label width, measured once
}

export interface SceneOpts {
  /** A star (or the Sun) was clicked or tapped: its id, or null for empty space. */
  onPick(id: string | null): void;
  reduced: boolean;
}

export class Neighbourhood {
  readonly canvas: HTMLCanvasElement;
  private renderer: THREE.WebGLRenderer;
  private scene = new THREE.Scene();
  private camera = new THREE.PerspectiveCamera(FOV, 1, 0.01, 600);
  private controls: OrbitControls;
  private bodies: Body[] = [];
  private labels: HTMLElement;
  private farRing: THREE.LineLoop;
  private farLabel: HTMLElement;
  private link: THREE.Line<THREE.BufferGeometry, THREE.LineDashedMaterial>;
  private linkLabel: HTMLElement;
  private linked: string | null = null;
  private trace: THREE.Line<THREE.BufferGeometry, THREE.LineBasicMaterial>;
  private todayDot: THREE.Sprite;
  private todayLabel: HTMLElement;
  private year = 2026;
  private focusId: string | null = null;
  private fly: { body: Body | null; dir: THREE.Vector3; from: THREE.Vector3; camFrom: THREE.Vector3; t0: number } | null = null;
  private cmp = new THREE.Group();
  private cmpLabel: HTMLElement;
  private inset = { right: 0, bottom: 0, top: 0 };
  private shown = { right: 0, bottom: 0, top: 0 };
  private glow = 0;
  private raf = 0;
  private visible = true;
  private ro: ResizeObserver;
  private io: IntersectionObserver;
  private w = 1;
  private h = 1;
  private tex = glowTexture();
  private coronaTex = coronaTexture();
  private sphere = new THREE.SphereGeometry(1, 48, 32);

  constructor(private host: HTMLElement, private opts: SceneOpts) {
    this.renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance' });
    this.renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
    this.renderer.setClearColor(0x030407);
    this.canvas = this.renderer.domElement;
    this.canvas.className = 's3-canvas';
    this.canvas.setAttribute('aria-hidden', 'true');
    this.labels = document.createElement('div');
    this.labels.className = 's3-labels';
    host.append(this.canvas, this.labels);
    // label widths are measured once; measure again when the web fonts arrive
    void document.fonts?.ready.then(() => this.bodies.forEach((b) => (b.w = 0)));

    this.resize();
    this.camera.position.copy(this.home());
    this.controls = new OrbitControls(this.camera, this.canvas);
    Object.assign(this.controls, { enableDamping: true, dampingFactor: 0.08, minDistance: 0.25, maxDistance: 40, enablePan: false, rotateSpeed: 0.6, zoomSpeed: 0.8 });
    this.controls.autoRotate = !opts.reduced;
    this.controls.autoRotateSpeed = 0.35;
    this.controls.addEventListener('start', () => {
      this.controls.autoRotate = false;
      this.fly = null;
    });

    this.backdrop();
    this.grid();
    for (const s of [SUN, ...STARS]) this.addStar(s);
    this.farRing = this.ring(FAR_RING, 0x8a8f9c, 0.32, true);
    this.farLabel = this.tag('s3-far', 'Outer ring, distance not to scale');
    // the size comparison beside the star in the close-up: a faint disc with an outline
    const circle = new THREE.BufferGeometry().setFromPoints(Array.from({ length: 128 }, (_, i) => new THREE.Vector3(Math.cos((i / 128) * Math.PI * 2), Math.sin((i / 128) * Math.PI * 2), 0)));
    this.cmp.add(
      new THREE.Mesh(new THREE.CircleGeometry(1, 96), new THREE.MeshBasicMaterial({ transparent: true, depthWrite: false })),
      new THREE.LineLoop(circle, new THREE.LineBasicMaterial({ transparent: true, depthWrite: false })),
    );
    this.cmp.visible = false;
    this.scene.add(this.cmp);
    this.cmpLabel = this.tag('s3-cmp', '');

    const lg = new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(), new THREE.Vector3()]);
    this.link = new THREE.Line(lg, new THREE.LineDashedMaterial({ dashSize: 0.08, gapSize: 0.06, transparent: true, opacity: 0.85 }));
    this.link.visible = false;
    this.link.frustumCulled = false;
    this.scene.add(this.link);
    this.linkLabel = this.tag('s3-dist mono', '');

    // the path of the star in focus: additive, so the colour fading to black fades it out
    this.trace = new THREE.Line(new THREE.BufferGeometry(), new THREE.LineBasicMaterial({ vertexColors: true, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending }));
    this.trace.visible = false;
    this.trace.frustumCulled = false;
    this.todayDot = new THREE.Sprite(additive(this.tex, 0xffffff));
    this.todayDot.material.depthTest = false;
    this.todayDot.visible = false;
    this.scene.add(this.trace, this.todayDot);
    this.todayLabel = this.tag('s3-today mono', 'Today');
    this.todayLabel.hidden = true;

    this.setYear(this.year);
    this.pointer();
    this.ro = new ResizeObserver(() => this.resize());
    this.ro.observe(host);
    this.io = new IntersectionObserver(([e]) => {
      this.visible = e.isIntersecting;
      if (this.visible) this.start();
    });
    this.io.observe(host);
    this.start();
  }

  /** A faint field of far stars, so space has depth. */
  private backdrop() {
    const n = 1800, p = new Float32Array(n * 3), c = new Float32Array(n * 3);
    for (let i = 0; i < n; i++) {
      const u = Math.random() * 2 - 1, a = Math.random() * Math.PI * 2, r = 160 + Math.random() * 120, s = Math.sqrt(1 - u * u);
      p.set([r * s * Math.cos(a), r * u, r * s * Math.sin(a)], i * 3);
      const b = 0.25 + Math.random() ** 3 * 0.75, warm = Math.random();
      c.set([b * (0.85 + warm * 0.15), b * 0.9, b * (1 - warm * 0.2)], i * 3);
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(p, 3));
    g.setAttribute('color', new THREE.BufferAttribute(c, 3));
    const m = new THREE.PointsMaterial({ size: 2.2, sizeAttenuation: false, map: this.tex, vertexColors: true, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending });
    this.scene.add(new THREE.Points(g, m));
  }

  private ring(r: number, color: number, opacity: number, dashed = false): THREE.LineLoop {
    const pts = Array.from({ length: 160 }, (_, i) => new THREE.Vector3(Math.cos((i / 160) * Math.PI * 2) * r, 0, Math.sin((i / 160) * Math.PI * 2) * r));
    const g = new THREE.BufferGeometry().setFromPoints(pts);
    const m = dashed
      ? new THREE.LineDashedMaterial({ color, transparent: true, opacity, dashSize: 0.18, gapSize: 0.14, depthWrite: false })
      : new THREE.LineBasicMaterial({ color, transparent: true, opacity, depthWrite: false });
    const l = new THREE.LineLoop(g, m);
    if (dashed) l.computeLineDistances();
    this.scene.add(l);
    return l;
  }

  /** Distance rings in the plane of the Earth's equator, 1 to 5 parsecs. */
  private grid() {
    for (let r = 1; r <= NEAR_LIMIT; r++) {
      this.ring(r, 0x9aa3b5, r === NEAR_LIMIT ? 0.22 : 0.1);
      const t = this.tag('s3-ring mono', r === NEAR_LIMIT ? `${r} pc / ${Math.round(r * 3.26)} light-years` : `${r} pc`);
      t.dataset.ring = String(r);
    }
  }

  private addStar(s: Star) {
    const sun = s.kind === 'sun', target = !!s.slug, cold = s.temp < 500, base = RADIUS[s.kind];
    const mat = new THREE.ShaderMaterial({
      uniforms: { uColor: { value: new THREE.Color(s.color) }, uTime: { value: 0 }, uBands: { value: s.kind === 'brown dwarf' ? 1 : 0 }, uBright: { value: cold ? 0.6 : 1 } },
      vertexShader: STAR_VERT, fragmentShader: STAR_FRAG,
    });
    const ball = new THREE.Mesh(this.sphere, mat);
    // the sphere hides the middle of the corona, so it shows as a glow around the edge
    const corona = new THREE.Sprite(additive(this.coronaTex, s.color, cold ? 0.22 : sun || target ? 0.5 : 0.32));
    const spark = new THREE.Sprite(additive(this.tex, s.color));
    spark.material.depthTest = false;
    this.scene.add(ball, corona, spark);
    const b: Body = {
      star: s, ball, corona, spark, base, r: base, grow: 0, pos: new THREE.Vector3(),
      label: this.button(s.id, s.name, `s3-lab${sun ? ' s3-lab-sun' : target ? '' : ' s3-lab-ctx'}${s.far ? ' s3-lab-far' : ''}`),
    };
    if (s.far) {
      b.label.append(Object.assign(document.createElement('small'), { textContent: `${Math.round(s.dist)} pc` }));
    } else if (!sun) {
      // a stalk down to the plane, so depth reads at a glance; shown for the star in focus
      b.stalk = new THREE.Line(new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(), new THREE.Vector3()]), new THREE.LineBasicMaterial({ color: 0x9aa3b5, transparent: true, opacity: 0.22, depthWrite: false }));
      b.foot = new THREE.Mesh(new THREE.CircleGeometry(0.035, 20), new THREE.MeshBasicMaterial({ color: 0x9aa3b5, transparent: true, opacity: 0.45, depthWrite: false, side: THREE.DoubleSide }));
      b.foot.rotation.x = -Math.PI / 2;
      b.stalk.frustumCulled = false; // moved in place, so its cached bounds go stale
      b.stalk.visible = b.foot.visible = false;
      this.scene.add(b.stalk, b.foot);
    }
    this.bodies.push(b);
  }

  private tag(cls: string, text: string): HTMLElement {
    const t = document.createElement('span');
    t.className = 's3-tag ' + cls;
    t.textContent = text;
    this.labels.append(t);
    return t;
  }

  private button(id: string, text: string, cls: string): HTMLButtonElement {
    const b = document.createElement('button');
    b.type = 'button';
    b.className = cls;
    b.dataset.id = id;
    b.append(Object.assign(document.createElement('span'), { textContent: text }));
    b.addEventListener('click', (e) => {
      e.stopPropagation();
      this.opts.onPick(id);
    });
    this.labels.append(b);
    return b;
  }

  /** A tap that did not drag picks the star nearest the pointer on screen. */
  private pointer() {
    let down: [number, number] | null = null;
    this.canvas.addEventListener('pointerdown', (e) => (down = [e.clientX, e.clientY]));
    this.canvas.addEventListener('pointerup', (e) => {
      if (!down || Math.hypot(e.clientX - down[0], e.clientY - down[1]) > 6) return;
      down = null;
      this.opts.onPick(this.nearest(e.clientX, e.clientY, 34));
    });
    this.canvas.addEventListener('pointermove', (e) => {
      if (e.buttons) return;
      this.canvas.style.cursor = this.nearest(e.clientX, e.clientY, 34) ? 'pointer' : 'grab';
    });
  }

  private nearest(cx: number, cy: number, maxPx: number): string | null {
    const r = this.canvas.getBoundingClientRect();
    let best: string | null = null, bd = Infinity;
    for (const b of this.bodies) {
      const p = this.screen(b.pos);
      if (!p) continue;
      // a big sphere in the close-up counts all over, but the nearest centre wins (Barnard's Star beside the Sun)
      const d = Math.hypot(p[0] - (cx - r.left), p[1] - (cy - r.top));
      if ((d < maxPx || d < b.r / this.pxAt(b.pos)) && d < bd) [bd, best] = [d, b.star.id];
    }
    return best;
  }

  /** Screen position (CSS px) of a scene point, or null when it is behind the camera. */
  private screen(v: THREE.Vector3): [number, number] | null {
    const p = v.clone().project(this.camera);
    if (p.z > 1 || p.z < -1) return null;
    return [((p.x + 1) / 2) * this.w, ((1 - p.y) / 2) * this.h];
  }

  /** World units per screen pixel at a point. */
  private pxAt(v: THREE.Vector3): number {
    return (this.camera.position.distanceTo(v) * 2 * Math.tan(((FOV / 2) * Math.PI) / 180)) / this.h;
  }

  /** Move every star to where it is in this year. */
  setYear(year: number) {
    this.year = year;
    for (const b of this.bodies) {
      if (b.star.kind === 'sun') continue;
      const p = scenePos(b.star, year), prev = b.pos.clone();
      b.pos.set(...p);
      b.ball.position.copy(b.pos);
      b.corona.position.copy(b.pos);
      b.spark.position.copy(b.pos);
      if (b.stalk && b.foot) {
        b.stalk.geometry.setFromPoints([b.pos, new THREE.Vector3(p[0], 0, p[2])]);
        b.foot.position.set(p[0], 0, p[2]);
      }
      // keep the camera riding along with the star in focus
      if (b.star.id === this.focusId && !this.fly) {
        const d = b.pos.clone().sub(prev);
        this.controls.target.add(d);
        this.camera.position.add(d);
      }
    }
    this.updateLink();
  }

  /** Draw the Sun-to-star distance for one star (null hides it). */
  setLink(id: string | null) {
    this.linked = id;
    this.updateLink();
  }

  private updateLink() {
    const b = this.bodies.find((x) => x.star.id === this.linked && !x.star.far && x.star.kind !== 'sun');
    this.link.visible = !!b;
    this.linkLabel.hidden = !b;
    if (!b) return;
    this.link.material.color.set(b.star.color);
    this.link.geometry.setFromPoints([new THREE.Vector3(), b.pos]);
    this.link.computeLineDistances();
    const pc = b.pos.length();
    this.linkLabel.textContent = `${pc.toFixed(2)} pc`;
  }

  /** Light up a star, 0 to 1 (the closest-approach moment). */
  setGlow(k: number) {
    this.glow = k;
  }

  /** Fly to a star's close-up (or back to the overview with null). */
  focus(id: string | null) {
    this.focusId = id;
    this.controls.autoRotate = false;
    for (const b of this.bodies) b.label.classList.toggle('on', b.star.id === id);
    const body = (id && this.bodies.find((x) => x.star.id === id)) || null;
    this.drawTrace(body);
    const dir = this.camera.position.clone().sub(this.controls.target).normalize();
    if (body) {
      const c = compare(body.star), tiny = 1 / c.ratio < 0.04;
      const [disc, line] = this.cmp.children as [THREE.Mesh<THREE.BufferGeometry, THREE.MeshBasicMaterial>, THREE.LineLoop<THREE.BufferGeometry, THREE.LineBasicMaterial>];
      disc.material.color.set(CMP_COLOR[c.body]);
      line.material.color.set(CMP_COLOR[c.body]);
      this.cmpLabel.textContent = tiny ? `The ${c.body} is smaller than this dot` : `${c.body === 'Sun' ? 'The Sun' : c.body}, to scale`;
    }
    this.fly = { body, dir, from: this.controls.target.clone(), camFrom: this.camera.position.clone(), t0: this.opts.reduced ? -1e9 : performance.now() };
  }

  /** Where the camera sits for a body's close-up: farther on a narrow screen, so the comparison fits. */
  private closeDist(b: Body): number {
    return (b.base * CLOSE) / Math.min(1, (this.w / this.h) * 0.75);
  }

  /** Zoom by a factor (below 1 is closer), for the + and - buttons. */
  zoom(f: number) {
    this.fly = null;
    this.controls.autoRotate = false;
    const d = this.camera.position.clone().sub(this.controls.target);
    const len = THREE.MathUtils.clamp(d.length() * f, this.controls.minDistance, this.controls.maxDistance);
    this.camera.position.copy(this.controls.target).addScaledVector(d.normalize(), len);
  }

  /** Room taken by the panel and the overlays (px), so the map sits in the open part of the view. */
  setInset(right: number, bottom: number, top = 0) {
    this.inset = { right, bottom, top };
    if (this.opts.reduced) this.shown = { ...this.inset };
    // the overview fits itself to the new room; a close-up keeps its distance
    if (!this.focusId && !this.fly) this.camera.position.setLength(this.home().length());
  }

  /** Far enough back that the far ring fits between the insets, also on a tall phone screen. */
  private home(): THREE.Vector3 {
    const band = Math.max(0.4, (this.h - this.inset.top - this.inset.bottom) / this.h);
    const half = Math.tan(((FOV / 2) * Math.PI) / 180) * Math.min(band, this.w / this.h);
    return HOME_DIR.clone().multiplyScalar(Math.max(15, (FAR_RING * 1.15) / half));
  }

  private resize() {
    const r = this.host.getBoundingClientRect();
    this.w = Math.max(1, r.width);
    this.h = Math.max(1, r.height);
    this.renderer.setSize(this.w, this.h, false);
    this.camera.aspect = this.w / this.h;
    this.camera.updateProjectionMatrix();
  }

  private start() {
    if (!this.raf) this.raf = requestAnimationFrame(this.frame);
  }

  private frame = (now: number) => {
    this.raf = 0;
    if (!this.visible) return;
    const t = now / 1000;
    if (this.fly) {
      const { body, dir, from, camFrom, t0 } = this.fly;
      const f = Math.min(1, (now - t0) / 1200), e = f < 0.5 ? 4 * f ** 3 : 1 - (-2 * f + 2) ** 3 / 2;
      // the star may be moving while we fly to it, so aim at where it is now
      const to = body ? body.pos : new THREE.Vector3();
      const camTo = body ? to.clone().addScaledVector(dir, this.closeDist(body)) : this.home();
      this.controls.target.lerpVectors(from, to, e);
      this.camera.position.lerpVectors(camFrom, camTo, e);
      if (f >= 1) this.fly = null;
    }
    // slide the view centre away from the panel
    this.shown.right += (this.inset.right - this.shown.right) * 0.12;
    this.shown.bottom += (this.inset.bottom - this.shown.bottom) * 0.12;
    this.shown.top += (this.inset.top - this.shown.top) * 0.12;
    const dy = (this.shown.bottom - this.shown.top) / 2;
    if (this.shown.right > 0.5 || Math.abs(dy) > 0.25) this.camera.setViewOffset(this.w, this.h, this.shown.right / 2, dy, this.w, this.h);
    else this.camera.clearViewOffset();
    this.controls.update();
    this.camera.updateMatrixWorld();

    const at: ([number, number] | null)[] = [];
    const cam = this.camera.position, pxk = (2 * Math.tan(((FOV / 2) * Math.PI) / 180)) / this.h, calm = this.opts.reduced;
    for (const b of this.bodies) {
      const on = b.star.id === this.focusId, lit = b.star.id === 'barnard' ? this.glow : 0;
      let k = 1, bright = b.star.temp < 500 ? 0.6 : 1;
      if (!calm) {
        if (b.star.kind === 'pulsating red giant') k = 1 + 0.14 * Math.sin(t * 1.6); // R Dra swells and fades
        else if (b.star.kind === 'young variable star') bright = 1 + 0.25 * Math.sin(t * 3.1) * Math.sin(t * 1.3 + 1); // RW Aur flickers
      }
      b.grow += ((on ? 1 : 0) - b.grow) * (calm ? 1 : 0.1);
      // spheres keep a steady size on screen when the camera comes close; the one in focus stays full size
      const dist = cam.distanceTo(b.pos), near = Math.min(1, Math.max(0.28, dist / 8));
      b.r = b.base * k * (near + (1 - near) * b.grow) * (1 + lit * 0.5 * (1 - b.grow));
      b.ball.scale.setScalar(b.r);
      b.ball.rotation.y = calm ? 0 : t * 0.05;
      b.ball.material.uniforms.uTime.value = calm ? 0 : t;
      b.ball.material.uniforms.uBright.value = bright * (1 + lit * 0.4);
      b.corona.scale.setScalar(b.r * 8 * (1 + lit * (0.6 + (calm ? 0 : 0.15 * Math.sin(t * 5)))));
      const rpx = b.r / (dist * pxk);
      b.spark.scale.setScalar(b.r * 6);
      b.spark.material.opacity = Math.max(0, Math.min(1, 1 - (rpx - 5) / 12));
      if (b.stalk && b.foot) b.stalk.visible = b.foot.visible = on;
      // in the close-up the card names the star, so its label steps aside
      at.push(b.grow > 0.5 ? null : this.screen(b.pos));
    }
    this.compare();
    this.placeToday(pxk);
    this.layoutLabels(at);
    // the far ring always faces the camera, like the outline of a sphere
    this.farRing.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), this.camera.position.clone().normalize());
    const up = new THREE.Vector3(0, 1, 0).applyQuaternion(this.camera.quaternion).multiplyScalar(FAR_RING * 1.02);
    this.place(this.farLabel, up);
    if (this.link.visible) {
      const b = this.bodies.find((x) => x.star.id === this.linked)!;
      this.place(this.linkLabel, b.pos.clone().multiplyScalar(0.5));
    }
    this.renderer.render(this.scene, this.camera);
    if (!document.hidden) this.raf = requestAnimationFrame(this.frame);
    else document.addEventListener('visibilitychange', () => this.start(), { once: true });
  };

  /**
   * Labels never sit on top of each other or on another star: the focus, the Sun and the challenge
   * stars win; others move to the left side, or a row up or down with a short leader line, or hide.
   * The ring distance tags take whatever room is left.
   */
  private layoutLabels(at: ([number, number] | null)[]) {
    const rank = (b: Body) => (b.star.id === this.focusId ? 4 : b.star.kind === 'sun' ? 3 : b.star.slug ? 2 : b.star.far ? 0 : 1);
    const idx: number[] = [], boxes: LabelBox[] = [], dots: [number, number][] = [];
    at.forEach((p, i) => {
      if (!p) return;
      const b = this.bodies[i];
      if (!b.w) b.w = b.label.offsetWidth || 0;
      idx.push(i);
      dots.push(p);
      boxes.push({ x: p[0], y: p[1], w: b.w || 80, h: 22, rank: rank(b) });
    });
    const rings = [...this.labels.querySelectorAll<HTMLElement>('[data-ring]')].map((el) => {
      const r = +el.dataset.ring!, p = this.screen(new THREE.Vector3(r * 0.7071, 0, r * 0.7071));
      el.dataset.w ||= String(el.offsetWidth || '');
      if (p) boxes.push({ x: p[0] - PAD + 6, y: p[1], w: +(el.dataset.w || 40), h: 14, rank: -1, fixed: true });
      return { el, p };
    });
    const spots = declutter(boxes, dots);
    let k = idx.length;
    for (const { el, p } of rings) {
      const ok = !!p && spots[k++] !== null;
      el.style.visibility = ok ? '' : 'hidden';
      if (ok) el.style.transform = `translate3d(${p![0].toFixed(1)}px, ${p![1].toFixed(1)}px, 0)`;
    }
    const shown = new Set<number>();
    idx.forEach((i, k) => {
      const b = this.bodies[i], p = at[i]!, s = spots[k];
      if (!s) return;
      shown.add(i);
      b.label.hidden = false;
      // never past the top or bottom edge of the map, where a far star can sit
      const y = Math.min(this.h - 16, Math.max(16, p[1] + s.dy));
      b.label.style.transform = `translate3d(${(p[0] + s.dx).toFixed(1)}px, ${y.toFixed(1)}px, 0)`;
      if (!s.lead) {
        if (b.lead) b.lead.hidden = true;
        return;
      }
      if (!b.lead) {
        b.lead = document.createElement('i');
        b.lead.className = 's3-leader';
        this.labels.prepend(b.lead);
      }
      // from just off the star to the near edge of the label
      const left = s.dx < 0, x1 = p[0] + (left ? s.dx + b.w! : s.dx), y1 = y, ang = Math.atan2(y1 - p[1], x1 - p[0]);
      const x0 = p[0] + Math.cos(ang) * 4, y0 = p[1] + Math.sin(ang) * 4;
      b.lead.hidden = false;
      b.lead.style.width = `${Math.hypot(x1 - x0, y1 - y0).toFixed(1)}px`;
      b.lead.style.transform = `translate3d(${x0.toFixed(1)}px, ${y0.toFixed(1)}px, 0) rotate(${ang.toFixed(3)}rad)`;
    });
    this.bodies.forEach((b, i) => {
      if (shown.has(i)) return;
      b.label.hidden = true;
      if (b.lead) b.lead.hidden = true;
    });
  }

  /** One thin line through the star's positions over the whole time slider, fading at both ends, in its own colour. */
  private drawTrace(b: Body | null) {
    const show = !!b && !b.star.far && b.star.kind !== 'sun';
    this.trace.visible = this.todayDot.visible = show;
    this.todayLabel.hidden = true;
    if (!show) return;
    const col = new THREE.Color(b.star.color).lerp(new THREE.Color(0xffffff), 0.15), steps = 120, pts: number[] = [], cols: number[] = [];
    for (let i = 0; i <= steps; i++) {
      const f = i / steps, k = 0.85 * Math.min(1, f / FADE, (1 - f) / FADE) ** 1.6;
      pts.push(...scenePos(b.star, PATH[0] + f * (PATH[1] - PATH[0])));
      cols.push(col.r * k, col.g * k, col.b * k);
    }
    this.trace.geometry.dispose();
    this.trace.geometry = new THREE.BufferGeometry();
    this.trace.geometry.setAttribute('position', new THREE.Float32BufferAttribute(pts, 3));
    this.trace.geometry.setAttribute('color', new THREE.Float32BufferAttribute(cols, 3));
    this.todayDot.material.color.copy(col);
    this.todayDot.position.set(...scenePos(b.star, TODAY));
  }

  /** The mark on the trace where the star is today: a small dot of steady size, named once the star has moved off it. */
  private placeToday(pxk: number) {
    if (!this.todayDot.visible) return;
    const b = this.bodies.find((x) => x.star.id === this.focusId), p = this.todayDot.position;
    this.todayDot.scale.setScalar(9 * this.camera.position.distanceTo(p) * pxk);
    const s = this.screen(p), at = b && this.screen(b.pos);
    const apart = !!s && !!at && Math.hypot(s[0] - at[0], s[1] - at[1]) > 26 + (b ? b.r / this.pxAt(b.pos) : 0);
    this.todayLabel.hidden = !apart;
    if (apart) this.place(this.todayLabel, p);
  }

  /** The Sun or Jupiter beside the star in focus, to the same scale. */
  private compare() {
    const b = this.bodies.find((x) => x.star.id === this.focusId);
    this.cmp.visible = !!b && b.grow > 0.03;
    this.cmpLabel.hidden = !b || b.grow < 0.6;
    if (!b || !this.cmp.visible) return;
    const q = this.camera.quaternion, right = new THREE.Vector3(1, 0, 0).applyQuaternion(q), up = new THREE.Vector3(0, 1, 0).applyQuaternion(q);
    const rel = Math.max(0.04, 1 / compare(b.star).ratio), r = b.r * rel;
    this.cmp.position.copy(b.pos).addScaledVector(right, b.r * 1.3 + r);
    this.cmp.quaternion.copy(q);
    this.cmp.scale.setScalar(r);
    const [disc, line] = this.cmp.children as [THREE.Mesh<THREE.BufferGeometry, THREE.MeshBasicMaterial>, THREE.LineLoop<THREE.BufferGeometry, THREE.LineBasicMaterial>];
    disc.material.opacity = 0.1 * b.grow;
    line.material.opacity = 0.75 * b.grow;
    // the label sits on top of a small circle; on a bigger one, on the shoulder nearest the star, so it stays in view
    const ang = rel > 0.9 ? Math.PI - Math.asin(0.9 / rel) : Math.PI / 2;
    this.place(this.cmpLabel, this.cmp.position.clone().addScaledVector(right, Math.cos(ang) * r).addScaledVector(up, Math.sin(ang) * r));
  }

  private place(el: HTMLElement, v: THREE.Vector3) {
    const p = this.screen(v);
    el.style.visibility = p ? '' : 'hidden';
    if (p) el.style.transform = `translate3d(${p[0].toFixed(1)}px, ${p[1].toFixed(1)}px, 0)`;
  }

  dispose() {
    cancelAnimationFrame(this.raf);
    this.raf = 0;
    this.visible = false;
    this.ro.disconnect();
    this.io.disconnect();
    this.controls.dispose();
    this.scene.traverse((o) => {
      const m = o as THREE.Mesh;
      m.geometry?.dispose();
      const mat = m.material as THREE.Material | THREE.Material[] | undefined;
      (Array.isArray(mat) ? mat : mat ? [mat] : []).forEach((x) => x.dispose());
    });
    this.tex.dispose();
    this.coronaTex.dispose();
    this.renderer.dispose();
    this.renderer.forceContextLoss();
    this.canvas.remove();
    this.labels.remove();
  }
}
