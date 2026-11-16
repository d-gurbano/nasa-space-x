// Real or junk?: one real SPHEREx image at a time, 41 x 41 pixels, centred on something. The player
// says what it is: an asteroid or one of four kinds of junk. Then the true label, one line of science,
// and what our real-or-fake AI said about that exact image (only where it was really run).
import '../../styles/game-junk.css';
import { icon } from '../../ui/components';
import { esc, provenance } from '../../ui/dom';
import { confetti } from './confetti';
import type { View } from '../page';
import { aiLine, buildRounds, CAT_NAME, CATS, pct, type Cat, type JunkData, type JunkStamp } from './junk-logic';

const ROUNDS = 10;

export const view: View = async (body, ctx) => {
  const { data, sample } = await ctx.load<JunkData>('games/junk/rounds.json');
  if (!data.pool?.length) {
    body.innerHTML = `<p class="muted">No rounds are available yet.</p>`;
    return;
  }
  const img = (s: JunkStamp) => ctx.source.base + 'games/junk/' + s.img;
  let rounds: JunkStamp[] = [], results: { ok: boolean; cat: Cat }[] = [], turn = 0;
  let answer: (a: Cat) => void = () => {};
  let next: (() => void) | null = null;

  body.innerHTML = `
    <div class="jk">
      <header class="gm-bar">
        <h2 class="gm-title">Real or junk?</h2>
        <ol class="gm-prog" aria-label="Rounds"></ol>
        <p class="gm-score"><span class="mono">Score</span><b class="mono jk-pts">0</b></p>
      </header>
      <div class="gm-stage">
        <figure class="jk-fig">
          <p class="jk-who mono"></p>
          <div class="jk-frame"><img class="jk-img" alt="" width="164" height="164"><span class="jk-ring" aria-hidden="true"></span></div>
          <figcaption class="jk-cap">One SPHEREx exposure, 41 by 41 pixels (about 4 arcminutes). The ring marks the centre.</figcaption>
        </figure>
        <div class="gm-side">
          <div class="jk-ask">
            <p class="gm-q">What is in the <b>ring</b>?</p>
            <p class="gm-sub">Most dots in a single image are stars. Our search has to tell a real moving object from the junk the camera also records.</p>
            <div class="jk-answers">${CATS.map((c) => `<button class="jk-a" data-a="${c.id}"><b>${c.name}</b><kbd class="mono">${c.key}</kbd></button>`).join('')}</div>
          </div>
          <div class="jk-reveal" hidden></div>
        </div>
      </div>
      <div class="tr-foot">${provenance(sample, 'Real SPHEREx images')}</div>
    </div>
    <div class="gm-end" hidden></div>`;
  const q = <T extends Element = HTMLElement>(s: string) => body.querySelector(s) as T;
  const ask = q('.jk-ask'), reveal = q('.jk-reveal');

  const play = (k: number) => {
    const me = ++turn;
    const s = rounds[k];
    next = null;
    q('.jk').hidden = false;
    q('.gm-end').hidden = true;
    q('.gm-prog').innerHTML = rounds.map((_, i) => `<li class="${i < k ? (results[i].ok ? 'ok' : 'no') : i === k ? 'now' : ''}"></li>`).join('');
    q('.jk-who').textContent = `Round ${k + 1} of ${rounds.length}`;
    const im = q<HTMLImageElement>('.jk-img');
    im.src = img(s);
    im.alt = `SPHEREx image, round ${k + 1}`;
    q('.jk-fig').classList.remove('done');
    ask.hidden = false;
    reveal.hidden = true;

    answer = (a) => {
      if (next || me !== turn) return;
      const ok = a === s.cat;
      results[k] = { ok, cat: s.cat };
      q('.jk-pts').textContent = String(results.filter((x) => x.ok).length * 10);
      q('.jk-fig').classList.add('done');
      const last = k + 1 === rounds.length;
      ask.hidden = true;
      reveal.hidden = false;
      reveal.innerHTML = `
        <p class="jk-verdict mono">${esc(CAT_NAME[s.cat])}</p>
        <p class="gm-q">${ok ? 'Right.' : `Not ${esc(CAT_NAME[a].toLowerCase())}.`} <span class="jk-plus mono">+${ok ? 10 : 0}</span></p>
        <p class="jk-say">${esc(CATS.find((c) => c.id === s.cat)!.say)}</p>
        <dl class="jk-key">
          <dt>Answer key</dt><dd>${esc(s.label)}${s.snr ? `, signal-to-noise ${s.snr}` : ''}</dd>
          <dt>Exposure</dt><dd class="mono">${esc(s.obsid)} ${esc(s.det)}</dd>
          <dt>Our AI</dt><dd>${esc(aiLine(s))}</dd>
        </dl>
        <div class="gm-row"><button class="btn btn-primary jk-next">${last ? 'See my score' : 'Next'}${icon('arrow')}</button></div>`;
      if (ok) confetti(reveal.querySelector<HTMLElement>('.gm-q') ?? reveal);
      next = () => (last ? end() : play(k + 1));
      const btn = q<HTMLButtonElement>('.jk-next');
      btn.onclick = () => next?.();
      btn.focus({ preventScroll: true });
    };
  };

  const end = () => {
    turn++;
    next = null;
    const n = rounds.length, right = results.filter((x) => x.ok).length;
    q('.jk').hidden = true;
    const fin = q('.gm-end');
    fin.hidden = false;
    body.closest('.page')?.scrollTo(0, 0);
    fin.innerHTML = `
      <p class="kicker">Real or junk?</p>
      <h2 class="gm-end-h"><b class="mono">${right * 10}</b> of ${n * 10}</h2>
      <p class="gm-end-lead">You sorted ${pct(right, n)}% of the images correctly. Our real-or-fake AI, a small neural network, got ${(data.ai_accuracy * 100).toFixed(1)}% right on its held-out test (${data.ai_test_n} stamps from sky regions it never trained on). That test had only two answers, real or fake, and its fakes were planted artifacts, so the two scores are not a like-for-like race.</p>
      <ol class="gm-list">${CATS.map((c) => {
        const of = results.filter((x) => x.cat === c.id);
        return of.length ? `<li><span>${c.name}</span><span class="mono">${of.filter((x) => x.ok).length} of ${of.length}</span></li>` : '';
      }).join('')}</ol>
      <p class="jk-src">Where the data comes from: ${esc(data.source)}</p>
      <div class="gm-row"><button class="btn btn-primary gm-again">Play again</button><button class="btn btn-ghost" data-game="hub">All games</button></div>`;
    q<HTMLButtonElement>('.gm-again').onclick = start;
  };

  const start = () => {
    rounds = buildRounds(data.pool, ROUNDS);
    results = [];
    q('.jk-pts').textContent = '0';
    play(0);
  };

  q('.jk-answers').addEventListener('click', (e) => {
    const b = (e.target as Element).closest<HTMLElement>('[data-a]');
    if (b) answer(b.dataset.a as Cat);
  });
  const onKey = (e: KeyboardEvent) => {
    if (e.metaKey || e.ctrlKey || e.altKey || q('.jk').hidden) return;
    const a = CATS.find((x) => x.key === e.key);
    if (a && !next) answer(a.id);
  };
  document.addEventListener('keydown', onKey);
  start();
  return () => {
    turn++;
    document.removeEventListener('keydown', onKey);
  };
};
