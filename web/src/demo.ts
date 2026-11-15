// ?demo=1: a scripted 25-second camera and time path for screen recording.
// Overview -> rewind -> flash -> fly to the object -> Before/After cloud. No UI chrome except a
// lower third (date kicker over a serif caption), large km numbers, and the SPHEREx photo card
// (the point of the story).
// The object is picked from index.json each time (see pickShowcase), so the wording follows
// the verdict: a FOUND object is "photographed", a HINT is only "may have caught it".
import * as THREE from 'three';
import type { ObjectPage } from './lib/types';
import { knownSince, type Showcase } from './lib/rank';
import type { Scene } from './scene/Scene';
import type { UncertaintyCloud } from './scene/cloud';
import type { FlashFx } from './scene/flash';
import { frameFlash, sleep, tweenTime } from './guided';
import { plainDate } from './lib/time';
import { el, plural } from './ui/dom';
import { kmText } from './ui/panel';
import { store } from './state';

export async function runDemo(o: {
  scene: Scene;
  cloud: UncertaintyCloud;
  flash: FlashFx;
  showcase: Showcase | null;
  page: (slug: string) => Promise<ObjectPage>;
  ui: HTMLElement;
}) {
  const { scene, cloud, flash, showcase: sc, ui } = o;
  document.body.classList.add('demo', 'explored');
  const cap = el('div', { class: 'demo-cap' });
  cap.innerHTML = `<div class="demo-km" hidden><span class="demo-km-label"></span><span class="demo-km-num"></span></div><span class="demo-date"></span><span class="demo-text"></span>`;
  ui.appendChild(cap);
  const date = cap.querySelector('.demo-date') as HTMLElement;
  const text = cap.querySelector('.demo-text') as HTMLElement;
  const km = cap.querySelector('.demo-km') as HTMLElement;
  const setKm = (label: string, value: string, gold: boolean) => {
    km.hidden = false;
    km.classList.toggle('gold', gold);
    km.classList.remove('demo-in');
    void km.offsetWidth;
    km.classList.add('demo-in');
    (km.querySelector('.demo-km-label') as HTMLElement).textContent = label;
    (km.querySelector('.demo-km-num') as HTMLElement).textContent = value;
  };
  let ended = false;
  store.on(() => !ended && (date.textContent = plainDate(store.mjd)));
  const say = (s: string) => {
    text.classList.remove('demo-in');
    void text.offsetWidth;
    text.textContent = s;
    text.classList.add('demo-in');
  };
  const t0 = performance.now();
  const at = (sec: number) => sleep(Math.max(0, t0 + sec * 1000 - performance.now()));

  // 0 s: overview, today
  store.setPlaying(false);
  store.setTime(store.today);
  scene.camera.position.set(0, 2.4, 3.9);
  scene.controls.target.set(0, 0, 0);
  scene.autoRotate = true;
  date.textContent = plainDate(store.mjd);
  say('These dots are real asteroids and comets, on their real orbits.');
  if (!sc) {
    await at(4);
    say('Rewind results are still coming in. Check back soon.');
    return;
  }
  const f = sc.flash;
  flash.only = f; // other photos on the way stay quiet
  const p = await o.page(f.slug);
  const days = Math.floor(knownSince(sc.object) - f.mjd);

  // 3.5 s: rewind the clock and fly to Earth and the object
  await at(3.5);
  scene.autoRotate = false;
  say(`${p.name} was discovered on ${plainDate(sc.object.discovered.iso)}. Let us rewind.`);
  frameFlash(scene, f, 1.1);
  await tweenTime(f.mjd - 21, 3200, () => false, flash);

  // 7.2 s: play forward into the flash
  await at(7.2);
  say(
    sc.sure
      ? `SPHEREx photographed it ${plural(days, 'day')} before anyone knew.`
      : `${plural(days, 'day')} before its discovery, SPHEREx may have caught it: a faint hint, still being checked.`,
  );
  store.speedIndex = 1;
  store.direction = 1;
  store.setPlaying(true);
  await new Promise<void>((r) => {
    const w = () => (store.mjd >= f.mjd + 0.2 ? (store.setPlaying(false), r()) : requestAnimationFrame(w));
    requestAnimationFrame(w);
  });

  // 13.5 s: fly to the object (no orbit line, it only distracts here) and show its possible positions
  await at(13.5);
  document.querySelector('.photocard')?.classList.remove('pc-in');
  scene.highlight(f.slug, false);
  cloud.show(p);
  const b = p.cloud?.before_sigma_km_at, a = p.cloud?.after_sigma_km_at;
  const cloudDate = b?.iso ? Date.parse(b.iso) / 86400000 + 40587 : store.mjd + 400;
  say('Its future path is uncertain. Each dot is one possible position.');
  const tmp = new THREE.Vector3();
  const follow = () => scene.rewindPosition(f.slug, tmp);
  const pos = scene.rewindPosition(f.slug) ?? new THREE.Vector3();
  const side = scene.sideView(f.slug) ?? undefined;
  scene.flyTo(pos, Math.min(0.6, Math.max(0.002, cloud.extentAt(p, cloudDate) * 2.4)), follow, side);
  await tweenTime(cloudDate, 3600, () => false, flash);
  // re-frame on the real cloud so it fills about half the screen width
  const fit = scene.fitDistance(cloud.beforePoints(), 0.55);
  if (fit) scene.flyTo(scene.rewindPosition(f.slug) ?? pos, fit, follow, scene.camera.position.clone().sub(scene.controls.target));

  // 19 s: before
  await at(19);
  if (b) setKm('Before Rewind', kmText(b.km), false);
  say(`Possible positions on ${plainDate(cloudDate)}, spread over about ${b ? kmText(b.km) : 'a wide area'}.`);

  // 20.6 s: after, only if the engine measured it
  await at(20.6);
  if (a && p.cloud?.after) {
    cloud.setMode('after');
    setKm('After Rewind', kmText(a.km), true);
    // say only what the numbers say: how much smaller the cloud is, and the engine's own
    // "right after discovery" scenario when it has one (computed, and called that)
    const shrink = b && b.km > 0 ? 1 - a.km / b.km : 0;
    const early = p.impact?.at_discovery_scenario;
    say(
      shrink >= 0.5
        ? 'Old SPHEREx photos, a much sharper future.'
        : `With the old SPHEREx photos the cloud is ${shrink >= 0.01 ? `${Math.round(shrink * 100)}% smaller` : 'about the same size'} today.` +
            (early?.factor != null && early.converged !== false && early.factor >= 1.5 ? ` Right after discovery it would have been ${early!.factor.toFixed(1)} times smaller (computed scenario).` : ''),
    );
  } else {
    say('Rewind is still checking these photos. If the hint holds, adding them would shrink this cloud.');
  }

  // 24 s: end card
  await at(24);
  km.hidden = true;
  cap.classList.add('demo-end');
  ended = true;
  date.textContent = 'Rewind';
  say('');
  text.innerHTML = 'Every discovery has a <em>past.</em>';
}
