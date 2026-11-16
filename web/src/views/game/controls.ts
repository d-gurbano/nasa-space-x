// The two controls of the game, built like camera rings: a direction dial and a speed tape.
// Both are role="slider" elements: drag (mouse, pen, touch), wheel, or arrow keys (Shift = 10x).
import { wrap360 } from './stack';

export interface Control {
  el: HTMLElement;
  get(): number;
  set(v: number, quiet?: boolean): void;
  lock(on: boolean): void;
  /** A hint: keep the value inside lo..hi (the dial: clockwise from lo to hi) and mark that range in gold. */
  limit(lo: number, hi: number): void;
}

const TAU = Math.PI * 2;

/** A ring with 72 ticks. Drag the knob (or anywhere on the ring) around; 0 = up, clockwise. */
export function directionDial(onInput: (deg: number) => void, onRelease: () => void): Control {
  const el = document.createElement('div');
  el.className = 'tr-dial';
  el.tabIndex = 0;
  el.setAttribute('role', 'slider');
  el.setAttribute('aria-label', 'Direction of motion');
  el.setAttribute('aria-valuemin', '0');
  el.setAttribute('aria-valuemax', '359');
  const ticks = Array.from({ length: 72 }, (_, i) => {
    const a = (i * 5 * Math.PI) / 180, big = i % 9 === 0, r0 = big ? 80 : 84;
    return `<line x1="${100 + Math.sin(a) * r0}" y1="${100 - Math.cos(a) * r0}" x2="${100 + Math.sin(a) * 90}" y2="${100 - Math.cos(a) * 90}" class="${big ? 'big' : ''}"/>`;
  }).join('');
  // north up, east left: so the compass letters go N, W (right), S, E (left)
  el.innerHTML = `
    <svg viewBox="0 0 200 200" aria-hidden="true">
      <circle class="tr-dial-face" cx="100" cy="100" r="96"/>
      <g class="tr-dial-ticks">${ticks}</g>
      <path class="tr-dial-arc" d=""/>
      <text x="100" y="62">N</text><text x="140" y="104">W</text><text x="100" y="146">S</text><text x="60" y="104">E</text>
      <g class="tr-dial-hand"><line x1="100" y1="74" x2="100" y2="36"/><path d="M100 24l7 14h-14z"/></g>
      <circle class="tr-dial-hub" cx="100" cy="100" r="25"/>
      <circle class="tr-dial-knob" cx="100" cy="10" r="9"/>
    </svg>
    <output class="tr-dial-val mono"></output>
    <span class="tr-dial-note mono">East is left, as on the sky</span>`;
  const hand = el.querySelector('.tr-dial-hand') as SVGGElement;
  const knob = el.querySelector('.tr-dial-knob') as SVGCircleElement;
  const out = el.querySelector('output') as HTMLOutputElement;
  let v = 0, locked = false, lim: [number, number] | null = null;

  const draw = () => {
    hand.setAttribute('transform', `rotate(${v} 100 100)`);
    const a = (v * Math.PI) / 180;
    knob.setAttribute('cx', String(100 + Math.sin(a) * 87));
    knob.setAttribute('cy', String(100 - Math.cos(a) * 87));
    out.textContent = `${Math.round(v)}°`;
    el.setAttribute('aria-valuenow', String(Math.round(v)));
    el.setAttribute('aria-valuetext', `${Math.round(v)} degrees`);
  };
  const set = (d: number, quiet = false) => {
    v = wrap360(d);
    if (lim && !quiet) {
      const off = wrap360(v - lim[0]), span = lim[1];
      if (off > span) v = off - span < 360 - off ? wrap360(lim[0] + span) : lim[0];
    }
    draw();
    if (!quiet) onInput(v);
  };
  const angleAt = (e: PointerEvent) => {
    const b = el.getBoundingClientRect();
    return (Math.atan2(e.clientX - (b.left + b.width / 2), -(e.clientY - (b.top + b.height / 2))) * 360) / TAU;
  };
  // drag adds up the change of angle, so the knob never jumps under the finger
  let last = 0;
  el.addEventListener('pointerdown', (e) => {
    if (locked) return;
    el.setPointerCapture(e.pointerId);
    el.classList.add('drag');
    last = angleAt(e);
    if (e.target === knob || (e.target as Element).closest('.tr-dial-ticks')) set(last);
    e.preventDefault();
  });
  el.addEventListener('pointermove', (e) => {
    if (!el.hasPointerCapture(e.pointerId)) return;
    const a = angleAt(e);
    let d = a - last;
    if (d > 180) d -= 360;
    if (d < -180) d += 360;
    last = a;
    set(v + d);
  });
  const up = (e: PointerEvent) => {
    if (!el.hasPointerCapture(e.pointerId)) return;
    el.releasePointerCapture(e.pointerId);
    el.classList.remove('drag');
    onRelease();
  };
  el.addEventListener('pointerup', up);
  el.addEventListener('pointercancel', up);
  el.addEventListener('wheel', (e) => {
    if (locked) return;
    e.preventDefault();
    set(v + Math.sign(e.deltaY) * (e.shiftKey ? 10 : 1));
  }, { passive: false });
  el.addEventListener('keydown', (e) => {
    const step = { ArrowRight: 1, ArrowUp: 1, ArrowLeft: -1, ArrowDown: -1, PageUp: 15, PageDown: -15 }[e.key];
    if (!step || locked) return;
    e.preventDefault();
    set(v + step * (e.shiftKey ? 10 : 1));
  });
  el.addEventListener('keyup', (e) => e.key.startsWith('Arrow') && onRelease());
  draw();
  const limit = (lo: number, hi: number) => {
    lim = [wrap360(lo), wrap360(hi - lo)];
    const at = (deg: number) => `${100 + Math.sin((deg * Math.PI) / 180) * 96} ${100 - Math.cos((deg * Math.PI) / 180) * 96}`;
    el.querySelector('.tr-dial-arc')!.setAttribute('d', `M${at(lo)}A96 96 0 ${lim[1] > 180 ? 1 : 0} 1 ${at(hi)}`);
    set(v);
  };
  return { el, get: () => v, set, lock: (on) => (locked = on), limit };
}

