// Blink!: two real SPHEREx images of the same patch of sky flip back and forth. Stars stay put;
// the one dot that jumps is a known asteroid. Tap it, then see its name and how far it moved.
import '../../styles/game-blink.css';
import { icon } from '../../ui/components';
import { esc, provenance } from '../../ui/dom';
import { reducedMotion } from '../../state';
import { confetti } from './confetti';
import type { View } from '../page';
import { isHit, missBy, pickRounds, points, span, toPixel, type BlinkData, type BlinkRound } from './blink-logic';

const ROUNDS = 7;
const FLIP_MS = reducedMotion ? 1100 : 650;

export const view: View = async (body, ctx) => {
  const { data, sample } = await ctx.load<BlinkData>('games/blink/rounds.json');
  if (!data.rounds?.length) {
    body.innerHTML = `<p class="muted">No rounds are available yet.</p>`;
    return;
  }
  const N = data.n, base = ctx.source.base + 'games/blink/';
  let rounds: BlinkRound[] = [], results: { ok: boolean; pts: number; r: BlinkRound }[] = [], turn = 0;

  body.innerHTML = `
    <div class="bk">
      <header class="gm-bar">
        <h2 class="gm-title">Blink!</h2>
        <ol class="gm-prog" aria-label="Rounds"></ol>
        <p class="gm-score"><span class="mono">Score</span><b class="mono bk-pts">0</b></p>
      </header>
      <div class="gm-stage">
        <figure class="bk-fig">
          <p class="bk-who"><span class="mono bk-round"></span><span class="mono bk-frame"></span></p>
          <div class="bk-sky" tabindex="0" role="application" aria-label="Two SPHEREx images of the same sky. Tap the dot that moves. Keyboard: arrow keys move the cursor, Enter taps, Space flips the images.">
            <img class="bk-img" alt="" draggable="false"><img class="bk-img" alt="" draggable="false">
            <svg class="bk-over" viewBox="0 0 ${N} ${N}" aria-hidden="true"></svg>
          </div>
          <p class="bk-scale"><span>North up, east left</span><span class="mono bk-size"></span></p>
        </figure>
        <div class="gm-side">
          <div class="bk-ask">
            <p class="gm-q">Tap the dot that <b>moved</b>.</p>
            <p class="gm-sub">These two SPHEREx images show the same patch of sky, taken some time apart. Stars stay put. An asteroid jumps.</p>
            <p class="gm-sub">In 1930 Clyde Tombaugh found Pluto the same way, by blinking two photographic plates of the same stars.</p>
            <div class="gm-row"><button type="button" class="btn btn-ghost bk-flip">Pause blinking</button><button type="button" class="btn btn-ghost bk-hint">Hint</button></div>
            <p class="bk-msg gm-sub" aria-live="polite"></p>
          </div>
          <div class="bk-reveal" hidden></div>
        </div>
      </div>
      <div class="tr-foot">${provenance(sample, 'Real SPHEREx L2 images, read from the public IRSA archive on AWS')}<p class="rb-note">Where the data comes from: SPHEREx Level 2 exposures (NASA/IPAC IRSA, public AWS bucket nasa-irsa-spherex). The asteroid positions come from our answer key of known objects, computed from JPL orbits for each exposure. Both images are on the same detector at nearly the same wavelength, turned north up, and scaled by their own background so the stars match.</p></div>
    </div>
    <div class="gm-end" hidden></div>`;
  const q = <T extends Element = HTMLElement>(s: string) => body.querySelector(s) as T;
  const sky = q('.bk-sky'), over = q<SVGSVGElement>('.bk-over'), imgs = [...body.querySelectorAll<HTMLImageElement>('.bk-img')];
  const ask = q('.bk-ask'), reveal = q('.bk-reveal'), msg = q('.bk-msg'), flipBtn = q<HTMLButtonElement>('.bk-flip');

  // the blinking
  let shown = 0, timer = 0, paused = false;
  const show = (i: number) => {
    shown = i;
    imgs.forEach((im, k) => im.classList.toggle('on', k === i));
    const r = rounds[cur];
    if (r) q('.bk-frame').textContent = `Image ${i + 1} · ${r.um[i].toFixed(2)} µm`;
  };
  const stop = () => {
    clearInterval(timer);
    timer = 0;
  };
  const run = () => {
    stop();
    if (!paused) timer = window.setInterval(() => show(1 - shown), FLIP_MS);
  };
  const setPaused = (p: boolean) => {
    paused = p;
    flipBtn.textContent = p ? 'Flip image' : 'Pause blinking';
    run();
  };
  flipBtn.onclick = () => (paused ? show(1 - shown) : setPaused(true));
  flipBtn.ondblclick = () => setPaused(false);

  // the keyboard cursor
  let cur = 0, tries = 0, done = false, kx = (N - 1) / 2, ky = (N - 1) / 2, keyed = false;
  const marks: string[] = [];
  const drawOver = (extra = '') => {
    over.innerHTML = marks.join('') + (keyed && !done ? `<g class="bk-cur"><circle cx="${kx}" cy="${ky}" r="2.5"/><path d="M${kx - 4} ${ky}h2.2M${kx + 1.8} ${ky}h2.2M${kx} ${ky - 4}v2.2M${kx} ${ky + 1.8}v2.2"/></g>` : '') + extra;
  };

  let next: (() => void) | null = null;
  const play = (k: number) => {
    const me = ++turn;
    cur = k;
    tries = 0;
    done = false;
    next = null;
    marks.length = 0;
    keyed = false;
    kx = ky = (N - 1) / 2;
    const r = rounds[k];
    q('.bk').hidden = false;
    q('.gm-end').hidden = true;
    q('.gm-prog').innerHTML = rounds.map((_, i) => `<li class="${i < k ? (results[i].pts === 10 ? 'ok' : results[i].ok ? 'half' : 'no') : i === k ? 'now' : ''}"></li>`).join('');
    q('.bk-round').textContent = `Round ${k + 1} of ${rounds.length}`;
    q('.bk-size').textContent = `${Math.round((N * data.arcsec_per_px) / 60)} arcminutes across`;
    imgs.forEach((im, i) => {
      im.src = base + r.imgs[i];
      im.alt = `SPHEREx image ${i + 1} of 2`;
    });
    sky.classList.remove('done');
    ask.hidden = false;
    reveal.hidden = true;
    msg.textContent = '';
    q<HTMLButtonElement>('.bk-hint').disabled = false;
    drawOver();
    show(0);
    setPaused(false);

    tap = (x, y) => {
      if (done || me !== turn) return;
      tries++;
      const hit = isHit(r, x, y);
      if (!hit && tries < 2) {
        marks.push(`<circle class="bk-miss" cx="${x}" cy="${y}" r="1.6"/>`);
        drawOver();
        msg.textContent = missBy(r, x, y) < 8 ? 'Close, but that is not it. One more try.' : 'That dot stays put in both images. One more try.';
        return;
      }
      finish(hit);
    };

    const finish = (hit: boolean) => {
      done = true;
      const pts = points(tries, hit);
      results[k] = { ok: hit, pts, r };
      q('.bk-pts').textContent = String(results.reduce((s, x) => s + x.pts, 0));
      sky.classList.add('done');
      const [[ax, ay], [bx, by]] = r.pos;
      drawOver(`<line class="bk-path" x1="${ax}" y1="${ay}" x2="${bx}" y2="${by}"/>
        <circle class="bk-at" cx="${ax}" cy="${ay}" r="2.6"/><circle class="bk-at" cx="${bx}" cy="${by}" r="2.6"/>
        <text class="bk-lab" x="${ax}" y="${ay - 4}">1</text><text class="bk-lab" x="${bx}" y="${by - 4}">2</text>`);
      setPaused(false);
      const last = k + 1 === rounds.length;
      ask.hidden = true;
      reveal.hidden = false;
      reveal.innerHTML = `
        <p class="rb-verdict">Asteroid <span class="mono">${esc(r.name)}</span></p>
        <p class="gm-q">${hit ? 'Found it.' : 'This one got away.'} <span class="rb-plus mono">+${pts}</span></p>
        <p class="rb-say">${esc(r.name)} moved ${r.moved_px.toFixed(1)} pixels (${Math.round(r.moved_arcsec)} arcseconds) in ${span(r.hours)}.</p>
        <p class="gm-sub">It orbits the Sun ${r.r_au.toFixed(1)} times as far out as Earth, so it shifts against the far-off stars within hours. The stars are so distant that they do not move at all here.</p>
        <dl class="bk-facts">
          <div><dt>Brightness in visible light</dt><dd class="mono">V ${r.V.toFixed(1)}</dd></div>
          <div><dt>Peak above the noise</dt><dd class="mono">${Math.round(r.snr)} times</dd></div>
          <div><dt>Wavelengths</dt><dd class="mono">${r.um[0].toFixed(2)} and ${r.um[1].toFixed(2)} µm</dd></div>
          <div><dt>Exposures</dt><dd class="mono">${esc(r.obsid[0])}<br>${esc(r.obsid[1])}</dd></div>
        </dl>
        <div class="gm-row"><button class="btn btn-primary bk-next">${last ? 'See my score' : 'Next'}${icon('arrow')}</button></div>`;
      if (hit) confetti(reveal.querySelector<HTMLElement>('.gm-q') ?? reveal);
      next = () => (last ? end() : play(k + 1));
      const btn = q<HTMLButtonElement>('.bk-next');
      btn.onclick = () => next?.();
      btn.focus({ preventScroll: true });
    };

    q<HTMLButtonElement>('.bk-hint').onclick = (e) => {
      if (done) return;
      // a ring around the region, not the dot itself
      const [[ax, ay], [bx, by]] = r.pos;
      const cx = (ax + bx) / 2, cy = (ay + by) / 2, rad = Math.max(8, Math.hypot(bx - ax, by - ay) / 2 + 6);
      marks.push(`<circle class="bk-hintring" cx="${cx}" cy="${cy}" r="${rad}"/>`);
      drawOver();
      msg.textContent = 'It is somewhere inside the ring.';
      (e.currentTarget as HTMLButtonElement).disabled = true;
    };
  };
  let tap: (x: number, y: number) => void = () => {};

  sky.addEventListener('pointerdown', (e) => {
    if (done) return;
    const [x, y] = toPixel(e.clientX, e.clientY, sky.getBoundingClientRect(), N);
    keyed = false;
    tap(x, y);
  });
  sky.addEventListener('keydown', (e) => {
    if (done) return;
    const step = e.shiftKey ? 4 : 1;
    const mv: Record<string, [number, number]> = { ArrowLeft: [-step, 0], ArrowRight: [step, 0], ArrowUp: [0, -step], ArrowDown: [0, step] };
    if (mv[e.key]) {
      keyed = true;
      kx = Math.max(0, Math.min(N - 1, kx + mv[e.key][0]));
      ky = Math.max(0, Math.min(N - 1, ky + mv[e.key][1]));
      drawOver();
    } else if (e.key === 'Enter') {
      if (!keyed) {
        keyed = true;
        drawOver();
      } else tap(kx, ky);
    } else if (e.key === ' ') {
      if (!paused) setPaused(true);
      else show(1 - shown);
    } else return;
    e.preventDefault();
  });
  sky.addEventListener('focus', () => {
    keyed = true;
    if (!done) drawOver();
  });

  const end = () => {
    turn++;
    next = null;
    stop();
    const n = rounds.length, score = results.reduce((s, x) => s + x.pts, 0);
    q('.bk').hidden = true;
    const fin = q('.gm-end');
    fin.hidden = false;
    body.closest('.page')?.scrollTo(0, 0);
    fin.innerHTML = `
      <p class="kicker">Blink!</p>
      <h2 class="gm-end-h"><b class="mono">${score}</b> of ${n * 10}</h2>
      <p class="gm-end-lead">You found ${results.filter((x) => x.ok).length} of ${n} asteroids. Rewind does the same search by computer, on thousands of SPHEREx images, and then stacks them to reach objects too faint to see in one image.</p>
      <ol class="gm-list">${results.map((x) => `<li><span>${esc(x.r.name)}</span><span class="gm-list-n mono">${x.r.moved_px.toFixed(1)} px in ${span(x.r.hours)}</span><span class="mono">${x.ok ? `+${x.pts}` : 'missed'}</span></li>`).join('')}</ol>
      <p class="rb-note">Where the data comes from: real SPHEREx Level 2 images from NASA/IPAC IRSA, with asteroid positions from JPL orbits in our known-object answer key.</p>
      <div class="gm-row"><button class="btn btn-primary gm-again">Play again</button><button class="btn btn-ghost" data-game="hub">All games</button></div>`;
    q<HTMLButtonElement>('.gm-again').onclick = start;
  };

  const start = () => {
    rounds = pickRounds(data.rounds, ROUNDS);
    results = [];
    q('.bk-pts').textContent = '0';
    play(0);
  };

  const onKey = (e: KeyboardEvent) => {
    if (e.metaKey || e.ctrlKey || e.altKey || q('.bk').hidden) return;
    if (e.key === 'Enter' && next && document.activeElement === sky) next();
  };
  document.addEventListener('keydown', onKey);
  start();
  return () => {
    turn++;
    stop();
    document.removeEventListener('keydown', onKey);
  };
};
