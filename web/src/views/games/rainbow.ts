// Rainbow Detective: SPHEREx splits light into 102 colours. Each round shows one object's colour
// fingerprint (brightness vs wavelength, 0.75 to 5 um). Match it to what the object is made of,
// then see the typical curve of that type laid over it and one feature explained.
import { icon } from '../../ui/components';
import { esc, provenance } from '../../ui/dom';
import { reducedMotion } from '../../state';
import type { View } from '../page';
import { hue, linePath, scaleTo, UM_MAX, UM_MIN, ux, yRange, type Kind, type RainbowData, type RainbowRound } from './rainbow-logic';

const KINDS: { id: Kind; name: string; tag: string; tell: string; key: string; icon: string }[] = [
  { id: 'S', name: 'Rocky', tag: 'S-type', tell: 'reddish, dip near 1 µm', key: '1', icon: '<path d="M4.5 14.5 7 7.5l6-3 5.5 4 1 6.5-5.5 4.5-7-1z"/><path d="m7 7.5 4.5 5 7-4M11.5 12.5 9.5 19"/>' },
  { id: 'C', name: 'Dark carbon', tag: 'C-type', tell: 'flat and dark, no big dips', key: '2', icon: '<circle cx="12" cy="12" r="7.5" fill="currentColor" fill-opacity="0.18"/><circle cx="9.5" cy="10" r="1"/><circle cx="14" cy="14.5" r="1.3"/><circle cx="14.5" cy="9" r="0.6"/>' },
  { id: 'X', name: 'Metal-rich', tag: 'X/M-type', tell: 'smooth rising slope', key: '3', icon: '<path d="m12 3.5 7.5 4.25v8.5L12 20.5l-7.5-4.25v-8.5z"/><path d="M8 9.5 11 8"/>' },
  { id: 'ice', name: 'Icy comet', tag: 'water ice', tell: 'deep dip near 3 µm (water ice)', key: '4', icon: '<circle cx="15.5" cy="8.5" r="3.5"/><path d="M12.5 10.5 4 17M13.5 12 7 19.5M11 9 3.5 12.5"/>' },
];
const NAME = Object.fromEntries(KINDS.map((k) => [k.id, k.name])) as Record<Kind, string>;
// the one feature to point at on the reveal
const FEATURE: Record<Kind, { from: number; to: number; text: string } | { at: number; text: string }> = {
  S: { from: 0.86, to: 1.16, text: 'olivine dip' },
  C: { at: 1.9, text: 'flat, no dips' },
  X: { at: 1.9, text: 'steady climb to the red' },
  ice: { from: 2.85, to: 3.3, text: 'water ice' },
};

// the hint: the wavelengths that tell this round apart
const HINT: Record<Kind, { from: number; to: number; text: string }> = {
  S: { from: 0.86, to: 1.16, text: 'Is there a dip here?' },
  C: { from: 1.0, to: 2.5, text: 'Flat or rising here?' },
  X: { from: 1.0, to: 2.5, text: 'Flat or rising here?' },
  ice: { from: 2.85, to: 3.3, text: 'Is there a deep dip here?' },
};

// chart geometry, in SVG units
const W = 640, H = 400, X0 = 40, X1 = 620, BAR = [18, 54], Y0 = 92, Y1 = 344;
const X = (um: number) => X0 + ux(um) * (X1 - X0);
const TICKS = [0.75, 1, 1.5, 2, 3, 4, 5];

function shuffle<T>(a: T[]): T[] {
  const b = [...a];
  for (let i = b.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [b[i], b[j]] = [b[j], b[i]];
  }
  return b;
}

const kindIcon = (k: Kind) => `<svg viewBox="0 0 24 24" aria-hidden="true">${KINDS.find((x) => x.id === k)!.icon}</svg>`;

