// The flash: when the clock passes a SPHEREx photo date, a short glowing beam runs
// from SPHEREx (at Earth) to the object, and a ring pulses on the object.
import * as THREE from 'three';
import type { Scene } from './Scene';
import { Line2 } from 'three/examples/jsm/lines/Line2.js';
import { LineGeometry } from 'three/examples/jsm/lines/LineGeometry.js';
import { LineMaterial } from 'three/examples/jsm/lines/LineMaterial.js';
import { eclToThree } from './asteroids';
import type { FlashEvent } from '../lib/types';
import { reducedMotion, store } from '../state';

const DURATION = 2.8; // seconds

function ringTexture(): THREE.Texture {
  const c = document.createElement('canvas');
  c.width = c.height = 128;
  const g = c.getContext('2d')!;
  g.strokeStyle = '#ffd98a';
  g.lineWidth = 7;
  g.beginPath();
  g.arc(64, 64, 52, 0, Math.PI * 2);
  g.stroke();
  return new THREE.CanvasTexture(c);
}

function dotTexture(): THREE.Texture {
  const c = document.createElement('canvas');
  c.width = c.height = 64;
  const g = c.getContext('2d')!;
  const grd = g.createRadialGradient(32, 32, 0, 32, 32, 32);
  grd.addColorStop(0, 'rgba(255,245,220,1)');
  grd.addColorStop(0.25, 'rgba(255,200,100,0.8)');
  grd.addColorStop(1, 'rgba(255,180,60,0)');
  g.fillStyle = grd;
  g.fillRect(0, 0, 64, 64);
  return new THREE.CanvasTexture(c);
}

export class FlashFx {
  private beam: Line2;
  private beamMat: LineMaterial;
  private photon: THREE.Sprite;
  private rings: THREE.Sprite[] = [];
  private active: { f: FlashEvent; t: number } | null = null;
  private prevMjd = store.mjd;
  /** While true, passing a photo date does not fire a flash (used during scripted time jumps). */
  muted = false;
  /** When set, only this photo fires (used by the guided rewind and the demo). */
  only: FlashEvent | null = null;
  /** Objects whose photos fire on their own while the clock runs. With hundreds of photos only the finds do; null = all. */
  auto: Set<string> | null = null;
  private a = new THREE.Vector3();
  private b = new THREE.Vector3();

  constructor(private scene: Scene, private flashes: FlashEvent[], private onFlash: (f: FlashEvent) => void) {
    // a screen-space thick line (3 px), so the beam reads at any zoom
    const g = new LineGeometry();
    g.setPositions([0, 0, 0, 1, 0, 0]);
    this.beamMat = new LineMaterial({ color: 0xffc35a, linewidth: 3, transparent: true, opacity: 0, blending: THREE.AdditiveBlending, depthWrite: false });
    this.beam = new Line2(g, this.beamMat);
    this.beam.frustumCulled = false;
    this.beam.renderOrder = 5;
    this.photon = new THREE.Sprite(new THREE.SpriteMaterial({ map: dotTexture(), sizeAttenuation: false, transparent: true, opacity: 0, blending: THREE.AdditiveBlending, depthWrite: false }));
    this.photon.scale.setScalar(0.05);
    const ringTex = ringTexture();
    for (let k = 0; k < 2; k++) {
      const r = new THREE.Sprite(new THREE.SpriteMaterial({ map: ringTex, sizeAttenuation: false, transparent: true, opacity: 0, blending: THREE.AdditiveBlending, depthWrite: false }));
      this.rings.push(r);
      scene.scene.add(r);
    }
    scene.scene.add(this.beam, this.photon);
    // explain the gold line while it is visible
    scene.labels.add({
      id: 'beam',
      text: 'SPHEREx line of sight',
      cls: 'label-beam',
      priority: 9.5,
      pos: (o) => (this.active && this.active.t < DURATION * 0.85 ? o.copy(this.a).lerp(this.b, 0.5) : null),
    });
    scene.addHook((dt) => this.tick(dt));
  }

  /** Play a flash now, regardless of the clock. */
  trigger(f: FlashEvent) {
    this.active = { f, t: 0 };
    this.onFlash(f);
  }

  private tick(dt: number) {
    const now = store.mjd;
    if (now !== this.prevMjd) {
      const lo = Math.min(now, this.prevMjd), hi = Math.max(now, this.prevMjd);
      // a big jump (e.g. "Today") should not fire every flash in between
      if (hi - lo < 120 && !this.muted) {
        const fires = (f: FlashEvent) => (this.only ? f === this.only : !this.auto || this.auto.has(f.slug));
        const crossed = this.flashes.filter((f) => f.mjd > lo && f.mjd <= hi && fires(f));
        const f = crossed[now > this.prevMjd ? crossed.length - 1 : 0];
        // one object photographed on several days in a row: let the flash that is running finish
        if (f && (this.only || this.active?.f.slug !== f.slug)) this.trigger(f);
      }
      this.prevMjd = now;
    }
    const act = this.active;
    if (!act) return;
    act.t += dt;
    const k = act.t / DURATION;
    if (k >= 1) {
      this.active = null;
      this.beamMat.opacity = 0;
      (this.photon.material as THREE.SpriteMaterial).opacity = 0;
      this.rings.forEach((r) => ((r.material as THREE.SpriteMaterial).opacity = 0));
      return;
    }
    this.scene.earthPosition(this.a);
    if (!this.scene.rewindPosition(act.f.slug, this.b)) {
      // no orbit for this object: use the positions stored with the flash event
      eclToThree(act.f.spherex_xyz_au, this.a);
      eclToThree(act.f.object_xyz_au, this.b);
    }
    this.beam.geometry.setPositions([this.a.x, this.a.y, this.a.z, this.b.x, this.b.y, this.b.z]);
    this.beamMat.resolution.set(innerWidth, innerHeight);
    // beam: quick rise, slow fade
    this.beamMat.opacity = reducedMotion ? 0.8 : Math.min(1, k * 8) * Math.pow(1 - k, 1.5);
    // photon travels SPHEREx -> object during the first 40 %
    const pk = Math.min(1, k / 0.4);
    this.photon.position.lerpVectors(this.a, this.b, reducedMotion ? 1 : 1 - Math.pow(1 - pk, 2));
    (this.photon.material as THREE.SpriteMaterial).opacity = reducedMotion ? 0 : pk < 1 ? 1 : 0;
    this.rings.forEach((r, i) => {
      const rk = reducedMotion ? 0.5 : Math.max(0, (k - 0.35 - i * 0.18) / 0.5);
      const m = r.material as THREE.SpriteMaterial;
      r.position.copy(this.b);
      r.scale.setScalar(0.02 + rk * 0.09);
      m.opacity = rk > 0 && rk < 1 ? (1 - rk) * 0.9 : 0;
    });
  }
}
