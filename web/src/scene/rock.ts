// A procedural rocky body for the close-up (an artist impression: real shapes are unknown):
// a lumpy, cratered mesh, a fine regolith normal map made in code (no download), and a dark
// rough material whose colour follows the object's type.
import * as THREE from 'three';
import { mergeVertices } from 'three/examples/jsm/utils/BufferGeometryUtils.js';

/** Small deterministic random numbers from a string, so each object keeps its own shape. */
export function seeded(key: string): () => number {
  let h = 2166136261;
  for (let i = 0; i < key.length; i++) h = Math.imul(h ^ key.charCodeAt(i), 16777619);
  return () => {
    h = Math.imul(h ^ (h >>> 15), 2246822507);
    h = Math.imul(h ^ (h >>> 13), 3266489909);
    h ^= h >>> 16;
    return (h >>> 0) / 4294967296;
  };
}

/** Smooth 3D value noise in about -1..1, summed over octaves. */
function makeNoise(rand: () => number) {
  const perm = Array.from({ length: 256 }, (_, i) => i);
  for (let i = 255; i > 0; i--) {
    const j = Math.floor(rand() * (i + 1));
    [perm[i], perm[j]] = [perm[j], perm[i]];
  }
  const val = Float32Array.from({ length: 256 }, () => rand() * 2 - 1);
  const h = (x: number, y: number, z: number) => val[perm[(perm[(perm[x & 255] + y) & 255] + z) & 255]];
  const s = (t: number) => t * t * (3 - 2 * t);
  const noise = (x: number, y: number, z: number) => {
    const xi = Math.floor(x), yi = Math.floor(y), zi = Math.floor(z);
    const u = s(x - xi), v = s(y - yi), w = s(z - zi);
    const l = (a: number, b: number, t: number) => a + (b - a) * t;
    return l(
      l(l(h(xi, yi, zi), h(xi + 1, yi, zi), u), l(h(xi, yi + 1, zi), h(xi + 1, yi + 1, zi), u), v),
      l(l(h(xi, yi, zi + 1), h(xi + 1, yi, zi + 1), u), l(h(xi, yi + 1, zi + 1), h(xi + 1, yi + 1, zi + 1), u), v),
      w,
    );
  };
  return (x: number, y: number, z: number, oct = 4) => {
    let sum = 0, amp = 0.5, f = 1;
    for (let k = 0; k < oct; k++) {
      sum += amp * noise(x * f, y * f, z * f);
      amp *= 0.5;
      f *= 2.03;
    }
    return sum;
  };
}

/**
 * A rocky body of radius about 1: an icosphere pushed in and out by several octaves of noise,
 * crater bowls with raised rims in three sizes, and a random overall elongation. Vertex
 * colours (around 1) darken the crater floors and brighten the rims a little. `soft` gives
 * the smoother, less cratered shape used for an icy comet nucleus.
 */
export function rockGeometry(key: string, detail = 56, soft = false): THREE.BufferGeometry {
  const rand = seeded(key);
  const fbm = makeNoise(rand);
  let g: THREE.BufferGeometry = new THREE.IcosahedronGeometry(1, detail);
  g.deleteAttribute('normal');
  g.deleteAttribute('uv');
  g = mergeVertices(g);
  // [count, smallest radius, radius range, smallest depth, depth range]
  const sizes = soft ? [[3, 0.3, 0.3, 0.02, 0.03], [6, 0.1, 0.14, 0.01, 0.02]] : [[4, 0.32, 0.26, 0.05, 0.05], [12, 0.11, 0.16, 0.025, 0.04], [30, 0.035, 0.06, 0.01, 0.018]];
  const craters = sizes.flatMap(([count, r0, dr, d0, dd]) => Array.from({ length: count }, () => {
    const c = new THREE.Vector3(rand() * 2 - 1, rand() * 2 - 1, rand() * 2 - 1).normalize();
    const r = r0 + rand() * dr;
    return { c, r, d: d0 + rand() * dd, reach: Math.cos(Math.min(Math.PI, r * 1.7)) };
  }));
  const stretch = new THREE.Vector3(1.15 + rand() * 0.45, 0.78 + rand() * 0.18, 0.86 + rand() * 0.16);
  const pos = g.attributes.position as THREE.BufferAttribute;
  const col = new Float32Array(pos.count * 3);
  const n = new THREE.Vector3();
  for (let i = 0; i < pos.count; i++) {
    n.fromBufferAttribute(pos, i).normalize();
    let r = 1 + 0.28 * fbm(n.x * 1.1 + 7, n.y * 1.1, n.z * 1.1, 3) + (soft ? 0.05 : 0.09) * fbm(n.x * 3.3, n.y * 3.3 + 5, n.z * 3.3, 3);
    if (!soft) r += 0.03 * fbm(n.x * 9 + 2, n.y * 9, n.z * 9, 3);
    let tone = 0;
    for (const k of craters) {
      const dot = n.dot(k.c);
      if (dot < k.reach) continue;
      const a = Math.acos(Math.min(1, dot)) / k.r;
      const rim = Math.exp(-(((a - 1) / 0.22) ** 2));
      if (a < 1) {
        r -= k.d * (1 - a * a);
        tone -= 0.16 * (1 - a * a);
      }
      r += k.d * 0.38 * rim;
      tone += 0.07 * rim;
    }
    pos.setXYZ(i, n.x * r * stretch.x, n.y * r * stretch.y, n.z * r * stretch.z);
    const shade = Math.max(0.5, 0.92 + 0.2 * fbm(n.x * 2.6 + 3, n.y * 2.6, n.z * 2.6, 3) + tone);
    col.set([shade * 1.02, shade * 0.99, shade * 0.95], i * 3);
  }
  g.setAttribute('color', new THREE.BufferAttribute(col, 3));
  g.computeVertexNormals();
  return g;
}

