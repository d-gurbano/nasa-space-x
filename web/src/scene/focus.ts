// The selected object's story in 3D: a glowing orbit that is brightest near the object (built
// around the dot from the same propagation as the map lines, so it runs through the body), an
// artist's impression of the body for the close-up (comets get a coma, an ion tail and a dust
// tail), lit hard by the real Sun with a faint fill and a rim light, one
// SPHEREx sightline per photo day that lights up as the clock passes it, and a marker where
// the object was at its first known observation.
import * as THREE from 'three';
import { Line2 } from 'three/examples/jsm/lines/Line2.js';
import { LineGeometry } from 'three/examples/jsm/lines/LineGeometry.js';
import { LineMaterial } from 'three/examples/jsm/lines/LineMaterial.js';
import type { Vec3 } from '../lib/kepler';
import { mjdFromIso, plainDate } from '../lib/time';
import type { ObjectPage } from '../lib/types';
import { eclToThree } from './asteroids';
import { reducedMotion, store } from '../state';
import type { Scene } from './Scene';
import { rockGeometry, rockMaterial, seeded, type RockLook } from './rock';
import { focusPath, type OrbitPath } from './orbits';

const GOLD = new THREE.Color(0xf2b544);

function glowTexture(stops: [number, string][]): THREE.CanvasTexture {
  const c = document.createElement('canvas');
  c.width = c.height = 128;
  const x = c.getContext('2d')!;
  const grd = x.createRadialGradient(64, 64, 0, 64, 64, 64);
  stops.forEach(([at, s]) => grd.addColorStop(at, s));
  x.fillStyle = grd;
  x.fillRect(0, 0, 128, 128);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}

interface TailLook {
  n: number;
  color: [number, number, number];
  width: [number, number]; // at the nucleus, added along the tail (fractions of the length)
  size: [number, number]; // particle size in px at the nucleus and at the end
  speed: number;
  alpha: number;
}
const ION: TailLook = { n: 1400, color: [0.45, 0.72, 1.0], width: [0.012, 0.07], size: [7, 2.5], speed: 1, alpha: 0.32 };
const DUST: TailLook = { n: 1100, color: [1.0, 0.86, 0.68], width: [0.03, 0.2], size: [9, 4], speed: 0.45, alpha: 0.2 };

/** A comet tail: particles streaming away from the nucleus, widening, bending and fading along the way. */
function cometTail(px: number, look: TailLook): THREE.Points {
  const n = reducedMotion ? Math.round(look.n * 0.45) : look.n;
  const seed = new Float32Array(n * 4);
  for (let k = 0; k < n; k++) seed.set([Math.random(), Math.random() * Math.PI * 2, Math.sqrt(Math.random()), (0.05 + Math.random() * 0.08) * look.speed], k * 4);
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(n * 3), 3));
  g.setAttribute('aSeed', new THREE.BufferAttribute(seed, 4));
  const m = new THREE.ShaderMaterial({
    uniforms: {
      uTime: { value: 0 }, uDir: { value: new THREE.Vector3(1, 0, 0) }, uBend: { value: new THREE.Vector3() }, uLen: { value: 1 }, uPx: { value: px }, uAlpha: { value: 1 },
      uCol: { value: new THREE.Vector3(...look.color) }, uWidth: { value: new THREE.Vector2(...look.width) }, uSize: { value: new THREE.Vector2(...look.size) },
    },
    vertexShader: /* glsl */ `
      #include <common>
      #include <logdepthbuf_pars_vertex>
      attribute vec4 aSeed; // start, angle, radius, speed
      uniform float uTime, uLen, uPx;
      uniform vec3 uDir, uBend;
      uniform vec2 uWidth, uSize;
      varying float vA;
      void main() {
        float t = fract(aSeed.x + uTime * aSeed.w);
        vec3 side = normalize(abs(uDir.y) < 0.9 ? cross(uDir, vec3(0.0, 1.0, 0.0)) : cross(uDir, vec3(1.0, 0.0, 0.0)));
        vec3 up = cross(uDir, side);
        float w = uLen * (uWidth.x + uWidth.y * t) * aSeed.z;
        vec3 p = uDir * (t * uLen) + uBend * (t * t * uLen) + (side * cos(aSeed.y) + up * sin(aSeed.y)) * w;
        vec4 mv = modelViewMatrix * vec4(p, 1.0);
        gl_Position = projectionMatrix * mv;
        #include <logdepthbuf_vertex>
        gl_PointSize = mix(uSize.x, uSize.y, t) * uPx;
        vA = pow(1.0 - t, 1.6) * smoothstep(0.0, 0.04, t);
      }`,
    fragmentShader: /* glsl */ `
      #include <common>
      #include <logdepthbuf_pars_fragment>
      uniform float uAlpha;
      uniform vec3 uCol;
      varying float vA;
      void main() {
        #include <logdepthbuf_fragment>
        vec2 p = (gl_PointCoord - 0.5) * 2.0;
        float s = exp(-3.0 * dot(p, p)) * vA * uAlpha;
        gl_FragColor = vec4(uCol * s, 1.0);
      }`,
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
  });
  m.uniforms.uAlpha.value = look.alpha;
  m.userData.alpha = look.alpha;
  const pts = new THREE.Points(g, m);
  pts.frustumCulled = false;
  pts.renderOrder = 4;
  return pts;
}

