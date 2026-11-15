// Uncertainty cloud: clone positions along the orbit, interpolated in time.
// "Before / After Rewind" morphs the wide cloud into the thin one.
import * as THREE from 'three';
import type { ObjectPage } from '../lib/types';
import { type Elements, type Vec3, isValidElements, positionAt } from '../lib/kepler';
import { eclToThree } from './asteroids';
import { reducedMotion, store } from '../state';
import type { Scene } from './Scene';

const vertex = /* glsl */ `
#include <common>
#include <logdepthbuf_pars_vertex>
attribute vec3 after;
uniform float uMix;
uniform float uPx;
uniform float uSize; // smaller in the close-up
void main() {
  vec3 p = mix(position, after, uMix);
  vec4 mv = modelViewMatrix * vec4(p, 1.0);
  gl_Position = projectionMatrix * mv;
  #include <logdepthbuf_vertex>
  // before: big soft dots; after: small crisp dots that line up along the path
  gl_PointSize = mix(10.0, 3.5, uMix) * uSize * uPx;
}`;
const fragment = /* glsl */ `
#include <common>
#include <logdepthbuf_pars_fragment>
uniform float uAlpha;
uniform float uMix;
void main() {
  #include <logdepthbuf_fragment>
  float r = length(gl_PointCoord - 0.5) * 2.0;
  if (r > 1.0) discard;
  // before Rewind: soft blue haze; after Rewind: sharp gold
  vec3 c = mix(vec3(0.42, 0.68, 1.0), vec3(1.0, 0.78, 0.36), uMix);
  float edge = mix(0.0, 0.45, uMix);
  float a = smoothstep(1.0, edge, r) * mix(0.8, 1.0, uMix);
  gl_FragColor = vec4(c * a * uAlpha, 1.0);
}`;

export class UncertaintyCloud {
  private points: THREE.Points | null = null;
  private page: ObjectPage | null = null;
  private mat: THREE.ShaderMaterial;
  private target = 0;
  private lastMjd = NaN;
  private mode: 'before' | 'after' = 'before';
  private toggled = false; // the reader used Before / After for this object
  private show_ = 0; // eased 0..1: hidden in the close-up unless Before / After was used
  private alpha = 0.75;

  constructor(private scene: Scene) {
    this.mat = new THREE.ShaderMaterial({
      vertexShader: vertex,
      fragmentShader: fragment,
      uniforms: { uMix: { value: 0 }, uPx: { value: scene.pixelRatio }, uAlpha: { value: 0.75 }, uSize: { value: 1 } },
      transparent: true,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
    });
    scene.addHook((dt) => this.tick(dt));
  }

  show(p: ObjectPage | null) {
    if (this.points) {
      this.scene.scene.remove(this.points);
      this.points.geometry.dispose();
      this.points = null;
    }
    this.page = p;
    this.target = 0;
    this.mode = 'before';
    this.toggled = false;
    this.mat.uniforms.uMix.value = 0;
    if (!p || !p.cloud?.before?.length || !isValidElements(p.orbit)) {
      this.page = null;
      return;
    }
    const n = p.cloud.before[0].length;
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(n * 3), 3));
    g.setAttribute('after', new THREE.BufferAttribute(new Float32Array(n * 3), 3));
    this.points = new THREE.Points(g, this.mat);
    this.points.frustumCulled = false;
    this.points.renderOrder = 3;
    this.scene.scene.add(this.points);
    this.lastMjd = NaN;
  }

  /** Spread of the "before" cloud at a time, in AU (largest distance of a clone from the nominal path). */
  extentAt(p: ObjectPage, mjd: number): number {
    const c = p.cloud;
    if (!c?.before?.length || !isValidElements(p.orbit)) return 0;
    let k = 0;
    while (k < c.dates_mjd.length - 1 && c.dates_mjd[k] < mjd) k++;
    const nominal = positionAt(p.orbit, c.dates_mjd[k]);
    let m = 0;
    for (const q of c.before[k]) m = Math.max(m, Math.hypot(q[0] - nominal[0], q[1] - nominal[1], q[2] - nominal[2]));
    return m;
  }

  /** Current "before" clone positions (three.js coordinates), e.g. to frame the camera. */
  beforePoints(): THREE.Vector3[] {
    if (!this.points) return [];
    const a = this.points.geometry.attributes.position as THREE.BufferAttribute;
    return Array.from({ length: a.count }, (_, i) => new THREE.Vector3().fromBufferAttribute(a, i));
  }

  setMode(mode: 'before' | 'after') {
    if (mode !== this.mode) this.toggled = true;
    this.mode = mode;
    this.target = mode === 'after' && this.page?.cloud?.after ? 1 : 0;
    if (reducedMotion) this.mat.uniforms.uMix.value = this.target;
  }

  // Interpolate each clone's OFFSET from the nominal orbit, then add the nominal position
  // at the current time. Straight-line interpolation of positions would cut across the curve.
  private fill(attr: THREE.BufferAttribute, sets: Vec3[][], dates: number[], mjd: number) {
    let k = 0;
    while (k < dates.length - 2 && mjd > dates[k + 1]) k++;
    const t = Math.min(1, Math.max(0, (mjd - dates[k]) / (dates[k + 1] - dates[k])));
    const el = this.elements();
    const n0 = positionAt(el, dates[k]), n1 = positionAt(el, dates[k + 1]), now = positionAt(el, mjd);
    const A = sets[k], B = sets[k + 1];
    const v = new THREE.Vector3();
    const p: Vec3 = [0, 0, 0];
    for (let i = 0; i < A.length; i++) {
      for (let j = 0; j < 3; j++) p[j] = now[j] + (A[i][j] - n0[j]) * (1 - t) + (B[i][j] - n1[j]) * t;
      eclToThree(p, v);
      attr.setXYZ(i, v.x, v.y, v.z);
    }
    attr.needsUpdate = true;
  }

  private elements(): Elements {
    const o = this.page!.orbit!;
    return { a: o.a, e: o.e, i: o.i, node: o.node, peri: o.peri, M: o.M, epoch_mjd: o.epoch_mjd };
  }

  private tick(dt: number) {
    if (!this.points || !this.page) return;
    const u = this.mat.uniforms.uMix;
    if (u.value !== this.target) {
      const step = dt / 1.6;
      u.value = this.target > u.value ? Math.min(this.target, u.value + step) : Math.max(this.target, u.value - step);
    }
    // in the close-up the clones would scatter across the body: only show them when asked for
    const close = this.scene.level === 'close';
    const want = close && !this.toggled ? 0 : 1;
    this.show_ += (want - this.show_) * (reducedMotion ? 1 : Math.min(1, dt * 6));
    this.points.visible = this.show_ > 0.01;
    this.mat.uniforms.uSize.value = close ? 0.45 : 1;
    this.mat.uniforms.uAlpha.value = this.alpha * this.show_;
    const c = this.page.cloud!;
    if (c.dates_mjd.length < 2 || store.mjd === this.lastMjd) return;
    this.lastMjd = store.mjd;
    const g = this.points.geometry;
    this.fill(g.attributes.position as THREE.BufferAttribute, c.before, c.dates_mjd, store.mjd);
    this.fill(g.attributes.after as THREE.BufferAttribute, c.after ?? c.before, c.dates_mjd, store.mjd);
    // outside the computed dates the cloud is only a guess, so fade it
    const out = store.mjd < c.dates_mjd[0] || store.mjd > c.dates_mjd[c.dates_mjd.length - 1];
    this.alpha = out ? 0.2 : 0.75;
  }
}
