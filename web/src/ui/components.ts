// Shared UI pieces as small HTML-string helpers. Styles are in styles/components.css.
// Text arguments are escaped here; arguments named "html" are inserted as they are.
import { esc } from './dom';

const ICONS = {
  play: '<path d="M8 5.5v13l10.5-6.5z" fill="currentColor"/>',
  back: '<path d="M16 5.5v13L5.5 12z" fill="currentColor"/>',
  pause: '<path d="M8.5 6v12M15.5 6v12" stroke="currentColor" stroke-width="2.6" stroke-linecap="round"/>',
  prev: '<path d="M18 6.5v11L10 12z" fill="currentColor"/><path d="M7 6.5v11" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>',
  next: '<path d="M6 6.5v11l8-5.5z" fill="currentColor"/><path d="M17 6.5v11" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>',
  today: '<circle cx="12" cy="12" r="7" fill="none" stroke="currentColor" stroke-width="1.8"/><circle cx="12" cy="12" r="2.2" fill="currentColor"/>',
  arrow: '<path d="M5 12h14M13 6l6 6-6 6" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>',
  search: '<circle cx="11" cy="11" r="6.5" fill="none" stroke="currentColor" stroke-width="1.8"/><path d="M16 16l4.5 4.5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>',
  menu: '<path d="M4 8h16M4 16h16" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>',
};
export type IconName = keyof typeof ICONS;

export function icon(name: IconName): string {
  return `<svg viewBox="0 0 24 24" aria-hidden="true">${ICONS[name]}</svg>`;
}

/** A button. kind: 'primary' (the one main action), 'gold', 'ghost' or '' (quiet). */
export function button(label: string, o: { kind?: string; cls?: string; icon?: IconName } = {}): string {
  return `<button class="btn ${o.kind ? 'btn-' + o.kind : ''} ${o.cls ?? ''}">${esc(label)}${o.icon ? icon(o.icon) : ''}</button>`;
}

/** A round icon button with a tooltip. The label is read by screen readers and shown on hover. */
export function iconButton(name: IconName, label: string, cls = ''): string {
  return `<button class="icon-btn tip ${cls}" aria-label="${esc(label)}" data-tip="${esc(label)}">${icon(name)}</button>`;
}

export function chip(text: string, cls = ''): string {
  return `<span class="chip ${cls}">${esc(text)}</span>`;
}

/** A number with a short label under it. cls: 'stat-gold', 'stat-blue', 'stat-l'. */
export function stat(num: string | number, label: string, cls = ''): string {
  return `<div class="stat ${cls}"><dd class="stat-num">${esc(num)}</dd><dt class="stat-label">${esc(label)}</dt></div>`;
}

export function stats(items: string[], cls = ''): string {
  return `<dl class="stats ${cls}">${items.join('')}</dl>`;
}

export function card(html: string, cls = ''): string {
  return `<div class="card card-pad ${cls}">${html}</div>`;
}

export function section(kicker: string, title: string, html: string, cls = ''): string {
  return `<section class="sec ${cls}"><header class="sec-head"><p class="kicker">${esc(kicker)}</p><h2 class="sec-title">${esc(title)}</h2></header>${html}</section>`;
}

export function pageHeader(kicker: string, title: string, lead = ''): string {
  return `<header class="ph">${kicker ? `<p class="kicker ph-kicker">${esc(kicker)}</p>` : ''}<h1 class="ph-title">${esc(title)}</h1>${lead ? `<p class="ph-lead">${esc(lead)}</p>` : ''}</header>`;
}

/** Segmented tabs. Each button carries data-tab; the caller listens for clicks. */
export function tabs(items: { id: string; label: string }[], active: string, cls = ''): string {
  return `<div class="seg ${cls}" role="tablist">${items
    .map((t) => `<button role="tab" data-tab="${esc(t.id)}" aria-selected="${t.id === active}">${esc(t.label)}</button>`)
    .join('')}</div>`;
}

/** A data table. Cells are HTML; the first column is the row name. */
export function table(head: string[], rows: string[][], cls = ''): string {
  return `<table class="data-table ${cls}"><thead><tr>${head.map((h) => `<th>${esc(h)}</th>`).join('')}</tr></thead><tbody>${rows
    .map((r) => `<tr>${r.map((c) => `<td>${c}</td>`).join('')}</tr>`)
    .join('')}</tbody></table>`;
}
