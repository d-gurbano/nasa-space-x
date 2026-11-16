// Tune the Rewind: shift-and-stack by hand. Each round is a set of real SPHEREx photos of one
// fixed patch of sky, with the still sky taken away. Turn the direction dial and the speed tape:
// the photos are shifted by that motion and averaged, live. At the object's real motion its light
// lands on one spot and a dot appears that no single photo shows. That is exactly how Rewind works.
import '../../styles/page-detectives.css';
import { calibrate, endError, findPeak, halfSpan, midTime, pixelStats, snrAt, stack, velocity, wrap360, boxSum, median, type Calib, type Frames, type Motion, type XY } from '../game/stack';
import { sampleRounds, type GameData, type GameRound, type SampleRound } from '../game/rounds';
import { directionDial, speedTape } from '../game/controls';
import { INTRO_LINES, playIntro } from '../game/intro';
import { shareCard } from '../game/share';
import { icon } from '../../ui/components';
import { esc, provenance } from '../../ui/dom';
import { reducedMotion } from '../../state';
import { rel, type View } from '../page';

const KEY = 'rewind.tune';
const LOCK_PX = 6; // the object may be off by this many image pixels at the ends of the set
const RADII = [5, 10, 20, 40]; // box sizes for the S/N, so a smeared dot still warms the meter
const ZONE = 0.72; // the target zone starts at this share of the meter
const FULL = 0.9; // where the true motion's signal sits on the meter

interface Store { seen?: boolean; best?: number }
const store = (): Store => {
  try {
    return JSON.parse(localStorage.getItem(KEY) ?? '{}') as Store;
  } catch {
    return {};
  }
};
const save = (s: Store) => {
  try {
    localStorage.setItem(KEY, JSON.stringify({ ...store(), ...s }));
  } catch {
    // private browsing: nothing is kept
  }
};

/** A round ready to play: something that turns a motion into a stacked image, plus its calibration. */
interface Ready {
  w: number;
  h: number;
  n: number; // photos in the set
  dt: number[];
  truth: Motion;
  rmax: number; // the top of the speed tape, pixels per hour
  render(m: Motion, out: Float32Array, cover: Uint8Array): void;
  spot: XY; // where the object sits in the true stack
  cal: Calib;
  snrTruth: number;
  snrOne: number; // the typical S/N of the object in one photo
  lo: number;
  hi: number;
}

function loadImage(src: string): Promise<HTMLImageElement> {
  return new Promise((ok, fail) => {
    const img = new Image();
    img.onload = () => ok(img);
    img.onerror = () => fail(new Error('a photo is missing: ' + src));
    img.src = src;
  });
}

function grey(img: HTMLImageElement): { w: number; h: number; px: Float32Array } {
  const w = img.naturalWidth, h = img.naturalHeight;
  const c = Object.assign(document.createElement('canvas'), { width: w, height: h });
  const g = c.getContext('2d', { willReadFrequently: true })!;
  g.drawImage(img, 0, 0);
  const d = g.getImageData(0, 0, w, h).data;
  return { w, h, px: Float32Array.from({ length: w * h }, (_, k) => d[k * 4]) };
}

async function framesOf(r: GameRound, url: string): Promise<Frames> {
  if ((r as SampleRound).data) return (r as SampleRound).data;
  const imgs = await Promise.all(r.frames!.map((f) => loadImage(rel(url, f.png)).then(grey)));
  return { w: imgs[0].w, h: imgs[0].h, px: imgs.map((i) => i.px), dt: r.frames!.map((f) => f.dt_hr) };
}

