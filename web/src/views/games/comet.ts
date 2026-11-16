// Comet or asteroid?: each round shows a real SPHEREx stack and the object's measured spectrum points.
// The player says comet or asteroid; the answer is the object's real kind. The reveal explains what
// the image and the points show, and claims extra light at 4.26 µm (CO2) only where the points show it.
import '../../styles/game-comet.css';
import { icon } from '../../ui/components';
import { esc, provenance } from '../../ui/dom';
import { confetti } from './confetti';
import type { View } from '../page';
import { explain, kindPhrase, nameNote, pickRounds, ux, yRange, type CometData, type CometRound, type Truth } from './comet-logic';

const ANS: { id: Truth; name: string; tell: string; key: string; icon: string }[] = [
  { id: 'comet', name: 'Comet', tell: 'fuzzy glow, maybe extra light at 4.26 µm', key: '1', icon: '<circle cx="15.5" cy="8.5" r="3.5"/><path d="M12.5 10.5 4 17M13.5 12 7 19.5M11 9 3.5 12.5"/>' },
  { id: 'asteroid', name: 'Asteroid', tell: 'sharp point of reflected sunlight', key: '2', icon: '<path d="M4.5 14.5 7 7.5l6-3 5.5 4 1 6.5-5.5 4.5-7-1z"/><path d="m7 7.5 4.5 5 7-4M11.5 12.5 9.5 19"/>' },
];

// chart geometry, in SVG units
const W = 360, H = 200, X0 = 34, X1 = 348, Y0 = 16, Y1 = 162;
const X = (um: number) => X0 + ux(um) * (X1 - X0);
const TICKS = [1, 2, 3, 4, 5];

function chart(pts: CometRound['points']): string {
  const [lo, hi] = yRange(pts);
  const Y = (v: number) => Y1 - ((Math.max(lo, Math.min(hi, v)) - lo) / (hi - lo)) * (Y1 - Y0);
  const co2 = X(4.26);
  return `<svg class="cm-svg" viewBox="0 0 ${W} ${H}" role="img" aria-label="Measured brightness at ${pts.length} wavelengths from 0.8 to 4.6 micrometres">
    <g class="cm-grid">${TICKS.map((u) => `<line x1="${X(u)}" x2="${X(u)}" y1="${Y0}" y2="${Y1}"/><text x="${X(u)}" y="${Y1 + 16}">${u}</text>`).join('')}
      <line class="cm-one" x1="${X0}" x2="${X1}" y1="${Y(1)}" y2="${Y(1)}"/><text class="cm-one-t" x="${X0 - 6}" y="${Y(1) + 4}">1</text>
      <line class="cm-zero" x1="${X0}" x2="${X1}" y1="${Y(0)}" y2="${Y(0)}"/><text class="cm-one-t" x="${X0 - 6}" y="${Y(0) + 4}">0</text>
      <text class="cm-axis" x="${X1}" y="${Y1 + 34}">wavelength, micrometres</text></g>
    <line class="cm-co2" x1="${co2}" x2="${co2}" y1="${Y0}" y2="${Y1}"/><text class="cm-co2-t" x="${co2 - 4}" y="${Y0 + 10}">CO2 4.26</text>
    ${pts.map((p) => `<line class="cm-err" x1="${X(p.um)}" x2="${X(p.um)}" y1="${Y(p.value - p.err)}" y2="${Y(p.value + p.err)}"/>`).join('')}
    ${pts.map((p) => `<circle class="cm-pt" cx="${X(p.um)}" cy="${Y(p.value)}" r="4.5"><title>${p.um} µm: ${p.value} ± ${p.err}</title></circle>`).join('')}
  </svg>`;
}

