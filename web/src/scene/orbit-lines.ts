// Orbit lines of Rewind objects: thin, brightest at the object and fading along the orbit,
// dimmer below the planets' plane so tilted orbits read as 3D, and gone far from the Sun.
// The geometry is offsets from the dot and the line object sits at the dot (in doubles on the
// CPU), so line and dot agree at every zoom. Drop lines tie each object to the planets' plane.
import * as THREE from 'three';
import { eclToThree } from './asteroids';
import type { OrbitPath } from './orbits';

const vertex = /* glsl */ `
#include <common>
#include <logdepthbuf_pars_vertex>
attribute float aU;   // -1 (behind the object) .. 0 (the object) .. 1 (ahead)
uniform float uCap;   // AU from the Sun where the line has faded out
varying float vU;
varying float vFade;
void main() {
  gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  #include <logdepthbuf_vertex>
  vec3 w = (modelMatrix * vec4(position, 1.0)).xyz;
  vU = aU;
  // below the planets' plane the line is dimmer
  vFade = (1.0 - smoothstep(uCap * 0.55, uCap, length(w))) * mix(0.42, 1.0, smoothstep(-0.03, 0.03, w.y));
}`;

const fragment = /* glsl */ `
#include <common>
#include <logdepthbuf_pars_fragment>
uniform vec3 uColor;
uniform float uGain;  // overall brightness, eased
uniform float uFloor; // brightness of the far side of the orbit, 0 = only a trail
uniform vec2 uLen;    // how far the glow reaches behind and ahead of the object
varying float vU;
varying float vFade;
void main() {
  #include <logdepthbuf_fragment>
  float glow = exp(-abs(vU) / (vU < 0.0 ? uLen.x : uLen.y));
  float a = (uFloor + (1.0 - uFloor) * glow) * vFade * uGain;
  gl_FragColor = vec4(mix(uColor, vec3(1.0), 0.45 * smoothstep(0.55, 1.0, glow)), a);
}`;

/** How a line looks at rest and under the pointer: [gain, floor]. */
export interface LineLook {
  color: number;
  rest: [number, number];
  hover: [number, number];
  len: [number, number];
}

export const LINE_LOOK = {
  found: { color: 0xf2b544, rest: [0.9, 0.16], hover: [1.25, 0.5], len: [0.2, 0.05] },
  hint: { color: 0x7fbcf2, rest: [0.5, 0], hover: [1.15, 0.45], len: [0.09, 0.02] },
  faint: { color: 0x7fbcf2, rest: [0, 0], hover: [1, 0.4], len: [0.09, 0.02] },
} satisfies Record<string, LineLook>;

export class OrbitLine {
  readonly line: THREE.Line;
  private u: Record<'uGain' | 'uFloor' | 'uCap', { value: number }>;
  private n = 0;
  readonly color: THREE.Color;
  mjd = NaN; // what the geometry was last built for
  src: unknown = null;

  constructor(readonly look: LineLook) {
    const m = new THREE.ShaderMaterial({
      vertexShader: vertex,
      fragmentShader: fragment,
      uniforms: { uColor: { value: new THREE.Color(look.color) }, uGain: { value: 0 }, uFloor: { value: look.rest[1] }, uLen: { value: new THREE.Vector2(...look.len) }, uCap: { value: 8 } },
      transparent: true,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
    });
    this.u = m.uniforms as OrbitLine['u'];
    this.color = m.uniforms.uColor.value;
    this.line = new THREE.Line(new THREE.BufferGeometry(), m);
    this.line.frustumCulled = false;
    this.line.renderOrder = 1;
    this.line.visible = false;
  }

  get gain(): number {
    return this.u.uGain.value;
  }

  /** Move the line to a freshly built path (same propagation as the dot). */
  set(path: OrbitPath) {
    const g = this.line.geometry;
    const count = path.u.length;
    if (count !== this.n) {
      g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(count * 3), 3));
      g.setAttribute('aU', new THREE.BufferAttribute(path.u, 1));
      this.n = count;
    }
    const pos = g.attributes.position as THREE.BufferAttribute, a = pos.array as Float32Array;
    // ecliptic (x, y, z) -> three (x, z, -y)
    for (let k = 0; k < count; k++) {
      a[k * 3] = path.rel[k * 3];
      a[k * 3 + 1] = path.rel[k * 3 + 2];
      a[k * 3 + 2] = -path.rel[k * 3 + 1];
    }
    pos.needsUpdate = true;
    eclToThree(path.origin, this.line.position);
    // long comet orbits fade out instead of running off hundreds of AU
    this.u.uCap.value = Math.max(7, this.line.position.length() * 2.4);
  }

  /** Ease the brightness towards rest or hover, scaled by `amount` (0 hides the line). */
  ease(hover: boolean, amount: number, k: number) {
    const [gain, floor] = hover ? this.look.hover : this.look.rest;
    this.u.uGain.value += (gain * amount - this.u.uGain.value) * k;
    this.u.uFloor.value += (floor - this.u.uFloor.value) * k;
    this.line.visible = this.u.uGain.value > 0.004;
  }

  dispose() {
    this.line.geometry.dispose();
    (this.line.material as THREE.Material).dispose();
  }
}

/** Faint vertical lines from objects to the planets' plane: one segment each, bright end at the object. */
export class DropLines {
  readonly lines: THREE.LineSegments;
  private max: number;

  constructor(max: number) {
    this.max = max;
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(max * 6), 3));
    g.setAttribute('color', new THREE.BufferAttribute(new Float32Array(max * 6), 3));
    this.lines = new THREE.LineSegments(g, new THREE.LineBasicMaterial({ vertexColors: true, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending }));
    this.lines.frustumCulled = false;
  }

  /** items: where the object is, its colour and a 0..1 strength. */
  set(items: { at: THREE.Vector3; color: THREE.Color; amount: number }[]) {
    const pos = this.lines.geometry.attributes.position as THREE.BufferAttribute, col = this.lines.geometry.attributes.color as THREE.BufferAttribute;
    let n = 0;
    for (const { at, color, amount } of items) {
      // nothing to tie down when the object is already in the plane
      if (n >= this.max || amount <= 0.01 || Math.abs(at.y) < 0.04) continue;
      pos.setXYZ(n * 2, at.x, at.y, at.z);
      pos.setXYZ(n * 2 + 1, at.x, 0, at.z);
      const top = 0.42 * amount, foot = 0.07 * amount;
      col.setXYZ(n * 2, color.r * top, color.g * top, color.b * top);
      col.setXYZ(n * 2 + 1, color.r * foot, color.g * foot, color.b * foot);
      n++;
    }
    this.lines.geometry.setDrawRange(0, n * 2);
    pos.needsUpdate = true;
    col.needsUpdate = true;
  }
}
