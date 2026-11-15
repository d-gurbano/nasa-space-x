// Map-scale extras for the demo, added to the shared three.js scene: the object's orbit as a
// bright gold line, pulsing gold dots, and the SPHEREx beam from Earth to the object.
import * as THREE from 'three';
import { Line2 } from 'three/examples/jsm/lines/Line2.js';
import { LineGeometry } from 'three/examples/jsm/lines/LineGeometry.js';
import { LineMaterial } from 'three/examples/jsm/lines/LineMaterial.js';
import { orbitPolyline } from '../lib/kepler';
import { eclToThree } from '../scene/asteroids';
import type { Scene } from '../scene/Scene';

const GOLD = 0xffc35a;

function glowTexture(): THREE.Texture {
  const c = document.createElement('canvas');
  c.width = c.height = 64;
  const g = c.getContext('2d')!;
  const r = g.createRadialGradient(32, 32, 0, 32, 32, 32);
  r.addColorStop(0, 'rgba(255,240,200,1)');
  r.addColorStop(0.18, 'rgba(255,200,100,0.95)');
  r.addColorStop(0.45, 'rgba(255,170,60,0.25)');
  r.addColorStop(1, 'rgba(255,170,60,0)');
  g.fillStyle = r;
  g.fillRect(0, 0, 64, 64);
  return new THREE.CanvasTexture(c);
}

function line(width: number): { line: Line2; mat: LineMaterial } {
  const mat = new LineMaterial({ color: GOLD, linewidth: width, transparent: true, opacity: 0, blending: THREE.AdditiveBlending, depthWrite: false });
  const l = new Line2(new LineGeometry(), mat);
  l.frustumCulled = false;
  l.renderOrder = 6;
  return { line: l, mat };
}

export class DemoFx {
  private orbit = line(2.6);
  private beam = line(3.2);
  private tex = glowTexture();
  private pulses = new Map<string, THREE.Sprite>();
  private a = new THREE.Vector3();
  private b = new THREE.Vector3();

  constructor(private scene: Scene, private slug: string, finds: string[]) {
    const dot = scene.rewindDot(slug);
    if (dot) {
      const pts = orbitPolyline(dot.el, 512, 8).flatMap((v) => eclToThree(v).toArray());
      this.orbit.line.geometry.setPositions(pts);
    }
    this.beam.line.geometry.setPositions([0, 0, 0, 1, 0, 0]);
    for (const s of new Set([slug, ...finds])) {
      const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: this.tex, sizeAttenuation: false, transparent: true, opacity: 0, blending: THREE.AdditiveBlending, depthWrite: false }));
      sp.renderOrder = 7;
      this.pulses.set(s, sp);
      scene.scene.add(sp);
    }
    scene.scene.add(this.orbit.line, this.beam.line);
  }

  /** orbit, beam: 0..1 opacity; beamGrow: 0..1 of the way from Earth; hero/finds: pulse strength 0..1. */
  update(t: number, s: { orbit: number; beam: number; beamGrow: number; hero: number; finds: number }) {
    const [w, h] = this.scene.viewSize;
    this.orbit.mat.resolution.set(w, h);
    this.beam.mat.resolution.set(w, h);
    this.orbit.mat.opacity = s.orbit;
    this.beam.mat.opacity = s.beam;
    if (s.beam > 0 && this.scene.rewindPosition(this.slug, this.b)) {
      this.scene.earthPosition(this.a);
      const end = this.a.clone().lerp(this.b, Math.max(0.001, s.beamGrow));
      this.beam.line.geometry.setPositions([this.a.x, this.a.y, this.a.z, end.x, end.y, end.z]);
    }
    const beat = 0.5 + 0.5 * Math.sin(t * Math.PI * 2 * 0.9);
    for (const [slug, sp] of this.pulses) {
      const k = slug === this.slug ? Math.max(s.hero, s.finds) : s.finds;
      const m = sp.material as THREE.SpriteMaterial;
      m.opacity = k * (0.55 + 0.45 * beat);
      sp.visible = k > 0.001 && !!this.scene.rewindPosition(slug, sp.position);
      sp.scale.setScalar(0.022 + 0.018 * beat * k);
    }
  }

  dispose() {
    this.scene.scene.remove(this.orbit.line, this.beam.line, ...this.pulses.values());
  }
}
