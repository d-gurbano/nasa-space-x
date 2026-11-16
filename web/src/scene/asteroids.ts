// All asteroid and comet dots in one Points object. Positions are solved on the GPU
// (Kepler's equation in the vertex shader) so dragging time costs nothing on the CPU.
// Each dot is a round, soft-edged disc with a small glow. Dots grow a little when the camera
// is close (clamped, so they never turn into big blobs), the far field twinkles slightly,
// and comets near the Sun get a short tail pointing away from it.
import * as THREE from 'three';
import { basis, DEG, meanMotion } from '../lib/kepler';
import type { OrbitColumns } from '../lib/data';
import { FLAG } from '../lib/types';
import { mjdFromIso } from '../lib/time';
import { reducedMotion } from '../state';
import { SPRITE_FRAG, TAIL_VERT } from './sprites';
import { cloudPosition } from './orbits';

/** Ecliptic (x, y, z) to three.js (x, z, -y): the ecliptic is the horizontal plane. */
export function eclToThree(v: ArrayLike<number>, out = new THREE.Vector3()): THREE.Vector3 {
  return out.set(v[0], v[2], -v[1]);
}

// Fallback when the data has no per-object discovery date: start of the "new since" window.
const NEW_SINCE_MJD = mjdFromIso('2025-04-01');

const vertex = /* glsl */ `
#include <common>
#include <logdepthbuf_pars_vertex>
attribute vec3 aP;
attribute vec3 aQ;
attribute vec4 aOrb;   // a, e, M0 (rad), n (rad/day)
attribute vec3 aMeta;  // H, flag, discovery (days from epoch)
uniform float uDt;     // days from epoch
uniform float uPx;     // device pixel ratio
uniform float uDim;    // 0..1, dims everything when an object is selected
uniform vec3 uGroup;   // 0..1 visibility of near-Earth, main belt and comets (the layers panel)
uniform float uGain;   // overall brightness, lower for big catalogues
uniform float uTime;   // seconds, for the twinkle
uniform float uTwinkle;
varying vec3 vColor;
varying float vAlpha;
varying vec2 vDisc;    // disc radius and one pixel, in sprite units
varying vec3 vTail;
${TAIL_VERT}

void main() {
  float a = aOrb.x;
  float e = aOrb.y;
  float M = mod(aOrb.z + aOrb.w * uDt, 6.2831853);
  if (M > 3.1415927) M -= 6.2831853;
  float E = e < 0.8 ? M : 3.1415927 * sign(M);
  for (int k = 0; k < 10; k++) {
    float d = (E - e * sin(E) - M) / (1.0 - e * cos(E));
    E -= d;
    if (abs(d) < 1e-5) break;
  }
  vec3 pos = a * (cos(E) - e) * aP + a * sqrt(1.0 - e * e) * sin(E) * aQ;

  vec4 mv = modelViewMatrix * vec4(pos, 1.0);
  gl_Position = projectionMatrix * mv;
  #include <logdepthbuf_vertex>

  float flag = aMeta.y;
  bool neo = mod(flag, 2.0) >= 1.0;
  bool isNew = mod(floor(flag / 4.0), 2.0) >= 1.0;
  bool comet = mod(floor(flag / 8.0), 2.0) >= 1.0;
  float shown = comet ? uGroup.z : (neo ? uGroup.x : uGroup.y);
  if (flag >= 1024.0) shown = 0.0; // drawn as a Rewind dot instead

  bool known = uDt >= aMeta.z;
  float bright = 0.7 * clamp(1.15 - (aMeta.x - 12.0) / 16.0, 0.35, 1.0);
  vec3 c = vec3(0.29, 0.55, 0.80);
  float size = 1.7;
  if (neo) { c = vec3(0.42, 0.68, 0.92); size = 1.9; }
  if (comet) { c = vec3(0.70, 0.88, 0.95); size = 2.1; }
  if (isNew) { c = vec3(0.80, 0.93, 1.0); size = 2.2; bright = min(1.0, bright + 0.1); }
  if (!known) { c = vec3(0.42, 0.43, 0.46); bright *= 0.55; size = 1.6; }
  // closer dots are drawn larger, within limits
  float near = clamp(1.6 / length(mv.xyz), 1.0, 3.2);
  float core = size * 0.62 * near;
  vTail = comet && known ? tailOf(mv.xyz, length(pos)) : vec3(0.0);
  float sprite = max(core * 2.4 + 1.5, vTail.z > 0.02 ? 16.0 * near : 0.0);
  // only the dense far field twinkles
  float ph = fract(aOrb.z * 12.9898 + a * 78.233) * 6.2831853;
  float tw = 1.0 + uTwinkle * 0.2 * sin(uTime * (0.6 + 1.4 * fract(ph * 2.7)) + ph) * (1.0 - smoothstep(1.0, 1.6, near));
  vColor = c;
  vAlpha = bright * uGain * tw * (1.0 - 0.75 * uDim) * shown;
  gl_PointSize = shown > 0.003 ? sprite * uPx : 0.0;
  vDisc = vec2(core / sprite, 1.5 / (sprite * uPx));
}
`;

