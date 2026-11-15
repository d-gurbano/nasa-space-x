// Guided rewind: frame Earth and the object, run the clock back to just before a SPHEREx
// photo, then play forward so the flash (beam + photo card) happens on its own.
import type { FlashEvent } from './lib/types';
import type { Scene } from './scene/Scene';
import type { FlashFx } from './scene/flash';
import { eclToThree } from './scene/asteroids';
import { reducedMotion, store } from './state';

export interface Guided {
  cancel(): void;
  done: Promise<void>;
}

/** Animate the clock from its current value to `to` over `ms`, with ease-out. */
export function tweenTime(to: number, ms: number, isCancelled: () => boolean, mute?: FlashFx): Promise<void> {
  // other photo dates passed on the way should not pop up their own flashes
  if (mute) mute.muted = true;
  return new Promise<void>((resolve) => {
    const from = store.mjd, t0 = performance.now();
    store.setPlaying(false);
    const step = () => {
      if (isCancelled()) return resolve();
      const k = Math.min(1, (performance.now() - t0) / ms);
      store.setTime(from + (to - from) * (1 - Math.pow(1 - k, 3)));
      if (k < 1) requestAnimationFrame(step);
      else resolve();
    };
    requestAnimationFrame(step);
  }).finally(() => {
    if (mute) requestAnimationFrame(() => (mute.muted = false));
  });
}

export const sleep = (ms: number) => new Promise<void>((r) => setTimeout(r, ms));

/** Camera position that shows both SPHEREx (Earth) and the object at the flash. */
export function frameFlash(scene: Scene, f: FlashEvent, extra = 1) {
  const a = eclToThree(f.spherex_xyz_au), b = eclToThree(f.object_xyz_au);
  const mid = a.clone().add(b).multiplyScalar(0.5);
  const d = Math.max(0.9, a.distanceTo(b) * 1.35 + 0.35) * extra;
  scene.flyTo(mid, d);
}

export function guidedRewind(scene: Scene, flash: FlashFx, f: FlashEvent, lead = 18): Guided {
  let cancelled = false;
  const cancel = () => {
    cancelled = true;
  };
  // any deliberate input from the visitor ends the tour
  const stopOn = ['pointerdown', 'wheel', 'keydown'] as const;
  const onInput = (e: Event) => {
    if ((e.target as HTMLElement)?.closest?.('.photocard, .captions')) return;
    cancel();
  };
  stopOn.forEach((t) => window.addEventListener(t, onInput, { capture: true, once: true }));

  flash.only = f;
  const done = (async () => {
    if (reducedMotion) {
      frameFlash(scene, f);
      store.setPlaying(false);
      store.setTime(f.mjd);
      flash.trigger(f);
      return;
    }
    frameFlash(scene, f);
    // rewind the clock (visibly) to a little before the photo
    await tweenTime(f.mjd - lead, 2400, () => cancelled, flash);
    if (cancelled) return;
    await sleep(250);
    store.speedIndex = 1; // 7 days per second
    store.direction = 1;
    store.setPlaying(true);
    // stop right at the photo so the card can be read
    await new Promise<void>((resolve) => {
      const watch = () => {
        if (cancelled || !store.playing) return resolve();
        if (store.mjd >= f.mjd + 0.3) {
          store.setPlaying(false);
          return resolve();
        }
        requestAnimationFrame(watch);
      };
      requestAnimationFrame(watch);
    });
  })().finally(() => {
    stopOn.forEach((t) => window.removeEventListener(t, onInput, { capture: true }));
    flash.only = null;
  });
  return { cancel, done };
}
