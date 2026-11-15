// Bottom time control: the date as the main readout, one thin track with a ring handle,
// and a small glowing mark for every SPHEREx photo (a "flash"). Photos too close together to
// tell apart on the track share one wider mark. No ticks, no year row: the past is a solid
// line, the future a dashed one, and a notch marks today.
// Hover a mark for a preview, click or tap it to jump there. Arrow keys step time, space plays.
import { fracFromMjd, mjdFromFrac, plainDate, relativeText } from '../lib/time';
import { SPEEDS, TIME_END, TIME_START, store } from '../state';
import type { FlashEvent, IndexObject } from '../lib/types';
import { clusterMarks, isKnown, type Mark } from '../lib/rank';
import { el, esc, fixPlural } from './dom';
import { icon, iconButton } from './components';
import { verdictWord } from './topbar';

const NEAR_PX = 10; // how close the pointer must be to a mark to pick it
const CLUSTER_PX = 12; // photos closer than this on the track share one mark

export function mountTimebar(root: HTMLElement, flashes: FlashEvent[], opts: {
  objectOf: (slug: string) => IndexObject | undefined;
  photoUrl: (f: FlashEvent) => string;
  onPin: (f: FlashEvent) => void;
}) {
  const frac = (mjd: number) => fracFromMjd(mjd, TIME_START, TIME_END);
  const sorted = [...flashes].sort((a, b) => a.mjd - b.mjd);
  // which mark wins when several sit under the pointer: finds, then hints, then known objects
  const rank = (f: FlashEvent) => {
    const o = opts.objectOf(f.slug);
    return !o ? 0 : isKnown(o) ? 1 : o.verdict === 'FOUND' ? 3 : 2;
  };
  const bar = el('section', { class: 'timebar', 'aria-label': 'Time control' });
  bar.innerHTML = `
    <div class="tb-grid" style="--today:${(frac(store.today) * 100).toFixed(3)}%">
      <div class="tb-ctl tb-left">
        ${iconButton('back', 'Rewind', 'tip-l tb-back')}
        ${iconButton('play', 'Play', 'tb-play')}
        <button class="tb-speed tip"></button>
      </div>
      <div class="tb-read">
        <span class="tb-when"></span>
        <div class="tb-date"><span class="tb-d"></span><span class="tb-m"></span><span class="tb-y"></span></div>
      </div>
      <div class="tb-ctl tb-right">
        ${iconButton('prev', 'Previous flash', 'tb-prev')}
        ${iconButton('next', 'Next flash', 'tb-next')}
        ${iconButton('today', 'Back to today', 'tip-r tb-today')}
      </div>
      <div class="tb-track" role="slider" tabindex="0" aria-label="Date" aria-valuemin="${TIME_START}" aria-valuemax="${TIME_END}">
        <div class="tb-rail"></div>
        <div class="tb-rail tb-future"></div>
        <div class="tb-fill"></div>
        <div class="tb-now"></div>
        <div class="tb-marks"></div>
        <div class="tb-thumb"></div>
        <div class="tb-pop" hidden></div>
      </div>
      <div class="tb-ends" aria-hidden="true"><span>Past</span><button tabindex="-1">Today</button><span>Future</span></div>
    </div>`;
  root.appendChild(bar);
  const $ = <T extends HTMLElement>(s: string) => bar.querySelector(s) as T;
  const track = $('.tb-track'), thumb = $('.tb-thumb'), fill = $('.tb-fill'), pop = $('.tb-pop');
  const when = $('.tb-when'), day = $('.tb-d'), month = $('.tb-m'), year = $('.tb-y');
  const back = $<HTMLButtonElement>('.tb-back'), play = $<HTMLButtonElement>('.tb-play'), speed = $<HTMLButtonElement>('.tb-speed');
  const prev = $<HTMLButtonElement>('.tb-prev'), next = $<HTMLButtonElement>('.tb-next');
  const marksEl = $('.tb-marks');
  let marks: Mark[] = [], markEls: HTMLElement[] = [];
  // a find stands for its mark before a hint or a known object; then the stronger photo
  const better = (a: number, b: number) => rank(sorted[a]) - rank(sorted[b]) > 0 || (rank(sorted[a]) === rank(sorted[b]) && (sorted[a].snr ?? 0) > (sorted[b].snr ?? 0));
  const layoutMarks = () => {
    const w = track.clientWidth;
    marks = clusterMarks(sorted.map((f) => frac(f.mjd) * w), CLUSTER_PX, better);
    const pct = (k: number) => (frac(sorted[k].mjd) * 100).toFixed(3);
    marksEl.innerHTML = marks
      .map((m) => {
        const cls = ['', 'known', 'hint', ''][rank(sorted[m.best])];
        return m.first === m.last
          ? `<i class="tb-mark ${cls}" style="left:${pct(m.first)}%"></i>`
          : `<i class="tb-mark tb-many ${cls}" style="left:${pct(m.first)}%;right:${(100 - +pct(m.last)).toFixed(3)}%"></i>`;
      })
      .join('');
    markEls = [...marksEl.children] as HTMLElement[];
    previewed = -1;
    pop.hidden = true;
  };

  const flashBefore = () => sorted.filter((f) => f.mjd < store.mjd - 0.01).pop();
  const flashAfter = () => sorted.find((f) => f.mjd > store.mjd + 0.01);
  const setBtn = (b: HTMLButtonElement, name: 'play' | 'back' | 'pause', label: string, on: boolean) => {
    if (b.dataset.icon !== name) {
      b.dataset.icon = name;
      b.innerHTML = icon(name);
    }
    b.setAttribute('aria-label', label);
    b.dataset.tip = label;
    b.classList.toggle('on', on);
  };

  let shown = '';
  const render = () => {
    const f = frac(store.mjd), t = frac(store.today);
    thumb.style.left = f * 100 + '%';
    fill.style.left = Math.min(f, t) * 100 + '%';
    fill.style.width = Math.abs(f - t) * 100 + '%';
    const text = plainDate(store.mjd);
    if (text !== shown) {
      shown = text;
      const [d, m, y] = text.split(' ');
      day.textContent = d;
      month.textContent = m;
      year.textContent = y;
      const rel = relativeText(Math.round(store.mjd) - store.today);
      when.textContent = rel;
      track.setAttribute('aria-valuenow', String(Math.round(store.mjd)));
      track.setAttribute('aria-valuetext', `${text}, ${rel}`);
      prev.disabled = !flashBefore();
      next.disabled = !flashAfter();
    }
    const fwd = store.playing && store.direction > 0, rev = store.playing && store.direction < 0;
    setBtn(play, fwd ? 'pause' : 'play', fwd ? 'Pause' : 'Play', fwd);
    setBtn(back, rev ? 'pause' : 'back', rev ? 'Pause' : 'Rewind', rev);
    const s = SPEEDS[store.speedIndex];
    if (speed.dataset.s !== String(s)) {
      speed.dataset.s = String(s);
      speed.innerHTML = `${s}<small>d/s</small>`;
      speed.dataset.tip = `Speed: ${s} ${s === 1 ? 'day' : 'days'} per second`;
      speed.setAttribute('aria-label', speed.dataset.tip);
    }
    bar.classList.toggle('is-today', Math.abs(store.mjd - store.today) < 0.5);
  };
  store.on(render);
  render();

  // ---------- marks: preview on hover, jump on click or tap ----------
  const nearest = (clientX: number): number => {
    const r = track.getBoundingClientRect();
    const x = (k: number) => r.left + frac(sorted[k].mjd) * r.width;
    let best = -1, bestScore = -Infinity;
    marks.forEach((m, k) => {
      const d = Math.max(0, x(m.first) - clientX, clientX - x(m.last));
      // a higher rank wins unless another mark is clearly closer
      const score = rank(sorted[m.best]) * 4 - d;
      if (d <= NEAR_PX && score > bestScore) {
        best = k;
        bestScore = score;
      }
    });
    return best;
  };
  let previewed = -1;
  const preview = (k: number) => {
    if (k === previewed) return;
    markEls[previewed]?.classList.remove('on');
    previewed = k;
    pop.hidden = k < 0;
    if (k < 0) return;
    const m = marks[k], f = sorted[m.best], o = opts.objectOf(f.slug);
    const n = m.last - m.first + 1;
    markEls[k].classList.add('on');
    pop.innerHTML = `
      <img alt="" src="${esc(opts.photoUrl(f))}">
      <div class="tb-pop-text">
        <span class="tb-pop-name">${esc(o?.name ?? f.slug)}${o ? `<span class="verdict-chip v-${o.verdict.toLowerCase()}">${isKnown(o) && o.verdict === 'FOUND' ? 'Known' : verdictWord(o.verdict)}</span>` : ''}</span>
        <span class="tb-pop-when">${esc(plainDate(f.iso))}${f.snr != null ? ` / S/N ${f.snr.toFixed(1)}` : ''}</span>
        <span class="tb-pop-label">${esc(fixPlural(f.label))}</span>
        ${n > 1 ? `<span class="tb-pop-more">The strongest of ${n} photos taken around this date. The arrow buttons step through all of them.</span>` : ''}
      </div>`;
    const w = track.clientWidth, pw = pop.offsetWidth;
    pop.style.left = Math.max(0, Math.min(w - pw, ((frac(sorted[m.first].mjd) + frac(sorted[m.last].mjd)) / 2) * w - pw / 2)) + 'px';
  };
  layoutMarks();
  new ResizeObserver(layoutMarks).observe(track);

  // ---------- dragging ----------
  let down: { x: number; mark: number; moved: boolean } | null = null;
  const setFromEvent = (e: PointerEvent) => {
    const r = track.getBoundingClientRect();
    store.setTime(mjdFromFrac((e.clientX - r.left) / r.width, TIME_START, TIME_END));
  };
  track.addEventListener('pointerdown', (e) => {
    const mark = nearest(e.clientX);
    down = { x: e.clientX, mark, moved: mark < 0 };
    track.setPointerCapture(e.pointerId);
    track.classList.add('dragging');
    store.setPlaying(false);
    // on a mark, wait: a click jumps to the photo, a drag moves time
    if (mark < 0) setFromEvent(e);
  });
  track.addEventListener('pointermove', (e) => {
    preview(nearest(e.clientX));
    if (!down) return;
    if (!down.moved && Math.abs(e.clientX - down.x) < 4) return;
    down.moved = true;
    setFromEvent(e);
  });
  const up = (e: PointerEvent) => {
    if (down && !down.moved && e.type === 'pointerup' && marks[down.mark]) opts.onPin(sorted[marks[down.mark].best]);
    down = null;
    track.classList.remove('dragging');
    if (e.pointerType !== 'mouse') preview(-1);
  };
  track.addEventListener('pointerup', up);
  track.addEventListener('pointercancel', up);
  track.addEventListener('pointerleave', () => !down && preview(-1));

  // ---------- buttons ----------
  const run = (dir: number) => {
    const same = store.playing && store.direction === dir;
    store.direction = dir;
    store.setPlaying(!same);
  };
  const toToday = () => {
    store.setPlaying(false);
    store.setTime(store.today);
  };
  const jump = (f?: FlashEvent) => f && opts.onPin(f);
  play.addEventListener('click', () => run(1));
  back.addEventListener('click', () => run(-1));
  speed.addEventListener('click', () => {
    store.speedIndex = (store.speedIndex + 1) % SPEEDS.length;
    store.emit();
  });
  prev.addEventListener('click', () => jump(flashBefore()));
  next.addEventListener('click', () => jump(flashAfter()));
  $('.tb-today').addEventListener('click', toToday);
  $('.tb-ends button').addEventListener('click', toToday);

  // keyboard: arrows step a day (shift = a month), page up/down jump between flashes, space plays
  window.addEventListener('keydown', (e) => {
    const t = e.target as HTMLElement;
    if (t.closest('input, textarea, select, [contenteditable]')) return;
    if (t.closest('button') && (e.key === ' ' || e.key === 'Enter')) return;
    if (document.body.classList.contains('page-open')) return;
    if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') {
      const step = (e.shiftKey ? 30 : 1) * (e.key === 'ArrowRight' ? 1 : -1);
      store.setPlaying(false);
      store.setTime(Math.round(store.mjd) + step);
    } else if ((e.key === 'PageUp' || e.key === 'PageDown') && !t.closest('.panel')) {
      jump(e.key === 'PageUp' ? flashBefore() : flashAfter());
    } else if (e.key === ' ') {
      run(store.direction);
    } else return;
    e.preventDefault();
  });
  return bar;
}
