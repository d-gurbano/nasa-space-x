// How things look in the 3D scene: every body is a point sprite drawn by a small shader,
// so it stays round and soft-edged at any zoom. Stars, the Sun, shaded planets, Rewind dots,
// and the GLSL pieces the asteroid cloud shares (soft disc, comet tail).
import * as THREE from 'three';

/** Fragment helpers. Sprite coordinates run -1..1 with y up; "core" is the disc radius in those units. */
export const SPRITE_FRAG = /* glsl */ `
vec2 spriteUv() { return vec2(gl_PointCoord.x - 0.5, 0.5 - gl_PointCoord.y) * 2.0; }
// an anti-aliased disc with a small glow around it, fading out before the sprite edge
float softDisc(float r, float core, float aa) {
  float disc = 1.0 - smoothstep(core - aa, core + aa, r);
  float glow = 0.4 * exp(-0.9 * r * r / (core * core));
  return (disc * 0.8 + glow) * smoothstep(1.0, 0.8, r);
}
// a faint tail from the centre to the sprite edge; t.xy = direction on screen, t.z = strength
float cometTail(vec2 p, vec3 t, float core) {
  float along = dot(p, t.xy);
  float across = dot(p, vec2(-t.y, t.x));
  float w = core * 0.7 + 0.16 * along;
  return t.z * step(0.0, along) * smoothstep(1.0, 0.0, along) * exp(-across * across / (w * w)) * 0.55;
}`;

/** Vertex helper: the tail points away from the Sun and fades with distance from it (rh, AU). */
export const TAIL_VERT = /* glsl */ `
vec3 tailOf(vec3 mv, float rh) {
  vec3 away = mv - (modelViewMatrix * vec4(0.0, 0.0, 0.0, 1.0)).xyz;
  float onScreen = length(away.xy);
  float s = clamp(2.4 / max(rh, 0.05) - 0.3, 0.0, 1.0) * onScreen / max(length(away), 1e-9);
  return vec3(onScreen > 1e-9 ? away.xy / onScreen : vec2(0.0, 1.0), s);
}`;

