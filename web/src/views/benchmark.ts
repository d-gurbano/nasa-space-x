// "Does it work?": the "pretend it is new" test. We hide what we know about asteroids and comets
// that SPHEREx did (or did not) see, run Rewind blind, then compare with the truth.
// One sentence, three small charts, one card per test object (its real orbit, moving; flip for
// the result), how the test works. Everything else is folded away. Reads benchmark.json v2;
// every block is skipped when its fields are missing.
import '../styles/page-benchmark.css';
import { mjdFromIso, plainDate } from '../lib/time';
import { esc, plural, provenance } from '../ui/dom';
import { chip } from '../ui/components';
import { byOutcome, byType, curveBars, decoyTally, explain, median, orbitKey, outcome, posErrors, snrBar, tally, usable, type Bench, type BenchCase, type Outcome } from './benchmark/logic';
import { PIXEL_ARCSEC } from './sky/logic';
import { BENCH_ORBITS } from './visuals/bench-orbits';
import { animateOrbits, type OrbitMini } from './visuals/orbit-mini';
import type { View } from './page';

const BADGE: Record<Outcome, string> = { found: 'Found', hint: 'Hint', missed: 'Missed', quiet: 'Not visible', false: 'False alarm' };
const COLOR: Record<Outcome, string> = { found: '#f2b544', hint: '#a6d2ff', missed: '#b7b9c0', quiet: '#868a96', false: '#ee8a78' };
const TYPE: Record<string, string> = { neo: 'Near-Earth asteroids', comet: 'Comets', mba: 'Main-belt asteroids' };
const CHECK: Record<string, string> = {
  snr: 'Signal above S/N 5', cleaned: 'Fixed sky cleaned', nulls: 'Beats fake paths nearby', time_shift: 'Strongest at the right time',
  days: 'Seen on 2+ days', detectable: 'Bright enough to see', sign_test: 'Shows in single photos', not_one_day: 'Not one day alone', orbit: 'Fits the orbit',
};

const ICON = {
  hide: '<path d="M3 12s3.5-6 9-6 9 6 9 6-3.5 6-9 6-9-6-9-6z"/><circle cx="12" cy="12" r="2.6"/><path d="M4 20L20 4"/>',
  search: '<rect x="3" y="5" width="11" height="11" rx="1.5"/><rect x="7" y="9" width="11" height="11" rx="1.5"/><circle cx="12.5" cy="14.5" r="1.4" fill="currentColor"/>',
  check: '<circle cx="12" cy="12" r="8.5"/><path d="M8 12.4l2.7 2.7L16.2 9.4"/>',
};
const svg = (k: keyof typeof ICON) => `<svg viewBox="0 0 24 24" aria-hidden="true">${ICON[k]}</svg>`;

const shortName = (name: string) => name.replace(/^\(\d+\)\s*/, '');
const number = (name: string) => /^\((\d+)\)/.exec(name)?.[1] ?? '';

function bar(label: string, snr: number | null | undefined) {
  const v = typeof snr === 'number' ? snr : null;
  return `<span class="dw-bar"><span class="dw-bar-label">${label}</span><span class="dw-bar-track"><i style="--w:${snrBar(v)}"></i><b style="--at:${snrBar(5)}" title="S/N 5"></b></span><span class="dw-bar-num mono">${v === null ? 'n/a' : v.toFixed(1)}</span></span>`;
}

function card(c: BenchCase, i: number, hasOrbit: boolean): string {
  const o = outcome(c);
  const checks = Object.entries(c.checks ?? {}).filter(([k]) => CHECK[k]);
  return `<li class="dw-card dw-${o}" style="--i:${i}">
    <button class="dw-flip" aria-pressed="false" aria-label="${esc(shortName(c.name))}: ${BADGE[o]}. Show the result">
      <span class="dw-face dw-front">
        ${hasOrbit ? '<canvas class="dw-orbit" aria-hidden="true"></canvas>' : '<span class="dw-orbit dw-no-orbit" aria-hidden="true"></span>'}
        <span class="dw-badge">${BADGE[o]}</span>
        <span class="dw-id"><span class="dw-name">${esc(shortName(c.name))}</span>${number(c.name) ? `<span class="dw-num mono">${number(c.name)}</span>` : ''}</span>
      </span>
      <span class="dw-face dw-back" aria-hidden="true">
        <span class="dw-badge">${BADGE[o]}</span>
        <span class="dw-sentence">${esc(explain(c))}</span>
        <span class="dw-bars">${bar('Rewind, blind', c.snr)}${bar('True spot', c.oracle_snr)}</span>
        ${checks.length ? `<span class="dw-checks" title="${checks.map(([k, ok]) => `${ok ? 'Passed' : 'Failed'}: ${CHECK[k]}`).join('\n')}">${checks.map(([, ok]) => `<i class="${ok ? 'ok' : 'no'}"></i>`).join('')}<span class="mono">${checks.filter(([, ok]) => ok).length}/${checks.length} checks</span></span>` : ''}
        ${c.hidden_until_iso ? `<span class="dw-when mono">Hidden from ${esc(plainDate(c.hidden_until_iso))}</span>` : ''}
      </span>
    </button>
  </li>`;
}