/** Precomputed stacks on a grid of motions: show the nearest one. */
async function gridOf(r: GameRound, url: string, onLoad: () => void) {
  const g = r.grid!;
  const near = (list: number[], v: number, wrap = false) =>
    list.reduce((b, x) => (Math.abs(wrap ? ((x - v + 540) % 360) - 180 : x - v) < Math.abs(wrap ? ((b - v + 540) % 360) - 180 : b - v) ? x : b), list[0]);
  const cache = new Map<string, Float32Array | null>();
  const key = (m: Motion) => `${near(g.angles, m.angle, true)}_${near(g.rates, m.rate)}`;
  const get = (k: string) => {
    if (!cache.has(k)) {
      cache.set(k, null);
      const [a, rt] = k.split('_');
      loadImage(rel(url, g.png_pattern.replace('{a}', a).replace('{r}', rt)))
        .then((img) => (cache.set(k, grey(img).px), onLoad()))
        .catch(() => {});
    }
    return cache.get(k) ?? null;
  };
  const truth = { angle: r.truth.angle_deg, rate: r.truth.rate_px_per_hr };
  const [a, rt] = key(truth).split('_');
  const first = grey(await loadImage(rel(url, g.png_pattern.replace('{a}', a).replace('{r}', rt))));
  cache.set(key(truth), first.px);
  let lastShown = first.px;
  return {
    w: first.w,
    h: first.h,
    same: (m: Motion) => key(m) === key(truth),
    render(m: Motion, out: Float32Array, cover: Uint8Array) {
      const px = get(key(m)) ?? lastShown;
      lastShown = px;
      out.set(px);
      cover.fill(255);
    },
  };
}

async function prepare(r: GameRound, url: string, redraw: () => void): Promise<Ready & { same?: (m: Motion) => boolean }> {
  const truth: Motion = { angle: wrap360(r.truth.angle_deg), rate: r.truth.rate_px_per_hr };
  let w: number, h: number, n: number, dt: number[], render: Ready['render'], same: ((m: Motion) => boolean) | undefined, f: Frames | null = null;
  if (r.frames?.length || (r as SampleRound).data) {
    f = await framesOf(r, url);
    ({ w, h, dt } = f);
    n = f.px.length;
    const fill = median(Array.from(f.px[0].filter((_, k) => k % 7 === 0)));
    render = (m, out, cover) => stack(f!, m, out, cover, fill);
  } else {
    const gr = await gridOf(r, url, redraw);
    ({ w, h, same } = gr);
    render = gr.render;
    n = 1;
    dt = [0, 1];
  }
  const out = new Float32Array(w * h), cover = new Uint8Array(w * h);
  render(truth, out, cover);
  // only trust spots where every photo overlaps: the edges are averages of fewer photos, so noisier
  const full = (x: number, y: number, rr: number) =>
    cover[Math.round(y - rr) * w + Math.round(x - rr)] >= n && cover[Math.round(y + rr) * w + Math.round(x + rr)] >= n &&
    cover[Math.round(y - rr) * w + Math.round(x + rr)] >= n && cover[Math.round(y + rr) * w + Math.round(x - rr)] >= n;
  const spot: XY = r.truth.x != null && r.truth.y != null ? [r.truth.x, r.truth.y] : findPeak(out, w, h, RADII[0], 12, full);
  const cal = calibrate(out, w, h, spot, RADII, 7, 240, full);
  const snrTruth = snrAt(out, w, h, spot, cal);
  const st = pixelStats(out);
  const peak = boxSum(out, w, h, spot[0], spot[1], 2);
  const lo = st.med - 1.2 * st.sigma;
  const hi = Math.max(st.med + 8 * st.sigma, peak[0] / peak[1]);
  // the object in one photo: where it was then, measured the same way
  let snrOne = NaN;
  if (f) {
    const v = velocity(truth), t0 = midTime(f.dt);
    const one = f.px.slice(0, 12).map((px, i) => {
      const p: XY = [spot[0] + v[0] * (f!.dt[i] - t0), spot[1] + v[1] * (f!.dt[i] - t0)];
      const c = calibrate(px, w, h, p, [RADII[0]], 3 + i, 120);
      return (boxSum(px, w, h, p[0], p[1], RADII[0])[0] - c.med[0]) / c.sigma[0];
    });
    snrOne = median(one);
  }
  const span = 2 * halfSpan(dt) || 1;
  const rmax = Math.max(truth.rate * 1.3, (Math.min(w, h) * 0.85) / span);
  return { w, h, n, dt, truth, rmax, render, spot, cal, snrTruth, snrOne, lo, hi, same };
}

