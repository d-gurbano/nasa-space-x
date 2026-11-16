// Guided rewind: frame Earth and the object's whole orbit, run the clock back to just before a
// SPHEREx photo, then play forward so the flash (beam + photo card) happens on its own and the
// clock keeps going.
import type { FlashEvent } from './lib/types';
import type { Scene } from './scene/Scene';
import type { FlashFx } from './scene/flash';
import { eclToThree } from './scene/asteroids';
import { isPhone, reducedMotion, store } from './state';

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

/**
 * The tour's view of the flash: the object's whole orbit with Earth's, never a dive into empty
 * space. The photo card covers the right side on a wide screen, so the view moves left of it.
 */
export function frameFlash(scene: Scene, f: FlashEvent): number {
  scene.setViewShift(isPhone ? 0 : 170, 0);
  const at = scene.rewindPositionAt(f.slug, f.mjd) ?? eclToThree(f.object_xyz_au);
  return scene.frameTour(f.slug, at, eclToThree(f.spherex_xyz_au));
}

const CARD_MS = 8500; // how long the tour holds the photo card while the clock plays on

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

  // only this photo may flash, so the card always matches the clock
  flash.only = f;
  scene.tour = f.slug;
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
    // the flash fires as the clock passes the photo; the clock keeps playing while the card is up
    const until = (ok: () => boolean) =>
      new Promise<void>((resolve) => {
        const watch = () => (cancelled || ok() ? resolve() : requestAnimationFrame(watch));
        requestAnimationFrame(watch);
      });
    await until(() => store.mjd >= f.mjd || !store.playing);
    const t0 = performance.now();
    await until(() => performance.now() - t0 > CARD_MS);
  })().finally(() => {
    stopOn.forEach((t) => window.removeEventListener(t, onInput, { capture: true }));
    if (flash.only === f) flash.only = null;
    scene.tour = null;
    if (!store.selected) scene.setViewShift(0, 0);
  });
  return { cancel, done };
}
