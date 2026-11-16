// Too faint?: each round shows one real searched object, its predicted brightness, how many SPHEREx
// images covered it and our measured detection limit. Bet whether stacking shows it, then see the verdict.
import '../../styles/game-faint.css';
import { icon } from '../../ui/components';
import { esc, provenance } from '../../ui/dom';
import type { View } from '../page';
import { confetti } from './confetti';
import { perImage, pickRounds, score, type Bet, type FaintObj } from './faint-logic';

const VERDICT = { FOUND: 'Found', HINT: 'Hint', TOO_FAINT: 'Too faint' } as const;

export const view: View = async (body, ctx) => {
  const { data, sample } = await ctx.load<{ objects: FaintObj[] }>('games/faint/objects.json');
  if (!data.objects?.length) {
    body.innerHTML = `<p class="muted">No rounds are available yet.</p>`;
    return;
  }
  let rounds: FaintObj[] = [], pts: number[] = [], next: (() => void) | null = null, bet: (b: Bet) => void = () => {};

  body.innerHTML = `
    <div class="tf">
      <header class="gm-bar">
        <h2 class="gm-title">Too faint?</h2>
        <ol class="gm-prog" aria-label="Rounds"></ol>
        <p class="gm-score"><span class="mono">Score</span><b class="mono tf-pts">0</b></p>
      </header>
      <p class="gm-sub tf-intro">Each object below is one we searched for in SPHEREx images taken before it was discovered. Look at the numbers and bet whether stacking the images will show it.</p>
      <div class="gm-stage">
        <figure class="tf-card">
          <p class="tf-who"><span class="mono tf-n"></span><b class="tf-name"></b><span class="tf-kind"></span></p>
          <dl class="tf-stats">
            <div><dt>Predicted brightness</dt><dd class="mono tf-pred"></dd><small>AB magnitude. Bigger numbers are fainter.</small></div>
            <div><dt>SPHEREx images</dt><dd class="mono tf-imgs"></dd><small>Images that covered its predicted path.</small></div>
            <div><dt>Our detection limit</dt><dd class="mono tf-lim"></dd><small>We recover half of the test sources planted at this brightness.</small></div>
          </dl>
          <div class="tf-meter" aria-hidden="true"><span class="tf-scale"></span></div>
        </figure>
        <div class="gm-side">
          <div class="tf-ask">
            <p class="gm-q">Will stacking <b>show it</b>?</p>
            <div class="tf-bets">
              <button class="btn btn-primary" data-bet="show">Stacking will show it<kbd class="mono">1</kbd></button>
              <button class="btn btn-ghost" data-bet="faint">Too faint<kbd class="mono">2</kbd></button>
            </div>
          </div>
          <div class="tf-reveal" hidden></div>
        </div>
      </div>
    </div>
    <div class="gm-end" hidden></div>`;
  const q = <T extends Element = HTMLElement>(s: string) => body.querySelector(s) as T;
  const ask = q('.tf-ask'), reveal = q('.tf-reveal');

  // a magnitude scale from 14 to 24, with the prediction and the limit on it
  const at = (m: number) => `${Math.max(0, Math.min(100, ((m - 14) / 10) * 100)).toFixed(1)}%`;
  const meter = (o: FaintObj) =>
    `<i class="tf-m-lim" style="left:${o.limit_ab != null ? at(o.limit_ab) : '-10%'}" ${o.limit_ab == null ? 'hidden' : ''}><span>limit</span></i>` +
    `<i class="tf-m-obj" style="left:${at(o.pred_ab)}"><span>predicted</span></i><b class="mono">14</b><b class="mono">24</b><em>brighter</em><em>fainter</em>`;

  const play = (k: number) => {
    const o = rounds[k];
    next = null;
    q('.tf').hidden = false;
    q('.gm-end').hidden = true;
    q('.gm-prog').innerHTML = rounds.map((_, i) => `<li class="${i < k ? (pts[i] === 10 ? 'ok' : pts[i] ? 'half' : 'no') : i === k ? 'now' : ''}"></li>`).join('');
    q('.tf-n').textContent = `Round ${k + 1} of ${rounds.length}`;
    q('.tf-name').textContent = o.name;
    q('.tf-kind').textContent = o.kind === 'comet' ? 'comet' : o.kind === 'neo' ? 'near-Earth asteroid' : o.kind === 'mba' ? 'main-belt asteroid' : o.kind === 'lost' ? 'lost asteroid' : 'asteroid';
    q('.tf-pred').textContent = o.pred_ab.toFixed(1);
    q('.tf-imgs').textContent = String(o.n_frames);
    q('.tf-lim').textContent = o.limit_ab != null ? o.limit_ab.toFixed(1) : 'not measured';
    q('.tf-scale').innerHTML = meter(o);
    ask.hidden = false;
    reveal.hidden = true;
    q<HTMLButtonElement>('[data-bet="show"]').focus({ preventScroll: true });

    bet = (b) => {
      if (next) return;
      const p = score(b, o.verdict);
      pts[k] = p;
      q('.tf-pts').textContent = String(pts.reduce((a, x) => a + x, 0));
      const root = Math.sqrt(o.n_frames), one = perImage(o.snr, o.n_frames);
      const gap = o.limit_ab != null ? o.limit_ab - o.pred_ab : null;
      const vs = gap == null ? '' : Math.abs(gap) < 0.05 ? 'Its predicted brightness was right at our detection limit. ' : `Its predicted brightness was ${Math.abs(gap).toFixed(1)} mag ${gap > 0 ? 'brighter' : 'fainter'} than our detection limit. `;
      const why = o.verdict === 'FOUND'
        ? 'The stacked signal was strong and passed every check, so we count it as found.'
        : o.verdict === 'HINT'
          ? 'A weak signal showed, but not strong enough to pass all our checks, so it stays a hint.'
          : 'Nothing stood out from the noise at the predicted spot.';
      const last = k + 1 === rounds.length;
      ask.hidden = true;
      reveal.hidden = false;
      reveal.innerHTML = `
        <p class="tf-verdict tf-v-${o.verdict}">${VERDICT[o.verdict]}<span class="mono">S/N ${o.snr.toFixed(1)}</span></p>
        <p class="gm-q">${p === 10 ? 'Right.' : p ? 'Half right.' : 'Not this time.'} <span class="tf-plus mono">+${p}</span></p>
        <p class="tf-say">${vs}${why}</p>
        <p class="gm-sub">Stacking ${o.n_frames} images lowers the noise about √${o.n_frames} ≈ ${root.toFixed(1)} times. One image alone would give S/N about ${one.toFixed(one < 1 ? 2 : 1)}${one < 3 ? ', too low to see' : ''}.</p>
        <div class="gm-row"><button class="btn btn-primary tf-next">${last ? 'See my score' : 'Next'}${icon('arrow')}</button><a class="btn btn-ghost" href="#/object/${esc(o.slug)}">Open ${esc(o.name)}</a></div>`;
      if (p === 10) confetti(q('.tf-reveal .gm-q'));
      next = () => (last ? end() : play(k + 1));
      const btn = q<HTMLButtonElement>('.tf-next');
      btn.onclick = () => next?.();
      btn.focus({ preventScroll: true });
    };
  };

  const end = () => {
    next = null;
    const sum = pts.reduce((a, x) => a + x, 0);
    q('.tf').hidden = true;
    const fin = q('.gm-end');
    fin.hidden = false;
    body.closest('.page')?.scrollTo(0, 0);
    fin.innerHTML = `
      <p class="kicker">Too faint?</p>
      <h2 class="gm-end-h"><b class="mono">${sum}</b> of ${rounds.length * 10}</h2>
      <p class="gm-end-lead">Stacking N images makes the signal-to-noise ratio grow with √N. So 100 images reach 10 times fainter in flux than one, about 2.5 magnitudes. Most of the objects we searched were still too faint.</p>
      <ol class="gm-list">${rounds.map((o, i) => `<li><a href="#/object/${esc(o.slug)}">${esc(o.name)}</a><span class="gm-list-n">${VERDICT[o.verdict]}, S/N ${o.snr.toFixed(1)}</span><span class="mono">+${pts[i] ?? 0}</span></li>`).join('')}</ol>
      <div class="gm-row"><button class="btn btn-primary gm-again">Play again</button><button class="btn btn-ghost" data-game="hub">All games</button></div>
      <div class="tr-foot">${provenance(sample, 'Rewind search results')}<p class="gm-sub">Where the data comes from: our Rewind search of public SPHEREx images (index.json and each object’s object.json). The predicted brightness is the one our search used for the stack; the detection limit comes from our injection tests.</p></div>`;
    q<HTMLButtonElement>('.gm-again').onclick = start;
    q<HTMLButtonElement>('.gm-again').focus({ preventScroll: true });
  };

  const start = () => {
    rounds = pickRounds(data.objects);
    pts = [];
    q('.tf-pts').textContent = '0';
    play(0);
  };

  q('.tf-bets').addEventListener('click', (e) => {
    const b = (e.target as Element).closest<HTMLElement>('[data-bet]');
    if (b) bet(b.dataset.bet as Bet);
  });
  const onKey = (e: KeyboardEvent) => {
    if (e.metaKey || e.ctrlKey || e.altKey || q('.tf').hidden || next) return;
    if (e.key === '1') bet('show');
    if (e.key === '2') bet('faint');
  };
  document.addEventListener('keydown', onKey);
  start();
  return () => document.removeEventListener('keydown', onKey);
};