/** Round soft markers with per-vertex colour (sightline ends, the first-observation ring). */
function markerMaterial(px: number, ring: boolean, size: number): THREE.ShaderMaterial {
  return new THREE.ShaderMaterial({
    uniforms: { uPx: { value: px }, uScale: { value: 1 } },
    vertexShader: /* glsl */ `
      #include <common>
      #include <logdepthbuf_pars_vertex>
      attribute vec3 color;
      uniform float uPx;
      uniform float uScale;
      varying vec3 vC;
      void main() {
        vec4 mv = modelViewMatrix * vec4(position, 1.0);
        gl_Position = projectionMatrix * mv;
        #include <logdepthbuf_vertex>
        gl_PointSize = ${size.toFixed(1)} * uPx * uScale;
        vC = color;
      }`,
    fragmentShader: /* glsl */ `
      #include <common>
      #include <logdepthbuf_pars_fragment>
      varying vec3 vC;
      void main() {
        #include <logdepthbuf_fragment>
        float r = length(gl_PointCoord - 0.5) * 2.0;
        float s = ${ring ? 'smoothstep(0.62, 0.74, r) * (1.0 - smoothstep(0.82, 0.96, r))' : '(1.0 - smoothstep(0.35, 1.0, r)) * (0.6 + 0.4 * exp(-6.0 * r * r))'};
        if (s < 0.01) discard;
        gl_FragColor = vec4(vC * s, 1.0);
      }`,
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
  });
}

interface Sight {
  mjd: number;
}

export class ObjectFocus {
  private group = new THREE.Group();
  private slug: string | null = null;
  /** Visual radius of the body in AU (hugely enlarged: the real body is far too small to see). */
  radius = 2e-4;
  // orbit
  private orbitGeo: LineGeometry | null = null;
  private orbit = new THREE.Group(); // sits at the dot; the line's vertices are offsets from it
  private orbitMjd = NaN;
  private orbitSrc: unknown = null;
  private orbitMats: LineMaterial[] = [];
  // body
  private body: THREE.Mesh | null = null;
  private spinAxis = new THREE.Vector3(0.3, 1, 0.2).normalize();
  private coma: THREE.Sprite | null = null;
  private tails: THREE.Points[] = [];
  // a hard Sun (at the origin, so the terminator is the real one), a faint fill, and a cool
  // rim light from behind the body as the camera sees it
  private light = new THREE.PointLight(0xfff4e6, 7, 0, 0);
  private ambient = new THREE.AmbientLight(0x8fa2c8, 0.035);
  private rim = new THREE.DirectionalLight(0xa9c4ff, 0);
  // sightlines and markers
  private sights: Sight[] = [];
  private sightLines: THREE.LineSegments | null = null;
  private sightEnds: THREE.Points | null = null;
  private fko: THREE.Points | null = null;
  private ring: THREE.Points | null = null; // marks the object from far out
  private clock = 0;
  private v = new THREE.Vector3();
  private w = new THREE.Vector3();
  private u = new THREE.Vector3();
  // in the close-up the orbit fades out around the body instead of running through it
  private gap = { uFocus: { value: new THREE.Vector3() }, uGap: { value: 0 } };
  private note = Object.assign(document.createElement('p'), {
    className: 'focus-note',
    innerHTML: '<strong>Artist impression, shape unknown</strong><small>Not to scale</small>',
  });

