// Predict the orbit: three known positions of a real Rewind find on a map seen from above the
// solar system. Drag the marker to where it will be 30 days later, then see the true spot and
// how big the guess area is one year ahead, without and with the older SPHEREx positions.
import { getJson } from '../../lib/data';
import { plainDate } from '../../lib/time';
import type { ObjectPage } from '../../lib/types';
import { icon } from '../../ui/components';
import { esc } from '../../ui/dom';
import type { View } from '../page';
import { AHEAD_DAYS, AU_KM, buildRound, dist2, factorText, fmtKm, pickRounds, scoreGuess, type P2, type WhereRound } from './where-logic';

const S = 600; // chart size in SVG units
const shortDate = (mjd: number) => plainDate(mjd).replace(/,? \d{4}$/, '');

export const whereGame: View = async (body, ctx) => {
  const finds = ctx.source.index.objects.filter((o) => o.verdict === 'FOUND' && o.days_before_first_known_obs != null);
  const built = await Promise.all(
    finds.map((o) => getJson<ObjectPage>(ctx.source.base + o.page).then((p) => buildRound(o, p)).catch(() => null)),
  );
  const rounds = pickRounds(built.filter((r): r is WhereRound => !!r));
  if (!rounds.length) {
    body.innerHTML = `<p class="muted">No orbits to play with yet.</p>`;
    return;
  }
  const total = rounds.length;
  let scores: number[] = [];

  body.innerHTML = `
    <div class="wh">
      <header class="gm-bar">
        <h2 class="gm-title"></h2>
        <ol class="gm-prog" aria-label="Rounds"></ol>
        <p class="gm-score"><span class="mono">Score</span><b class="mono">0</b></p>
      </header>
      <div class="gm-stage">
        <div class="wh-map">
          <svg class="wh-svg" viewBox="0 0 ${S} ${S}" role="application" aria-label="Map of the inner solar system seen from above. Drag the gold marker to your guess."></svg>
          <p class="wh-scale mono"><i></i><span></span></p>
        </div>
        <div class="gm-side">
          <div class="wh-ask">
            <p class="gm-q">Where will it be <b>${AHEAD_DAYS} days later</b>?</p>
            <p class="gm-sub">Three known positions, 15 days apart. Drag the gold marker to your guess.</p>
            <button class="btn btn-primary wh-lock">Lock in my guess${icon('arrow')}</button>
          </div>
          <div class="wh-reveal" hidden></div>
        </div>
      </div>
    </div>
    <div class="gm-end" hidden></div>`;
  const q = <T extends Element = HTMLElement>(s: string) => body.querySelector(s) as T;
  const svg = q<SVGSVGElement>('.wh-svg'), ask = q('.wh-ask'), reveal = q('.wh-reveal');

  const play = (k: number) => {
    const r = rounds[k];
    q('.gm-title').textContent = r.name;
    q('.gm-prog').innerHTML = rounds.map((_, i) => `<li class="${i < k ? 'ok' : i === k ? 'now' : ''}"></li>`).join('');
    q('.gm-score b').textContent = String(scores.reduce((a, b) => a + b, 0));
    q('.wh').hidden = false;
    q('.gm-end').hidden = true;
    ask.hidden = false;
    reveal.hidden = true;

    // the view: centred on the last known position, wide enough for any sensible guess
    const last = r.dots[2].p, c = last;
    const hw = Math.max(1.05 * dist2(r.target.p, r.dots[0].p), 1e-4);
    const u = S / 2 / hw; // SVG units per AU
    const X = (p: P2) => S / 2 + (p[0] - c[0]) * u, Y = (p: P2) => S / 2 - (p[1] - c[1]) * u;
    const world = (x: number, y: number): P2 => [c[0] + (x - S / 2) / u, c[1] - (y - S / 2) / u];

    // rings around the Sun for a sense of place; the Sun itself, or an arrow to it at the edge
    const rSun = Math.hypot(c[0], c[1]);
    const stepAu = [0.1, 0.25, 0.5, 1, 2, 5].find((s) => hw / s < 4) ?? 10;
    let rings = '';
    for (let a = Math.max(stepAu, Math.ceil((rSun - hw * 1.5) / stepAu) * stepAu); a < rSun + hw * 1.5; a += stepAu)
      rings += `<circle class="wh-ring${Math.abs(a - 1) < 1e-6 ? ' earth' : ''}" cx="${X([0, 0])}" cy="${Y([0, 0])}" r="${a * u}"/>`;
    const sx = X([0, 0]), sy = Y([0, 0]);
    const sunIn = sx > 20 && sx < S - 20 && sy > 20 && sy < S - 20;
    const ang = Math.atan2(sy - S / 2, sx - S / 2), ex = S / 2 + Math.cos(ang) * (S / 2 - 34), ey = S / 2 + Math.sin(ang) * (S / 2 - 34);
    const sun = sunIn
      ? `<circle class="wh-sun" cx="${sx}" cy="${sy}" r="9"/><text class="wh-lab" x="${sx}" y="${sy + 26}">Sun</text>`
      : `<g transform="translate(${ex} ${ey})"><path class="wh-sunarrow" d="M0-7L14 0 0 7z" transform="rotate(${(ang * 180) / Math.PI})"/><text class="wh-lab" y="${ey > S / 2 ? -14 : 24}">to the Sun</text></g>`;
    const path = r.path.map((p) => `${X(p).toFixed(1)},${Y(p).toFixed(1)}`).join(' ');
    const start: P2 = [Math.min(S - 40, Math.max(40, X(last) + 60)), Math.min(S - 40, Math.max(40, Y(last) - 60))];
    svg.innerHTML = `
      <g class="wh-rings">${rings}</g>${sun}
      <polyline class="wh-path" points="${path}"/>
      <polyline class="wh-seen" points="${r.dots.map((d) => `${X(d.p)},${Y(d.p)}`).join(' ')}"/>
      ${r.dots.map((d, i) => `<g class="wh-dot" style="--i:${i}"><circle cx="${X(d.p)}" cy="${Y(d.p)}" r="6"/><text class="wh-lab" x="${X(d.p)}" y="${Y(d.p) + 24}">${esc(shortDate(d.mjd))}</text></g>`).join('')}
      <g class="wh-truth" hidden><line class="wh-miss"/><circle class="wh-pulse" cx="${X(r.target.p)}" cy="${Y(r.target.p)}" r="8"/><circle class="wh-true" cx="${X(r.target.p)}" cy="${Y(r.target.p)}" r="7"/><text class="wh-lab wh-lab-true" x="${X(r.target.p)}" y="${Y(r.target.p) - 16}">${esc(shortDate(r.target.mjd))}</text></g>
      <g class="wh-guess" tabindex="0" role="slider" aria-label="Your guess" aria-valuetext="Use the arrow keys to move"><circle class="wh-hit" r="30"/><circle class="wh-g-ring" r="13"/><circle class="wh-g-dot" r="3.5"/><text class="wh-lab wh-lab-g" y="-22">?</text></g>`;
    // a round scale bar
    const barAu = [0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1, 2].find((b) => b * u > 60) ?? 5;
    q<HTMLElement>('.wh-scale i').style.width = `${((barAu * u) / S) * 100}%`;
    q('.wh-scale span').textContent = fmtKm(barAu * AU_KM);

    const g = svg.querySelector('.wh-guess') as SVGGElement;
    let pos = start, locked = false, moved = false;
    const place = (x: number, y: number) => {
      pos = [Math.min(S - 8, Math.max(8, x)), Math.min(S - 8, Math.max(8, y))];
      g.setAttribute('transform', `translate(${pos[0]} ${pos[1]})`);
    };
    place(start[0], start[1]);
    const toSvg = (e: PointerEvent): P2 => {
      const b = svg.getBoundingClientRect();
      return [((e.clientX - b.left) / b.width) * S, ((e.clientY - b.top) / b.height) * S];
    };
    svg.onpointerdown = (e) => {
      if (locked) return;
      svg.setPointerCapture(e.pointerId);
      moved = true;
      svg.classList.add('drag', 'moved');
      place(...toSvg(e));
      e.preventDefault();
    };
    svg.onpointermove = (e) => {
      if (!locked && svg.hasPointerCapture(e.pointerId)) place(...toSvg(e));
    };
    svg.onpointerup = svg.onpointercancel = (e) => {
      if (svg.hasPointerCapture(e.pointerId)) svg.releasePointerCapture(e.pointerId);
      svg.classList.remove('drag');
    };
    g.onkeydown = (e) => {
      const d = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1] }[e.key];
      if (!d || locked) return;
      e.preventDefault();
      moved = true;
      svg.classList.add('moved');
      place(pos[0] + d[0] * (e.shiftKey ? 30 : 6), pos[1] + d[1] * (e.shiftKey ? 30 : 6));
    };
    svg.classList.remove('done', 'moved');

    q<HTMLButtonElement>('.wh-lock').onclick = () => {
      if (locked) return;
      if (!moved) {
        svg.classList.add('nudge');
        setTimeout(() => svg.classList.remove('nudge'), 600);
        return;
      }
      locked = true;
      const guess = world(pos[0], pos[1]);
      const pts = scoreGuess(guess, r.target.p, last);
      scores[k] = pts;
      const missKm = dist2(guess, r.target.p) * AU_KM;
      const miss = svg.querySelector('.wh-miss')!;
      miss.setAttribute('x1', String(pos[0]));
      miss.setAttribute('y1', String(pos[1]));
      miss.setAttribute('x2', String(X(r.target.p)));
      miss.setAttribute('y2', String(Y(r.target.p)));
      svg.querySelector('.wh-truth')!.removeAttribute('hidden');
      svg.classList.add('done');
      q('.gm-score b').textContent = String(scores.reduce((a, b) => a + b, 0));

      // the guess area one year ahead: the same shape, drawn to scale, without and with the old photos
      const z = r.sizes, big = Math.max(z.before_km, z.after_km), R = 84;
      const deg = (-r.shape.angle * 180) / Math.PI, ratio = Math.max(0.14, r.shape.ratio);
      const ell = (km: number, cls: string) => `<ellipse class="${cls}" rx="${Math.max(2, (km / big) * R)}" ry="${Math.max(1.5, (km / big) * R * ratio)}" transform="rotate(${deg})"/>`;
      const days = r.days_earlier;
      const last5 = k + 1 === total;
      ask.hidden = true;
      reveal.hidden = false;
      reveal.innerHTML = `
        <p class="wh-pts"><b>+${pts}</b><span>${pts >= 85 ? 'Spot on.' : pts >= 55 ? 'Close.' : pts > 0 ? 'Not far.' : 'It went elsewhere.'} ${esc(fmtKm(missKm))} off.</span></p>
        <div class="wh-lens">
          <svg viewBox="-100 -100 200 200" aria-hidden="true">${ell(z.before_km, 'wh-e-before')}${ell(z.after_km, 'wh-e-after')}<circle class="wh-e-c" r="2.5"/></svg>
          <div class="wh-lens-t">
            <p class="wh-factor">${esc(factorText(z.factor))}</p>
            <p class="wh-leg"><i class="before"></i>Without the old photos<b class="mono">${esc(fmtKm(z.before_km))}</b></p>
            <p class="wh-leg"><i class="after"></i>With SPHEREx${days ? `, ${days} days earlier` : ''}<b class="mono">${esc(fmtKm(z.after_km))}</b></p>
          </div>
        </div>
        <p class="gm-sub">The guess area one year ahead${z.scenario ? ', as if Rewind had run in discovery week (computed scenario)' : ', from every observation so far (computed)'}.</p>
        <div class="gm-row">
          <button class="btn btn-primary wh-next">${last5 ? 'See my score' : 'Next asteroid'}${icon('arrow')}</button>
          <a class="btn btn-ghost" href="#/object/${esc(r.slug)}">Open ${esc(r.name)}</a>
        </div>`;
      const next = q<HTMLButtonElement>('.wh-next');
      next.onclick = () => (last5 ? end() : play(k + 1));
      next.focus({ preventScroll: true });
    };
  };

  const end = () => {
    const sum = scores.reduce((a, b) => a + b, 0);
    q('.wh').hidden = true;
    const fin = q('.gm-end');
    fin.hidden = false;
    body.closest('.page')?.scrollTo(0, 0);
    fin.innerHTML = `
      <p class="kicker">Predict the orbit</p>
      <h2 class="gm-end-h"><b class="mono">${sum}</b> of ${total * 100}</h2>
      <p class="gm-end-lead">${sum >= total * 75 ? 'You think like an orbit.' : sum >= total * 45 ? 'A good eye for motion.' : 'Orbits curve and speed up. That is why every extra position counts.'}</p>
      <ol class="gm-list">${rounds.map((r, i) => `<li><a href="#/object/${esc(r.slug)}">${esc(r.name)}</a><span class="mono">+${scores[i] ?? 0}</span><span class="gm-list-n">old photos: ${esc(factorText(r.sizes.factor))}</span></li>`).join('')}</ol>
      <div class="gm-row"><button class="btn btn-primary gm-again">Play again</button><button class="btn btn-ghost" data-game="hub">All games</button></div>`;
    q<HTMLButtonElement>('.gm-again').onclick = () => {
      scores = [];
      play(0);
    };
  };

  play(0);
};