// share found (gold) and share hint (blue) in each brightness bin
function curveHtml(data: Bench): string {
  const bars = curveBars(data.completeness_curve ?? []);
  if (!bars.length) return '';
  return `<article class="dw-panel">
    <p class="kicker">Brighter is easier</p>
    <ol class="dw-curve" aria-label="Share of test objects found, by brightness">${bars.map((b) => `<li aria-label="Magnitude ${b.label}: ${b.found} of ${b.n} found${b.hint ? `, ${plural(b.hint, 'hint')}` : ''}">
      <span class="dw-col-num mono">${b.found}/${b.n}</span>
      <span class="dw-col"><i class="dw-col-hint" style="--h:${b.hint / b.n}"></i><i class="dw-col-found" style="--h:${b.found / b.n}"></i></span>
      <span class="dw-col-label mono">${esc(b.label)}</span></li>`).join('')}</ol>
    <p class="dw-panel-foot">Found per brightness step (magnitude; left is brighter). Blue is a hint.</p>
  </article>`;
}

// one dot per case on a line from 0 to one SPHEREx pixel
function closeHtml(data: Bench, cases: BenchCase[]): string {
  const errs = posErrors(cases);
  const med = data.summary?.pos_err_arcsec?.median ?? median(errs);
  if (med == null) return '';
  const at = (v: number) => Math.min(1, v / PIXEL_ARCSEC);
  return `<article class="dw-panel">
    <p class="kicker">How close it pointed</p>
    <p class="dw-big">${med.toFixed(1)}<small>arcsec, median</small></p>
    ${errs.length ? `<div class="dw-strip" role="img" aria-label="${errs.length} measured positions, all within ${errs[errs.length - 1].toFixed(1)} arcsec of the true one">${errs.map((v) => `<i style="--x:${at(v)}"></i>`).join('')}<b style="--x:${at(med)}"></b></div>
    <p class="dw-strip-ends mono"><span>0</span><span>1 SPHEREx pixel, ${PIXEL_ARCSEC.toFixed(1)}"</span></p>` : ''}
    <p class="dw-panel-foot">Distance from the true position. Every dot is one test object.</p>
  </article>`;
}

function typeHtml(cases: BenchCase[]): string {
  const types = [...byType(cases)].filter(([, t]) => t.seen > 0);
  if (!types.length) return '';
  return `<article class="dw-panel">
    <p class="kicker">By type</p>
    <ul class="dw-types">${types.map(([k, t]) => `<li>
      <span class="dw-type-name">${esc(TYPE[k] ?? k)}</span><span class="dw-type-num mono">${t.found} of ${t.seen}</span>
      <span class="dw-seg" aria-hidden="true">${(['found', 'hint', 'missed'] as Outcome[]).map((o) => (t[o] ? `<i class="dw-${o}" style="flex:${t[o]}"></i>` : '')).join('')}</span></li>`).join('')}</ul>
    <p class="dw-panel-foot">Found, of those SPHEREx could see. Blue is a hint, grey is missed.</p>
  </article>`;
}

// the first, smaller run: one line per case
function firstTestHtml(v1: Bench['v1']): string {
  const cases = byOutcome((v1?.cases ?? []).filter(usable));
  if (!cases.length) return '';
  const t = tally(cases);
  return `<details class="dw-fold"><summary>First test (${plural(cases.length, 'case')})</summary>
    <p>Found ${t.found} of ${t.seen} it could see${t.hint ? `, ${plural(t.hint, 'hint')}` : ''}${t.missed ? `, ${t.missed} missed` : ''}, ${plural(t.false, 'false alarm')}. The larger test above repeats it with more objects and with empty-sky decoys.</p>
    <ul class="dw-v1">${cases.map((c) => `<li class="dw-card dw-${outcome(c)}"><span class="dw-badge">${BADGE[outcome(c)]}</span><span>${esc(shortName(c.name))}</span><span class="mono">${typeof c.snr === 'number' ? 'S/N ' + c.snr.toFixed(1) : ''}</span></li>`).join('')}</ul>
  </details>`;
}

export const benchmarkView: View = async (body, ctx) => {
  const { data, sample } = await ctx.load<Bench>('benchmark.json');
  const all = data.cases ?? [];
  const cases = byOutcome(all.filter(usable));
  const skipped = all.length - cases.length;
  const t = tally(cases);
  const decoys = decoyTally(data.decoys ?? []);
  const wrong = t.false + decoys.false;
  const alarms = wrong === 0 ? 'zero false alarms' : wrong === 1 ? 'one false alarm' : `${wrong} false alarms`;
  const orbits = cases.map((c) => BENCH_ORBITS[orbitKey(c.name)] ?? null);
  const counts = (['found', 'hint', 'missed', 'quiet', 'false'] as Outcome[]).filter((o) => t[o] > 0);
  const kinds = new Set(cases.map((c) => c.type));
  const what = kinds.has('comet') ? 'asteroids and comets' : 'asteroids';
  const panels = [curveHtml(data), closeHtml(data, cases), typeHtml(cases)].filter(Boolean);

  body.innerHTML = `
    <p class="dw-hero display">We hid the answers and asked Rewind. It found <em>${t.found} of ${t.seen}</em> known ${what} it could see, with ${alarms}.</p>
    <ul class="dw-tally" aria-label="Results">${counts.map((o) => `<li class="dw-${o}"><i></i><b class="mono">${t[o]}</b>${BADGE[o]}</li>`).join('')}${decoys.ran ? `<li class="dw-decoys"><b class="mono">${decoys.false}</b>${decoys.false === 1 ? 'false alarm' : 'false alarms'} on ${plural(decoys.ran, 'patch', 'patches')} of empty sky</li>` : ''}</ul>
    ${panels.length ? `<div class="dw-panels">${panels.join('')}</div>` : ''}

    <ol class="dw-grid" aria-label="${plural(t.total, 'test object')}, found first">${cases.map((c, i) => card(c, i, !!orbits[i])).join('')}</ol>
    <p class="dw-hint-line">The real orbit of each test object, with Earth's orbit dotted. Hover or tap a card for the result.</p>

    <ol class="dw-how" aria-label="How the test works">
      <li>${svg('hide')}<span><b>Hide</b>Keep only the first weeks of a known object's observations, as if it were just found.</span></li>
      <li>${svg('search')}<span><b>Search blind</b>Rewind stacks the older SPHEREx photos along that rough path.</span></li>
      <li>${svg('check')}<span><b>Compare</b>Check against the true JPL position. A miss costs nothing; a false alarm would.</span></li>
    </ol>

    <div class="dw-folds">
      ${firstTestHtml(data.v1)}
      ${skipped ? `<details class="dw-fold"><summary>${plural(skipped, 'more case')} could not be tested</summary><p>${esc(data.summary?.unusable_note ?? 'These had no usable "pretend it is new" test: ' + all.filter((c) => !usable(c)).map((c) => c.name).join(', ') + '.')}</p></details>` : ''}
      ${data.summary?.method ? `<details class="dw-fold"><summary>How the test was run, exactly</summary><p>${esc(data.summary.method)}</p></details>` : ''}
      <!-- numbers from the Kaggle runs: MAIN/data/kaggle/SUMMARY.md, K2 -->
      <details class="dw-fold"><summary>The AI, honestly</summary><p>On parts of the sky it had never seen, a small neural network told real asteroids from planted fakes with 0.974 accuracy, against 0.931 for gradient boosting. The fakes are planted, so this says nothing about real junk. A second network, the "Expected Sky" U-Net, did not beat the simple static-sky reference (about twice the false alarms at bright stars), so Rewind does not use it. No verdict depends on AI.</p></details>
    </div>
    <div class="dw-foot">${provenance(sample, 'Rewind test on NASA SPHEREx')}${data.summary?.label ? chip(data.summary.label) : ''}<span class="hint">Orbits: JPL Small-Body Database.</span></div>`;

  // flip: hover on a mouse, tap or Enter anywhere; one card open at a time on touch
  const flips = [...body.querySelectorAll<HTMLButtonElement>('.dw-flip')];
  const set = (b: HTMLButtonElement, on: boolean) => {
    b.setAttribute('aria-pressed', String(on));
    b.querySelector('.dw-back')?.setAttribute('aria-hidden', String(!on));
  };
  flips.forEach((b) => {
    b.addEventListener('click', () => {
      const on = b.getAttribute('aria-pressed') !== 'true';
      flips.forEach((x) => x !== b && set(x, false));
      set(b, on);
    });
    b.addEventListener('pointerenter', (e) => e.pointerType === 'mouse' && set(b, true));
    b.addEventListener('pointerleave', (e) => e.pointerType === 'mouse' && set(b, false));
  });

  const items: OrbitMini[] = [];
  body.querySelectorAll<HTMLLIElement>('.dw-grid .dw-card').forEach((li, i) => {
    const canvas = li.querySelector('canvas');
    if (canvas && orbits[i]) items.push({ canvas, el: orbits[i]!, mjd0: cases[i].hidden_until_iso ? mjdFromIso(cases[i].hidden_until_iso!) : orbits[i]!.epoch_mjd, color: COLOR[outcome(cases[i])] });
  });
  return animateOrbits(items);
};