  constructor(private scene: Scene) {
    this.scene.scene.add(this.group, this.light, this.ambient, this.rim, this.rim.target);
    scene.addHook((dt) => this.tick(dt));
  }

  get active() {
    return this.slug !== null;
  }

  show(slug: string, p: ObjectPage, comet: boolean, radius: number) {
    this.hide();
    const dot = this.scene.rewindDot(slug);
    if (!dot) return;
    this.slug = slug;
    this.radius = radius;
    this.addOrbit(slug);
    this.addBody(slug, comet ? 'comet' : rockLook(p));
    this.addSightlines(slug, p);
    this.addFirstKnown(slug, p);
    const rg = new THREE.BufferGeometry();
    rg.setAttribute('position', new THREE.BufferAttribute(new Float32Array(3), 3));
    rg.setAttribute('color', new THREE.BufferAttribute(Float32Array.of(GOLD.r, GOLD.g, GOLD.b), 3));
    this.ring = new THREE.Points(rg, markerMaterial(this.scene.pixelRatio, true, 26));
    this.ring.frustumCulled = false;
    this.ring.renderOrder = 5;
    this.group.add(this.ring);
    this.note.hidden = true;
    document.getElementById('ui')?.append(this.note);
  }

  hide() {
    this.slug = null;
    for (const c of [...this.group.children]) {
      this.group.remove(c);
      const o = c as THREE.Mesh;
      o.geometry?.dispose();
      const m = o.material as (THREE.Material & { map?: THREE.Texture | null }) | undefined;
      m?.map?.dispose();
      m?.dispose();
    }
    for (const c of [...this.orbit.children] as Line2[]) {
      this.orbit.remove(c);
      c.geometry.dispose();
      c.material.dispose();
    }
    this.orbitGeo = null;
    this.orbitMats = [];
    this.orbitMjd = NaN;
    this.orbitSrc = null;
    this.body = this.coma = null;
    this.sightLines = this.sightEnds = this.fko = this.ring = null;
    this.tails = [];
    this.rim.intensity = 0;
    this.note.remove();
    this.scene.labels.remove('focus-fko');
  }

  // ---------- glowing orbit ----------
  private addOrbit(slug: string) {
    const dot = this.scene.rewindDot(slug)!;
    const path = focusPath(dot, store.mjd);
    const n = path.u.length;
    const geo = new LineGeometry();
    geo.setPositions(new Float32Array(n * 3));
    geo.setColors(new Float32Array(n * 3)); // painted below
    this.orbitGeo = geo;
    this.paintOrbit(path.u);
    this.setOrbit(path);
    this.orbitMjd = store.mjd;
    this.orbitSrc = dot.el;
    this.orbit.clear();
    this.group.add(this.orbit);
    // a thin bright core and a wide faint glow
    for (const [width, opacity] of [[1.6, 1], [7, 0.22]] as const) {
      const m = new LineMaterial({ vertexColors: true, linewidth: width, transparent: true, opacity, depthWrite: false, blending: THREE.AdditiveBlending });
      m.userData.width = width;
      m.onBeforeCompile = (sh) => {
        Object.assign(sh.uniforms, this.gap);
        sh.vertexShader = sh.vertexShader
          .replace('#include <logdepthbuf_pars_vertex>', '#include <logdepthbuf_pars_vertex>\nvarying vec3 vGapP;')
          .replace('vec4 end = modelViewMatrix * vec4( instanceEnd, 1.0 );', 'vec4 end = modelViewMatrix * vec4( instanceEnd, 1.0 );\nvGapP = ( position.y < 0.5 ) ? instanceStart : instanceEnd;');
        sh.fragmentShader = sh.fragmentShader
          .replace('#include <logdepthbuf_pars_fragment>', '#include <logdepthbuf_pars_fragment>\nvarying vec3 vGapP;\nuniform vec3 uFocus;\nuniform float uGap;')
          .replace('gl_FragColor = vec4( diffuseColor.rgb, alpha );', 'alpha *= smoothstep( uGap, uGap * 2.5, distance( vGapP, uFocus ) );\ngl_FragColor = vec4( diffuseColor.rgb, alpha );');
      };
      m.customProgramCacheKey = () => 'orbit-gap';
      const line = new Line2(geo, m);
      line.frustumCulled = false;
      line.renderOrder = 1;
      this.orbitMats.push(m);
      this.orbit.add(line);
    }
  }