/** Background stars: round, soft, mostly faint, a few brighter, slightly blue or warm. */
export function starField(px: number): THREE.Points {
  const n = 3200;
  const pos = new Float32Array(n * 3), star = new Float32Array(n * 3);
  for (let k = 0; k < n; k++) {
    const u = Math.random() * 2 - 1, t = Math.random() * Math.PI * 2, r = Math.sqrt(1 - u * u);
    pos.set([r * Math.cos(t) * 4000, u * 4000, r * Math.sin(t) * 4000], k * 3);
    const big = Math.pow(Math.random(), 7);
    star.set([2.2 + 4.2 * big, 0.22 + 0.5 * Math.pow(Math.random(), 2) + 0.28 * big, Math.random()], k * 3);
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  g.setAttribute('aStar', new THREE.BufferAttribute(star, 3)); // size px, brightness, tint
  const m = new THREE.ShaderMaterial({
    uniforms: { uPx: { value: px } },
    vertexShader: /* glsl */ `
      attribute vec3 aStar;
      uniform float uPx;
      varying vec3 vC;
      void main() {
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
        gl_PointSize = aStar.x * uPx;
        vC = mix(vec3(0.62, 0.74, 1.0), vec3(1.0, 0.86, 0.7), aStar.z) * aStar.y;
      }`,
    fragmentShader: /* glsl */ `
      varying vec3 vC;
      void main() {
        vec2 p = (gl_PointCoord - 0.5) * 2.0;
        gl_FragColor = vec4(vC * exp(-5.0 * dot(p, p)) * smoothstep(1.0, 0.7, length(p)), 1.0);
      }`,
    transparent: true,
    depthWrite: false,
    depthTest: false,
    blending: THREE.AdditiveBlending,
  });
  const points = new THREE.Points(g, m);
  points.frustumCulled = false;
  points.renderOrder = -1;
  return points;
}

const OBLIQUITY = 23.4393 * (Math.PI / 180);

/**
 * The Milky Way behind everything: NASA SVS Deep Star Maps 2020 (equatorial, RA 0h in the middle,
 * east to the left), turned into the ecliptic frame of the scene. Kept dim so the dots stay in front.
 * It fades in once the image has loaded; uFade runs 0..1.
 */
export function milkyWay(url: string): THREE.Mesh<THREE.SphereGeometry, THREE.ShaderMaterial> {
  const m = new THREE.ShaderMaterial({
    uniforms: { uMap: { value: null }, uFade: { value: 0 }, uBright: { value: 0.3 } },
    vertexShader: /* glsl */ `
      varying vec3 vDir;
      void main() {
        vDir = position;
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
      }`,
    fragmentShader: /* glsl */ `
      uniform sampler2D uMap;
      uniform float uFade;
      uniform float uBright;
      varying vec3 vDir;
      void main() {
        vec3 d = normalize(vDir);
        // three.js (x, y, z) -> ecliptic (x, -z, y) -> equatorial (tilt by the obliquity about x)
        vec3 ecl = vec3(d.x, -d.z, d.y);
        float c = ${Math.cos(OBLIQUITY).toFixed(6)}, s = ${Math.sin(OBLIQUITY).toFixed(6)};
        vec3 eq = vec3(ecl.x, ecl.y * c - ecl.z * s, ecl.y * s + ecl.z * c);
        float ra = atan(eq.y, eq.x), dec = asin(clamp(eq.z, -1.0, 1.0));
        vec3 col = texture2D(uMap, vec2(fract(0.5 - ra / 6.2831853), 0.5 + dec / 3.1415927)).rgb;
        // lift the black point a little so the sky floor stays black and only the band shows
        col = max(col - 0.07, 0.0) / 0.93;
        gl_FragColor = vec4(col * uBright * uFade, 1.0);
      }`,
    side: THREE.BackSide,
    depthWrite: false,
    depthTest: false,
  });
  const mesh = new THREE.Mesh(new THREE.SphereGeometry(3000, 48, 24), m);
  mesh.renderOrder = -2;
  mesh.frustumCulled = false;
  mesh.visible = false;
  new THREE.TextureLoader().load(url, (t) => {
    // the sky is always magnified on screen, so no mipmaps (and no seam where the image wraps)
    t.generateMipmaps = false;
    t.minFilter = THREE.LinearFilter;
    t.wrapS = THREE.RepeatWrapping;
    m.uniforms.uMap.value = t;
    mesh.visible = true;
  });
  return mesh;
}

/** The Sun: a white-hot core, a warm glow and a wide faint corona. */
export function sunSprite(): THREE.Sprite {
  const c = document.createElement('canvas');
  c.width = c.height = 256;
  const g = c.getContext('2d')!;
  const grd = g.createRadialGradient(128, 128, 0, 128, 128, 128);
  const stops: [number, string][] = [
    [0, 'rgba(255,253,244,1)'],
    [0.03, 'rgba(255,246,220,1)'],
    [0.065, 'rgba(255,214,140,0.6)'],
    [0.15, 'rgba(255,178,88,0.2)'],
    [0.4, 'rgba(255,150,64,0.05)'],
    [1, 'rgba(255,140,60,0)'],
  ];
  stops.forEach(([at, col]) => grd.addColorStop(at, col));
  g.fillStyle = grd;
  g.fillRect(0, 0, 256, 256);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return new THREE.Sprite(new THREE.SpriteMaterial({ map: t, blending: THREE.AdditiveBlending, depthWrite: false }));
}

/** Colour, size on screen (px across), ring and cloud bands for each planet. */
export const PLANET_LOOK: Record<string, { color: number; px: number; ring?: boolean; bands?: number }> = {
  Mercury: { color: 0x9c948a, px: 6 },
  Venus: { color: 0xe3c58f, px: 8 },
  Earth: { color: 0x4f8fd9, px: 9 },
  Mars: { color: 0xc8663f, px: 7 },
  Jupiter: { color: 0xd6b08a, px: 15, bands: 1 },
  Saturn: { color: 0xe2cf9f, px: 13, ring: true, bands: 0.5 },
  Uranus: { color: 0x9fdcde, px: 10 },
  Neptune: { color: 0x5278e0, px: 10 },
};

const PLANET_SPRITE = 2.6; // sprite width / sphere width: room for the ring and the halo

/**
 * Planets as small shaded spheres: lit from the Sun with a soft terminator, a thin
 * atmosphere halo, bands on the gas giants and a ring for Saturn. Sizes are symbolic.
 * Earth wears NASA's Blue Marble (with clouds) and a blue atmosphere rim; the others keep shaded
 * colours with limb darkening. Attributes: color (vec3), look (px across, ring 0/1, band strength),
 * earth (0/1).
 */
export function planetMaterial(px: number, earthUrl: string): THREE.ShaderMaterial {
  const m = new THREE.ShaderMaterial({
    uniforms: { uPx: { value: px }, uEarth: { value: null }, uHasEarth: { value: 0 }, uSpin: { value: 0 } },
    vertexShader: /* glsl */ `
      #include <common>
      #include <logdepthbuf_pars_vertex>
      attribute vec3 color;
      attribute vec3 look;
      attribute float earth;
      uniform float uPx;
      varying vec3 vC;
      varying vec3 vSun;   // direction to the Sun, view space
      varying vec3 vPole;  // the planet's north pole, view space
      varying vec3 vLook;  // 1 px in sphere units, ring, bands
      varying vec3 vEastA; // two axes of the planet's equator, view space (for Earth's map)
      varying vec3 vEastB;
      varying float vEarth;
      varying float vLod;  // mip level for Earth's map at this size (picked by hand: no seam where it wraps)
      void main() {
        vec4 mv = modelViewMatrix * vec4(position, 1.0);
        gl_Position = projectionMatrix * mv;
        #include <logdepthbuf_vertex>
        vSun = normalize((modelViewMatrix * vec4(0.0, 0.0, 0.0, 1.0)).xyz - mv.xyz);
        // ringed planets are tilted so the ring opens up; Earth leans by its 23.4 degrees
        vec3 pole = mix(vec3(0.0, 1.0, 0.0), vec3(0.42, 0.9, 0.12), look.y);
        if (earth > 0.5) pole = vec3(0.0, 0.9175, -0.3978); // ecliptic (0, 0.398, 0.917)
        vPole = normalize(mat3(modelViewMatrix) * pole);
        vec3 a = normalize(cross(pole, vec3(0.0, 0.0, 1.0)));
        vEastA = normalize(mat3(modelViewMatrix) * a);
        vEastB = normalize(mat3(modelViewMatrix) * cross(pole, a));
        vEarth = earth;
        float across = look.x * clamp(1.2 / length(mv.xyz), 1.0, 2.6);
        gl_PointSize = across * ${PLANET_SPRITE.toFixed(1)} * uPx;
        vC = color;
        vLook = vec3(1.5 / (across * uPx), look.y, look.z);
        vLod = max(0.0, log2(1024.0 / (across * uPx * 2.0)));
      }`,
    fragmentShader: /* glsl */ `
      #include <common>
      #include <logdepthbuf_pars_fragment>
      uniform sampler2D uEarth;
      uniform float uHasEarth;
      uniform float uSpin;
      varying vec3 vC;
      varying vec3 vSun;
      varying vec3 vPole;
      varying vec3 vLook;
      varying vec3 vEastA;
      varying vec3 vEastB;
      varying float vEarth;
      varying float vLod;
      void main() {
        #include <logdepthbuf_fragment>
        vec2 q = vec2(gl_PointCoord.x - 0.5, 0.5 - gl_PointCoord.y) * 2.0 * ${PLANET_SPRITE.toFixed(1)}; // sphere radius = 1
        float r = length(q);
        float disc = 1.0 - smoothstep(1.0 - vLook.x, 1.0 + vLook.x, r);
        vec3 n = vec3(q, sqrt(max(0.0, 1.0 - r * r)));
        float sunDot = dot(n, vSun);
        float lit = smoothstep(-0.2, 0.55, sunDot);
        float band = 1.0 - vLook.z * 0.24 * (0.5 + 0.5 * sin(dot(n, vPole) * 13.0));
        vec3 base = vC * band;
        bool isEarth = vEarth > 0.5;
        if (isEarth && uHasEarth > 0.5) {
          float lat = asin(clamp(dot(n, vPole), -1.0, 1.0));
          float lon = atan(dot(n, vEastB), dot(n, vEastA)) + uSpin;
          base = texture2DLodEXT(uEarth, vec2(fract(lon / 6.2831853), 0.5 + lat / 3.1415927), vLod).rgb * 1.15;
        }
        // limb darkening: the edge of the disc is a little darker than its middle
        float limb = mix(0.72, 1.0, n.z);
        vec3 col = base * limb * (0.035 + 0.965 * lit) + vC * pow(r, 5.0) * lit * 0.25;
        // thin halo, brighter on the sunlit side
        float halo = exp(-(max(r, 1.0) - 1.0) * 4.5) * 0.2 * (0.35 + 0.65 * smoothstep(-0.6, 0.6, dot(normalize(vec3(q, 0.0)), vSun)));
        vec3 haloC = vC;
        if (isEarth) {
          // Earth's atmosphere: a blue rim on the day side, inside the disc and just outside it
          vec3 sky = vec3(0.42, 0.68, 1.0);
          float day = smoothstep(-0.25, 0.4, sunDot);
          col += sky * pow(1.0 - n.z, 2.5) * 0.85 * day * disc;
          halo = exp(-(max(r, 1.0) - 1.0) * 6.0) * 0.55 * (0.2 + 0.8 * smoothstep(-0.5, 0.5, dot(normalize(vec3(q, 0.0)), vSun)));
          haloC = sky;
        }
        vec4 o = vec4(col * disc + haloC * halo * (1.0 - disc), disc + halo * (1.0 - disc));
        if (vLook.y > 0.5 && abs(vPole.z) > 0.03) {
          // where the line of sight crosses the ring plane
          float z = -(q.x * vPole.x + q.y * vPole.y) / vPole.z;
          float rho = length(vec3(q, z));
          float ra = smoothstep(1.3, 1.42, rho) * (1.0 - smoothstep(2.2, 2.32, rho)) * (0.5 + 0.2 * sin(rho * 20.0));
          vec4 ring = vec4(vC * 0.95 * ra, ra);
          o = z > 0.0 || r > 1.0 ? ring + o * (1.0 - ra) : o + ring * (1.0 - o.a);
        }
        if (o.a < 0.003) discard;
        gl_FragColor = o;
      }`,
    transparent: true,
    premultipliedAlpha: true,
    depthWrite: false,
  });
  new THREE.TextureLoader().load(earthUrl, (t) => {
    t.wrapS = THREE.RepeatWrapping;
    t.minFilter = THREE.LinearMipmapLinearFilter;
    m.uniforms.uEarth.value = t;
    m.uniforms.uHasEarth.value = 1;
  });
  return m;
}

/**
 * Rewind objects: a soft round dot with a glow; comets get a short tail away from the Sun.
 * Finds breathe: a soft halo ring swells out of the dot and fades, every few seconds (a still glow
 * under reduced motion). Attributes: color (vec3), size (px across), tail (0/1), fade (0..1, for
 * layers switching on and off), pulse (0 = none, else a 0..1 phase offset).
 */
export function rewindMaterial(px: number, motion = true): THREE.ShaderMaterial {
  return new THREE.ShaderMaterial({
    uniforms: { uPx: { value: px }, uTime: { value: 0 }, uMotion: { value: motion ? 1 : 0 } },
    vertexShader: /* glsl */ `
      #include <common>
      #include <logdepthbuf_pars_vertex>
      attribute vec3 color;
      attribute float size;
      attribute float tail;
      attribute float fade;
      attribute float pulse;
      uniform float uPx;
      varying vec3 vC;
      varying vec2 vDisc;
      varying vec3 vTail;
      varying float vFade;
      varying float vPulse;
      ${TAIL_VERT}
      void main() {
        vec4 mv = modelViewMatrix * vec4(position, 1.0);
        gl_Position = projectionMatrix * mv;
        #include <logdepthbuf_vertex>
        vTail = tail > 0.5 ? tailOf(mv.xyz, length(position)) : vec3(0.0);
        float sprite = vTail.z > 0.02 ? size * 10.0 : size * 4.0;
        gl_PointSize = fade > 0.003 ? sprite * uPx : 0.0;
        vC = color;
        vFade = fade;
        vPulse = pulse;
        vDisc = vec2(size / sprite, 1.5 / (sprite * uPx));
      }`,
    fragmentShader: /* glsl */ `
      #include <common>
      #include <logdepthbuf_pars_fragment>
      varying vec3 vC;
      varying vec2 vDisc;
      varying vec3 vTail;
      varying float vFade;
      varying float vPulse;
      uniform float uTime;
      uniform float uMotion;
      ${SPRITE_FRAG}
      void main() {
        #include <logdepthbuf_fragment>
        vec2 p = spriteUv();
        float r = length(p);
        if (r > 1.0) discard;
        float s = softDisc(r, vDisc.x, vDisc.y) + cometTail(p, vTail, vDisc.x);
        if (vPulse > 0.0) {
          // a ring that swells from the dot to the sprite edge and fades, every 2.8 s
          float ph = fract(uTime / 2.8 + vPulse);
          // in dot radii, so a comet's wider sprite (room for its tail) gets the same ring
          float rr = vDisc.x * mix(1.2, 3.7, ph);
          float w = vDisc.x * (0.2 + 0.24 * ph);
          float ring = (1.0 - ph) * (1.0 - ph) * exp(-(r - rr) * (r - rr) / (w * w)) * 0.5;
          float glow = 0.16 * exp(-r * r / (vDisc.x * vDisc.x * 1.9));
          s += uMotion * ring + glow * mix(1.0, 0.75 + 0.25 * sin(uTime * 2.244 + vPulse * 6.28), uMotion);
        }
        s *= vFade;
        gl_FragColor = vec4(vC * s, min(1.0, s));
      }`,
    transparent: true,
    premultipliedAlpha: true,
    depthWrite: false,
  });
}
