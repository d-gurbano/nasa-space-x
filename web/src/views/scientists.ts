// For scientists: the method as a step diagram, the full results table, what the finds do to
// the orbit, check definitions, validation, downloads, the data contract and positions in MPC
// 80-column format for expert review. Nothing here is ever submitted anywhere.
import '../styles/page-scientists.css';
import type { Verdict } from '../lib/types';
import { decoyTally, tally as benchTally, usable, type Bench } from './benchmark/logic';
import { mpcLine } from '../lib/mpc';
import { isKnown, tally } from '../lib/rank';
import { getJson } from '../lib/data';
import { button, icon, section, stat } from '../ui/components';
import { esc, fixPlural, fmt, plural, provenance } from '../ui/dom';
import { verdictWord } from '../ui/topbar';
import { reducedMotion } from '../state';
import { rel, type View } from './page';
import { bytes, filterRows, gainRange, km, lead, snrBar, sortRows, splitContract, toCsv, type Row, type Sort, type SortKey } from './scientists/logic';

const PAGE = 25;
const KIND: Record<string, string> = { neo: 'NEO', comet: 'Comet', mba: 'Main belt', lost: 'Lost', famous: 'Known' };

// the engine's rules, as written in rewind_engine/verdict.py
const CHECKS: [string, string, string][] = [
  ['snr', 'Signal', 'The sky-cleaned stack has a null-scaled S/N of 5 or more.'],
  ['cleaned', 'Sky cleaned', 'A static-sky reference exists for at least 10 photos.'],
  ['nulls', 'Fake paths', 'None of the fake paths next to the real one (at least 12) is as strong.'],
  ['time_shift', 'Right time', 'The S/N peaks at zero time shift and falls off on both sides.'],
  ['days', 'Separate days', 'At least 2 days are positive on their own (S/N of 2 or more).'],
  ['detectable', 'Detectable', 'Sources planted at the predicted brightness are recovered at least 50% of the time.'],
  ['sign_test', 'Sign test', 'More photos are positive on the real path than on every fake path, by 3 sigma or more. Passes without the test when single photos already show the object.'],
  ['not_one_day', 'Not one day', 'The S/N stays at 3 or more without the best day.'],
  ['orbit', 'Orbit fit', 'The orbit refit with the new positions stays good. Not required for known objects.'],
];
const VERDICTS: [Verdict, string][] = [
  ['FOUND', 'Every check passes. For a known object this means "SPHEREx saw it", never a precovery.'],
  ['HINT', 'There is a signal (null-scaled S/N of 3 or more, or 2 or more with two core checks passed), but not every check passes. A hint is never upgraded.'],
  ['TOO_FAINT', 'Nothing significant at the predicted spot: the planted-source test puts the object below the limit there, or it was fainter than predicted.'],
  ['NO_PHOTOS', 'SPHEREx did not photograph the object in the time we searched.'],
];

const STEPS = (searched: number, frames: number): [string, string, string][] => [
  ['Targets', 'New asteroids and comets from the MPC and JPL SBDB, lost objects whose search area is small enough, and a few well-known objects as controls.', `${fmt(searched)} objects`],
  ['Photos', 'Each orbit is run back over the SPHEREx survey to list every Level 2 image that covers the predicted position (NASA/IPAC IRSA, QR3 and DR1).', `${fmt(frames)} photos read`],
  ['Clean', 'A stamp is cut at the predicted position, the static sky is subtracted using other SPHEREx photos of the same spot, and forced PSF flux is measured.', 'flux, error, flags'],
  ['Stack', 'The cleaned stamps are shifted and added along the predicted motion, per day and over all days. The S/N is scaled by the spread of fake-path stacks.', 'null-scaled S/N'],
  ['Checks', 'Nine checks per object: fake paths, time shifts, each day alone, a sign test, and planted sources that measure the limit at that spot.', '9 pass or fail marks'],
  ['Verdict and orbit', 'FOUND only when every check passes. For a find, the measured positions join the MPC observations and the orbit is refit with kete.', 'verdict, positions, refit'],
];

