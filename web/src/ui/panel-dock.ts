// A small dock over the 3D view while an object is open: back to the solar system, the two
// object framings (whole orbit, close-up) and the Before / After Rewind cloud with its real
// size in km.
import type { ObjectPage } from '../lib/types';
import type { Level } from '../scene/Scene';
import { plainDate } from '../lib/time';
import { reducedMotion } from '../state';
import { el, esc } from './dom';
import { uncText } from './panel';

export interface DockHooks {
  onView: (l: Level) => void;
  onCloud: (mode: 'before' | 'after') => void;
}

export interface Dock {
  show(p: ObjectPage | null, hasPath: boolean): void;
  hide(): void;
  setLevel(l: Level): void;
}

export function mountDock(parent: HTMLElement, hooks: DockHooks): Dock {
  const root = el('div', { class: 'dock', role: 'toolbar', 'aria-label': '3D view' });
  root.hidden = true;
  root.innerHTML = `
    <button class="dock-btn dock-back" data-view="system" aria-label="Solar system"><svg viewBox="0 0 16 16" aria-hidden="true"><path d="M10 3 5 8l5 5"/></svg><span class="dock-long">Solar system</span></button>
    <div class="dock-views seg seg-s" role="group">
      <button data-view="orbit" aria-pressed="true">Orbit</button>
      <button data-view="close" aria-pressed="false">Close-up</button>
    </div>
    <div class="dock-cloud" hidden>
      <span class="dock-sep" aria-hidden="true"></span>
      <div class="seg seg-s" role="group" aria-label="Position uncertainty before or after adding the SPHEREx positions">
        <button data-cloud="before" aria-pressed="true" title="Position uncertainty from the earlier observations only">Before</button>
        <button data-cloud="after" aria-pressed="false" title="Position uncertainty with the SPHEREx positions added">After<span class="dock-long"> Rewind</span></button>
      </div>
      <span class="dock-km"><strong class="mono"></strong><small></small></span>
    </div>`;
  parent.appendChild(root);
  const cloud = root.querySelector('.dock-cloud') as HTMLElement;
  const km = root.querySelector('.dock-km strong') as HTMLElement;
  const when = root.querySelector('.dock-km small') as HTMLElement;
  const views = root.querySelector('.dock-views') as HTMLElement;
  let before = 0, after = 0, shown = 0, anim = 0;

  // the number counts down (or up) to the new size, in step with the cloud
  const countTo = (to: number) => {
    cancelAnimationFrame(anim);
    const from = shown || to, t0 = performance.now();
    const step = () => {
      const k = reducedMotion ? 1 : Math.min(1, (performance.now() - t0) / 1600);
      shown = from + (to - from) * (1 - Math.pow(1 - k, 3));
      km.textContent = uncText(shown);
      if (k < 1) anim = requestAnimationFrame(step);
    };
    step();
  };

  root.querySelectorAll<HTMLButtonElement>('[data-view]').forEach((b) => b.addEventListener('click', () => hooks.onView(b.dataset.view as Level)));
  root.querySelectorAll<HTMLButtonElement>('[data-cloud]').forEach((b) =>
    b.addEventListener('click', () => {
      if (b.disabled) return;
      const mode = b.dataset.cloud as 'before' | 'after';
      root.querySelectorAll('[data-cloud]').forEach((x) => x.setAttribute('aria-pressed', String(x === b)));
      hooks.onCloud(mode);
      countTo(mode === 'after' ? after : before);
    }),
  );

  return {
    show(p, hasPath) {
      root.hidden = false;
      views.hidden = !hasPath;
      const c = p?.cloud;
      const b = c?.before_sigma_km_at, a = c?.after_sigma_km_at;
      cloud.hidden = !(c?.before?.length && b?.km != null);
      if (cloud.hidden || !b) return;
      before = b.km;
      after = c?.after && a?.km != null ? a.km : b.km;
      shown = 0;
      countTo(before);
      when.innerHTML = `position uncertainty${b.iso ? ` by ${esc(plainDate(b.iso))}` : ''}`;
      const afterBtn = root.querySelector('[data-cloud="after"]') as HTMLButtonElement;
      afterBtn.disabled = !(c?.after && a?.km != null);
      afterBtn.title = afterBtn.disabled ? 'There are no SPHEREx positions for this object yet' : '';
      root.querySelectorAll('[data-cloud]').forEach((x) => x.setAttribute('aria-pressed', String((x as HTMLElement).dataset.cloud === 'before')));
    },
    hide() {
      root.hidden = true;
      cancelAnimationFrame(anim);
    },
    setLevel(l) {
      root.querySelectorAll<HTMLButtonElement>('.dock-views [data-view]').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.view === l)));
    },
  };
}