export const view: View = async (body, ctx) => {
  const { data, sample } = await ctx.load<CometData>('games/comet/rounds.json');
  if (!data.rounds?.length) {
    body.innerHTML = `<p class="muted">No rounds are available yet.</p>`;
    return;
  }
  let rounds: CometRound[] = [], results: boolean[] = [], turn = 0;
  let answer: (a: Truth) => void = () => {};
  let next: (() => void) | null = null;

  body.innerHTML = `
    <div class="cm">
      <header class="gm-bar">
        <h2 class="gm-title">Comet or asteroid?</h2>
        <ol class="gm-prog" aria-label="Rounds"></ol>
        <p class="gm-score"><span class="mono">Score</span><b class="mono cm-pts">0</b></p>
      </header>
      <p class="gm-sub cm-intro">Each round is a real SPHEREx stack of one moving object and the brightness we measured at its wavelengths. Decide if it is a comet or an asteroid.</p>
      <div class="gm-stage">
        <figure class="cm-fig">
          <p class="cm-who"><span class="mono cm-kind"></span><b class="cm-name"></b></p>
          <div class="cm-img"><img alt="" width="324" height="324"/></div>
          <figcaption class="cm-cap"></figcaption>
          <div class="cm-chart"></div>
          <p class="cm-leg">1 is the colour of plain reflected sunlight. Points above 1 at long wavelengths mean extra light.</p>
        </figure>
        <div class="gm-side">
          <div class="cm-ask">
            <p class="gm-q">Is it a <b>comet</b> or an <b>asteroid</b>?</p>
            <p class="gm-sub">Comets can show a fuzzy glow, the coma, and extra light near 4.26 µm from CO2 gas. Asteroids are bare rock and show as a sharp point.</p>
            <div class="cm-answers">${ANS.map((k) => `<button class="rb-a cm-a" data-a="${k.id}"><svg viewBox="0 0 24 24" aria-hidden="true">${k.icon}</svg><span><b>${k.name}</b><small>${k.tell}</small></span><kbd class="mono">${k.key}</kbd></button>`).join('')}</div>
          </div>
          <div class="cm-reveal" hidden></div>
        </div>
      </div>
      <div class="tr-foot">${provenance(sample, 'Real SPHEREx stacks and our measured spectrum points')}</div>
    </div>
    <div class="gm-end" hidden></div>`;
  const q = <T extends Element = HTMLElement>(s: string) => body.querySelector(s) as T;
  const ask = q('.cm-ask'), reveal = q('.cm-reveal');

  const play = (k: number) => {
    const me = ++turn;
    const r = rounds[k];
    next = null;
    q('.cm').hidden = false;
    q('.gm-end').hidden = true;
    q('.gm-prog').innerHTML = rounds.map((_, i) => `<li class="${i < k ? (results[i] ? 'ok' : 'no') : i === k ? 'now' : ''}"></li>`).join('');
    q('.cm-kind').textContent = `Round ${k + 1} of ${rounds.length}`;
    q('.cm-name').textContent = 'Name hidden until you answer';
    const img = q<HTMLImageElement>('.cm-img img');
    img.src = ctx.source.base + 'games/comet/' + r.img;
    img.alt = `SPHEREx stack of ${r.n_frames ?? 'many'} photos, centred on the object`;
    q('.cm-cap').textContent = `Stack of ${r.n_frames ?? '?'} SPHEREx photos, shifted to follow the object, which sits in the centre.`;
    q('.cm-chart').innerHTML = r.points.length ? chart(r.points) : `<p class="muted">We have no spectrum points for this object.</p>`;
    q('.cm-fig').classList.remove('done');
    ask.hidden = false;
    reveal.hidden = true;

    answer = (a) => {
      if (next || me !== turn) return;
      const ok = a === r.truth;
      results[k] = ok;
      q('.cm-pts').textContent = String(results.filter(Boolean).length * 10);
      q('.cm-fig').classList.add('done');
      q('.cm-name').textContent = r.name;
      const last = k + 1 === rounds.length;
      const snr = r.snr != null ? `We measured it at S/N ${r.snr.toFixed(1)} in the stack.` : '';
      const hint = r.verdict === 'HINT' ? ' Our verdict for it is a hint, not a find, because not every check passed.' : '';
      ask.hidden = true;
      reveal.hidden = false;
      reveal.innerHTML = `
        <p class="rb-verdict">${ANS.find((x) => x.id === r.truth)!.name} <span class="mono">${esc(r.name)}</span></p>
        <p class="gm-q">${ok ? 'Right.' : `Not ${a === 'comet' ? 'a comet' : 'an asteroid'}.`} <span class="rb-plus mono">+${ok ? 10 : 0}</span></p>
        <p class="rb-say">${esc(r.name)} is ${esc(kindPhrase(r))}. ${esc(nameNote(r))}</p>
        ${explain(r).map((s) => `<p class="gm-sub">${esc(s)}</p>`).join('')}
        <p class="gm-sub cm-small">${esc(snr + hint)}</p>
        <div class="gm-row"><button class="btn btn-primary cm-next">${last ? 'See my score' : 'Next'}${icon('arrow')}</button><a class="btn btn-ghost" href="#/object/${esc(r.slug)}">Open ${esc(r.name)}</a></div>`;
      if (ok) confetti(reveal.querySelector<HTMLElement>('.gm-q') ?? reveal);
      next = () => (last ? end() : play(k + 1));
      const btn = q<HTMLButtonElement>('.cm-next');
      btn.onclick = () => next?.();
      btn.focus({ preventScroll: true });
    };
  };

  const end = () => {
    turn++;
    next = null;
    const n = rounds.length, right = results.filter(Boolean).length;
    q('.cm').hidden = true;
    const fin = q('.gm-end');
    fin.hidden = false;
    body.closest('.page')?.scrollTo(0, 0);
    fin.innerHTML = `
      <p class="kicker">Comet or asteroid?</p>
      <h2 class="gm-end-h"><b class="mono">${right * 10}</b> of ${n * 10}</h2>
      <p class="gm-end-lead">A coma is the clearest sign of a comet. Most of our finds are faint, so the stack shows only a small smudge and the spectrum points are noisy. Then the orbit and follow-up from other telescopes decide what the object is.</p>
      <ol class="gm-list">${rounds.map((r, i) => `<li><a href="#/object/${esc(r.slug)}">${esc(r.name)}</a><span class="gm-list-n">${r.truth}, ${results[i] ? 'right' : 'missed'}</span></li>`).join('')}</ol>
      <p class="gm-sub cm-src"><b>Where the data comes from.</b> SPHEREx images from NASA/IRSA, stacked by Rewind along each object's predicted path, with spectrum points we measured from the same photos. Kinds and names come from the JPL Small-Body Database.</p>
      <div class="gm-row"><button class="btn btn-primary gm-again">Play again</button><button class="btn btn-ghost" data-game="hub">All games</button></div>`;
    q<HTMLButtonElement>('.gm-again').onclick = start;
  };

  const start = () => {
    rounds = pickRounds(data.rounds);
    results = [];
    q('.cm-pts').textContent = '0';
    play(0);
  };

  q('.cm-answers').addEventListener('click', (e) => {
    const b = (e.target as Element).closest<HTMLElement>('[data-a]');
    if (b) answer(b.dataset.a as Truth);
  });
  const onKey = (e: KeyboardEvent) => {
    if (e.metaKey || e.ctrlKey || e.altKey || q('.cm').hidden) return;
    const a = ANS.find((x) => x.key === e.key);
    if (a && !next) answer(a.id);
  };
  document.addEventListener('keydown', onKey);
  start();
  return () => {
    turn++;
    document.removeEventListener('keydown', onKey);
  };
};