  /** Move the line to a fresh path around the dot: vertices in place, the group at the dot (in doubles). */
  private setOrbit(path: OrbitPath) {
    const buf = (this.orbitGeo!.attributes.instanceStart as THREE.InterleavedBufferAttribute).data;
    const arr = buf.array as Float32Array, r = path.rel;
    // segments [start xyz, end xyz]; ecliptic (x, y, z) -> three (x, z, -y)
    for (let k = 0; k < path.u.length - 1; k++) {
      for (const [j, i] of [[0, k], [3, k + 1]] as const) {
        arr[k * 6 + j] = r[i * 3];
        arr[k * 6 + j + 1] = r[i * 3 + 2];
        arr[k * 6 + j + 2] = -r[i * 3 + 1];
      }
    }
    buf.needsUpdate = true;
    eclToThree(path.origin, this.orbit.position);
    this.orbit.updateMatrixWorld();
  }

  /** Brightness along the orbit: strongest at the object, a longer fade behind it than ahead. */
  private paintOrbit(u: Float32Array) {
    const buf = (this.orbitGeo!.attributes.instanceColorStart as THREE.InterleavedBufferAttribute).data;
    const arr = buf.array as Float32Array;
    // u runs half a turn each way, so u / 2 is the fraction of the orbit
    const b = (i: number) => {
      const d = u[i] / 2, s = d < 0 ? 0.16 : 0.05;
      return 0.16 + 0.84 * Math.exp(-(d * d) / (s * s));
    };
    for (let k = 0; k < u.length - 1; k++) {
      for (const [j, i] of [[0, k], [3, k + 1]] as const) {
        const t = b(i);
        const white = Math.max(0, t - 0.75) * 1.6;
        arr[k * 6 + j] = (GOLD.r + (1 - GOLD.r) * white) * t;
        arr[k * 6 + j + 1] = (GOLD.g + (1 - GOLD.g) * white) * t;
        arr[k * 6 + j + 2] = (GOLD.b + (1 - GOLD.b) * white) * t;
      }
    }
    buf.needsUpdate = true;
  }

  // ---------- body ----------
  private addBody(slug: string, look: RockLook) {
    const comet = look === 'comet';
    this.body = new THREE.Mesh(rockGeometry(slug, 56, comet), rockMaterial(look));
    this.body.scale.setScalar(this.radius * (comet ? 0.6 : 1));
    const r = seeded(slug + ':spin');
    this.spinAxis.set(r() - 0.5, 1, r() - 0.5).normalize();
    this.body.rotation.set(r() * 6, r() * 6, r() * 6);
    this.group.add(this.body);
    if (!comet) return;
    this.coma = new THREE.Sprite(new THREE.SpriteMaterial({
      map: glowTexture([[0, 'rgba(225,240,255,0.85)'], [0.1, 'rgba(170,215,255,0.4)'], [0.38, 'rgba(110,170,255,0.11)'], [1, 'rgba(90,150,255,0)']]),
      blending: THREE.AdditiveBlending, depthWrite: false, transparent: true,
    }));
    this.coma.scale.setScalar(this.radius * 9);
    this.coma.renderOrder = 4;
    this.tails = [cometTail(this.scene.pixelRatio, ION), cometTail(this.scene.pixelRatio, DUST)];
    this.group.add(this.coma, ...this.tails);
  }

