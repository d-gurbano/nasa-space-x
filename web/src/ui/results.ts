// Results card: the one number that matters, how all searched objects split by verdict,
// then the Rewind objects ranked by verdict: the strongest 20 first, the rest on request,
// and one verdict at a time by pressing its count. All numbers are counted from the object list.
import type { SiteIndex } from '../lib/types';
import { beforeWhat, daysBefore, isKnown, rankObjects, seenNotEarlier, tally } from '../lib/rank';
import { el, esc, plural, provenance } from './dom';
import { verdictWord } from './topbar';

const LIST_MAX = 20; // rows shown before "Show all"

export function objectLine(o: SiteIndex['objects'][number]): string {
  if (isKnown(o)) return 'Known object - shows what SPHEREx sees';
  switch (o.verdict) {
    case 'FOUND':
    case 'HINT': {
      const d = daysBefore(o);
      const seen = o.verdict === 'FOUND' ? 'Seen' : 'Maybe seen';
      if (d != null && d > 0) return `${seen} ${plural(d, 'day')} before ${beforeWhat(o)}`;
      if (d === 0) return `${seen} hours before ${beforeWhat(o)}`;
      // the engine says these photos are not earlier than the known observations
      return o.days_before_first_known_obs === null ? `${seen} by SPHEREx, not before the first known observation` : `${seen} in older SPHEREx photos`;
    }
    case 'TOO_FAINT':
      return 'Too faint for SPHEREx then';
    case 'NO_PHOTOS':
      return 'No SPHEREx photos of the right spot';
    default:
      return 'Not searched yet';
  }
}

export function mountResults(root: HTMLElement, idx: SiteIndex, sample: boolean, onPick: (slug: string) => void) {
  const t = tally(idx.objects);
  const title = idx.final ? 'Final results' : "Tonight's results";
  const card = el('section', { class: 'results card', 'aria-label': title });
  const ranked = rankObjects(idx.objects);
  type Obj = SiteIndex['objects'][number];
  // one segment per verdict, in the same words the chips use; each one also filters the list
  const parts: [string, number, string, (o: Obj) => boolean][] = [
    [verdictWord('FOUND'), t.found, 'var(--gold)', (o) => o.verdict === 'FOUND' && !isKnown(o)],
    ['Known, seen', t.known, 'var(--ink)', (o) => o.verdict === 'FOUND' && isKnown(o)],
    [verdictWord('HINT'), t.hints, 'var(--blue)', (o) => o.verdict === 'HINT'],
    [verdictWord('TOO_FAINT'), t.tooFaint, '#5a5f6b', (o) => o.verdict === 'TOO_FAINT'],
    [verdictWord('NO_PHOTOS'), t.noPhotos, '#30343d', (o) => o.verdict === 'NO_PHOTOS'],
    [verdictWord('PENDING'), t.pending, '#30343d', (o) => o.verdict === 'PENDING'],
  ];
  const shown = parts.filter((p) => p[1] > 0);
  const hero = t.allBefore
    ? 'found in older photos,<br>before their discovery'
    : `found in older photos${t.before ? `,<br>${t.before} before anyone had seen them` : ''}`;
  card.innerHTML = `
    <button class="rs-toggle" aria-expanded="true"><span class="rs-kicker kicker">${title}</span><span class="rs-count">${t.searched} searched</span><span class="rs-caret" aria-hidden="true"></span></button>
    <div class="rs-body">
      <div class="rs-hero"><span class="stat-num">${t.found}</span><p>${hero}</p></div>
      <div class="rs-bar" aria-hidden="true">${shown.map(([, n, c]) => `<i style="flex:${n};--c:${c}"></i>`).join('')}</div>
      <div class="rs-key" role="group" aria-label="Show one group">${shown.map(([w, n, c], k) => `<button data-k="${k}" aria-pressed="false" style="--c:${c}"><b>${n}</b>${w}</button>`).join('')}</div>
      <p class="rs-honest">If an object is too faint to see, Rewind says so instead of guessing.</p>
      ${ranked.length ? '' : '<p class="empty">No objects searched yet. Results appear here as soon as Rewind has checked a new asteroid or comet.</p>'}
      <p class="rs-listhead mono" aria-live="polite"></p>
      <ol class="rs-list"></ol>
      <button class="rs-more btn btn-s" hidden></button>
      <div class="rs-foot">${provenance(sample, 'Rewind on NASA SPHEREx')}<span class="muted mono">${plural(idx.headline_stats.frames_read, 'photo')} read</span></div>
    </div>`;
  root.appendChild(card);
  const toggle = card.querySelector('.rs-toggle') as HTMLButtonElement;
  const setOpen = (open: boolean) => {
    card.classList.toggle('collapsed', !open);
    toggle.setAttribute('aria-expanded', String(open));
  };
  // phones start collapsed so the scene stays visible
  setOpen(!window.matchMedia('(max-width: 720px)').matches);
  toggle.addEventListener('click', () => setOpen(card.classList.contains('collapsed')));

  // ---------- the list: strongest first, a short top list until the visitor asks for more ----------
  const listEl = card.querySelector('.rs-list') as HTMLElement, head = card.querySelector('.rs-listhead') as HTMLElement;
  const more = card.querySelector('.rs-more') as HTMLButtonElement;
  const keys = [...card.querySelectorAll<HTMLButtonElement>('.rs-key button')];
  let group = -1, all = false;
  const renderList = () => {
    const list = group < 0 ? ranked : ranked.filter(shown[group][3]);
    const rows = all ? list : list.slice(0, LIST_MAX);
    head.textContent = !list.length ? '' : rows.length < list.length ? `Strongest ${rows.length} of ${list.length}` : group < 0 ? `All ${list.length}, strongest first` : `${shown[group][0]}: ${list.length}`;
    listEl.innerHTML = rows
      .map((o) => `<li><button data-slug="${esc(o.slug)}"><span class="rs-name">${esc(o.name)}</span>${seenNotEarlier(o) ? '<span class="verdict-chip v-seen">Seen, not earlier</span>' : `<span class="verdict-chip v-${o.verdict.toLowerCase()}">${isKnown(o) && o.verdict === 'FOUND' ? 'Known' : verdictWord(o.verdict)}</span>`}<span class="rs-line">${esc(objectLine(o))}</span></button></li>`)
      .join('');
    more.hidden = list.length <= LIST_MAX;
    more.textContent = all ? `Show the strongest ${LIST_MAX}` : `Show all ${list.length}`;
    keys.forEach((b, k) => b.setAttribute('aria-pressed', String(k === group)));
  };
  keys.forEach((b, k) =>
    b.addEventListener('click', () => {
      group = group === k ? -1 : k;
      all = false;
      renderList();
    }),
  );
  more.addEventListener('click', () => {
    all = !all;
    renderList();
  });
  listEl.addEventListener('click', (e) => {
    const b = (e.target as HTMLElement).closest<HTMLButtonElement>('button[data-slug]');
    if (!b) return;
    if (window.matchMedia('(max-width: 720px)').matches) setOpen(false);
    onPick(b.dataset.slug!);
  });
  renderList();
  return card;
}
