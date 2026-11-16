// Games: a small hub with three games about how Rewind works, each opening on the same page.
//   Tune the Rewind   shift and stack real photos by hand until the asteroid appears
//   Rainbow Detective match an object's 102-colour fingerprint to what it is made of
//   Where will it be? guess where a find goes next, and see what the old photos change
import '../styles/page-detectives.css';
import '../styles/page-games.css';
import { esc } from '../ui/dom';
import type { View } from './page';


interface GameDef {
  id: string;
  title: string;
  promise: string;
  level: string;
  preview: string;
  load: () => Promise<View>;
}

// tiny looping previews, drawn in SVG and moved with CSS
const stars = [[22, 30], [150, 22], [96, 64], [40, 96], [170, 88], [128, 108], [70, 18]].map(([x, y]) => `<circle class="pv-star" cx="${x}" cy="${y}" r="1.4"/>`).join('');
const PREVIEW = {
  tune: `<svg viewBox="0 0 200 120" aria-hidden="true">${stars}
    <g class="pv-ghosts"><circle cx="70" cy="60" r="5"/><circle cx="100" cy="60" r="5"/><circle cx="130" cy="60" r="5"/></g>
    <circle class="pv-pop" cx="100" cy="60" r="7"/><circle class="pv-lock" cx="100" cy="60" r="16"/>
    <g class="pv-dial" transform="translate(172 92)"><circle r="16"/><line y2="-12"/></g></svg>`,
  rainbow: `<svg viewBox="0 0 200 120" aria-hidden="true">
    <g class="pv-bar">${Array.from({ length: 34 }, (_, i) => `<rect x="${14 + i * 5.2}" y="20" width="5.4" height="16" style="fill:hsl(${Math.round(268 * (1 - i / 33))} 92% 60%);--i:${i}"/>`).join('')}</g>
    <path class="pv-spec" d="M14 88C30 78 38 70 48 80S62 98 76 86 104 66 122 70 138 64 146 84 158 92 168 70 180 60 186 62"/>
    <rect class="pv-band" x="36" y="48" width="26" height="62" rx="4"/></svg>`,
  where: `<svg viewBox="0 0 200 120" aria-hidden="true">
    <path class="pv-orbit" d="M10 104C50 40 120 20 192 34"/>
    <circle class="pv-sun" cx="150" cy="106" r="7"/>
    <circle class="pv-k" cx="30" cy="80" r="4"/><circle class="pv-k" cx="62" cy="54" r="4"/><circle class="pv-k" cx="100" cy="38" r="4"/>
    <g class="pv-guess"><circle cx="146" cy="30" r="9"/><circle class="in" cx="146" cy="30" r="2.5"/></g></svg>`,
};

const GAMES: GameDef[] = [
  { id: 'tune', title: 'Tune the Rewind', promise: 'Shift real SPHEREx images along an asteroid’s motion until it appears.', level: 'Easy to start', preview: PREVIEW.tune, load: () => import('./games/tune').then((m) => m.tuneGame) },
  { id: 'rainbow', title: 'Rainbow Detective', promise: 'Match a reflectance spectrum to a rocky, carbon-rich, metal-rich or icy surface.', level: 'Quick', preview: PREVIEW.rainbow, load: () => import('./games/rainbow').then((m) => m.rainbowGame) },
  { id: 'where', title: 'Where will it be?', promise: 'Guess where an object will be next. Then see how much its earlier SPHEREx positions shrink the uncertainty.', level: 'Medium', preview: PREVIEW.where, load: () => import('./games/where').then((m) => m.whereGame) },
];

/** The open game lives in ?game= (before the hash), so a link to one game can be shared. */
function remember(id: string | null) {
  const u = new URL(location.href);
  if (id) u.searchParams.set('game', id);
  else u.searchParams.delete('game');
  history.replaceState(history.state, '', u);
}

export const detectivesView: View = async (body, ctx) => {
  const shell = body.parentElement!;
  shell.classList.add('gm-on');
  body.innerHTML = `
    <div class="gm">
      <header class="gm-head">
        <h1 class="gm-h">Three games, one for each step of the pipeline</h1>
        <p class="gm-lead">Each game is one step that Rewind runs on real data. You stack images along a motion (shift-and-stack), match a spectrum to a surface type, and predict where an orbit goes.</p>
      </header>
      <nav class="gm-tabs" role="tablist" aria-label="Games" hidden>
        <button role="tab" data-game="hub" class="gm-tab gm-tab-all" aria-selected="false">All games</button>
        ${GAMES.map((g) => `<button role="tab" data-game="${g.id}" class="gm-tab" aria-selected="false">${esc(g.title)}</button>`).join('')}
      </nav>
      <div class="gm-hub">
        ${GAMES.map((g, i) => `
          <div class="gm-slot"><button class="gm-card gm-card-${g.id}" data-game="${g.id}" style="--i:${i}">
            <span class="gm-card-pv">${g.preview}</span>
            <span class="gm-card-txt">
              <span class="gm-card-level mono"><b>0${i + 1}</b>${esc(g.level)}</span>
              <span class="gm-card-t">${esc(g.title)}</span>
              <span class="gm-card-p">${esc(g.promise)}</span>
              <span class="gm-card-go">Play<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg></span>
            </span>
          </button></div>`).join('')}
      </div>
      <div class="gm-mount" hidden></div>
    </div>`;
  const q = <T extends Element = HTMLElement>(s: string) => body.querySelector(s) as T;
  const head = q('.gm-head'), tabs = q('.gm-tabs'), hub = q('.gm-hub'), mount = q('.gm-mount');
  let cleanup: (() => void) | void, turn = 0;

  const open = async (id: string) => {
    const me = ++turn;
    cleanup?.();
    cleanup = undefined;
    const g = GAMES.find((x) => x.id === id);
    head.hidden = hub.hidden = !!g;
    tabs.hidden = mount.hidden = !g;
    tabs.querySelectorAll('button').forEach((b) => b.setAttribute('aria-selected', String(b.dataset.game === id)));
    remember(g ? g.id : null);
    document.title = `${g ? g.title : 'Games'} · Rewind`;
    mount.innerHTML = '';
    body.closest('.page')?.scrollTo(0, 0);
    if (!g) return;
    // each game gets a fresh box, so a slow one that finishes late cannot draw over the next
    const box = document.createElement('div');
    box.className = `gm-game gm-game-${g.id}`;
    box.innerHTML = `<p class="muted">Loading the game.</p>`;
    mount.append(box);
    try {
      const view = await g.load();
      if (me !== turn) return;
      box.innerHTML = '';
      const done = await view(box, ctx);
      if (me !== turn) done?.();
      else cleanup = done;
    } catch (e) {
      if (me === turn) box.innerHTML = `<p class="warn">This game did not load (${esc(e instanceof Error ? e.message : e)}).</p>`;
    }
  };

  body.addEventListener('click', (e) => {
    const b = (e.target as Element).closest<HTMLElement>('[data-game]');
    if (b) void open(b.dataset.game!);
  });

  const first = new URLSearchParams(location.search).get('game');
  void open(GAMES.some((g) => g.id === first) ? first! : 'hub');
  return () => {
    turn++;
    cleanup?.();
    remember(null);
    shell.classList.remove('gm-on');
  };
};