export const rainbowGame: View = async (body, ctx) => {
  const { data, sample } = await ctx.load<RainbowData>('games/rainbow.json');
  if (!data.rounds?.length) {
    body.innerHTML = `<p class="muted">No rounds yet.</p>`;
    return;
  }
  const um = data.um;
  let rounds: RainbowRound[] = [], results: { ok: boolean; truth: Kind }[] = [], turn = 0;
  // a small chart of each type's typical curve, all on one scale, with its tell-tale zone shaded
  const [mlo, mhi] = yRange(KINDS.map((k) => data.classes[k.id]));
  const mini = (k: Kind, w: number, h: number) => {
    const mx = (u: number) => 2 + ux(u) * (w - 4), my = (v: number) => h - 2 - ((v - mlo) / (mhi - mlo)) * (h - 4);
    const f = FEATURE[k];
    return `<svg class="rb-mini" viewBox="0 0 ${w} ${h}" aria-hidden="true">${'from' in f ? `<rect class="rb-mini-band" x="${mx(f.from)}" y="0" width="${mx(f.to) - mx(f.from)}" height="${h}"/>` : ''}<path d="${linePath(um, data.classes[k], mx, my)}"/></svg>`;
  };
  const gradStops = TICKS.map((u) => `<stop offset="${ux(u).toFixed(3)}" stop-color="hsl(${hue(u)} 95% 66%)"/>`).join('');

  body.innerHTML = `
    <div class="rb">
      <header class="gm-bar">
        <h2 class="gm-title">Rainbow Detective</h2>
        <ol class="gm-prog" aria-label="Rounds"></ol>
        <button type="button" class="btn btn-ghost rb-guide-open">Field guide</button>
        <p class="gm-score"><span class="mono">Score</span><b class="mono rb-pts">0</b></p>
      </header>
      <div class="gm-stage">
        <figure class="rb-chart">
          <p class="rb-who"><span class="mono rb-kind"></span><b class="rb-name"></b></p>
          <svg class="rb-svg" viewBox="0 0 ${W} ${H}" role="img" aria-label="Brightness of the object in each of the SPHEREx colours, from 0.75 to 5 micrometres">
            <defs>
              <linearGradient id="rb-grad" gradientUnits="userSpaceOnUse" x1="${X0}" x2="${X1}" y1="0" y2="0">${gradStops}</linearGradient>
              <filter id="rb-glow" x="-10%" y="-30%" width="120%" height="160%"><feGaussianBlur stdDeviation="4" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
              <pattern id="rb-hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line y2="6" stroke="rgba(255,255,255,0.07)" stroke-width="2"/></pattern>
            </defs>
            <g class="rb-grid">${TICKS.map((u) => `<line x1="${X(u)}" x2="${X(u)}" y1="${Y0 - 8}" y2="${Y1}"/><text x="${X(u)}" y="${Y1 + 22}">${u}</text>`).join('')}
              <text class="rb-axis" x="${X1}" y="${Y1 + 44}">wavelength, micrometres</text>
              <text class="rb-axis rb-axis-l" x="${X0}" y="${Y1 + 44}">brighter is up</text></g>
            <clipPath id="rb-clip"><rect x="${X0}" y="${Y0 - 8}" width="${X1 - X0}" height="${Y1 - Y0 + 8}"/></clipPath>
            <g class="rb-bar"></g>
            <g class="rb-feat"></g>
            <g class="rb-tpl" clip-path="url(#rb-clip)"></g>
            <g class="rb-data"></g>
          </svg>
        </figure>
        <div class="gm-side">
          <div class="rb-ask">
            <p class="gm-q">What is it <b>made of</b>?</p>
            <p class="gm-sub">A dip means something is soaking up that colour. Point at an answer to lay its typical curve over the mystery one.</p>
            <div class="rb-answers">${KINDS.map((k) => `<button class="rb-a rb-a-${k.id}" data-a="${k.id}">${mini(k.id, 88, 40)}<span><b>${k.name}</b><small>${k.tell}</small></span><kbd class="mono">${k.key}</kbd></button>`).join('')}</div>
            <div class="gm-row"><button type="button" class="btn btn-ghost rb-hint">Hint</button></div>
          </div>
          <div class="rb-reveal" hidden></div>
        </div>
      </div>
      <div class="tr-foot">${provenance(sample, 'Real ground-based spectra, resampled to SPHEREx colours')}<p class="rb-note">${esc(data.note)}</p></div>
    </div>
    <div class="gm-end" hidden></div>
    <dialog class="rb-guide" aria-labelledby="rb-guide-h">
      <p class="kicker">Field guide</p>
      <h2 id="rb-guide-h" class="rb-guide-h">Four shapes to know</h2>
      <p class="gm-sub">Each curve is the typical colour fingerprint of one type, from violet (0.75 µm) to red (5 µm). Match the shape, not the height.</p>
      <ol class="rb-guide-list">${KINDS.map((k) => `<li>${mini(k.id, 200, 96)}<b>${kindIcon(k.id)}${k.name}</b><span>${k.tell}</span></li>`).join('')}</ol>
      <div class="gm-row"><button type="button" class="btn btn-primary rb-guide-ok">Got it</button></div>
    </dialog>`;
  const q = <T extends Element = HTMLElement>(s: string) => body.querySelector(s) as T;
  const ask = q('.rb-ask'), reveal = q('.rb-reveal'), guide = q<HTMLDialogElement>('.rb-guide');
  let seenGuide = false;
  const openGuide = () => {
    if (!guide.open) guide.showModal?.();
  };
  q('.rb-guide-open').onclick = openGuide;
  q('.rb-guide-ok').onclick = () => guide.close();
  guide.addEventListener('close', () => {
    seenGuide = true;
    if (!next) q<HTMLButtonElement>('.rb-a').focus({ preventScroll: true });
  });
  // the round on screen: its scale, so a template can be laid over it
  let cur: { r: RainbowRound; Y: (v: number) => number } | null = null, peeking: Kind | null = null;
  /** A type's typical curve, scaled to match the mystery curve. */
  const tplPath = (kind: Kind, cls: string, label = true) => {
    if (!cur) return '';
    const { r, Y } = cur, tv = data.classes[kind];
    const k = r.points?.length ? scaleTo(um, tv, r.points.map((p) => p.um), r.points.map((p) => p.value)) : scaleTo(um, tv, um, r.values ?? []);
    const lastI = Math.max(...tv.map((v, i) => (v == null ? -1 : i)));
    return `<path class="rb-t ${cls}" d="${linePath(um, tv.map((v) => (v == null ? null : v * k)), X, Y)}"/>` +
      (label && lastI > 0 ? `<text class="rb-t-lab" x="${X(um[lastI]) - 4}" y="${Y(tv[lastI]! * k) - 10}">typical ${esc(NAME[kind].toLowerCase())}</text>` : '');
  };
  let answer: (a: Kind) => void = () => {};
  let next: (() => void) | null = null;

  const draw = (r: RainbowRound) => {
    const pts = r.points ?? [];
    const vals = r.values ?? [];
    const [lo, hi] = yRange([vals, pts.map((p) => p.value - p.err), pts.map((p) => p.value + p.err), data.classes.S, data.classes.C, data.classes.X]);
    const Y = (v: number) => Y1 - ((v - lo) / (hi - lo)) * (Y1 - Y0);
    const light = (v: number | null | undefined) => (v == null ? null : Math.max(0, Math.min(1, (v - lo) / (hi - lo))));
    // the rainbow bar: one strip per colour, brighter where the object reflects more
    const strips: { a: number; b: number; u: number; t: number | null }[] = [];
    if (pts.length) {
      pts.forEach((p, i) => {
        const a = i ? Math.sqrt(pts[i - 1].um * p.um) : UM_MIN, b = i < pts.length - 1 ? Math.sqrt(p.um * pts[i + 1].um) : UM_MAX;
        strips.push({ a, b, u: p.um, t: light(p.value) });
      });
    } else {
      um.forEach((u, i) => strips.push({ a: i ? Math.sqrt(um[i - 1] * u) : UM_MIN, b: i < um.length - 1 ? Math.sqrt(u * um[i + 1]) : UM_MAX, u, t: light(vals[i]) }));
    }
    q('.rb-bar').innerHTML = `<rect x="${X0}" y="${BAR[0]}" width="${X1 - X0}" height="${BAR[1] - BAR[0]}" rx="6" fill="url(#rb-hatch)"/>` +
      strips.map((s) => s.t == null ? '' : `<rect x="${X(s.a).toFixed(1)}" y="${BAR[0]}" width="${(X(s.b) - X(s.a) + 0.6).toFixed(1)}" height="${BAR[1] - BAR[0]}" fill="hsl(${hue(s.u)} 92% ${(20 + 50 * s.t).toFixed(0)}%)"/>`).join('') +
      `<rect class="rb-bar-edge" x="${X0}" y="${BAR[0]}" width="${X1 - X0}" height="${BAR[1] - BAR[0]}" rx="6"/>`;
    // where the ground could not see, say so
    let gap = '';
    if (r.kind === 'measured') {
      const last = Math.max(...vals.map((v, i) => (v == null ? -1 : i)));
      if (last >= 0 && last < um.length - 1) {
        const a = X(Math.sqrt(um[last] * um[last + 1]));
        gap = `<rect class="rb-gap" x="${a}" y="${Y0 - 8}" width="${X1 - a}" height="${Y1 - Y0 + 8}" fill="url(#rb-hatch)"/><text class="rb-gap-t" x="${(a + X1) / 2}" y="${Y0 + 14}">Air blocks these colours</text><text class="rb-gap-t" x="${(a + X1) / 2}" y="${Y0 + 32}">for ground telescopes.</text><text class="rb-gap-t gold" x="${(a + X1) / 2}" y="${Y0 + 54}">SPHEREx sees them from space.</text>`;
      }
    }
    const line = pts.length
      ? `${pts.map((p) => `<line class="rb-err" x1="${X(p.um)}" x2="${X(p.um)}" y1="${Y(p.value - p.err)}" y2="${Y(p.value + p.err)}"/>`).join('')}
         <path class="rb-line" d="${linePath(pts.map((p) => p.um), pts.map((p) => p.value), X, Y)}"/>
         ${pts.map((p) => `<circle class="rb-pt" cx="${X(p.um)}" cy="${Y(p.value)}" r="5" style="fill:hsl(${hue(p.um)} 95% 66%)"/>`).join('')}`
      : `<path class="rb-line" d="${linePath(um, vals, X, Y)}"/>`;
    q('.rb-data').innerHTML = gap + line;
    q('.rb-tpl').innerHTML = q('.rb-feat').innerHTML = '';
    return Y;
  };

  const play = (k: number) => {
    const me = ++turn;
    const r = rounds[k];
    next = null;
    q('.rb').hidden = false;
    q('.gm-end').hidden = true;
    q('.gm-prog').innerHTML = rounds.map((_, i) => `<li class="${i < k ? (results[i].ok ? 'ok' : 'no') : i === k ? 'now' : ''}"></li>`).join('');
    q('.rb-kind').textContent = r.kind === 'spherex' ? 'Bonus: a real Rewind find' : `Round ${k + 1} of ${rounds.length}`;
    q('.rb-name').textContent = r.name;
    ask.hidden = false;
    reveal.hidden = true;
    q('.rb-chart').classList.remove('done');
    q('.rb-chart').classList.toggle('bonus', r.kind === 'spherex');
    const Y = draw(r);
    cur = { r, Y };
    peeking = null;
    q<HTMLButtonElement>('.rb-hint').disabled = false;
    if (!reducedMotion) {
      const path = q<SVGPathElement>('.rb-line');
      const len = path.getTotalLength?.() || 1200;
      path.style.strokeDasharray = `${len}`;
      path.animate([{ strokeDashoffset: len }, { strokeDashoffset: 0 }], { duration: 1100, easing: 'cubic-bezier(0.16, 1, 0.3, 1)' });
    }

    answer = (a) => {
      if (next || me !== turn) return;
      const ok = a === r.truth;
      results[k] = { ok, truth: r.truth };
      q('.rb-pts').textContent = String(results.filter((x) => x.ok).length * 10);
      q('.rb-chart').classList.add('done');
      // the typical curve of the right type, and the player's pick if it was different
      q('.rb-tpl').innerHTML = (ok ? '' : tplPath(a, 'rb-t-pick', false)) + tplPath(r.truth, 'rb-t-true');
      const f = FEATURE[r.truth];
      q('.rb-feat').innerHTML = 'from' in f
        ? `<rect class="rb-band" x="${X(f.from)}" y="${Y0 - 8}" width="${X(f.to) - X(f.from)}" height="${Y1 - Y0 + 8}"/><text class="rb-band-t" x="${(X(f.from) + X(f.to)) / 2}" y="${Y0 + 10}">${f.text}</text>`
        : `<text class="rb-band-t" x="${X(f.at)}" y="${Y0 + 10}">${f.text}</text>`;
      const last = k + 1 === rounds.length;
      ask.hidden = true;
      reveal.hidden = false;
      reveal.innerHTML = `
        <p class="rb-verdict rb-v-${r.truth}">${kindIcon(r.truth)}${esc(NAME[r.truth])}${r.kind === 'spherex' && r.label ? ` <span class="mono">(${esc(r.label)})</span>` : ''}</p>
        <p class="gm-q">${ok ? 'Right.' : `Not ${esc(NAME[a].toLowerCase())}.`} <span class="rb-plus mono">+${ok ? 10 : 0}</span></p>
        <p class="rb-say">${esc(r.say)}</p>
        ${r.kind === 'model' ? `<p class="gm-sub">This round is a model built from lab ice bands, not a measured comet.</p>` : r.kind === 'measured' ? `<p class="gm-sub">A real spectrum from the NASA IRTF telescope, resampled to SPHEREx colours.</p>` : ''}
        <div class="gm-row"><button class="btn btn-primary rb-next">${last ? 'See my score' : 'Next'}${icon('arrow')}</button>${r.slug ? `<a class="btn btn-ghost" href="#/object/${esc(r.slug)}">Open ${esc(r.name)}</a>` : ''}</div>`;
      next = () => (last ? end() : play(k + 1));
      const btn = q<HTMLButtonElement>('.rb-next');
      btn.onclick = () => next?.();
      btn.focus({ preventScroll: true });
    };
  };

  const end = () => {
    turn++;
    next = null;
    const n = rounds.length, right = results.filter((x) => x.ok).length;
    q('.rb').hidden = true;
    const fin = q('.gm-end');
    fin.hidden = false;
    body.closest('.page')?.scrollTo(0, 0);
    fin.innerHTML = `
      <p class="kicker">Rainbow Detective</p>
      <h2 class="gm-end-h"><b class="mono">${right * 10}</b> of ${n * 10}</h2>
      <p class="gm-end-lead">SPHEREx measures 102 colours for every object it sees, across the whole sky. That is how Rewind can start to tell what a new find is made of.</p>
      <ol class="gm-list">${KINDS.map((k) => {
        const of = results.filter((x) => x.truth === k.id);
        return of.length ? `<li><span>${k.name}</span><span class="mono">${of.filter((x) => x.ok).length} of ${of.length}</span></li>` : '';
      }).join('')}</ol>
      <div class="gm-row"><button class="btn btn-primary gm-again">Play again</button><button class="btn btn-ghost" data-game="hub">All games</button></div>`;
    q<HTMLButtonElement>('.gm-again').onclick = start;
  };

  const start = () => {
    rounds = [...shuffle(data.rounds), ...(data.bonus ? [data.bonus] : [])];
    results = [];
    q('.rb-pts').textContent = '0';
    play(0);
    if (!seenGuide) openGuide();
  };

  q('.rb-answers').addEventListener('click', (e) => {
    const b = (e.target as Element).closest<HTMLElement>('[data-a]');
    if (b) answer(b.dataset.a as Kind);
  });
  // point at an answer: its typical curve over the mystery one
  const peek = (e: Event) => {
    if (next) return;
    const leaving = e.type === 'pointerout' || e.type === 'focusout';
    const to = (leaving ? (e as PointerEvent | FocusEvent).relatedTarget : e.target) as Element | null;
    const k = (to?.closest?.('[data-a]')?.getAttribute('data-a') ?? null) as Kind | null;
    if (k === peeking) return;
    peeking = k;
    q('.rb-tpl').innerHTML = k ? tplPath(k, 'rb-t-peek') : '';
  };
  ['pointerover', 'pointerout', 'focusin', 'focusout'].forEach((t) => q('.rb-answers').addEventListener(t, peek));
  q<HTMLButtonElement>('.rb-hint').onclick = (e) => {
    if (!cur || next) return;
    const h = HINT[cur.r.truth];
    q('.rb-feat').innerHTML = `<rect class="rb-band rb-hint-band" x="${X(h.from)}" y="${Y0 - 8}" width="${X(h.to) - X(h.from)}" height="${Y1 - Y0 + 8}"/><text class="rb-band-t" x="${(X(h.from) + X(h.to)) / 2}" y="${Y0 + 10}">${h.text}</text>`;
    (e.currentTarget as HTMLButtonElement).disabled = true;
  };
  const onKey = (e: KeyboardEvent) => {
    if (e.metaKey || e.ctrlKey || e.altKey || q('.rb').hidden || guide.open) return;
    const a = KINDS.find((x) => x.key === e.key);
    if (a && !next) answer(a.id);
  };
  document.addEventListener('keydown', onKey);
  start();
  return () => {
    turn++;
    document.removeEventListener('keydown', onKey);
  };
};
