// Full-screen pages over the (dimmed) 3D scene: Detectives, Challenge stars, Benchmark,
// For scientists, About. Each view renders into the page body and may return a cleanup.
import { getJson, resolveRel, type DataSource } from '../lib/data';
import { el, esc } from '../ui/dom';
import { pageHeader } from '../ui/components';

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

export class PageHost {
  private root: HTMLElement;
  private body: HTMLElement;
  private cleanup: (() => void) | void = undefined;
  current: string | null = null;

  constructor(parent: HTMLElement, private ctx: ViewCtx) {
    this.root = el('section', { class: 'page', 'aria-live': 'polite', tabindex: '-1' });
    this.root.hidden = true;
    this.root.innerHTML = `<div class="page-inner"><a class="page-back" href="#/">&larr; Back to the solar system</a><div class="page-body"></div></div>`;
    this.body = this.root.querySelector('.page-body') as HTMLElement;
    parent.appendChild(this.root);
  }

  async open(name: string, title: string, kicker: string, view: View) {
    this.close();
    this.current = name;
    document.body.classList.add('page-open');
    this.root.hidden = false;
    this.root.scrollTop = 0;
    this.body.innerHTML = `${pageHeader(kicker, title)}<div class="page-content"><p class="muted">Loading...</p></div>`;
    document.title = `${title} - Rewind`;
    const content = this.body.querySelector('.page-content') as HTMLElement;
    try {
      content.innerHTML = '';
      this.cleanup = await view(content, this.ctx);
    } catch (e) {
      content.innerHTML = `<p class="warn">Could not load this page: ${esc(e)}</p>`;
    }
    this.root.focus({ preventScroll: true });
  }

  close() {
    if (this.cleanup) this.cleanup();
    this.cleanup = undefined;
    this.current = null;
    this.root.hidden = true;
    document.body.classList.remove('page-open');
    document.title = 'Rewind: every discovery has a past';
  }
}
