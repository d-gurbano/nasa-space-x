// Name that rock: a new asteroid's name is a date stamp. Read rounds give a real name from our
// list and ask for the half-month and the order. Build rounds give a real discovery date and
// order and ask for the name. Every answer is checked against the real designation, and the
// listed discovery date is compared with the name's half-month.
import { icon } from '../../ui/components';
import { esc, provenance } from '../../ui/dom';
import type { View } from '../page';
import { confetti } from './confetti';
import { HALF, ORDER, build, halfLabel, halfOf, normalise, ordinal, orderSum, pickRounds, scoreBuild, scoreRead, type Round } from './name-logic';
import '../../styles/game-name.css';

const isoDate = (iso: string) => {
  const [y, m, d] = iso.split('-').map(Number);
  return `${d} ${halfLabel((m - 1) * 2).split(' ')[0]} ${y}`;
};
const kindWord = (p: string | null) => (p === 'P' ? 'a periodic comet (P/)' : p === 'C' ? 'a long-period comet (C/)' : 'an asteroid');

const RULES = `
  <p class="kicker">Rules card</p>
  <ol class="nm-steps">
    <li><b class="mono">2025</b> The year.</li>
    <li><b class="mono">Y</b> The half-month. A = Jan 1-15, B = Jan 16-31, and so on. I is skipped and Z is not used.</li>
    <li><b class="mono">H5</b> The order in that half-month. A to Z without I is 1st to 25th. The number adds 25 for each time round, so H5 = 8 + 5 x 25 = 133rd.</li>
    <li><b class="mono">C/ P/</b> Comets get a prefix (C/ long-period, P/ periodic) and a plain number for the order, as in C/2026 N1.</li>
  </ol>
  <div class="nm-tab" aria-label="Half-month letters">${Array.from({ length: 12 }, (_, m) => `<span><i>${halfLabel(m * 2, true).split(' ')[0]}</i><b class="mono">${HALF[m * 2]}</b><b class="mono">${HALF[m * 2 + 1]}</b></span>`).join('')}</div>
  <p class="nm-ord mono" aria-label="Order letters">${[...ORDER].map((l, i) => `<span>${l}<i>${i + 1}</i></span>`).join('')}</p>`;