/**
 * A tileable normal map of fine regolith: grainy noise at several scales plus small pits.
 * Returns RGBA bytes (x and y of the normal in red and green).
 */
export function regolithNormals(size = 256, key = 'regolith'): Uint8Array {
  const rand = seeded(key);
  const h = new Float32Array(size * size);
  // periodic value noise, so the tile repeats without a seam
  for (let cells = 8, amp = 1; cells <= size / 2; cells *= 2, amp *= 0.62) {
    const lat = Float32Array.from({ length: cells * cells }, () => rand() * 2 - 1);
    const step = cells / size;
    for (let y = 0; y < size; y++) {
      const fy = y * step, y0 = Math.floor(fy), ty = fy - y0, v = ty * ty * (3 - 2 * ty);
      for (let x = 0; x < size; x++) {
        const fx = x * step, x0 = Math.floor(fx), tx = fx - x0, u = tx * tx * (3 - 2 * tx);
        const x1 = (x0 + 1) % cells, y1 = (y0 + 1) % cells;
        const a = lat[y0 * cells + x0], b = lat[y0 * cells + x1], c = lat[y1 * cells + x0], d = lat[y1 * cells + x1];
        h[y * size + x] += amp * (a + (b - a) * u + (c - a) * v + (a - b - c + d) * u * v);
      }
    }
  }
  // small pits with a faint rim
  for (let k = 0; k < 70; k++) {
    const cx = rand() * size, cy = rand() * size, r = 2.5 + rand() * rand() * 12, depth = 0.5 + rand() * 0.9;
    const m = Math.ceil(r * 1.5);
    for (let dy = -m; dy <= m; dy++) {
      for (let dx = -m; dx <= m; dx++) {
        const a = Math.hypot(dx, dy) / r;
        if (a > 1.5) continue;
        const x = (Math.floor(cx) + dx + size) % size, y = (Math.floor(cy) + dy + size) % size;
        h[y * size + x] += depth * ((a < 1 ? -(1 - a * a) : 0) + 0.3 * Math.exp(-(((a - 1) / 0.25) ** 2)));
      }
    }
  }
  const out = new Uint8Array(size * size * 4);
  const at = (x: number, y: number) => h[((y + size) % size) * size + ((x + size) % size)];
  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      const nx = (at(x - 1, y) - at(x + 1, y)) * 1.6, ny = (at(x, y - 1) - at(x, y + 1)) * 1.6;
      const l = Math.hypot(nx, ny, 1), i = (y * size + x) * 4;
      out[i] = Math.round((nx / l * 0.5 + 0.5) * 255);
      out[i + 1] = Math.round((ny / l * 0.5 + 0.5) * 255);
      out[i + 2] = Math.round((1 / l * 0.5 + 0.5) * 255);
      out[i + 3] = 255;
    }
  }
  return out;
}