/** Paint a stacked image: one fixed stretch per round, edges dimmed where fewer photos overlap. */
function paint(img: ImageData, v: Float32Array, cover: Uint8Array, n: number, lo: number, hi: number) {
  const Q = 3, norm = 1 / Math.asinh(Q), span = 1 / (hi - lo || 1), d = img.data;
  for (let k = 0; k < v.length; k++) {
    let t = (v[k] - lo) * span;
    t = t <= 0 ? 0 : Math.asinh(t * Q) * norm;
    if (t > 1) t = 1;
    const c = cover[k] >= n ? 1 : (cover[k] / n) ** 1.5 * 0.55;
    const s = t * c * 255;
    const j = k * 4;
    d[j] = s * 0.93 + 3;
    d[j + 1] = s * 0.97 + 4;
    d[j + 2] = Math.min(255, s + 9);
    d[j + 3] = 255;
  }
}

const fmtS = (s: number) => (s < 60 ? `${s.toFixed(1)} s` : `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, '0')}`);
const starsFor = (s: number | null) => (s == null ? 0 : s <= 20 ? 3 : s <= 60 ? 2 : 1);
const starRow = (k: number) => `<span class="tr-stars" aria-label="${k} of 3 stars">${[0, 1, 2].map((i) => `<i class="${i < k ? 'on' : ''}"></i>`).join('')}</span>`;

