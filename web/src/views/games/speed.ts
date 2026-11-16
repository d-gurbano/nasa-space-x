// Star speedometer: two real SPHEREx season stacks of one star, months apart, blink back and
// forth. The player drags a marker from the star's first position to where it sits in the later
// image; the shift becomes arcsec and arcsec per year, then we show our measured shift and Gaia's.
import '../../styles/game-speed.css';
import { plainDate } from '../../lib/time';
import { icon } from '../../ui/components';
import { esc, fmt } from '../../ui/dom';
import { reducedMotion } from '../../state';
import type { View } from '../page';
import { confetti } from './confetti';
import { clamp, compass, perYear, pxToSky, score, type SpeedData, type SpeedRound } from './speed-logic';

const VIEW = 200; // crop size in PNG px (37.5 arcsec)
const BLINK_MS = 800;

// one plain lesson per star; distances from Gaia DR3 parallaxes (546.98, 270.66, 6.41 mas)
const TEACH: Record<string, string> = {
  barnard: 'Barnard’s Star is 6 light years away, one of the Sun’s closest neighbours. It has the largest proper motion of any star, about 10.4″ a year, so it crosses the width of the full Moon in about 175 years.',
  epsindib: 'Epsilon Indi B is a pair of brown dwarfs 12 light years away. It moves 4.7″ a year, less than one SPHEREx pixel, yet the shift shows when two passes a year apart are compared.',
  rwaur: 'RW Aurigae is a young star about 510 light years away. At that distance its drift is 0.03″ a year, far too small to see. Most stars look fixed for this reason.',
};
const SATURATED: Record<string, string> = {
  barnard: 'Its centre is saturated (white), so we measured the position from the edges of the glow.',
  rwaur: 'Its centre is saturated in most images, so our position has an error of a few tenths of an arcsecond.',
};