  // ---------- SPHEREx sightlines ----------
  private addSightlines(slug: string, p: ObjectPage) {
    const frames = p.spherex?.frames ?? [];
    const xyz = p.spherex?.spherex_xyz_au_at_frames ?? [];
    const days = new Map<string, { mjd: number; s: Vec3; n: number }>();
    frames.forEach((f, k) => {
      const at = xyz[k];
      if (!at || !f.iso || !Number.isFinite(f.mjd)) return;
      const key = f.iso.slice(0, 10);
      const d = days.get(key) ?? { mjd: 0, s: [0, 0, 0] as Vec3, n: 0 };
      d.mjd += f.mjd;
      for (let j = 0; j < 3; j++) d.s[j] += at[j];
      d.n++;
      days.set(key, d);
    });
    if (!days.size) return;
    const list = [...days.values()].map((d) => ({ mjd: d.mjd / d.n, s: d.s.map((x) => x / d.n) as Vec3 }));
    const pos = new Float32Array(list.length * 6), ends = new Float32Array(list.length * 3);
    list.forEach((d, k) => {
      eclToThree(d.s, this.v);
      if (!this.scene.rewindPositionAt(slug, d.mjd, this.w)) return;
      pos.set([this.v.x, this.v.y, this.v.z, this.w.x, this.w.y, this.w.z], k * 6);
      ends.set([this.w.x, this.w.y, this.w.z], k * 3);
    });
    this.sights = list.map((d) => ({ mjd: d.mjd }));
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    g.setAttribute('color', new THREE.BufferAttribute(new Float32Array(list.length * 6), 3));
    this.sightLines = new THREE.LineSegments(g, new THREE.LineBasicMaterial({ vertexColors: true, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending }));
    this.sightLines.frustumCulled = false;
    const ge = new THREE.BufferGeometry();
    ge.setAttribute('position', new THREE.BufferAttribute(ends, 3));
    ge.setAttribute('color', new THREE.BufferAttribute(new Float32Array(list.length * 3), 3));
    this.sightEnds = new THREE.Points(ge, markerMaterial(this.scene.pixelRatio, false, 7));
    this.sightEnds.frustumCulled = false;
    this.group.add(this.sightLines, this.sightEnds);
  }

  private paintSights() {
    if (!this.sightLines || !this.sightEnds) return;
    const c = this.sightLines.geometry.attributes.color as THREE.BufferAttribute;
    const e = this.sightEnds.geometry.attributes.color as THREE.BufferAttribute;
    this.sights.forEach((s, k) => {
      const dt = (store.mjd - s.mjd) / 2.5;
      const lit = Math.exp(-dt * dt);
      const a = 0.1 + 0.9 * lit;
      // a cool blue line from SPHEREx, warming to gold at the object
      c.setXYZ(k * 2, 0.35 * a, 0.62 * a, 1.0 * a);
      c.setXYZ(k * 2 + 1, GOLD.r * a, GOLD.g * a, GOLD.b * a);
      e.setXYZ(k, GOLD.r * (0.35 + 0.65 * lit), GOLD.g * (0.35 + 0.65 * lit), GOLD.b * (0.35 + 0.65 * lit));
    });
    c.needsUpdate = e.needsUpdate = true;
  }