const fragment = /* glsl */ `
#include <common>
#include <logdepthbuf_pars_fragment>
varying vec3 vColor;
varying float vAlpha;
varying vec2 vDisc;
varying vec3 vTail;
${SPRITE_FRAG}
void main() {
  #include <logdepthbuf_fragment>
  vec2 p = spriteUv();
  float r = length(p);
  if (r > 1.0 || vAlpha <= 0.0) discard;
  float s = softDisc(r, vDisc.x, vDisc.y) + cometTail(p, vTail, vDisc.x);
  gl_FragColor = vec4(vColor * s * vAlpha, 1.0);
}
`;

export class AsteroidCloud {
  readonly points: THREE.Points;
  readonly material: THREE.ShaderMaterial;
  readonly epoch: number;
  readonly count: number;
  readonly newCount: number;
  /** How many dots each layer holds: near-Earth, main belt (everything else), comets. */
  readonly groups = { neo: 0, mba: 0, comet: 0 };

  /** `skip`: rows drawn as Rewind dots instead, so no object shows twice at slightly different places. */
  constructor(orb: OrbitColumns, pixelRatio: number, skip: Set<number> = new Set()) {
    const F = orb.fields.length;
    const ix = (n: string) => orb.col(n);
    const [ia, ie, ii, inode, iperi, iM, iH, iflag] = ['a', 'e', 'i', 'node', 'peri', 'M', 'H', 'flag'].map(ix);
    const idisc = ix('disc_mjd'); // optional extension; see docs/DATA-CONTRACT.md
    // keep only rows that can be propagated (bound orbits, finite numbers); near-parabolic rows
    // are left out, since float32 elements and the shader's solver would put them far off
    const keep: number[] = [];
    for (let r = 0; r < orb.count; r++) {
      const o = r * F;
      const ok = [ia, ie, ii, inode, iperi, iM].every((c) => Number.isFinite(orb.data[o + c]));
      if (ok && orb.data[o + ia] > 0 && orb.data[o + ie] < 0.995 && !skip.has(r)) keep.push(r);
    }
    const N = keep.length;
    const P = new Float32Array(N * 3), Q = new Float32Array(N * 3);
    const O = new Float32Array(N * 4), Mt = new Float32Array(N * 3);
    const d = orb.data;
    let newCount = 0;
    for (let r = 0; r < N; r++) {
      const o = keep[r] * F;
      const a = d[o + ia], e = d[o + ie];
      const b = basis(d[o + ii], d[o + inode], d[o + iperi]);
      // ecliptic -> three: (x, z, -y)
      P.set([b.P[0], b.P[2], -b.P[1]], r * 3);
      Q.set([b.Q[0], b.Q[2], -b.Q[1]], r * 3);
      const flag = d[o + iflag];
      // The table's main-belt sample bunches up in mean anomaly (most rows sit near perihelion on
      // one side of the Sun), so the belt looked lopsided. Its background dots keep their real orbits
      // but get an even spread of phases along them, so the belt reads as the ring it is.
      // Near-Earth objects, comets and new objects keep their real positions.
      const spread = !(flag & (FLAG.NEO | FLAG.COMET | FLAG.NEW));
      O.set([a, e, spread ? ((r * 0.6180339887) % 1) * 2 * Math.PI : d[o + iM] * DEG, meanMotion(a)], r * 4);
      let disc = -1e6;
      if (idisc >= 0 && d[o + idisc] > 0) disc = d[o + idisc] - orb.epoch_mjd;
      else if (flag & FLAG.NEW) disc = NEW_SINCE_MJD - orb.epoch_mjd;
      if (flag & FLAG.NEW) newCount++;
      this.groups[flag & FLAG.COMET ? 'comet' : flag & FLAG.NEO ? 'neo' : 'mba']++;
      Mt.set([d[o + iH], flag, disc], r * 3);
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(N * 3), 3)); // unused, needed by three
    g.setAttribute('aP', new THREE.BufferAttribute(P, 3));
    g.setAttribute('aQ', new THREE.BufferAttribute(Q, 3));
    g.setAttribute('aOrb', new THREE.BufferAttribute(O, 4));
    g.setAttribute('aMeta', new THREE.BufferAttribute(Mt, 3));
    g.boundingSphere = new THREE.Sphere(new THREE.Vector3(), 1e4);