export const view: View = async (body, ctx) => {
  const { data } = await ctx.load<SpeedData>('games/speed/rounds.json');
  if (!data.rounds?.length) {
    body.innerHTML = `<p class="muted">No rounds are available yet.</p>`;
    return;
  }
  const rounds = data.rounds, total = rounds.length, S = data.scale_arcsec_per_px, N = data.size_px;
  const img = (r: SpeedRound, e: 'a' | 'b') => ctx.source.base + `stars/${r.slug}/${r[e].season}`;
  const pxPerSpx = 6.15 / S;
  let scores: number[] = [], mine: number[] = [], timer = 0, showB = false, blinking = !reducedMotion;

  body.innerHTML = `
    <div class="sp">
      <header class="gm-bar">
        <h2 class="gm-title">Star speedometer</h2>
        <ol class="gm-prog" aria-label="Rounds"></ol>
        <p class="gm-score"><span class="mono">Score</span><b class="mono sp-pts">0</b></p>
      </header>
      <p class="gm-sub sp-intro">Nearby stars drift slowly across the sky, a motion called proper motion. Compare two SPHEREx images taken months apart, mark where the star moved, and we turn your mark into a speed.</p>
      <div class="gm-stage">
        <figure class="sp-fig">
          <svg class="sp-svg" role="application" aria-label="Two SPHEREx images of the star, north up and east left. Drag the gold marker to where the star is in the later image."></svg>
          <figcaption class="sp-cap mono"><span class="sp-now"></span><span class="sp-dir">N up, E left</span></figcaption>
          <div class="gm-row sp-flip" role="group" aria-label="Which image to show">
            <button type="button" class="btn btn-ghost sp-ep" data-ep="a"></button>
            <button type="button" class="btn btn-ghost sp-ep" data-ep="b"></button>
            <button type="button" class="btn btn-ghost sp-blink" aria-pressed="false">Blink</button>
          </div>
        </figure>
        <div class="gm-side">
          <div class="sp-ask">
            <p class="sp-who mono"></p>
            <p class="gm-q">Where is the star in the <b>later</b> image?</p>
            <p class="gm-sub">The dashed ring marks where it was in the first image. Drag the gold marker to the centre of the star in the second image. Arrow keys move it in small steps (hold Shift for larger ones).</p>
            <p class="sp-read mono" aria-live="polite"></p>
            <button class="btn btn-primary sp-lock">Measure my shift${icon('arrow')}</button>
          </div>
          <div class="sp-reveal" hidden></div>
        </div>
      </div>
    </div>
    <div class="gm-end" hidden></div>`;
  const q = <T extends Element = HTMLElement>(s: string) => body.querySelector(s) as T;
  const svg = q<SVGSVGElement>('.sp-svg'), ask = q('.sp-ask'), reveal = q('.sp-reveal');

  const setEpoch = (b: boolean) => {
    showB = b;
    svg.classList.toggle('show-b', b);
    body.querySelectorAll<HTMLButtonElement>('.sp-ep').forEach((x) => x.setAttribute('aria-pressed', String((x.dataset.ep === 'b') === b)));
    const r = cur;
    if (r) q('.sp-now').textContent = `${b ? 'Second' : 'First'} image, ${plainDate(r[b ? 'b' : 'a'].mjd)}`;
  };
  const setBlink = (on: boolean) => {
    blinking = on;
    clearInterval(timer);
    q('.sp-blink').setAttribute('aria-pressed', String(on));
    if (on) timer = window.setInterval(() => setEpoch(!showB), BLINK_MS);
  };
  body.querySelectorAll<HTMLButtonElement>('.sp-ep').forEach((b) => (b.onclick = () => {
    setBlink(false);
    setEpoch(b.dataset.ep === 'b');
  }));
  q<HTMLButtonElement>('.sp-blink').onclick = () => setBlink(!blinking);

  let cur: SpeedRound | null = null;

  const play = (k: number) => {
    const r = rounds[k];
    cur = r;
    const days = r.b.mjd - r.a.mjd;
    q('.sp').hidden = false;
    q('.gm-end').hidden = true;
    q('.gm-prog').innerHTML = rounds.map((_, i) => `<li class="${i < k ? (scores[i] >= 7 ? 'ok' : scores[i] > 0 ? 'half' : 'no') : i === k ? 'now' : ''}"></li>`).join('');
    q('.sp-pts').textContent = String(scores.reduce((a, b) => a + b, 0));
    q('.sp-who').textContent = `Round ${k + 1} of ${total} · ${r.name} · ${fmt(days)} days apart`;
    q('[data-ep="a"]').textContent = plainDate(r.a.mjd);
    q('[data-ep="b"]').textContent = plainDate(r.b.mjd);
    ask.hidden = false;
    reveal.hidden = true;

    // crop around the two positions so a small shift is easy to see
    const cx = (r.a.xy[0] + r.b.xy[0]) / 2, cy = (r.a.xy[1] + r.b.xy[1]) / 2;
    const vx = clamp(cx - VIEW / 2, 0, N - VIEW), vy = clamp(cy - VIEW / 2, 0, N - VIEW);
    svg.setAttribute('viewBox', `${vx} ${vy} ${VIEW} ${VIEW}`);
    const [ax, ay] = r.a.xy, [bx, by] = r.b.xy;
    const sbX = vx + 10, sbY = vy + VIEW - 12;
    svg.innerHTML = `
      <image class="sp-img sp-img-a" href="${esc(img(r, 'a'))}" x="0" y="0" width="${N}" height="${N}"/>
      <image class="sp-img sp-img-b" href="${esc(img(r, 'b'))}" x="0" y="0" width="${N}" height="${N}"/>
      <g class="sp-start"><circle cx="${ax}" cy="${ay}" r="9"/><line x1="${ax - 15}" x2="${ax - 11}" y1="${ay}" y2="${ay}"/><line x1="${ax + 11}" x2="${ax + 15}" y1="${ay}" y2="${ay}"/><line x1="${ax}" x2="${ax}" y1="${ay - 15}" y2="${ay - 11}"/><line x1="${ax}" x2="${ax}" y1="${ay + 11}" y2="${ay + 15}"/></g>
      <g class="sp-truth" hidden><line class="sp-arrow" x1="${ax}" y1="${ay}" x2="${bx}" y2="${by}"/><circle cx="${bx}" cy="${by}" r="2.6"/><circle class="sp-truth-ring" cx="${bx}" cy="${by}" r="${1 / S}"/></g>
      <line class="sp-you" x1="${ax}" y1="${ay}" x2="${ax}" y2="${ay}"/>
      <g class="sp-mark" tabindex="0" role="slider" aria-label="Your marker. Use the arrow keys to move it." aria-valuetext="no shift yet"><circle class="sp-hit" r="16"/><circle class="sp-m-ring" r="6.5"/><circle class="sp-m-dot" r="1.4"/></g>
      <g class="sp-scale"><line x1="${sbX}" x2="${sbX + pxPerSpx}" y1="${sbY}" y2="${sbY}"/><text x="${sbX}" y="${sbY - 5}">one SPHEREx pixel, 6.15″</text></g>`;

    const g = svg.querySelector('.sp-mark') as SVGGElement, you = svg.querySelector('.sp-you') as SVGLineElement;
    let pos: [number, number] = [ax, ay], locked = false;
    const read = () => {
      const s = pxToSky(pos[0] - ax, pos[1] - ay, S);
      const dir = compass(s.east, s.north, 0.3);
      const txt = `Your shift ${fmt(s.total, 1)}″${dir ? ` ${dir}` : ''} · ${fmt(perYear(s.total, days), 1)}″ per year`;
      q('.sp-read').textContent = txt;
      g.setAttribute('aria-valuetext', txt);
      return s;
    };
    const place = (x: number, y: number) => {
      pos = [clamp(x, vx + 2, vx + VIEW - 2), clamp(y, vy + 2, vy + VIEW - 2)];
      g.setAttribute('transform', `translate(${pos[0]} ${pos[1]})`);
      you.setAttribute('x2', String(pos[0]));
      you.setAttribute('y2', String(pos[1]));
      read();
    };
    place(ax, ay);
    const toSvg = (e: PointerEvent): [number, number] => {
      const b = svg.getBoundingClientRect();
      return [vx + ((e.clientX - b.left) / b.width) * VIEW, vy + ((e.clientY - b.top) / b.height) * VIEW];
    };
    svg.onpointerdown = (e) => {
      if (locked) return;
      svg.setPointerCapture(e.pointerId);
      svg.classList.add('drag');
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
      const d = ({ ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1] } as Record<string, number[]>)[e.key];
      if (!d || locked) return;
      e.preventDefault();
      const step = e.shiftKey ? 5 : 1;
      place(pos[0] + d[0] * step, pos[1] + d[1] * step);
    };
    svg.classList.remove('done');
    setEpoch(false);
    setBlink(blinking);

    q<HTMLButtonElement>('.sp-lock').onclick = () => {
      if (locked) return;
      locked = true;
      const s = read();
      const missArc = Math.hypot(pos[0] - bx, pos[1] - by) * S;
      const pts = score(missArc);
      scores[k] = pts;
      mine[k] = perYear(s.total, days);
      svg.querySelector('.sp-truth')!.removeAttribute('hidden');
      svg.classList.add('done');
      q('.sp-pts').textContent = String(scores.reduce((a, b) => a + b, 0));
      const meas = Math.hypot(r.meas_east, r.meas_north), dir = compass(r.meas_east, r.meas_north, 1);
      const gaia = r.gaia_mas_yr / 1000;
      const halfYear = Math.abs(days - 365.25) > 60;
      const last = k + 1 === total;
      ask.hidden = true;
      reveal.hidden = false;
      reveal.innerHTML = `
        <p class="sp-pts-line"><b class="mono">+${pts}</b><span>${pts === 10 ? 'Spot on.' : pts >= 7 ? 'Close.' : pts > 0 ? 'Not far.' : 'Some way off.'} Your mark was ${fmt(missArc, 1)}″ from where we measured the star.</span></p>
        <dl class="sp-nums">
          <div><dt>Your speed</dt><dd class="mono">${fmt(mine[k], 1)}″/yr</dd></div>
          <div><dt>We measured</dt><dd class="mono">${fmt(meas, meas < 1 ? 2 : 1)}″ in ${fmt(days)} days${dir ? `, ${dir}` : ''}</dd></div>
          <div><dt>Gaia DR3</dt><dd class="mono">${fmt(gaia, gaia < 1 ? 3 : 1)}″/yr</dd></div>
        </dl>
        <p class="sp-say">${esc(TEACH[r.slug] ?? '')}</p>
        ${halfYear ? `<p class="gm-sub">These passes are about half a year apart, so part of the shift is parallax, the small yearly wobble caused by Earth moving around the Sun. Passes a year apart cancel it.</p>` : ''}
        ${r.slug === 'rwaur' ? `<p class="gm-sub">Our ${fmt(meas, 2)}″ is under a tenth of a SPHEREx pixel and within the error of our fit to a saturated star, so we read it as no real motion.</p>` : ''}
        ${SATURATED[r.slug] ? `<p class="gm-sub">${esc(SATURATED[r.slug])}</p>` : ''}
        <div class="gm-row"><button class="btn btn-primary sp-next">${last ? 'See my score' : 'Next star'}${icon('arrow')}</button></div>`;
      if (pts >= 7) confetti(q('.sp-pts-line'));
      const nx = q<HTMLButtonElement>('.sp-next');
      nx.onclick = () => (last ? end() : play(k + 1));
      nx.focus({ preventScroll: true });
    };
  };

  const end = () => {
    setBlink(false);
    blinking = !reducedMotion;
    const sum = scores.reduce((a, b) => a + b, 0);
    q('.sp').hidden = true;
    const fin = q('.gm-end');
    fin.hidden = false;
    body.closest('.page')?.scrollTo(0, 0);
    fin.innerHTML = `
      <p class="kicker">Star speedometer</p>
      <h2 class="gm-end-h"><b class="mono">${sum}</b> of ${total * 10}</h2>
      <p class="gm-end-lead">Barnard’s Star moved about 10.4″ in one year in our SPHEREx images, as Gaia predicts (10.3″). The closer a star is, the faster it seems to move, so the fastest movers are our nearest neighbours.</p>
      <ol class="gm-list">${rounds.map((r, i) => `<li><span>${esc(r.name)}, ${fmt(r.b.mjd - r.a.mjd)} days</span><span class="mono">you ${fmt(mine[i] ?? 0, 1)}″/yr</span><span class="gm-list-n">Gaia ${fmt(r.gaia_mas_yr / 1000, r.gaia_mas_yr < 1000 ? 3 : 1)}″/yr</span></li>`).join('')}</ol>
      <p class="gm-sub sp-src">Where the data comes from. SPHEREx season stacks from NASA/IPAC IRSA, star positions we measured with point-spread-function fits, and proper motions from ESA Gaia DR3.</p>
      <div class="gm-row"><button class="btn btn-primary gm-again">Play again</button><button class="btn btn-ghost" data-game="hub">All games</button></div>`;
    q<HTMLButtonElement>('.gm-again').onclick = () => {
      scores = [];
      mine = [];
      play(0);
    };
  };

  play(0);
  return () => clearInterval(timer);
};
