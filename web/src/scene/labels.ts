// HTML labels over the canvas. At most MAX_LABELS are shown, highest priority first.
// A label is hidden when it would overlap a higher-priority one, or when it falls into
// the top-bar or time-bar areas. Labels can sit on a short leader line (offset).
import * as THREE from 'three';

export const MAX_LABELS = 20;

export interface LabelSpec {
  id: string;
  text: string;
  cls?: string;
  priority: number; // 0 = never shown on its own (only while it is the focus or selected)
  sub?: () => string | null; // small tag after the name, e.g. "Before first known obs."
  sticky?: boolean; // show the tag all the time, not only in focus"
  pos: (out: THREE.Vector3) => THREE.Vector3 | null;
  offset?: [number, number]; // px; draws a leader line from the point to the label
  pad?: () => number; // px of extra room between the point and the text, for bodies drawn larger than a dot
  onClick?: () => void;
  onHover?: (on: boolean) => void; // the pointer is over the name
  visible?: () => boolean; // false hides the label, e.g. when its layer is switched off
}

interface Label extends LabelSpec {
  el: HTMLDivElement;
  body: HTMLDivElement;
  subEl: HTMLSpanElement;
  shown: boolean;
  hover: boolean;
  w: number; // measured width of the body, 0 = unknown
  tr?: string; // last transform written, to skip identical style writes
  padPx?: number;
}

type Box = [number, number, number, number];

export class LabelLayer {
  private labels = new Map<string, Label>();
  private v = new THREE.Vector3();
  private safeTop = 0;
  private safeBottom = Infinity;
  /** Id of the label the story is about right now (e.g. the object in a flash): it shows its tag. */
  focus: string | null = null;
  /** When set, only labels it accepts are shown (e.g. fewer names in a close-up). */
  filter: ((id: string) => boolean) | null = null;
  constructor(private root: HTMLElement) {}

  /** Labels are kept between these y values (px). */
  setSafeArea(top: number, bottom: number) {
    this.safeTop = top;
    this.safeBottom = bottom;
  }

  add(spec: LabelSpec) {
    this.remove(spec.id);
    const el = document.createElement('div');
    el.className = 'label ' + (spec.cls ?? '');
    el.innerHTML = `<div class="label-leader"></div><div class="label-body"><span class="label-text"></span><span class="label-sub"></span></div>`;
    (el.querySelector('.label-text') as HTMLElement).textContent = spec.text;
    const body = el.querySelector('.label-body') as HTMLDivElement;
    if (spec.offset) {
      const [dx, dy] = spec.offset;
      const leader = el.querySelector('.label-leader') as HTMLDivElement;
      const len = Math.hypot(dx, dy);
      leader.style.width = len - 4 + 'px';
      leader.style.transform = `rotate(${Math.atan2(dy, dx)}rad)`;
      body.style.left = dx + 'px';
      body.style.top = dy + 'px';
      el.classList.add('has-leader', dx < 0 ? 'leader-left' : 'leader-right');
    }
    if (spec.onClick) {
      el.classList.add('clickable');
      el.addEventListener('click', spec.onClick);
    }
    el.style.display = 'none';
    this.root.appendChild(el);
    const label: Label = { ...spec, el, body, subEl: el.querySelector('.label-sub') as HTMLSpanElement, shown: false, hover: false, w: 0 };
    if (spec.sub || spec.onHover) {
      const over = (on: boolean) => {
        label.hover = on;
        spec.onHover?.(on);
      };
      el.addEventListener('pointerenter', () => over(true));
      el.addEventListener('pointerleave', () => over(false));
    }
    this.labels.set(spec.id, label);
  }

  remove(id: string) {
    const l = this.labels.get(id);
    if (l) {
      l.el.remove();
      this.labels.delete(id);
    }
  }

  setPriority(id: string, p: number) {
    const l = this.labels.get(id);
    if (l) l.priority = p;
  }

  setClass(id: string, cls: string, on: boolean) {
    this.labels.get(id)?.el.classList.toggle(cls, on);
  }

  private box(l: Label, x: number, y: number): Box {
    const [dx, dy] = l.offset ?? [0, 0];
    const w = l.w || 12 + l.text.length * 7.5 + (l.subEl.textContent ? 24 + l.subEl.textContent.length * 6.5 : 0);
    const bx = x + dx + (l.offset && dx < 0 ? -w - 4 : 8);
    return [bx - 2, y + dy - 10, bx + w + 2, y + dy + 10];
  }

  update(camera: THREE.Camera, w: number, h: number) {
    // the label in focus and the one under the pointer are placed first, so their tag has room
    const rank = (l: Label) => (l.id === this.focus ? 99 : l.hover ? 98 : l.priority);
    const sorted = [...this.labels.values()].sort((a, b) => rank(b) - rank(a));
    const placed: Box[] = [];
    const overlaps = (b: Box) => placed.some((p) => b[0] < p[2] && b[2] > p[0] && b[1] < p[3] && b[3] > p[1]);
    let n = 0;
    for (const l of sorted) {
      let show = false;
      let x = 0, y = 0;
      if (n < MAX_LABELS && (l.priority > 0 || l.id === this.focus) && (!this.filter || this.filter(l.id)) && (!l.visible || l.visible()) && l.pos(this.v)) {
        this.v.project(camera);
        if (this.v.z < 1 && Math.abs(this.v.x) < 1.05 && Math.abs(this.v.y) < 1.05) {
          x = (this.v.x * 0.5 + 0.5) * w;
          y = (-this.v.y * 0.5 + 0.5) * h;
          let s = (l.sticky || l.id === this.focus || l.hover || l.el.classList.contains('selected') ? l.sub?.() : null) ?? '';
          // no room for the tag on a narrow screen: keep the name alone
          if (s && x + 44 + l.text.length * 7.5 + s.length * 6.5 >= w) s = '';
          if (l.subEl.textContent !== s) {
            l.subEl.textContent = s;
            l.w = 0;
          }
          const b = this.box(l, x, y);
          // the point itself also reserves a little room so other text does not cover it
          const dot: Box = [x - 5, y - 5, x + 5, y + 5];
          if (b[1] > this.safeTop && b[3] < this.safeBottom && y < this.safeBottom && b[0] > 0 && b[2] < w && !overlaps(b)) {
            placed.push(b, dot);
            show = true;
          }
        }
      }
      if (show) {
        n++;
        const tr = `translate3d(${x.toFixed(1)}px, ${y.toFixed(1)}px, 0)`;
        if (tr !== l.tr) {
          l.el.style.transform = tr;
          l.tr = tr;
        }
        const pad = l.pad ? Math.round(l.pad()) : 0;
        if (pad !== (l.padPx ?? 0)) {
          l.body.style.marginLeft = pad + 'px';
          l.padPx = pad;
        }
      }
      // labels fade in and out (CSS) instead of popping
      if (show !== l.shown) {
        if (show) l.el.style.display = '';
        l.el.classList.toggle('off', !show);
        l.shown = show;
      }
      if (show && !l.w) l.w = l.body.offsetWidth;
    }
  }
}