export const tuneGame: View = async (body, ctx) => {
  let data: GameData | null = null, url = '', sample = false;
  try {
    const got = await ctx.load<GameData>('game/rounds.json');
    if (got.data.rounds?.length) ({ data, url, sample } = got);
  } catch {
    // no real rounds yet: play the synthetic sample below
  }
  const rounds: GameRound[] = data ? data.rounds : sampleRounds();
  if (!data) sample = true;
  const total = rounds.length;

  const find = ctx.source.index.objects.find((o) => o.slug === '2025yh5');
  let raf = 0, tick = 0, turn = 0;
  let film: { stop(): void } | null = null;
  let times: (number | null)[] = [];
  let lastStack: HTMLCanvasElement | null = null;
  const cache = new Map<number, Promise<Ready & { same?: (m: Motion) => boolean }>>();
  let redraw = () => {};
  const ready = (k: number) => cache.get(k) ?? cache.set(k, prepare(rounds[k], url, () => redraw())).get(k)!;

  const stopAll = () => {
    cancelAnimationFrame(raf);
    clearInterval(tick);
    film?.stop();
    film = null;
    return ++turn;
  };

  body.innerHTML = `
    <div class="tr">
      <header class="tr-top">
        <div class="tr-name"><h2 class="tr-h"></h2></div>
        <ol class="tr-prog" aria-label="Rounds"></ol>
        <p class="tr-clock mono" aria-live="off">0.0 s</p>
        <button class="icon-btn tip tip-r tr-help" aria-label="How it works" data-tip="How it works"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9.2 9.3a2.9 2.9 0 1 1 4.1 2.6c-.8.4-1.3 1-1.3 1.9v.7M12 17.6v.1" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"/></svg></button>
      </header>
      <ol class="tr-how">
        <li><b class="mono">1</b><span>These are real SPHEREx photos, taken hours apart.</span></li>
        <li><b class="mono">2</b><span>The asteroid is too faint to see in one photo.</span></li>
        <li><b class="mono">3</b><span>Turn the dial and the speed to follow it. Match its motion and the photos add up: it appears.</span></li>
      </ol>
      <div class="tr-stage">
        <div class="tr-sky">
          <canvas class="tr-img" aria-label="The stacked photos"></canvas>
          <svg class="tr-over" aria-hidden="true"><circle class="tr-ring" r="0"/><circle class="tr-ring tr-ring-2" r="0"/></svg>
          <p class="tr-banner" aria-live="assertive"></p>
          <canvas class="tr-film" hidden></canvas>
          <p class="tr-film-cap" hidden></p>
          <button class="btn btn-ghost tr-skip" hidden>Skip</button>
          <i class="tr-corner tl"></i><i class="tr-corner tr"></i><i class="tr-corner bl"></i><i class="tr-corner br"></i>
        </div>
        <div class="tr-deck">
          <div class="tr-sig" aria-live="off">
            <p class="tr-sig-k"><span class="mono">Signal</span><span class="tr-sig-v mono"><b>0.0</b> / <i></i></span></p>
            <div class="tr-meter"><i class="tr-zone"><em class="mono">Target</em></i><span></span></div>
            <p class="tr-sig-say">Match the motion to raise the signal.</p>
          </div>
          <div class="tr-ctrl">
            <div class="tr-c tr-c-dir"><p class="tr-c-k mono">Direction</p></div>
            <div class="tr-c tr-c-speed"><p class="tr-c-k mono">Speed</p></div>
            <button class="btn tr-hint">Hint</button>
          </div>
          <div class="tr-guided" hidden></div>
          <div class="tr-result" hidden></div>
        </div>
      </div>
      <div class="tr-foot">${provenance(sample, 'NASA SPHEREx photos')}${sample ? '<span class="hint">Sample rounds made in your browser, until the real ones are ready.</span>' : ''}</div>
    </div>
    <div class="tr-end" hidden></div>`;
  const q = <T extends Element = HTMLElement>(s: string) => body.querySelector(s) as T;
  const sky = q('.tr-sky'), canvas = q<HTMLCanvasElement>('.tr-img'), over = q<SVGSVGElement>('.tr-over');
  const meter = q('.tr-meter span'), snrEl = q('.tr-sig-v b'), goalEl = q('.tr-sig-v i'), sigSay = q('.tr-sig-say'), banner = q('.tr-banner');
  const clock = q('.tr-clock'), hintBtn = q<HTMLButtonElement>('.tr-hint'), result = q('.tr-result'), ctrl = q('.tr-ctrl'), guided = q('.tr-guided');
  q<HTMLElement>('.tr-zone').style.left = `${ZONE * 100}%`;

  /** The signal meter: the fill, the number, and gold once it is inside the target zone. */
  const showSignal = (snr: number, goal: number, won: boolean) => {
    const f = Math.min(1, (snr / (goal || 1)) * FULL);
    meter.style.transform = `scaleX(${f})`;
    snrEl.textContent = snr.toFixed(1);
    q('.tr-sig').classList.toggle('in', won || f >= ZONE);
    sky.classList.toggle('warm', !won && f > 0.35 * FULL);
    sky.classList.toggle('hot', !won && f >= ZONE);
  };

  /** A burst of gold bits from the dot. */
  const burst = (xPct: number, yPct: number) => {
    if (reducedMotion) return;
    const box = document.createElement('div');
    box.className = 'tr-burst';
    box.style.left = `${xPct}%`;
    box.style.top = `${yPct}%`;
    box.innerHTML = Array.from({ length: 30 }, (_, i) => {
      const a = (i / 30) * Math.PI * 2 + Math.random() * 0.4, d = 70 + Math.random() * 150;
      return `<i style="--dx:${(Math.cos(a) * d).toFixed(0)}px;--dy:${(Math.sin(a) * d).toFixed(0)}px;--rot:${(Math.random() * 540 - 270).toFixed(0)}deg;animation-delay:${(Math.random() * 90).toFixed(0)}ms" class="b${i % 3}"></i>`;
    }).join('');
    sky.append(box);
    setTimeout(() => box.remove(), 1600);
  };
  const gfx = canvas.getContext('2d')!;

  const progress = (k: number) => {
    q('.tr-prog').innerHTML = rounds.map((_, i) => `<li class="${i < k ? (times[i] == null ? 'help' : 'ok') : i === k ? 'now' : ''}"><span class="sr-only">Round ${i + 1}</span></li>`).join('');
  };

  // ---- the "how it works" film ----
  const film$ = (): Promise<void> => {
    const me = stopAll();
    const c = q<HTMLCanvasElement>('.tr-film'), cap = q('.tr-film-cap'), skip = q<HTMLButtonElement>('.tr-skip');
    sky.classList.add('filming');
    q('.tr').classList.add('filming');
    q('.tr-h').textContent = 'How it works';
    c.hidden = cap.hidden = skip.hidden = false;
    const f = playIntro(c, (i) => {
      cap.textContent = INTRO_LINES[i];
      cap.classList.remove('in');
      void cap.offsetWidth;
      cap.classList.add('in');
    }, reducedMotion);
    film = f;
    skip.onclick = () => f.stop();
    return f.done.then(() => {
      save({ seen: true });
      if (me !== turn) return;
      sky.classList.remove('filming');
      q('.tr').classList.remove('filming');
      c.hidden = cap.hidden = skip.hidden = true;
    });
  };

  // ---- one round ----
  const play = async (k: number) => {
    const me = stopAll();
    const r = rounds[k];
    progress(k);
    q('.tr-h').textContent = r.title || `Round ${k + 1}`;
    sky.classList.remove('won', 'warm', 'hot');
    sky.classList.add('loading');
    banner.textContent = '';
    banner.classList.remove('err');
    result.hidden = true;
    ctrl.hidden = r.mode === 'guided';
    guided.hidden = true;
    clock.textContent = r.mode === 'guided' ? '' : '0.0 s';
    sigSay.textContent = 'Match the motion to raise the signal.';
    hintBtn.textContent = 'Hint';
    showSignal(0, 1, false);
    if (r.mode === 'guided' && r.stacks?.length) return playGuided(k, me);
    let R: Awaited<ReturnType<typeof ready>>;
    try {
      R = await ready(k);
    } catch (e) {
      if (me === turn) {
        banner.classList.add('err');
        banner.textContent = `Could not load this round (${e instanceof Error ? e.message : e}).`;
      }
      return;
    }
    if (me !== turn) return;
    if (k + 1 < total && rounds[k + 1].mode !== 'guided') void ready(k + 1).catch(() => {});
    sky.classList.remove('loading');

    const { w, h, n, dt, truth } = R;
    canvas.width = w;
    canvas.height = h;
    over.setAttribute('viewBox', `0 0 ${w} ${h}`);
    over.querySelectorAll('circle').forEach((c) => (c.setAttribute('cx', String(R.spot[0])), c.setAttribute('cy', String(R.spot[1]))));
    const out = new Float32Array(w * h), cover = new Uint8Array(w * h), img = gfx.createImageData(w, h);
    const arcsec = r.px_arcsec ?? 6.15 / 4;
    goalEl.textContent = R.snrTruth.toFixed(1);

    let m: Motion = { angle: 0, rate: 0 };
    let dirty = true, shown = 0, started = 0, won = false, near = 0, hints = 0;
    const dial = directionDial((a) => input({ ...m, angle: a }), () => release());
    const tape = speedTape((u) => input({ ...m, rate: u * R.rmax }), () => release(), (u) => `${(u * R.rmax * arcsec).toFixed(u * R.rmax * arcsec < 10 ? 1 : 0)}″ / hour`);
    q('.tr-c-dir').querySelector('.tr-dial')?.remove();
    q('.tr-c-speed').querySelector('.tr-tape')?.remove();
    q('.tr-c-dir').append(dial.el);
    q('.tr-c-speed .tr-c-k').after(tape.el);
    dial.set(0, true);
    tape.set(0, true);

    const isNear = (x: Motion) => (R.same ? R.same(x) : endError(dt, x, truth) <= LOCK_PX);
    const input = (x: Motion) => {
      if (won) return;
      m = x;
      dirty = true;
      if (!started) {
        started = performance.now();
        tick = window.setInterval(() => {
          const s = (performance.now() - started) / 1000;
          clock.textContent = fmtS(s);
        }, 100);
      }
      // holding still on the right motion for a moment counts too (keyboard, slow drags)
      if (isNear(m)) near ||= performance.now();
      else near = 0;
    };
    const release = () => isNear(m) && lock(false);
    keysUp = release;

    const lock = (helped: boolean) => {
      if (won) return;
      won = true;
      clearInterval(tick);
      dial.lock(true);
      tape.lock(true);
      const secs = started ? (performance.now() - started) / 1000 : 0;
      times[k] = helped ? null : secs;
      hintBtn.blur();
      // glide the controls onto the exact motion
      const from = { ...m }, t0 = performance.now(), da = ((truth.angle - from.angle + 540) % 360) - 180;
      const glide = (t: number) => {
        const e = Math.min(1, (t - t0) / (reducedMotion ? 1 : helped ? 900 : 380));
        const s = 1 - Math.pow(1 - e, 3);
        m = { angle: wrap360(from.angle + da * s), rate: from.rate + (truth.rate - from.rate) * s };
        dial.set(m.angle, true);
        tape.set(m.rate / R.rmax, true);
        dirty = true;
        if (e < 1) requestAnimationFrame(glide);
        else celebrate(secs, helped);
      };
      requestAnimationFrame(glide);
    };

    const celebrate = (secs: number, helped: boolean) => {
      sky.classList.add('won');
      navigator.vibrate?.(30);
      burst((R.spot[0] / w) * 100, (R.spot[1] / h) * 100);
      banner.textContent = helped ? 'There it is.' : 'You rewound it!';
      sigSay.textContent = 'Motion matched. The photos add up.';
      const last = k + 1 === total;
      const stars = helped ? 0 : Math.max(1, starsFor(secs) - hints);
      ctrl.hidden = true;
      result.innerHTML = `
        <div class="tr-res-top">
          <p class="tr-res-time"><span class="mono">${helped ? 'Shown' : 'Locked in'}</span>${helped ? '' : fmtS(secs)}</p>
          ${starRow(stars)}
          <p class="tr-res-snr mono">Signal ${R.snrTruth.toFixed(1)}${Number.isFinite(R.snrOne) ? ` <span>vs ${Math.max(0, R.snrOne).toFixed(1)} in one photo</span>` : ''}</p>
        </div>
        ${r.explain ? `<p class="tr-res-say">${esc(r.explain)}</p>` : ''}
        <button class="btn btn-primary tr-next">${last ? 'See what Rewind found' : 'Next round'}${icon('arrow')}</button>`;
      result.hidden = false;
      const next = q<HTMLButtonElement>('.tr-next');
      next.onclick = () => {
        lastStack = snapshot();
        void (last ? end() : play(k + 1));
      };
      next.focus({ preventScroll: true });
    };
    // each hint narrows the search: a quarter of the dial, then a twelfth, then the speed, then the answer
    hintBtn.onclick = () => {
      if (won) return;
      hints++;
      if (hints <= 2) {
        const wide = hints === 1 ? 90 : 30;
        const lo = truth.angle - wide * (0.25 + 0.5 * Math.random());
        dial.limit(lo, lo + wide);
        sigSay.textContent = `Hint: it moves somewhere inside the gold arc.`;
      } else if (hints === 3) {
        const u = truth.rate / R.rmax, lo = Math.max(0, u - 0.08 - 0.08 * Math.random());
        tape.limit(lo, Math.min(1, lo + 0.24));
        sigSay.textContent = 'Hint: the speed is inside the gold part of the bar.';
      } else return lock(true);
      hintBtn.textContent = hints === 3 ? 'Show me' : 'Another hint';
      input({ angle: dial.get(), rate: tape.get() * R.rmax });
    };

    const snapshot = () => {
      const c = Object.assign(document.createElement('canvas'), { width: w, height: h });
      c.getContext('2d')!.drawImage(canvas, 0, 0);
      return c;
    };

    redraw = () => (dirty = true);
    let target = 0;
    const loop = () => {
      if (me !== turn) return;
      if (near && !won && performance.now() - near > 450 && isNear(m)) lock(false);
      if (dirty) {
        dirty = false;
        R.render(m, out, cover);
        paint(img, out, cover, n, R.lo, R.hi);
        gfx.putImageData(img, 0, 0);
        const snr = snrAt(out, w, h, R.spot, R.cal);
        target = Math.max(0, snr);
      }
      shown += (target - shown) * 0.22;
      showSignal(shown, R.snrTruth, won);
      raf = requestAnimationFrame(loop);
    };
    raf = requestAnimationFrame(loop);
    if (import.meta.env.DEV) Object.assign(window, { __tr: { R, set: (x: Motion) => (dial.set(x.angle), tape.set(x.rate / R.rmax)), snr: () => shown, won: () => won } });
    // arrow keys work without focusing a control first: left/right turn, up/down speed
    keys = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement;
      if (won || e.metaKey || e.ctrlKey || t.closest('.tr-dial, .tr-tape, input, textarea, select')) return;
      const turnBy = { ArrowLeft: -1, ArrowRight: 1 }[e.key], speedBy = { ArrowDown: -1, ArrowUp: 1 }[e.key];
      if (!turnBy && !speedBy) return;
      e.preventDefault();
      if (turnBy) dial.set(dial.get() + turnBy * (e.shiftKey ? 10 : 1));
      else tape.set(tape.get() + speedBy! * (e.shiftKey ? 0.01 : 0.002));
    };
  };

  // ---- a reveal round: Rewind did the shifting; the player tries a wrong, a close and the exact motion ----
  const playGuided = async (k: number, me: number) => {
    const r = rounds[k], st = r.stacks!;
    keys = () => {};
    keysUp = () => {};
    let imgs: HTMLImageElement[];
    try {
      imgs = await Promise.all(st.map((s) => loadImage(rel(url, s.png))));
    } catch (e) {
      if (me === turn) {
        banner.classList.add('err');
        banner.textContent = `Could not load this round (${e instanceof Error ? e.message : e}).`;
      }
      return;
    }
    if (me !== turn) return;
    sky.classList.remove('loading');
    const w = imgs[0].naturalWidth, h = imgs[0].naturalHeight;
    canvas.width = w;
    canvas.height = h;
    over.setAttribute('viewBox', `0 0 ${w} ${h}`);
    over.querySelectorAll('circle').forEach((c) => (c.setAttribute('cx', String(w / 2)), c.setAttribute('cy', String(h / 2))));
    const goal = r.snr_truth ?? Math.max(...st.map((s) => s.snr));
    goalEl.textContent = goal.toFixed(1);
    sigSay.textContent = 'This one is too fast to tune by hand, so Rewind did the shifting. Try each motion.';
    const names: Record<string, string> = { wrong: 'A wrong motion', close: 'A close motion', exact: 'The exact motion' };
    guided.innerHTML = st.map((s, i) => `<button class="tr-g" data-i="${i}"><span class="mono">${i + 1}</span>${esc(names[s.label] ?? s.label)}</button>`).join('');
    guided.hidden = false;
    let shown = 0, target = 0, won = false;
    const pick = (i: number) => {
      gfx.drawImage(imgs[i], 0, 0);
      target = st[i].snr;
      guided.querySelectorAll('button').forEach((b, j) => b.classList.toggle('on', j === i));
      if (st[i].label !== 'exact' || won) return;
      won = true;
      times[k] = 0;
      setTimeout(() => {
        if (me !== turn) return;
        sky.classList.add('won');
        navigator.vibrate?.(30);
        burst(50, 50);
        banner.textContent = 'There it is.';
        sigSay.textContent = 'Only the right motion makes it pop.';
        const last = k + 1 === total;
        result.innerHTML = `
          <div class="tr-res-top">
            <p class="tr-res-snr mono">Signal ${st.map((s) => s.snr.toFixed(1)).join(' → ')}</p>
          </div>
          ${r.explain ? `<p class="tr-res-say">${esc(r.explain)}</p>` : ''}
          <button class="btn btn-primary tr-next">${last ? 'See what Rewind found' : 'Next round'}${icon('arrow')}</button>`;
        result.hidden = false;
        q<HTMLButtonElement>('.tr-next').onclick = () => {
          lastStack = Object.assign(document.createElement('canvas'), { width: w, height: h });
          lastStack.getContext('2d')!.drawImage(canvas, 0, 0);
          void (last ? end() : play(k + 1));
        };
      }, reducedMotion ? 0 : 500);
    };
    guided.onclick = (e) => {
      const b = (e.target as Element).closest<HTMLElement>('[data-i]');
      if (b) pick(Number(b.dataset.i));
    };
    pick(0);
    const loop = () => {
      if (me !== turn) return;
      shown += (target - shown) * 0.16;
      showSignal(shown, goal, won);
      raf = requestAnimationFrame(loop);
    };
    raf = requestAnimationFrame(loop);
  };

  let keys: (e: KeyboardEvent) => void = () => {};
  const onKey = (e: KeyboardEvent) => keys(e);
  const onKeyUp = (e: KeyboardEvent) => e.key.startsWith('Arrow') && keysUp();
  let keysUp = () => {};
  document.addEventListener('keydown', onKey);
  document.addEventListener('keyup', onKeyUp);

  // ---- the end: the real result ----
  const end = () => {
    stopAll();
    const done = times.filter((t): t is number => t != null);
    const totalS = done.reduce((a, b) => a + b, 0);
    const solo = done.length === total;
    const prev = store().best;
    if (solo && (!prev || totalS < prev)) save({ best: totalS });
    const stars = times.reduce((a: number, t) => a + starsFor(t), 0);
    const days = find?.days_before_first_known_obs ?? 18;
    const photos = /stack of (\d+) (?:photos|images)/.exec(find?.verdict_text ?? '')?.[1];
    // the picture is the player's own stack only if the last round really was 2025 YH5; otherwise Rewind's
    const last = rounds[total - 1];
    const tunedYH5 = !sample && /2025\s*YH5/i.test(`${last.object ?? ''} ${last.title}`);
    const art = tunedYH5 ? lastStack : null;
    const game = q('.tr'), fin = q('.tr-end');
    game.hidden = true;
    fin.hidden = false;
    body.closest('.page')?.scrollTo(0, 0);
    fin.innerHTML = `
        <div class="tr-end-art">${art ? '' : `<img src="${esc(ctx.source.base)}objects/2025yh5/stack.png" alt="Rewind's stack of SPHEREx photos that shows 2025 YH5">`}</div>
        <div class="tr-end-text">
          <p class="kicker">The real one</p>
          <h1 class="tr-end-h">This is how Rewind recovered 2025 YH5.</h1>
          <p class="tr-end-lead">A potentially hazardous asteroid, in SPHEREx photos taken <b>${days} days</b> before its first known observation. No single photo shows it; the stack along its motion does${find?.best_snr ? `: S/N ${find.best_snr.toFixed(1)}` : ''}${photos ? ` from ${photos} photos` : ''}.</p>
          <a class="btn btn-gold" href="#/object/2025yh5">See 2025 YH5${icon('arrow')}</a>
          <div class="tr-score">
            <p class="tr-score-big"><span class="mono">${solo ? 'Your time' : 'Rounds solved'}</span>${solo ? fmtS(totalS) : `${done.length} of ${total}`}</p>
            ${starRow(Math.round(stars / total))}
            <ol class="tr-laps">${times.map((t, i) => `<li><span class="mono">${i + 1}</span>${t == null ? 'shown' : rounds[i].mode === 'guided' ? 'reveal' : fmtS(t)}</li>`).join('')}</ol>
            <p class="hint">${prev && solo ? `Best ${fmtS(Math.min(prev, totalS))}. ` : ''}Kept only in this browser.${sample ? ' Sample rounds.' : ''}${total < 2 ? ' More rounds coming.' : ''}</p>
          </div>
          <div class="tr-end-btns">
            <button class="btn btn-primary tr-share">Share my card</button>
            <button class="btn tr-again">Play again</button>
          </div>
        </div>`;
    if (art) q('.tr-end-art').prepend(art);
    q<HTMLButtonElement>('.tr-again').onclick = () => {
      times = [];
      fin.hidden = true;
      game.hidden = false;
      void play(0);
    };
    q<HTMLButtonElement>('.tr-share').onclick = (e) =>
      void shareCard({ stack: lastStack, time: solo ? fmtS(totalS) : `${done.length} of ${total} rounds`, stars: Math.round(stars / total), days, sample, yh5: tunedYH5 }, e.currentTarget as HTMLButtonElement);
  };

  q<HTMLButtonElement>('.tr-help').onclick = () => {
    const k = Math.min(times.length, total - 1);
    void film$().then(() => play(k));
  };

  if (rounds[0].mode !== 'guided') void ready(0).catch(() => {});
  void play(0);
  return () => {
    stopAll();
    document.removeEventListener('keydown', onKey);
    document.removeEventListener('keyup', onKeyUp);
  };
};