export const view: View = async (body, ctx) => {
  const objs = ctx.source.index.objects.map((o) => ({ slug: o.slug, name: o.name, kind: o.kind, iso: o.discovered?.iso ?? '' })).filter((o) => o.iso);
  let rounds: Round[] = [], pts: number[] = [], turn = 0;
  if (!pickRounds(objs).length) {
    body.innerHTML = `<p class="muted">No names are available for this game yet.</p>`;
    return;
  }

  body.innerHTML = `
    <div class="nm">
      <header class="gm-bar">
        <h2 class="gm-title">Name that rock</h2>
        <ol class="gm-prog" aria-label="Rounds"></ol>
        <p class="gm-score"><span class="mono">Score</span><b class="mono nm-pts">0</b></p>
      </header>
      <p class="gm-sub nm-intro">Every new asteroid and comet gets a name from the Minor Planet Center that records when it was found. Read the date in a real name, or build the name from a real date.</p>
      <div class="gm-stage">
        <div class="nm-left">
          <div class="nm-plate" aria-live="polite"></div>
          <details class="nm-rules" open>${RULES.replace('<p class="kicker">Rules card</p>', '<summary class="kicker">Rules card</summary>')}</details>
        </div>
        <div class="gm-side">
          <form class="nm-ask" novalidate></form>
          <div class="nm-reveal" hidden></div>
        </div>
      </div>
      <div class="tr-foot">${provenance(ctx.source.sample, 'Real Minor Planet Center names and dates')}</div>
    </div>
    <div class="gm-end" hidden></div>`;
  const q = <T extends Element = HTMLElement>(s: string) => body.querySelector(s) as T;
  const plate = q('.nm-plate'), ask = q<HTMLFormElement>('.nm-ask'), reveal = q('.nm-reveal');
  // the rules card starts closed on phones, where it would push the question off screen
  if (matchMedia?.('(max-width: 720px)').matches) q<HTMLDetailsElement>('.nm-rules').open = false;

  const parts = (name: string) => {
    const r = rounds.find((x) => x.obj.name === name)!;
    const p = r.p, m = /^(?:([CPDXA])\/)?(\d{4}) ([A-Z])(.*)$/.exec(name)!;
    return `<ol class="nm-parts">
      ${m[1] ? `<li><b class="mono">${m[1]}/</b><span>${m[1] === 'P' ? 'periodic comet' : 'long-period comet'}</span></li>` : ''}
      <li><b class="mono">${m[2]}</b><span>year</span></li>
      <li><b class="mono">${m[3]}</b><span>${halfLabel(p.half)}</span></li>
      <li><b class="mono">${esc(m[4])}</b><span>${ordinal(p.order)} ${p.prefix ? 'comet' : 'object'}</span></li>
    </ol>`;
  };

  /** What the listed discovery date says next to the name's half-month. */
  const dateCheck = (r: Round) => {
    const h = halfOf(r.obj.iso), same = +r.obj.iso.slice(0, 4) === r.p.year && h === r.p.half;
    return same
      ? `Our data lists its discovery on ${isoDate(r.obj.iso)}, inside ${halfLabel(r.p.half)}, so the name and the date agree.`
      : `Our data lists its first known observation on ${isoDate(r.obj.iso)}, which is in ${halfLabel(h)}, not ${halfLabel(r.p.half)}. That is not a mistake in the name. The letter comes from the observations reported as the discovery, and images found later can push the first known observation earlier without renaming the object.`;
  };

  const play = (k: number) => {
    const me = ++turn, r = rounds[k], last = k + 1 === rounds.length;
    q('.nm').hidden = false;
    q('.gm-end').hidden = true;
    q('.gm-prog').innerHTML = rounds.map((_, i) => `<li class="${i < k ? (pts[i] === 10 ? 'ok' : 'no') : i === k ? 'now' : ''}"></li>`).join('');
    q('.nm-pts').textContent = String(pts.reduce((a, b) => a + b, 0));
    ask.hidden = false;
    reveal.hidden = true;
    let half = -1;

    if (r.mode === 'read') {
      plate.innerHTML = `<p class="mono nm-round">Round ${k + 1} of ${rounds.length}. Read the name</p><p class="nm-name mono">${esc(r.obj.name)}</p><p class="gm-sub">A real ${r.p.prefix ? 'comet' : r.obj.kind === 'neo' ? 'near-Earth asteroid' : 'object'} from our list of ${objs.length}.</p>`;
      ask.innerHTML = `
        <p class="gm-q">When was it named, and in <b>what order</b>?</p>
        <fieldset class="nm-halves"><legend class="gm-sub">Pick the half-month</legend>
          ${Array.from({ length: 24 }, (_, i) => `<button type="button" class="nm-h" data-h="${i}" aria-pressed="false"><b class="mono">${HALF[i]}</b><small>${halfLabel(i, true)}</small></button>`).join('')}
        </fieldset>
        <label class="nm-field"><span class="gm-sub">${r.p.prefix ? 'Comet number' : 'Order'} in that half-month</span><input class="nm-in mono" type="number" inputmode="numeric" min="1" max="999" required placeholder="e.g. 12"></label>
        <div class="gm-row"><button class="btn btn-primary nm-go" type="submit" disabled>Check${icon('arrow')}</button></div>`;
      const go = q<HTMLButtonElement>('.nm-go'), inp = q<HTMLInputElement>('.nm-in');
      const ready = () => (go.disabled = half < 0 || !(+inp.value > 0));
      ask.querySelectorAll<HTMLButtonElement>('.nm-h').forEach((b) => (b.onclick = () => {
        half = +b.dataset.h!;
        ask.querySelectorAll('.nm-h').forEach((x) => x.setAttribute('aria-pressed', String(x === b)));
        ready();
      }));
      inp.oninput = ready;
    } else {
      plate.innerHTML = `<p class="mono nm-round">Round ${k + 1} of ${rounds.length}. Build the name</p>
        <p class="nm-clue">Found on <b>${isoDate(r.obj.iso)}</b>. It is ${kindWord(r.p.prefix)}, the <b>${ordinal(r.p.order)}</b> ${r.p.prefix ? 'comet' : 'new object'} designated in that half-month.</p>`;
      ask.innerHTML = `
        <p class="gm-q">What is its <b>name</b>?</p>
        <label class="nm-field"><span class="gm-sub">Type the designation${r.p.prefix ? `, starting with ${r.p.prefix}/` : ''}</span><input class="nm-in nm-text mono" type="text" autocomplete="off" autocapitalize="characters" spellcheck="false" required placeholder="${r.p.prefix ? 'C/2026 A1' : '2026 AB1'}"></label>
        <div class="gm-row"><button class="btn btn-primary nm-go" type="submit" disabled>Check${icon('arrow')}</button></div>`;
      const go = q<HTMLButtonElement>('.nm-go'), inp = q<HTMLInputElement>('.nm-in');
      inp.oninput = () => (go.disabled = !inp.value.trim());
    }

    ask.onsubmit = (e) => {
      e.preventDefault();
      if (me !== turn || ask.hidden) return;
      const inp = q<HTMLInputElement>('.nm-in');
      let p = 0, head = '', say = '';
      if (r.mode === 'read') {
        if (half < 0 || !(+inp.value > 0)) return;
        const s = scoreRead(r.p, half, Math.round(+inp.value));
        p = s.points;
        head = s.half && s.order ? 'Right.' : s.half || s.order ? 'Half right.' : 'Not quite.';
        say = `${esc(r.obj.name)} was named in ${halfLabel(r.p.half)} ${r.p.year}${s.half ? '' : ` (you picked ${halfLabel(half)})`}. Its order is the ${ordinal(r.p.order)}${s.order ? '' : `, not the ${ordinal(Math.round(+inp.value))}`}, because ${orderSum(r.obj.name)}.`;
      } else {
        const typed = normalise(inp.value), s = scoreBuild(r.obj.name, typed);
        if (!s.valid) {
          q('.nm-field .gm-sub').textContent = `That is not a designation yet. Try the form ${r.p.prefix ? `${r.p.prefix}/2026 A1` : '2026 AB1'}.`;
          inp.focus();
          return;
        }
        p = s.points;
        head = s.half && s.order ? 'Right.' : s.half || s.order ? 'Half right.' : 'Not quite.';
        say = `${halfLabel(r.p.half)} is letter ${HALF[r.p.half]}. ${r.p.prefix ? `The ${ordinal(r.p.order)} comet is number ${r.p.order}` : `The ${ordinal(r.p.order)} object is ${build(r.p).split(' ')[1].slice(1)} (${orderSum(r.obj.name)})`}, so the name is ${esc(r.obj.name)}.${s.half && s.order ? '' : ` You typed ${esc(typed)}.`}`;
      }
      pts[k] = p;
      q('.nm-pts').textContent = String(pts.reduce((a, b) => a + b, 0));
      ask.hidden = true;
      reveal.hidden = false;
      reveal.innerHTML = `
        <p class="gm-q">${head} <span class="nm-plus mono">+${p}</span></p>
        ${parts(r.obj.name)}
        <p class="nm-say">${say}</p>
        <p class="gm-sub nm-check">${dateCheck(r)}</p>
        <div class="gm-row"><button type="button" class="btn btn-primary nm-next">${last ? 'See my score' : 'Next'}${icon('arrow')}</button><a class="btn btn-ghost" href="#/object/${esc(r.obj.slug)}">Open ${esc(r.obj.name)}</a></div>`;
      if (r.mode === 'build') plate.innerHTML += `<p class="nm-name mono nm-answer">${esc(r.obj.name)}</p>`;
      if (p === 10) confetti(reveal.querySelector<HTMLElement>('.gm-q') ?? reveal);
      const nx = q<HTMLButtonElement>('.nm-next');
      nx.onclick = () => (last ? end() : play(k + 1));
      nx.focus({ preventScroll: true });
    };
    (r.mode === 'read' ? ask.querySelector<HTMLButtonElement>('.nm-h') : ask.querySelector<HTMLInputElement>('.nm-in'))?.focus({ preventScroll: true });
  };

  const end = () => {
    turn++;
    const sum = pts.reduce((a, b) => a + b, 0), n = rounds.length;
    const by = (m: Round['mode']) => rounds.map((r, i) => ({ r, p: pts[i] })).filter((x) => x.r.mode === m);
    q('.nm').hidden = true;
    const fin = q('.gm-end');
    fin.hidden = false;
    body.closest('.page')?.scrollTo(0, 0);
    fin.innerHTML = `
      <p class="kicker">Name that rock</p>
      <h2 class="gm-end-h"><b class="mono">${sum}</b> of ${n * 10}</h2>
      <p class="gm-end-lead">${sum >= n * 8 ? 'You can read the Minor Planet Center code like an astronomer.' : 'The code is a date stamp. Half-month first, then the order in that half-month.'} A provisional name stays until the orbit is known well enough for a permanent number, like 433 Eros.</p>
      <ol class="gm-list">${(['read', 'build'] as const).map((m) => {
        const x = by(m);
        return x.length ? `<li><span>${m === 'read' ? 'Read the name' : 'Build the name'}</span><span class="mono">${x.filter((y) => y.p === 10).length} of ${x.length}</span></li>` : '';
      }).join('')}</ol>
      <div class="gm-row"><button class="btn btn-primary gm-again">Play again</button><button class="btn btn-ghost" data-game="hub">All games</button></div>
      <p class="gm-sub">Where the data comes from. Names and discovery dates of the ${objs.length} objects in Rewind, from Minor Planet Center records. The naming rules are the MPC provisional designation rules.</p>`;
    q<HTMLButtonElement>('.gm-again').onclick = start;
  };

  const start = () => {
    rounds = pickRounds(objs);
    pts = [];
    play(0);
  };
  start();
  return () => {
    turn++;
  };
};