    this.material = new THREE.ShaderMaterial({
      vertexShader: vertex,
      fragmentShader: fragment,
      uniforms: {
        uDt: { value: 0 },
        uPx: { value: pixelRatio },
        uDim: { value: 0 },
        uGroup: { value: new THREE.Vector3(1, 1, 1) },
        uGain: { value: Math.min(1, Math.max(0.45, Math.sqrt(70000 / Math.max(1, N)))) },
        uTime: { value: 0 },
        uTwinkle: { value: reducedMotion ? 0 : 1 },
      },
      transparent: true,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
    });
    this.points = new THREE.Points(g, this.material);
    this.points.frustumCulled = false;
    this.epoch = orb.epoch_mjd;
    this.count = N;
    this.newCount = newCount;
  }

  /**
   * Hide new objects of the table that sit within `tol` AU of a Rewind dot at `mjd` (three.js
   * coordinates): the same object under another name, so it is not drawn twice beside its line.
   */
  hideNear(at: ArrayLike<number>[], mjd: number, tol = 2e-3) {
    if (!at.length) return;
    const g = this.points.geometry, at2 = tol * tol;
    const P = g.attributes.aP.array as Float32Array, Q = g.attributes.aQ.array as Float32Array;
    const O = g.attributes.aOrb.array as Float32Array, Mt = g.attributes.aMeta as THREE.BufferAttribute;
    const meta = Mt.array as Float32Array;
    let n = 0;
    for (let r = 0; r < this.count; r++) {
      const flag = meta[r * 3 + 1];
      if (!(flag & FLAG.NEW) || flag >= 1024) continue;
      const p = cloudPosition(O.subarray(r * 4, r * 4 + 4), P.subarray(r * 3, r * 3 + 3), Q.subarray(r * 3, r * 3 + 3), mjd - this.epoch);
      if (at.some((q) => (q[0] - p[0]) ** 2 + (q[1] - p[1]) ** 2 + (q[2] - p[2]) ** 2 < at2)) {
        meta[r * 3 + 1] = flag + 1024;
        n++;
      }
    }
    if (n) Mt.needsUpdate = true;
  }

  setTime(mjd: number, seconds: number) {
    this.material.uniforms.uDt.value = mjd - this.epoch;
    this.material.uniforms.uTime.value = seconds;
  }
}
