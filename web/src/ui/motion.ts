// Motion helpers, all driven by one IntersectionObserver: big numbers count up and page sections
// fade in when they come into view. Styles (.reveal, .cu, img shimmer) are in styles/components.css.
// With reduced motion nothing moves: numbers and sections are simply there.
import { reducedMotion } from '../state';

/** Big numbers that count up. Add data-count to any other element to opt in. */
const COUNT = '.stat-num, .op-num, .sci-big, .dw-big, .dw-hero em, [data-count]';
const NUM = /\d[\d,]*(?:\.\d+)?/;
const COUNT_MS = 800;
const STAGGER_MS = 60;

const runs = new WeakMap<Element, () => void>();
const io =
  'IntersectionObserver' in window
    ? new IntersectionObserver(
        (entries) => {
          let k = 0;
          for (const e of entries) {
            if (!e.isIntersecting) continue;
            io!.unobserve(e.target);
            if (e.target.classList.contains('reveal')) (e.target as HTMLElement).style.setProperty('--ri', String(k++));
            runs.get(e.target)?.();
            runs.delete(e.target);
          }
        },
        { rootMargin: '0px 0px -6% 0px', threshold: 0.12 },
      )
    : null;

const watch = (target: Element, run: () => void) => {
  if (!io) return run();
  runs.set(target, run);
  io.observe(target);
};

/** Counts the first number in the element's own text from 0 when it scrolls into view. */
function countUp(el: HTMLElement, delay: number) {
  if (el.dataset.cu) return;
  el.dataset.cu = '1';
  const text = [...el.childNodes].find((n): n is Text => n.nodeType === 3 && NUM.test(n.nodeValue ?? ''));
  if (!text) return;
  const v = text.nodeValue!, m = v.match(NUM)!, raw = m[0];
  const target = parseFloat(raw.replace(/,/g, ''));
  const dec = raw.split('.')[1]?.length ?? 0;
  if (!(target >= 2) && !dec) return;
  const show = (n: number) => (raw.includes(',') ? n.toLocaleString('en-US', { minimumFractionDigits: dec, maximumFractionDigits: dec }) : n.toFixed(dec));
  // the animated digits are hidden from screen readers, which read the real number once
  const vis = document.createElement('span');
  vis.className = 'cu';
  vis.setAttribute('aria-hidden', 'true');
  vis.textContent = raw;
  const sr = document.createElement('span');
  sr.className = 'sr-only';
  sr.textContent = raw;
  text.replaceWith(v.slice(0, m.index), vis, sr, v.slice(m.index! + raw.length));
  // keep the width of the final number so nothing next to it jumps
  vis.style.minWidth = vis.getBoundingClientRect().width + 'px';
  const digits = vis.firstChild as Text;
  digits.nodeValue = show(0);
  watch(el, () => {
    const t0 = performance.now() + delay;
    const step = () => {
      const k = Math.max(0, Math.min(1, (performance.now() - t0) / COUNT_MS));
      digits.nodeValue = k < 1 ? show(target * (1 - Math.pow(1 - k, 3))) : raw;
      if (k < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  });
}

/** Count-up for every big number inside root; delay (ms) waits for an entrance animation. */
export function countUps(root: ParentNode, delay = 0) {
  if (reducedMotion) return;
  root.querySelectorAll<HTMLElement>(COUNT).forEach((el) => countUp(el, delay));
}

/** Fade and rise each element in when it scrolls into view, 60 ms apart within a batch. */
export function reveal(els: Iterable<Element>) {
  if (reducedMotion) return;
  for (const el of els) {
    if (el.classList.contains('reveal')) continue;
    el.classList.add('reveal');
    watch(el, () => {
      el.classList.add('in');
      // drop the class once in, so nothing is left holding a transform or a delay
      const d = (parseFloat((el as HTMLElement).style.getPropertyValue('--ri')) || 0) * STAGGER_MS;
      setTimeout(() => el.classList.remove('reveal', 'in'), 700 + d);
    });
  }
}

/** A page's content: its top-level blocks reveal, its big numbers count. */
export function enhancePage(content: HTMLElement) {
  reveal(content.children);
  countUps(content);
}

/** Images show a soft shimmer until they load (see img.sk in components.css). */
export function watchImages() {
  const done = (e: Event) => e.target instanceof HTMLImageElement && e.target.classList.add('ld');
  document.addEventListener('load', done, true);
  document.addEventListener('error', done, true);
}