/** A tape of ticks that slides under a fixed gold index. Value 0..1. */
export function speedTape(onInput: (u: number) => void, onRelease: () => void, label: (u: number) => string): Control {
  const el = document.createElement('div');
  el.className = 'tr-tape';
  el.tabIndex = 0;
  el.setAttribute('role', 'slider');
  el.setAttribute('aria-label', 'Speed of motion');
  el.setAttribute('aria-valuemin', '0');
  el.setAttribute('aria-valuemax', '100');
  el.innerHTML = `
    <div class="tr-tape-win"><div class="tr-tape-strip"></div><span class="tr-tape-index"></span></div>
    <div class="tr-tape-fill"><span></span><i hidden></i></div>
    <output class="tr-tape-val mono"></output>`;
  const strip = el.querySelector('.tr-tape-strip') as HTMLElement;
  const fill = el.querySelector('.tr-tape-fill span') as HTMLElement;
  const out = el.querySelector('output') as HTMLOutputElement;
  let u = 0, locked = false, lim: [number, number] = [0, 1];
  const draw = () => {
    strip.style.transform = `translateX(${-u * 100}%)`;
    fill.style.transform = `scaleX(${u})`;
    out.textContent = label(u);
    el.setAttribute('aria-valuenow', String(Math.round(u * 100)));
    el.setAttribute('aria-valuetext', label(u));
  };
  const set = (x: number, quiet = false) => {
    u = Math.min(1, Math.max(0, x));
    if (!quiet) u = Math.min(lim[1], Math.max(lim[0], u));
    draw();
    if (!quiet) onInput(u);
  };
  // drag moves the tape like a film strip: right-to-left drag = faster
  let x0 = 0, u0 = 0;
  el.addEventListener('pointerdown', (e) => {
    if (locked) return;
    el.setPointerCapture(e.pointerId);
    el.classList.add('drag');
    x0 = e.clientX;
    u0 = u;
    e.preventDefault();
  });
  el.addEventListener('pointermove', (e) => {
    if (!el.hasPointerCapture(e.pointerId)) return;
    const w = (el.querySelector('.tr-tape-win') as HTMLElement).clientWidth || 300;
    set(u0 - ((e.clientX - x0) / w) * (e.shiftKey ? 0.1 : 0.5));
  });
  const up = (e: PointerEvent) => {
    if (!el.hasPointerCapture(e.pointerId)) return;
    el.releasePointerCapture(e.pointerId);
    el.classList.remove('drag');
    onRelease();
  };
  el.addEventListener('pointerup', up);
  el.addEventListener('pointercancel', up);
  el.addEventListener('wheel', (e) => {
    if (locked) return;
    e.preventDefault();
    set(u + Math.sign(e.deltaY || e.deltaX) * (e.shiftKey ? 0.01 : 0.002));
  }, { passive: false });
  el.addEventListener('keydown', (e) => {
    const step = { ArrowRight: 1, ArrowUp: 1, ArrowLeft: -1, ArrowDown: -1, PageUp: 10, PageDown: -10 }[e.key];
    if (!step || locked) return;
    e.preventDefault();
    set(u + step * (e.shiftKey ? 0.01 : 0.002));
  });
  el.addEventListener('keyup', (e) => e.key.startsWith('Arrow') && onRelease());
  draw();
  const limit = (lo: number, hi: number) => {
    lim = [lo, hi];
    const zone = el.querySelector('.tr-tape-fill i') as HTMLElement;
    zone.hidden = false;
    zone.style.left = `${lo * 100}%`;
    zone.style.width = `${(hi - lo) * 100}%`;
    set(u);
  };
  return { el, get: () => u, set, lock: (on) => (locked = on), limit };
}