  // ---------- first known observation ----------
  private addFirstKnown(slug: string, p: ObjectPage) {
    const iso = (p as ObjectPage & { first_known_obs_iso?: string | null }).first_known_obs_iso ?? p.story?.discovered_iso;
    if (!iso) return;
    const mjd = mjdFromIso(iso);
    if (!Number.isFinite(mjd) || !this.scene.rewindPositionAt(slug, mjd, this.v)) return;
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(Float32Array.of(this.v.x, this.v.y, this.v.z), 3));
    g.setAttribute('color', new THREE.BufferAttribute(Float32Array.of(0.95, 0.95, 0.92), 3));
    this.fko = new THREE.Points(g, markerMaterial(this.scene.pixelRatio, true, 16));
    this.fko.frustumCulled = false;
    this.group.add(this.fko);
    const at = this.v.clone();
    this.scene.labels.add({ id: 'focus-fko', text: 'First known observation', sub: () => plainDate(iso), sticky: true, cls: 'label-note', priority: 9.5, pos: (o) => o.copy(at) });
  }

  private tick(dt: number) {
    if (!this.slug) return;
    const pos = this.scene.rewindPosition(this.slug, this.v);
    if (!pos) return;
    const res = this.scene.viewSize;
    for (const m of this.orbitMats) m.resolution.set(res[0], res[1]);
    const dot = this.scene.rewindDot(this.slug);
    if (this.orbitGeo && dot && (this.orbitMjd !== store.mjd || this.orbitSrc !== dot.el)) {
      // rebuilt around the dot whenever it moves, so the line runs through the body at any zoom
      this.setOrbit(focusPath(dot, store.mjd));
      this.orbitMjd = store.mjd;
      this.orbitSrc = dot.el;
    }
    this.paintSights();
    const camD = this.scene.camera.position.distanceTo(pos);
    this.gap.uFocus.value.set(0, 0, 0); // the dot, in the orbit's own coordinates
    this.gap.uGap.value = this.radius * 3;
    // thinner up close, so the line reads as a path and not a beam
    const thin = THREE.MathUtils.lerp(0.4, 1, THREE.MathUtils.smoothstep(camD, this.radius * 40, this.radius * 400));
    for (const m of this.orbitMats) m.linewidth = m.userData.width * thin;
    this.clock += dt;
    if (this.ring) {
      // a slow breathing ring around the dot; it gives way to the body in the close-up
      this.ring.position.copy(pos);
      this.ring.visible = camD > this.radius * 60;
      const u = (this.ring.material as THREE.ShaderMaterial).uniforms.uScale;
      u.value = reducedMotion ? 1 : 1 + 0.18 * Math.sin(this.clock * 2.2);
    }
    // the body only exists for the close-up; from further out the dot stands for it
    const near = camD < this.radius * 600;
    if (this.body) {
      this.body.visible = near;
      if (this.note.hidden === near) this.note.hidden = !near;
      this.body.position.copy(pos);
      if (!reducedMotion) this.body.rotateOnWorldAxis(this.spinAxis, dt * 0.12);
      // the rim light sits behind and a little above the body, so only its far edge catches it
      this.rim.intensity = near ? 0.45 : 0;
      this.w.copy(pos).sub(this.scene.camera.position).normalize().addScaledVector(this.scene.camera.up, 0.45);
      this.rim.position.copy(pos).addScaledVector(this.w, this.radius * 20);
      this.rim.target.position.copy(pos);
    }
    if (this.coma && this.tails.length) {
      const fade = THREE.MathUtils.clamp(1.6 - camD / (this.radius * 400), 0, 1);
      this.coma.visible = fade > 0;
      this.coma.position.copy(pos);
      // the ion tail points straight away from the Sun; the dust tail lags behind along the orbit
      const away = this.w.copy(pos).normalize();
      const next = this.scene.rewindPositionAt(this.slug, store.mjd + 1, this.u);
      const back = next ? this.u.sub(pos).normalize().negate() : this.u.set(0, 0, 0);
      this.tails.forEach((t, k) => {
        const u = (t.material as THREE.ShaderMaterial).uniforms;
        t.visible = fade > 0;
        t.position.copy(pos);
        u.uDir.value.copy(away);
        if (k === 1) {
          u.uDir.value.addScaledVector(back, 0.22).normalize();
          u.uBend.value.copy(back).multiplyScalar(0.3);
        }
        u.uLen.value = this.radius * (k === 1 ? 60 : 90);
        u.uAlpha.value = fade * (t.material as THREE.ShaderMaterial).userData.alpha;
        u.uTime.value += reducedMotion ? 0 : dt;
      });
    }
  }
}

/** Rock colour from the spectrum's best match (C dark, S lighter); unknown types get a middle grey-brown. */
function rockLook(p: ObjectPage): RockLook {
  const m = p.composition?.best_match?.trim().charAt(0).toUpperCase();
  return m === 'C' || m === 'S' || m === 'D' || m === 'X' ? m : 'unknown';
}
