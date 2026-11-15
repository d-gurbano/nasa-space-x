// Opening: a calm headline over the live scene with one action, then three short captions with Skip.
// While the headline is up (body.hero) the time bar, search and scene labels stay out of the way.
import { el } from './dom';
import { icon, stat } from './components';
import { reducedMotion } from '../state';

const CAPTIONS = [
  'These dots are real asteroids and comets, on their real orbits.',
  'Drag time backward.',
  'Watch for the flash: SPHEREx saw it before anyone knew.',
];

export interface OpeningHooks {
  /** Numbers under the headline, straight from the data: [number, label, highlight]. */
  stats: [string, string, boolean?][];
  /** Replaces the third caption, e.g. when there is no sure find to promise yet. */
  lastCaption?: string;
  /** Phones load the heavy scene only after Start. Resolves when ready. */
  start: () => Promise<void>;
  onCaption?: (i: number) => void;
  onDone: () => void;
}

export function mountOpening(root: HTMLElement, hooks: OpeningHooks) {
  const o = el('section', { class: 'opening', 'aria-label': 'Introduction' });
  o.innerHTML = `
    <div class="op-inner">
      <p class="op-kicker kicker" style="--i:0">NASA Space Apps 2026 / SPHEREx</p>
      <h1 class="op-title" style="--i:1">Every discovery<br>has a <em>past.</em></h1>
      <p class="op-line" style="--i:2">When a new comet or asteroid is discovered, Rewind looks for it in older NASA SPHEREx photos, taken before anyone knew it was there. Then its future path becomes more certain.</p>
      <div class="op-actions" style="--i:3">
        <button class="btn btn-primary op-start">Start the rewind${icon('arrow')}</button>
        <span class="op-status" aria-live="polite"></span>
      </div>
      <dl class="stats op-stats" style="--i:4">${hooks.stats.map(([num, label, gold]) => stat(num, label, gold ? 'stat-gold' : '')).join('')}</dl>
    </div>`;
  document.body.classList.add('hero');
  root.appendChild(o);
  const btn = o.querySelector('.op-start') as HTMLButtonElement;
  const status = o.querySelector('.op-status') as HTMLElement;

  btn.addEventListener('click', async () => {
    btn.disabled = true;
    status.textContent = 'Loading orbits...';
    await hooks.start();
    status.textContent = '';
    document.body.classList.remove('hero');
    o.classList.add('op-out');
    setTimeout(() => o.remove(), reducedMotion ? 0 : 600);
    runCaptions(root, hooks);
  });
}

function runCaptions(root: HTMLElement, hooks: OpeningHooks) {
  const c = el('div', { class: 'captions', role: 'status' });
  c.innerHTML = `<p class="cap-text"></p><div class="cap-foot"><span class="cap-dots" aria-hidden="true">${CAPTIONS.map(() => '<i></i>').join('')}</span><button class="cap-skip">Skip</button></div>`;
  root.appendChild(c);
  const text = c.querySelector('.cap-text') as HTMLElement;
  const dots = c.querySelectorAll('.cap-dots i');
  let i = -1;
  let timer = 0;
  const finish = () => {
    clearTimeout(timer);
    c.classList.add('cap-out');
    setTimeout(() => c.remove(), 400);
    hooks.onDone();
  };
  const next = () => {
    i++;
    if (i >= CAPTIONS.length) return finish();
    text.classList.remove('cap-in');
    void text.offsetWidth;
    text.textContent = i === CAPTIONS.length - 1 && hooks.lastCaption ? hooks.lastCaption : CAPTIONS[i];
    text.classList.add('cap-in');
    dots.forEach((d, k) => d.classList.toggle('on', k <= i));
    hooks.onCaption?.(i);
    timer = window.setTimeout(next, i === 2 ? 6500 : 4200);
  };
  (c.querySelector('.cap-skip') as HTMLButtonElement).addEventListener('click', finish);
  next();
}