// line icons for the six method steps, drawn on a 24 grid; the gold part marks what the step adds
const svg = (d: string) => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${d}</svg>`;
const STEP_ICONS = [
  '<ellipse cx="12" cy="12" rx="9.5" ry="4.5" transform="rotate(-20 12 12)"/><circle cx="12" cy="12" r="1.6"/><circle class="ico-gold" cx="19.6" cy="8.6" r="1.4"/>',
  '<rect x="3" y="7" width="13" height="13" rx="1.5"/><path d="M7 3.5h12A1.5 1.5 0 0 1 20.5 5v12"/><circle class="ico-gold" cx="9.5" cy="13.5" r="1.4"/>',
  '<rect x="3.5" y="3.5" width="17" height="17" rx="2"/><circle class="ico-gold" cx="12" cy="12" r="3.5"/><path d="M12 5.5v2.5M12 16v2.5M5.5 12H8M16 12h2.5"/>',
  '<path d="M12 4 3.5 8.5 12 13l8.5-4.5z"/><path d="M3.5 12.5 12 17l8.5-4.5"/><path class="ico-gold" d="M3.5 16.5 12 21l8.5-4.5"/>',
  '<path class="ico-gold" d="M4 6.5 5.5 8l3-3M4 12.5 5.5 14l3-3M4 18.5 5.5 20l3-3"/><path d="M11.5 6.5H20M11.5 12.5H20M11.5 18.5H20"/>',
  '<ellipse cx="12" cy="12" rx="9.5" ry="5.5"/><circle cx="12" cy="12" r="1.8"/><path class="ico-gold" d="M17.5 4.5v3M16 6h3"/><circle class="ico-gold" cx="6" cy="16" r="1.4"/>',
].map(svg);
const ICO_FILE = svg('<path d="M14 3.5H7A1.5 1.5 0 0 0 5.5 5v14A1.5 1.5 0 0 0 7 20.5h10a1.5 1.5 0 0 0 1.5-1.5V8z"/><path d="M14 3.5V8h4.5"/><path class="ico-gold" d="M9 13h6M9 16.5h4"/>');
const ICO_FOLDER = svg('<path d="M3.5 7A1.5 1.5 0 0 1 5 5.5h4l2 2h8A1.5 1.5 0 0 1 20.5 9v9a1.5 1.5 0 0 1-1.5 1.5H5A1.5 1.5 0 0 1 3.5 18z"/><path class="ico-gold" d="M8 14h8"/>');
const ICO_DOWN = svg('<path d="M12 4.5v11M7 11l5 5 5-5M5 19.5h14"/>');
const ICO_COPY = svg('<rect x="8.5" y="8.5" width="11" height="11" rx="2"/><path d="M15.5 8.5V6A1.5 1.5 0 0 0 14 4.5H6A1.5 1.5 0 0 0 4.5 6v8A1.5 1.5 0 0 0 6 15.5h2.5"/>');
const copyButton = `<button type="button" class="btn btn-s btn-ghost sci-copy">${ICO_COPY}<span aria-live="polite">Copy</span></button>`;
const fileType = (f: string) => (f.endsWith('.bin') ? 'Binary, Float32' : 'JSON');

const FILES: [string, string][] = [
  ['index.json', 'All objects, verdicts and flash events'],
  ['benchmark.json', 'The "pretend it is new" test, case by case'],
  ['kaggle_crosscheck.json', 'The 12 objects run on two machines'],
  ['orbits.json', 'Orbital elements for the 3D dots'],
  ['orbits.bin', 'The same as Float32 rows (fields in orbits.bin.json)'],
  ['planets.json', 'Planet elements used by the 3D view'],
  ['detectives/rounds.json', 'The rounds of the Detectives game'],
];

// what the engine adds to a find's object.json
interface Position { mjd: number; ra: number; dec: number }
interface Sigma { sigma3_km_before?: number; sigma3_km_after?: number; factor?: number; converged?: boolean; error?: string }
interface Impact {
  first_known_obs_iso?: string; earliest_spherex_day_iso?: string; days_before_first_known_obs?: number | null;
  spherex_positions?: number; sigma_floor_arcsec?: number; arc_days_before?: number; arc_days_after?: number;
  one_year_after_last_obs?: Sigma | null; at_discovery_scenario?: Sigma | null;
}
interface FindPage { name: string; sample?: boolean; impact?: Impact | null; checks?: { orbit_fit?: { positions?: Position[] } | null } }
interface Find { o: Row; impact: Impact | null; lines: string[] }
interface Crosscheck {
  summary: { already_in_site: number; crosscheck_same_verdict: number };
  crosscheck: { slug: string; mac_verdict: string; kaggle_verdict: string; mac_snr: number; kaggle_snr: number; mac_frames: number; kaggle_frames: number }[];
}

const chipFor = (v: string) => `<span class="verdict-chip v-${esc(v.toLowerCase())}">${esc(verdictWord(v))}</span>`;
const arrow = (a: string, b: string) => `${a} <span class="sci-to">→</span> ${b}`;
const times = (f: number) => `×${f.toFixed(f >= 2 ? 1 : 2)}`;

export const scientistsView: View = (body, ctx) => {
  const { source } = ctx;
  const idxUrl = source.base + 'index.json';
  const rows = source.index.objects as Row[];
  const t = tally(rows);
  const early = rows.filter((o) => (o.days_before_first_known_obs ?? 0) > 0).length;
  const counts = (v: Verdict) => rows.filter((o) => o.verdict === v).length;
  const shown = (['FOUND', 'HINT', 'TOO_FAINT', 'NO_PHOTOS', 'PENDING'] as Verdict[]).filter((v) => counts(v) > 0);
  let alive = true;

  const nav: [string, string][] = [['method', 'Method'], ['results', 'Results'], ['impact', 'Orbit impact'], ['checks', 'Checks'], ['validation', 'Validation'], ['files', 'Downloads'], ['contract', 'Data contract'], ['mpc', 'Positions']];
  const th = (k: SortKey, label: string, cls = '', tip = '') =>
    `<th scope="col" class="${cls}" aria-sort="none"><button class="sci-sort${tip ? ' tip tip-r tip-down' : ''}" data-sort="${k}"${tip ? ` data-tip="${esc(tip)}"` : ''}>${esc(label)}</button></th>`;

  body.innerHTML = `
    <p class="lead">The method, the results, the checks and every file.</p>
    <dl class="stats sci-stats">
      ${stat(fmt(t.searched), 'objects searched')}
      ${stat(t.found, early ? `found, ${early} of them before the first known observation` : 'found in SPHEREx photos', 'stat-gold')}
      ${stat(t.known, 'known objects seen, as controls')}
      ${stat(t.hints, 'hints, not upgraded', 'stat-blue')}
      ${stat(t.tooFaint, 'too faint')}
      ${stat(t.noPhotos, 'with no photos')}
    </dl>
    <nav class="sci-nav" aria-label="On this page"><div class="sci-nav-track">${nav.map(([id, label]) => `<button type="button" class="sci-nav-btn" data-go="sci-${id}">${label}</button>`).join('')}</div></nav>

    ${section('Method', 'From a new orbit to a verdict, in six steps', `
      <ol class="sci-steps">${STEPS(t.searched, source.index.headline_stats.frames_read).map(([h, p, out], i) => `<li class="sci-step">
        <div class="sci-step-head"><span class="sci-step-num" aria-hidden="true">${i + 1}</span></div>
        <span class="sci-step-ico">${STEP_ICONS[i]}</span>
        <h3>${h}</h3><p>${p}</p><p class="sci-out mono">${esc(out)}</p></li>`).join('')}</ol>`, 'sci-sec sci-s-method')}

    ${section('Results', `All ${fmt(rows.length)} objects`, `
      <div class="sci-bar">
        <div class="sci-filters sci-tabs" role="group" aria-label="Show by verdict">${[['ALL', 'All', rows.length] as [string, string, number], ...shown.map((v) => [v, verdictWord(v), counts(v)] as [string, string, number])]
          .map(([id, label, n]) => `<button type="button" class="sci-filter f-${id.toLowerCase()}" data-tab="${id}" aria-pressed="${id === 'ALL'}">${id === 'ALL' ? '' : '<i class="sci-dot" aria-hidden="true"></i>'}${esc(label)}<span class="sci-n">${fmt(n)}</span></button>`).join('')}</div>
        <label class="sci-search">${icon('search')}<input type="search" placeholder="Search by name" aria-label="Search objects by name" autocomplete="off" spellcheck="false"></label>
      </div>
      <table class="data-table sci-table">
        <thead><tr>
          ${th('name', 'Object')}${th('kind', 'Type', 'sci-wide')}${th('verdict', 'Verdict', 'sci-left')}${th('snr', 'S/N', 'sci-snr', 'Null-scaled S/N of the stack. Bar: square-root scale, tick at S/N 5')}
          ${th('frames', 'Photos', 'sci-wide')}${th('discovered', 'Discovered', 'sci-wide')}${th('lead', 'vs first known obs.', 'sci-wide', 'Against the first known observation anywhere (JPL SBDB)')}
          <th scope="col"><span class="sr-only">Details</span></th>
        </tr></thead>
        <tbody></tbody>
      </table>
      <div class="sci-pager">
        <p class="sci-count mono" aria-live="polite"></p>
        ${button('Previous', { cls: 'btn-s sci-prev' })}${button('Next', { cls: 'btn-s sci-next' })}
        ${button('CSV of this list', { kind: 'ghost', cls: 'btn-s sci-csv' })}
        ${provenance(source.sample, 'NASA SPHEREx')}
      </div>`, 'sci-sec sci-s-results')}

    ${section('Orbit impact', 'What the finds do to the orbit', `<div class="sci-impact"><p class="muted">Loading the orbit fits...</p></div>`, 'sci-sec sci-s-impact')}

    ${section('Definitions', 'Nine checks, four verdicts', `
      <div class="sci-defs">
        <table class="data-table sci-checks">
          <thead><tr><th scope="col">Check</th><th scope="col">Key in object.json</th><th scope="col">Passes when</th></tr></thead>
          <tbody>${CHECKS.map(([k, n, d]) => `<tr><td>${n}</td><td>${k}</td><td>${d}</td></tr>`).join('')}</tbody>
        </table>
        <dl class="sci-verdicts">${VERDICTS.map(([v, d]) => `<div><dt>${chipFor(v)}</dt><dd>${d}</dd></div>`).join('')}</dl>
      </div>
      <p class="hint">Each object.json carries the measured numbers behind every check and the pass marks in checks.passed.</p>`, 'sci-sec sci-s-checks')}

    ${section('Validation', 'How the pipeline was tested', `
      <div class="sci-cards">
        <article class="card card-pad sci-bm"><p class="kicker">Blind test</p><p class="muted">Loading...</p></article>
        <article class="card card-pad sci-cross"><p class="kicker">Two machines</p><p class="muted">Loading...</p></article>
      </div>
      <article class="card card-pad sci-ai">
        <p class="chip chip-ai">AI, tested and reported</p>
        <ul>
          <li><h3>Real-or-fake score: works, advises only</h3><p>A small CNN separates known asteroids from planted artifacts with accuracy 0.974 and AUC 0.998 on held-out sky (1,043 samples), against 0.931 and 0.986 for gradient boosting. The fakes are planted, so this says nothing about real junk. No verdict rule uses the score.</p></li>
          <li><h3>Expected-sky U-Net: not better, not used</h3><p>A U-Net that predicts the static sky did not beat the plain reference: false alarms at bright stars rose to 18.3%, against about 10%. It is not in the engine.</p></li>
          <li><h3>Outside its range on bright objects</h3><p>On real objects the CNN scores lower than gradient boosting (433 Eros 0.76 against 0.99, 3I/ATLAS 0.35 against 0.66). Bright objects and comas are outside its training set.</p></li>
        </ul>
        <p class="hint">From the Kaggle training run of 2026-11-15 (T4 GPU, 8,792 SPHEREx frames). MEASURED on held-out data.</p>
      </article>`, 'sci-sec sci-s-validation')}

    ${section('Downloads', 'Every file behind this site', `
      <ul class="sci-files">${FILES.map(([f, d]) => `<li><a class="sci-file" href="${esc(rel(idxUrl, f))}" download>
          <span class="sci-file-ico">${ICO_FILE}</span><span class="sci-file-down">${ICO_DOWN}</span>
          <span class="sci-file-name">${esc(f)}</span><span class="sci-file-desc">${esc(d)}</span>
          <span class="sci-file-meta"><span>${fileType(f)}</span><span class="sci-size"></span></span></a></li>`).join('')}
        <li><div class="sci-file sci-file-static">
          <span class="sci-file-ico">${ICO_FOLDER}</span>
          <span class="sci-file-name">objects/&lt;slug&gt;/object.json</span><span class="sci-file-desc">One per object: photos, checks, cloud, spectrum. Open a row in the results table for its link.</span>
          <span class="sci-file-meta"><span>JSON, one per object</span></span></div></li>
      </ul>`, 'sci-sec sci-s-files')}

    ${section('Data contract', 'The format of every file', `
      <p>The analysis engine writes plain JSON and PNG files; this website only reads them. Times are MJD (UTC) plus ISO strings, 3D positions are heliocentric ecliptic J2000 in AU, angles are in degrees, and images are north up and east left with one brightness stretch per object and no smoothing.</p>
      <div class="sci-contract"></div>
      <p><a class="sci-link" href="DATA-CONTRACT.md" target="_blank" rel="noopener">Open the full DATA-CONTRACT.md</a></p>`, 'sci-sec sci-s-contract')}

    ${section('Positions', 'Measured positions in MPC 80-column format', `
      <div class="note note-warn"><strong>For expert review, never submitted</strong><p>These lines have not been sent to the Minor Planet Center or anywhere else. The observatory code is left as XXX, and the second line that space-based observations need (the spacecraft position) is not included.</p></div>
      <div class="sci-mpc"><p class="muted">Loading the positions...</p></div>`, 'sci-sec sci-s-mpc')}

    <footer class="sci-ack">
      <p class="kicker">Acknowledgements</p>
      <p>This publication makes use of data products from the Spectro-Photometer for the History of the Universe, Epoch of Reionization and Ices Explorer (SPHEREx), which is a joint project of the Jet Propulsion Laboratory and the California Institute of Technology, and is funded by the National Aeronautics and Space Administration.</p>
      <p>This research has made use of the NASA/IPAC Infrared Science Archive, which is funded by the National Aeronautics and Space Administration and operated by the California Institute of Technology.</p>
    </footer>`;

  const $ = <T extends HTMLElement>(sel: string) => body.querySelector(sel) as T;
  nav.forEach(([id]) => ($(`.sci-s-${id}`).id = `sci-${id}`));

  // ---------- sticky section nav: the section in the upper part of the view is marked ----------
  const navEl = $('.sci-nav');
  const track = $('.sci-nav-track');
  const mark = (id: string) => {
    track.querySelectorAll<HTMLElement>('[data-go]').forEach((b) => {
      const on = b.dataset.go === id;
      b.classList.toggle('on', on);
      if (on) {
        b.setAttribute('aria-current', 'true');
        // keep the marked pill visible when the bar scrolls sideways on phones, without moving the page
        const l = b.offsetLeft - track.offsetLeft;
        if (l < track.scrollLeft || l + b.offsetWidth > track.scrollLeft + track.clientWidth)
          track.scrollTo({ left: l - 16, behavior: reducedMotion ? 'auto' : 'smooth' });
      } else b.removeAttribute('aria-current');
    });
  };
  const seen = new Set<string>();
  const io = new IntersectionObserver((entries) => {
    entries.forEach((en) => (en.isIntersecting ? seen.add(en.target.id) : seen.delete(en.target.id)));
    const first = nav.find(([id]) => seen.has(`sci-${id}`));
    if (first) mark(`sci-${first[0]}`);
  }, { rootMargin: '-140px 0px -55% 0px' });
  nav.forEach(([id]) => io.observe($(`#sci-${id}`)));
  navEl.addEventListener('click', (e) => {
    const go = (e.target as HTMLElement).closest<HTMLElement>('[data-go]')?.dataset.go;
    if (!go) return;
    mark(go);
    document.getElementById(go)?.scrollIntoView({ behavior: reducedMotion ? 'auto' : 'smooth', block: 'start' });
  });

  // ---------- copy buttons on every code panel (the MPC ruler is left out) ----------
  body.addEventListener('click', async (e) => {
    const btn = (e.target as HTMLElement).closest<HTMLButtonElement>('.sci-copy');
    const pre = btn?.closest('.sci-panel')?.querySelector('pre');
    if (!btn || !pre) return;
    const copy = pre.cloneNode(true) as HTMLElement;
    copy.querySelectorAll('.sci-ruler').forEach((r) => r.remove());
    const label = btn.querySelector('span')!;
    try {
      await navigator.clipboard.writeText(copy.textContent!.replace(/\n*$/, '\n'));
      label.textContent = 'Copied';
      btn.classList.add('done');
    } catch {
      label.textContent = 'Select and copy';
    }
    setTimeout(() => {
      label.textContent = 'Copy';
      btn.classList.remove('done');
    }, 2200);
  });

  // ---------- download sizes, read from the server without fetching the files ----------
  body.querySelectorAll<HTMLAnchorElement>('a.sci-file').forEach((a) => {
    fetch(a.href, { method: 'HEAD' }).then((r) => {
      const n = Number(r.headers.get('content-length'));
      // a compressed response gives the transfer size, not the file size: show the type only
      if (alive && r.ok && n > 0 && !r.headers.get('content-encoding')) a.querySelector('.sci-size')!.textContent = bytes(n);
    }).catch(() => {});
  });

  // ---------- results table ----------
  const state = { verdict: 'ALL' as Verdict | 'ALL', q: '', sort: { key: 'verdict', dir: 1 } as Sort, page: 0, open: '' };
  const tbody = $('.sci-table tbody');
  const list = () => sortRows(filterRows(rows, state.verdict, state.q), state.sort);
  // every S/N bar shares one scale, set by the strongest object; the tick marks S/N 5
  const maxSnr = Math.max(0, ...rows.map((o) => o.best_snr ?? 0));
  $('.sci-table').style.setProperty('--five', `${snrBar(5, maxSnr)}%`);

  const rowHtml = (o: Row) => {
    const open = state.open === o.slug;
    const main = `<tr class="sci-row r-${esc(o.verdict.toLowerCase())}${open ? ' open' : ''}" data-slug="${esc(o.slug)}">
      <td><a href="#/object/${esc(o.slug)}">${esc(o.name)}</a></td>
      <td class="sci-wide">${esc(KIND[o.kind] ?? o.kind)}</td>
      <td class="sci-left">${chipFor(o.verdict)}</td>
      <td class="sci-snr">${o.best_snr == null ? '<span class="muted">-</span>' : `<span class="sci-spark" aria-hidden="true"><i style="width:${snrBar(o.best_snr, maxSnr).toFixed(1)}%"></i></span><span class="sci-snr-v">${o.best_snr.toFixed(1)}</span>`}</td>
      <td class="sci-wide">${fmt(o.n_frames ?? 0)}</td>
      <td class="sci-wide">${esc(o.discovered?.iso ?? '-')}</td>
      <td class="sci-wide${(o.days_before_first_known_obs ?? 0) > 0 ? ' gold' : ''}">${esc(lead(o))}</td>
      <td><button class="sci-more" aria-expanded="${open}" aria-label="Details for ${esc(o.name)}"></button></td>
    </tr>`;
    if (!open) return main;
    const by = [o.discovered?.by, o.discovered?.site].filter(Boolean).join(', ');
    const facts: [string, string][] = [
      ['Type', KIND[o.kind] ?? o.kind],
      ['Photos read', fmt(o.n_frames ?? 0)],
      ['Discovered', `${o.discovered?.iso ?? '-'}${by ? ` (${by})` : ''}`],
      ...(o.first_known_obs_iso ? [['First known observation', `${o.first_known_obs_iso} (JPL SBDB)`] as [string, string]] : []),
      ...(o.claim ? [['Claim', o.claim] as [string, string]] : []),
    ];
    return `${main}<tr class="sci-detail"><td colspan="8">
      <p>${esc(fixPlural(o.verdict_text ?? ''))}</p>
      <dl>${facts.map(([k, v]) => `<div><dt>${k}</dt><dd>${esc(v)}</dd></div>`).join('')}</dl>
      <p class="sci-detail-links"><a class="btn btn-s" href="#/object/${esc(o.slug)}">Open the object page${icon('arrow')}</a><a class="sci-link" href="${esc(rel(idxUrl, o.page))}" download>object.json</a></p>
    </td></tr>`;
  };

  const draw = () => {
    const all = list();
    const pages = Math.max(1, Math.ceil(all.length / PAGE));
    state.page = Math.min(state.page, pages - 1);
    const from = state.page * PAGE;
    tbody.innerHTML = all.slice(from, from + PAGE).map(rowHtml).join('') || `<tr><td colspan="8" class="empty">No object matches. Try another name or verdict.</td></tr>`;
    $('.sci-count').textContent = all.length ? `${from + 1} to ${Math.min(from + PAGE, all.length)} of ${all.length}` : '0 objects';
    $<HTMLButtonElement>('.sci-prev').disabled = state.page === 0;
    $<HTMLButtonElement>('.sci-next').disabled = state.page >= pages - 1;
    body.querySelectorAll<HTMLElement>('.sci-sort').forEach((b) =>
      b.parentElement!.setAttribute('aria-sort', b.dataset.sort !== state.sort.key ? 'none' : state.sort.dir === 1 ? 'ascending' : 'descending'));
  };

  $('.sci-tabs').addEventListener('click', (e) => {
    const tab = (e.target as HTMLElement).closest<HTMLElement>('[data-tab]');
    if (!tab) return;
    state.verdict = tab.dataset.tab as Verdict | 'ALL';
    state.page = 0;
    body.querySelectorAll('.sci-tabs button').forEach((b) => b.setAttribute('aria-pressed', String(b === tab)));
    draw();
  });
  $('.sci-search input').addEventListener('input', (e) => {
    state.q = (e.target as HTMLInputElement).value;
    state.page = 0;
    draw();
  });
  $('.sci-table thead').addEventListener('click', (e) => {
    const k = (e.target as HTMLElement).closest<HTMLElement>('[data-sort]')?.dataset.sort as SortKey | undefined;
    if (!k) return;
    // text columns start A to Z, number columns start with the largest
    const first = k === 'name' || k === 'kind' || k === 'verdict' ? 1 : -1;
    state.sort = { key: k, dir: state.sort.key === k ? (-state.sort.dir as 1 | -1) : first };
    state.page = 0;
    draw();
  });
  tbody.addEventListener('click', (e) => {
    const el = e.target as HTMLElement;
    if (el.closest('a') || el.closest('.sci-detail')) return;
    const slug = el.closest<HTMLElement>('.sci-row')?.dataset.slug;
    if (!slug) return;
    state.open = state.open === slug ? '' : slug;
    draw();
    if (el.closest('.sci-more')) tbody.querySelector<HTMLElement>(`[data-slug="${CSS.escape(slug)}"] .sci-more`)?.focus();
  });
  const turn = (d: number) => {
    state.page += d;
    draw();
    // keep the top of the table in view when the page changes
    const top = $('.sci-bar');
    if (top.getBoundingClientRect().top < 0) top.scrollIntoView({ block: 'start' });
  };
  $('.sci-prev').addEventListener('click', () => turn(-1));
  $('.sci-next').addEventListener('click', () => turn(1));
  $('.sci-csv').addEventListener('click', () => {
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([toCsv(list())], { type: 'text/csv' }));
    a.download = `rewind-results-${state.verdict.toLowerCase()}.csv`;
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  });
  draw();

  // ---------- validation: blind test and the two-machine cross-check ----------
  ctx.load<Bench>('benchmark.json').then(({ data, sample }) => {
    if (!alive) return;
    // counted from the cases (v2 marks cases with no usable test as "unknown"); decoys are patches of empty sky
    const bt = benchTally((data.cases ?? []).filter(usable));
    const decoys = decoyTally(data.decoys ?? []);
    const err = data.summary?.pos_err_arcsec;
    $('.sci-bm').innerHTML = `<p class="kicker">Blind test</p>
      <p class="sci-big">${bt.found} of ${bt.seen}<span>${plural(bt.false + decoys.false, 'false alarm')}</span></p>
      <p>${esc(data.summary?.plain ?? `Rewind found ${bt.found} of ${bt.seen} known objects that SPHEREx could see, in ${plural(bt.total, 'case')}.`)}</p>
      ${err?.median != null ? `<p class="mono">Position error: median ${err.median} arcsec${err.p90 != null ? `, 90% within ${err.p90}` : ''}${err.n ? ` (n = ${err.n})` : ''}.</p>` : ''}
      <p class="sci-card-foot"><a class="sci-link" href="#/benchmark">See every case</a>${provenance(sample, 'NASA SPHEREx')}</p>`;
  }).catch(() => alive && ($('.sci-bm').innerHTML = `<p class="kicker">Blind test</p><p class="muted">The benchmark file is not in this data set.</p>`));

  getJson<Crosscheck>(source.base + 'kaggle_crosscheck.json').then((x) => {
    if (!alive) return;
    const cc = x.crosscheck;
    const same = cc.filter((c) => c.mac_verdict === c.kaggle_verdict).length;
    const equal = cc.filter((c) => c.mac_snr === c.kaggle_snr).length;
    const name = (slug: string) => rows.find((o) => o.slug === slug)?.name ?? slug;
    $('.sci-cross').innerHTML = `<p class="kicker">Two machines</p>
      <p class="sci-big">${same} of ${cc.length}<span>same verdict</span></p>
      <p>${cc.length} objects, run on a Mac and on Kaggle from the same code. ${same === cc.length ? 'Every verdict agrees.' : `${cc.length - same} verdicts differ.`} The S/N is identical for ${equal} and differs a little for ${cc.length - equal}, for example where the earlier Mac run picked its reference photos under an older rule.</p>
      <details class="sci-fold"><summary>Show the ${cc.length} objects</summary>
        <table class="data-table sci-cc"><thead><tr><th scope="col">Object</th><th scope="col">Mac</th><th scope="col">Kaggle</th><th scope="col">S/N Mac</th><th scope="col">S/N Kaggle</th><th scope="col">Photos</th></tr></thead>
        <tbody>${cc.map((c) => `<tr><td><a href="#/object/${esc(c.slug)}">${esc(name(c.slug))}</a></td><td>${chipFor(c.mac_verdict)}</td><td>${chipFor(c.kaggle_verdict)}</td><td>${c.mac_snr.toFixed(2)}</td><td>${c.kaggle_snr.toFixed(2)}</td><td>${c.mac_frames === c.kaggle_frames ? c.mac_frames : `${c.mac_frames} / ${c.kaggle_frames}`}</td></tr>`).join('')}</tbody></table>
      </details>`;
  }).catch(() => {
    if (!alive) return;
    $('.sci-cross').innerHTML = `<p class="kicker">Two machines</p><p class="muted">The cross-check file is not in this data set.</p>`;
    body.querySelector('.sci-files a[href$="kaggle_crosscheck.json"]')?.closest('li')?.remove();
  });

  // ---------- data contract ----------
  fetch('DATA-CONTRACT.md').then((r) => (r.ok ? r.text() : '')).then((md) => {
    if (!alive) return;
    $('.sci-contract').innerHTML = splitContract(md).map((s) => `<details class="sci-fold"><summary>${esc(s.title)}</summary>
      <div class="sci-panel"><div class="sci-panel-head"><p class="mono">DATA-CONTRACT.md</p>${copyButton}</div><pre class="sci-code sci-wrap" tabindex="0" aria-label="${esc(s.title)}">${esc(s.body)}</pre></div></details>`).join('');
  }).catch(() => {});

  // ---------- the finds: orbit impact and MPC lines ----------
  const targets = rows.filter((o) => o.verdict === 'FOUND' && !isKnown(o));
  Promise.all(targets.map((o) => getJson<FindPage>(rel(idxUrl, o.page)).catch(() => null))).then((pages) => {
    if (!alive) return;
    const finds: Find[] = targets.map((o, k) => {
      const p = pages[k];
      const lines = (p?.checks?.orbit_fit?.positions ?? []).filter((q) => [q.mjd, q.ra, q.dec].every(Number.isFinite))
        .map((q) => mpcLine({ name: o.name.replace(/\s*\(.*\)$/, ''), mjd: q.mjd, ra: q.ra, dec: q.dec, note2: 'S', code: 'XXX' }));
      return { o, impact: p?.impact ?? null, lines };
    });
    impact(finds.filter((f) => f.impact));
    mpc(finds.filter((f) => f.lines.length));
  });

  const impact = (finds: Find[]) => {
    const box = $('.sci-impact');
    if (!finds.length) {
      box.innerHTML = `<p class="empty">No orbit fits in this data set.</p>`;
      return;
    }
    const sig = (s: Sigma | null | undefined) => (s?.sigma3_km_before != null && s.sigma3_km_after != null && s.factor != null ? s : null);
    const today = finds.map((f) => sig(f.impact!.one_year_after_last_obs)?.factor).filter((x): x is number => x != null);
    const best = finds.map((f) => ({ f, s: sig(f.impact!.at_discovery_scenario) })).filter((x) => x.s?.converged && x.s.factor! >= 2).sort((a, b) => b.s!.factor! - a.s!.factor!).slice(0, 2);
    const cell = (s: Sigma | null | undefined, none: string) => {
      const v = sig(s);
      if (!v) return `<td colspan="2" class="sci-na">${esc(s?.error ? 'fit too weak to sample' : none)}</td>`;
      return `<td>${arrow(km(v.sigma3_km_before!), km(v.sigma3_km_after!))}${v.converged === false ? '<small>fit did not converge: unreliable</small>' : ''}</td><td class="${v.factor! >= 2 && v.converged !== false ? 'gold' : ''}">${times(v.factor!)}</td>`;
    };
    box.innerHTML = `
      <dl class="stats sci-gain">
        ${best.map(({ f, s }) => stat(times(s!.factor!), `${f.o.name}, had Rewind run at discovery: ${km(s!.sigma3_km_before!)} to ${km(s!.sigma3_km_after!)} km`, 'stat-gold')).join('')}
        ${today.length ? stat(gainRange(today), 'today, now that weeks to a year of follow-up exist') : ''}
      </dl>
      <p>Rewind's value is speed. Right after discovery, a few old SPHEREx positions can shrink the uncertainty of the future path several times over. After the follow-up they add little.</p>
      <div class="sci-scroll"><table class="data-table sci-impact-table">
        <thead><tr><th scope="col">Object</th><th scope="col">First known obs.</th><th scope="col">Earlier by</th><th scope="col">Positions</th><th scope="col">Arc, days</th><th scope="col" colspan="2">3 sigma in 1 yr, today (km)</th><th scope="col" colspan="2">At discovery (km)</th></tr></thead>
        <tbody>${finds.map(({ o, impact: m }) => `<tr>
          <td><a href="#/object/${esc(o.slug)}">${esc(o.name)}</a></td>
          <td>${esc(m!.first_known_obs_iso ?? '-')}</td>
          <td>${(m!.days_before_first_known_obs ?? 0) > 0 ? `${m!.days_before_first_known_obs} d` : '<span class="muted">not earlier</span>'}</td>
          <td>${m!.spherex_positions ?? '-'}</td>
          <td>${m!.arc_days_before != null && m!.arc_days_after != null ? arrow(String(m!.arc_days_before), String(m!.arc_days_after)) : '-'}</td>
          ${cell(m!.one_year_after_last_obs, 'no fit')}
          ${cell(m!.at_discovery_scenario, 'no earlier position')}
        </tr>`).join('')}</tbody>
      </table></div>
      <p class="hint">COMPUTED with kete least-squares fits of the real MPC observations, without and with the SPHEREx positions (each given an uncertainty of at least ${finds[0].impact!.sigma_floor_arcsec ?? 2} arcsec). 3 sigma is the largest axis of 300 covariance clones (linear, gravity only), one year after the last observation. "At discovery" uses only the MPC observations of the first 7 days plus the SPHEREx positions that are earlier than them. First known observation: JPL SBDB, 2026-11-15.</p>`;
  };

  const mpc = (finds: Find[]) => {
    const box = $('.sci-mpc');
    if (!finds.length) {
      box.innerHTML = `<p class="empty">No measured positions in this data set.</p>`;
      return;
    }
    const ruler = Array.from({ length: 8 }, (_, i) => `${i + 1}`.padStart(10)).join('') + '\n' + '1234567890'.repeat(8);
    const pick = (k: number) => {
      const set = k < 0 ? finds : [finds[k]];
      const lines = set.flatMap((f) => f.lines);
      box.querySelectorAll('.sci-pick button').forEach((b, i) => b.classList.toggle('chip-on', i === k + 1));
      $('.sci-mpc-title').textContent = `${k < 0 ? `${finds.length} objects` : finds[k].o.name}, ${plural(lines.length, 'position')}`;
      $('.sci-mpc pre').innerHTML = `<span class="sci-ruler" aria-hidden="true">${ruler}\n</span>${esc(lines.join('\n'))}`;
      const copy = box.querySelector('.sci-copy')!;
      copy.classList.remove('done');
      copy.querySelector('span')!.textContent = 'Copy';
    };
    box.innerHTML = `
      <div class="sci-pick" role="group" aria-label="Object"><button type="button" class="chip" data-k="-1">All</button>${finds.map((f, k) => `<button type="button" class="chip" data-k="${k}">${esc(f.o.name)}</button>`).join('')}</div>
      <div class="sci-panel sci-panel-mpc">
        <div class="sci-panel-head"><p class="mono"><span class="sci-tag">MPC 80-col</span><span class="sci-mpc-title"></span></p>${copyButton}</div>
        <pre class="sci-code" tabindex="0" aria-label="MPC 80-column lines"></pre>
      </div>
      <p class="hint">Each line is the measured centre of one stack (one day of photos, or all days when a single day is too weak), from the SPHEREx frames used in the detection. These are the positions added in the orbit refits above. Note 2 is S (space-based).</p>
      <p class="sci-prov">${provenance(source.sample, 'NASA SPHEREx')}</p>`;
    $('.sci-pick').addEventListener('click', (e) => {
      const k = (e.target as HTMLElement).closest<HTMLElement>('[data-k]')?.dataset.k;
      if (k != null) pick(+k);
    });
    pick(-1);
  };

  return () => {
    alive = false;
    io.disconnect();
  };
};
