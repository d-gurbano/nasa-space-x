// Slim top bar: logo, search pill, menu.
import type { IndexObject } from '../lib/types';
import { el, esc } from './dom';
import { isKnown, rankObjects } from '../lib/rank';

export const VIEWS = [
  { hash: '#/sky', label: 'Sky' },
  { hash: '#/detectives', label: 'Tune the Rewind' },
  { hash: '#/stars', label: 'Challenge stars' },
  { hash: '#/benchmark', label: 'Does it work?' },
  { hash: '#/scientists', label: 'For scientists' },
  { hash: '#/about', label: 'About' },
];

export function mountTopbar(root: HTMLElement, objects: IndexObject[], sample: boolean, onPick: (slug: string) => void) {
  const bar = el('header', { class: 'topbar' });
  bar.innerHTML = `
    <a class="logo" href="#/" aria-label="Rewind home">Rewind<span class="logo-dot">.</span></a>
    <div class="search">
      <svg class="search-ico" viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="6.5" fill="none" stroke="currentColor" stroke-width="1.8"/><path d="M16 16l4.5 4.5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>
      <input type="search" placeholder="${matchMedia('(max-width: 480px)').matches ? 'Search objects' : 'Search an asteroid or comet'}" aria-label="Search objects" autocomplete="off" spellcheck="false">
      <ul class="search-results" role="listbox" hidden></ul>
    </div>
    <div class="tb-end">
      ${sample ? '<span class="chip chip-sample" title="The engine has not published real results yet. Orbits are real; photos and results are made-up test data.">Sample data</span>' : ''}
      <button class="icon-btn menu-btn" aria-label="Menu" aria-expanded="false">
        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h16M4 12h16M4 17h16" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>
      </button>
    </div>
    <nav class="menu" hidden>
      <a href="#/">Home</a>
      ${VIEWS.map((v) => `<a href="${v.hash}">${v.label}</a>`).join('')}
    </nav>`;
  root.appendChild(bar);

  const input = bar.querySelector('input') as HTMLInputElement;
  const list = bar.querySelector('.search-results') as HTMLUListElement;
  const menu = bar.querySelector('.menu') as HTMLElement;
  const menuBtn = bar.querySelector('.menu-btn') as HTMLButtonElement;
  let active = 0;
  let matches: IndexObject[] = [];

  const norm = (s: string) => s.toLowerCase().replace(/[^a-z0-9]/g, '');
  const renderList = () => {
    const q = norm(input.value);
    const found = q ? objects.filter((o) => norm(o.name).includes(q) || o.slug.includes(q)) : objects;
    matches = rankObjects(found).slice(0, 8);
    list.hidden = document.activeElement !== input || (!q && !matches.length);
    // say how many there are, not only how many fit
    const head = !found.length ? 'No object with that name in Rewind' : found.length > matches.length ? `Strongest ${matches.length} of ${found.length}${q ? ' matches' : ' in Rewind'}` : `${found.length} ${q ? (found.length === 1 ? 'match' : 'matches') : 'in Rewind'}`;
    list.innerHTML = `<li class="sr-head mono">${head}</li>` + matches
      .map((o, k) => `<li role="option" data-slug="${esc(o.slug)}" class="${k === active ? 'on' : ''}" aria-selected="${k === active}">
        <span>${esc(o.name)}</span><span class="verdict-chip v-${o.verdict.toLowerCase()}">${isKnown(o) && o.verdict === 'FOUND' ? 'Known' : verdictWord(o.verdict)}</span></li>`)
      .join('');
  };
  const choose = (slug: string) => {
    input.value = '';
    input.blur();
    list.hidden = true;
    onPick(slug);
  };
  input.addEventListener('input', () => {
    active = 0;
    renderList();
  });
  input.addEventListener('focus', renderList);
  input.addEventListener('blur', () => setTimeout(() => (list.hidden = true), 150));
  input.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowDown') active = Math.min(matches.length - 1, active + 1);
    else if (e.key === 'ArrowUp') active = Math.max(0, active - 1);
    else if (e.key === 'Enter' && matches[active]) return choose(matches[active].slug);
    else if (e.key === 'Escape') return input.blur();
    else return;
    e.preventDefault();
    renderList();
  });
  list.addEventListener('mousedown', (e) => {
    const li = (e.target as HTMLElement).closest('li[data-slug]') as HTMLElement | null;
    if (li) choose(li.dataset.slug!);
  });

  const setMenu = (open: boolean) => {
    menu.hidden = !open;
    menuBtn.setAttribute('aria-expanded', String(open));
  };
  menuBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    setMenu(menu.hasAttribute('hidden'));
  });
  document.addEventListener('click', (e) => {
    if (!menu.contains(e.target as Node)) setMenu(false);
  });
  window.addEventListener('hashchange', () => setMenu(false));
  return bar;
}

export function verdictWord(v: string): string {
  return ({ FOUND: 'Found', HINT: 'Hint', TOO_FAINT: 'Too faint', NO_PHOTOS: 'No photos', PENDING: 'Not yet' } as Record<string, string>)[v] ?? v;
}