let regolith: THREE.DataTexture | null = null;
function regolithTexture(): THREE.DataTexture {
  if (regolith) return regolith;
  regolith = new THREE.DataTexture(regolithNormals(256), 256, 256, THREE.RGBAFormat);
  regolith.wrapS = regolith.wrapT = THREE.RepeatWrapping;
  regolith.magFilter = THREE.LinearFilter;
  regolith.minFilter = THREE.LinearMipmapLinearFilter;
  regolith.generateMipmaps = true;
  regolith.anisotropy = 4;
  regolith.needsUpdate = true;
  return regolith;
}

export type RockLook = 'C' | 'S' | 'D' | 'X' | 'comet' | 'unknown';

// linear albedo, near the measured geometric albedos: dark carbon-rich (C about 0.06, D darker),
// stony (S about 0.2), grey (X), and a dark dusty nucleus under the coma (comet)
const ALBEDO: Record<RockLook, [number, number, number]> = {
  C: [0.075, 0.068, 0.06],
  D: [0.062, 0.05, 0.042],
  S: [0.21, 0.19, 0.16],
  X: [0.13, 0.126, 0.12],
  comet: [0.07, 0.074, 0.08],
  unknown: [0.11, 0.1, 0.09],
};

/** Exposure for the close-up; the rock is tone-mapped on its own (ACES), so the rest of the scene keeps its look. */
const ROCK_EXPOSURE = 0.85;

/**
 * Rough, dark regolith. The normal map is laid on from three sides (no texture seams or
 * poles) at two scales, so the surface stays grainy from the first view down to the close-up.
 */
export function rockMaterial(look: RockLook): THREE.MeshStandardMaterial {
  const icy = look === 'comet';
  const m = new THREE.MeshStandardMaterial({ vertexColors: true, roughness: icy ? 0.72 : 0.95, metalness: 0 });
  m.color.setRGB(...ALBEDO[look]);
  const uniforms = { uRego: { value: regolithTexture() }, uRockBump: { value: icy ? 0.45 : 0.9 }, uRockExposure: { value: ROCK_EXPOSURE } };
  m.onBeforeCompile = (sh) => {
    Object.assign(sh.uniforms, uniforms);
    sh.vertexShader = sh.vertexShader
      .replace('#include <common>', '#include <common>\nvarying vec3 vRockP;\nvarying vec3 vRockN;')
      .replace('#include <begin_vertex>', '#include <begin_vertex>\nvRockP = position;\nvRockN = normal;');
    sh.fragmentShader = sh.fragmentShader
      .replace('#include <common>', /* glsl */ `#include <common>
        uniform mat3 normalMatrix;
        uniform sampler2D uRego;
        uniform float uRockBump;
        uniform float uRockExposure;
        varying vec3 vRockP;
        varying vec3 vRockN;
        // three.js's ACES filmic fit, here so the rock is tone-mapped whatever the renderer does
        vec3 rockAces(vec3 c) {
          c = mat3(vec3(0.59719, 0.07600, 0.02840), vec3(0.35458, 0.90834, 0.13383), vec3(0.04823, 0.01566, 0.83777)) * (c / 0.6);
          c = (c * (c + 0.0245786) - 0.000090537) / (c * (0.983729 * c + 0.4329510) + 0.238081);
          return clamp(mat3(vec3(1.60475, -0.10208, -0.00327), vec3(-0.53108, 1.10813, -0.07276), vec3(-0.07367, -0.00605, 1.07602)) * c, 0.0, 1.0);
        }
        vec2 rockTap(vec2 uv) {
          return (texture2D(uRego, uv * 1.7).xy - 0.5) * 2.0 + (texture2D(uRego, uv * 6.1 + 0.37).xy - 0.5) * 1.3;
        }`)
      .replace('#include <normal_fragment_maps>', /* glsl */ `#include <normal_fragment_maps>
        {
          vec3 on = normalize(vRockN);
          vec3 w = pow(abs(on), vec3(4.0));
          w /= w.x + w.y + w.z;
          vec2 tx = rockTap(vRockP.zy), ty = rockTap(vRockP.xz), tz = rockTap(vRockP.xy);
          vec3 bump = vec3(0.0, tx.y, tx.x) * w.x + vec3(ty.x, 0.0, ty.y) * w.y + vec3(tz.x, tz.y, 0.0) * w.z;
          normal = normalize(normalMatrix * normalize(on + bump * uRockBump));
        }`)
      // ACES filmic with a lower exposure: lit faces roll off softly instead of clipping to white
      .replace('#include <tonemapping_fragment>', 'gl_FragColor.rgb = rockAces( gl_FragColor.rgb * uRockExposure );');
  };
  m.customProgramCacheKey = () => 'rock-regolith';
  return m;
}
