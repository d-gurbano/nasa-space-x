// Full-screen pages over the (dimmed) 3D scene: Games, Challenge targets, Benchmark,
// Methods, About. Each view renders into the page body and may return a cleanup.
import { getJson, resolveRel, type DataSource } from '../lib/data';
import { el, esc } from '../ui/dom';
import { pageHeader } from '../ui/components';
import { enhancePage } from '../ui/motion';
import { reducedMotion } from '../state';

export interface ViewCtx {
  source: DataSource;
  /** Load a JSON file from the real data folder, or from data-sample/ if it is missing there. */
  load<T>(rel: string): Promise<{ data: T; url: string; sample: boolean }>;
}

export type View = (body: HTMLElement, ctx: ViewCtx) => (() => void) | void | Promise<(() => void) | void>;

export function makeCtx(source: DataSource): ViewCtx {
  return {
    source,
    async load<T>(rel: string) {
      try {
        const url = source.base + rel;
        const data = await getJson<T>(url);
        return { data, url, sample: source.sample || !!(data as { sample?: boolean }).sample };
      } catch {
        const url = 'data-sample/' + rel;
        return { data: await getJson<T>(url), url, sample: true };
      }
    },
  };
}

export const rel = resolveRel;

/** Page fade out, in ms; matches .page.pg-out in app.css. */
const OUT_MS = reducedMotion ? 0 : 160;

export class PageHost {
  private root: HTMLElement;
  private body: HTMLElement;
  private cleanup: (() => void) | void = undefined;
  private seq = 0;
  private hideTimer = 0;
  current: string | null = null;

  constructor(parent: HTMLElement, private ctx: ViewCtx) {
    this.root = el('section', { class: 'page', 'aria-live': 'polite', tabindex: '-1' });
    this.root.hidden = true;
    this.root.innerHTML = `<div class="page-inner"><a class="page-back" href="#/">&larr; Solar system</a><div class="page-body"></div></div>`;
    this.body = this.root.querySelector('.page-body') as HTMLElement;
    parent.appendChild(this.root);
  }

  /** kicker '' leaves the orange line out, so not every page opens the same way. */
  async open(name: string, title: string, kicker: string, view: View) {
    // page to page: the old content fades out first, the 3D scene stays behind both
    const swap = this.current !== null && !this.root.hidden;
    this.close(swap);
    const seq = ++this.seq;
    clearTimeout(this.hideTimer);
    if (swap && OUT_MS) {
      this.root.classList.add('pg-out');
      await new Promise((r) => setTimeout(r, OUT_MS));
      if (seq !== this.seq) return;
    }
    this.current = name;
    document.body.classList.add('page-open');
    this.root.classList.remove('pg-out', 'pg-leave');
    if (this.root.hidden) {
      this.root.hidden = false;
      this.root.classList.remove('pg-in');
      void this.root.offsetWidth;
      this.root.classList.add('pg-in');
    }
    this.root.scrollTop = 0;
    this.body.innerHTML = `${pageHeader(kicker, title)}<div class="page-content"><p class="muted">Loading...</p></div>`;
    this.body.classList.toggle('ph-plain', !kicker);
    // restart the rise for every page
    this.body.classList.remove('pg-rise');
    void this.body.offsetWidth;
    this.body.classList.add('pg-rise');
    document.title = `${title} · Rewind`;
    const content = this.body.querySelector('.page-content') as HTMLElement;
    try {
      const cleanup = await view(content, this.ctx);
      if (seq !== this.seq) {
        if (cleanup) cleanup();
        return;
      }
      this.cleanup = cleanup;
      enhancePage(content);
    } catch (e) {
      if (seq !== this.seq) return;
      content.innerHTML = `<p class="warn">This page could not load (${esc(e)}).</p>`;
    }
    this.root.focus({ preventScroll: true });
  }

  /** keep: another page opens next, so the frame stays up. */
  close(keep = false) {
    if (this.cleanup) this.cleanup();
    this.cleanup = undefined;
    if (keep) return;
    const was = this.current !== null;
    this.seq++;
    this.current = null;
    document.body.classList.remove('page-open');
    document.title = 'Rewind · Finding recently discovered asteroids and comets in older SPHEREx images';
    if (!was || this.root.hidden) return;
    // back to the solar system: the page fades away over the scene
    clearTimeout(this.hideTimer);
    if (!OUT_MS) {
      this.root.hidden = true;
      this.root.classList.remove('pg-out');
      return;
    }
    this.root.classList.add('pg-leave');
    this.hideTimer = window.setTimeout(() => {
      this.root.hidden = true;
      this.root.classList.remove('pg-leave', 'pg-out');
    }, 240);
  }
}
