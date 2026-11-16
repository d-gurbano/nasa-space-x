// "Does it work?": the "pretend it is new" test. We hide what we know about asteroids and comets
// that SPHEREx did (or did not) see, run Rewind blind, then compare with the truth.
// One sentence, three small charts, one card per test object (its real orbit, moving; flip for
// the result), how the test works. Everything else is folded away. Reads benchmark.json v2;
// every block is skipped when its fields are missing.
import '../styles/page-benchmark.css';
import { mjdFromIso, plainDate } from '../lib/time';
import { esc, plural, provenance } from '../ui/dom';
import { chip } from '../ui/components';
import { alarmLine, byOutcome, byType, curveBars, decoyTally, explain, methodText, median, orbitKey, outcome, posErrors, snrBar, tally, usable, type Bench, type BenchCase, type Outcome } from './benchmark/logic';
import { PIXEL_ARCSEC } from './sky/logic';
import { BENCH_ORBITS } from './visuals/bench-orbits';
import { animateOrbits, type OrbitMini } from './visuals/orbit-mini';
import type { View } from './page';
import type { IndexObject } from '../lib/types';
import { CHECKS } from '../lib/checks';

const BADGE: Record<Outcome, string> = { found: 'Found', hint: 'Hint', missed: 'Missed', quiet: 'Below limit', false: 'False alarm' };
const COLOR: Record<Outcome, string> = { found: '#f2b544', hint: '#a6d2ff', missed: '#b7b9c0', quiet: '#868a96', false: '#ee8a78' };
const TYPE: Record<string, string> = { neo: 'Near-Earth asteroids', comet: 'Comets', mba: 'Main-belt asteroids' };
const CHECK: Record<string, string> = Object.fromEntries(CHECKS.map((d) => [d.key, d.name]));

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

function card(c: BenchCase, i: number, hasOrbit: boolean, xref = ''): string {
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
        <span class="dw-sentence">${esc(explain(c))}${xref ? `<span class="dw-xref">${esc(xref)}</span>` : ''}</span>
        <span class="dw-bars">${bar('S/N, blind search', c.snr)}${bar('S/N at JPL position', c.oracle_snr)}</span>
        ${checks.length ? `<span class="dw-checks" title="${checks.map(([k, ok]) => `${ok ? 'Passed' : 'Failed'}: ${CHECK[k]}`).join('\n')}">${checks.map(([, ok]) => `<i class="${ok ? 'ok' : 'no'}"></i>`).join('')}<span class="mono">${checks.filter(([, ok]) => ok).length}/${checks.length} checks</span></span>` : ''}
        ${c.hidden_until_iso ? `<span class="dw-when mono">Observations after ${esc(plainDate(c.hidden_until_iso))} hidden</span>` : ''}
      </span>
    </button>
  </li>`;
}

/** A note when the main search (full arc) reached a different verdict than this blind run. */
function xrefText(c: BenchCase, o: IndexObject | undefined): string {
  if (!o) return '';
  const blind = outcome(c);
  if (o.verdict === 'FOUND' && blind !== 'found') {
    return `Main search: FOUND${o.best_snr != null ? ` (S/N ${o.best_snr.toFixed(1)})` : ''}, using the full observed arc and ${plural(o.n_frames ?? 0, 'SPHEREx image')}. This blind run used ${c.arc_days != null ? `a ${c.arc_days}-day arc` : 'a truncated arc'}${c.n_frames != null ? ` and ${plural(c.n_frames, 'image')}` : ''}.`;
  }
  if (o.verdict !== 'FOUND' && blind === 'found') return `Main search verdict: ${o.verdict.replace('_', ' ')}.`;
  return '';
}

// share found (gold) and share hint (blue) in each brightness bin
function curveHtml(data: Bench): string {
  const bars = curveBars(data.completeness_curve ?? []);
  if (!bars.length) return '';
  return `<article class="dw-panel">
    <p class="kicker">Completeness vs magnitude</p>
    <ol class="dw-curve" aria-label="Fraction of detectable test objects recovered, by predicted V magnitude">${bars.map((b) => `<li aria-label="V magnitude ${b.label}: ${b.found} of ${b.n} found${b.hint ? `, ${plural(b.hint, 'hint')}` : ''}">
      <span class="dw-col-num mono">${b.found}/${b.n}</span>
      <span class="dw-col"><i class="dw-col-hint" style="--h:${b.hint / b.n}"></i><i class="dw-col-found" style="--h:${b.found / b.n}"></i></span>
      <span class="dw-col-label mono">${esc(b.label)}</span></li>`).join('')}</ol>
    <p class="dw-panel-foot">FOUND fraction among objects SPHEREx recorded, per bin of predicted V magnitude (JPL Horizons; left is brighter). Blue: HINT.</p>
  </article>`;
}

// one dot per case on a line from 0 to one SPHEREx pixel
function closeHtml(data: Bench, cases: BenchCase[]): string {
  const errs = posErrors(cases);
  const med = data.summary?.pos_err_arcsec?.median ?? median(errs);
  if (med == null) return '';
  const at = (v: number) => Math.min(1, v / PIXEL_ARCSEC);
  return `<article class="dw-panel">
    <p class="kicker">Astrometric offset</p>
    <p class="dw-big">${med.toFixed(1)}<small>arcsec, median</small></p>
    ${errs.length ? `<div class="dw-strip" role="img" aria-label="${errs.length} measured positions, all within ${errs[errs.length - 1].toFixed(1)} arcsec of the JPL Horizons position">${errs.map((v) => `<i style="--x:${at(v)}"></i>`).join('')}<b style="--x:${at(med)}"></b></div>
    <p class="dw-strip-ends mono"><span>0</span><span>1 SPHEREx pixel, ${PIXEL_ARCSEC.toFixed(1)}"</span></p>` : ''}
    <p class="dw-panel-foot">Offset of the blind-search position from JPL Horizons; one mark per test object.</p>
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
    <p class="dw-panel-foot">FOUND fraction among detectable test objects. Blue: HINT; grey: missed.</p>
  </article>`;
}

// the first, smaller run: one line per case
function firstTestHtml(v1: Bench['v1']): string {
  const cases = byOutcome((v1?.cases ?? []).filter(usable));
  if (!cases.length) return '';
  const t = tally(cases);
  return `<details class="dw-fold"><summary>First test (${plural(cases.length, 'case')})</summary>
    <p>${t.found} of ${t.seen} detectable objects recovered as FOUND${t.hint ? `, ${plural(t.hint, 'HINT')}` : ''}${t.missed ? `, ${t.missed} missed` : ''}, ${plural(t.false, 'false FOUND')}. The test above repeats it with more objects and with empty-sky decoys.</p>
    <ul class="dw-v1">${cases.map((c) => `<li class="dw-card dw-${outcome(c)}"><span class="dw-badge">${BADGE[outcome(c)]}</span><span>${esc(shortName(c.name))}</span><span class="mono">${typeof c.snr === 'number' ? 'S/N ' + c.snr.toFixed(1) : ''}</span></li>`).join('')}</ul>
  </details>`;
}

export const benchmarkView: View = async (body, ctx) => {
  const { data, sample } = await ctx.load<Bench>('benchmark.json');
  // the same object can also be in the main search, which uses its full observed arc and all
  // SPHEREx images; say so when the two runs disagree, so the pages never contradict each other
  const main = await ctx.load<{ objects: IndexObject[] }>('index.json').then((r) => r.data.objects, () => [] as IndexObject[]);
  const mainBy = new Map(main.map((o) => [orbitKey(o.name), o]));
  const all = data.cases ?? [];
  const cases = byOutcome(all.filter(usable));
  const skipped = all.length - cases.length;
  const t = tally(cases);
  const decoys = decoyTally(data.decoys ?? []);
  const wrong = t.false + decoys.false;
  const alarms = wrong === 0 ? 'no false FOUNDs' : wrong === 1 ? 'one false FOUND' : `${wrong} false FOUNDs`;
  const orbits = cases.map((c) => BENCH_ORBITS[orbitKey(c.name)] ?? null);
  const counts = (['found', 'hint', 'missed', 'quiet', 'false'] as Outcome[]).filter((o) => t[o] > 0);
  const kinds = new Set(cases.map((c) => c.type));
  const what = kinds.has('comet') ? 'asteroids and comets' : 'asteroids';
  const panels = [curveHtml(data), closeHtml(data, cases), typeHtml(cases)].filter(Boolean);

  body.innerHTML = `
    <p class="dw-hero display">With the later observations hidden, Rewind recovered <em>${t.found} of ${t.seen}</em> known ${what} that SPHEREx recorded, with ${alarms}.</p>
    <p class="dw-sub">${t.found} FOUND, ${plural(t.hint, 'HINT')}, ${t.missed} missed, of ${t.seen} objects detectable at their true positions (S/N ≥ 5). ${t.quiet ? `${t.quiet} more were below S/N 5 even at the true position. ` : ''}A false alarm would be a FOUND on an object SPHEREx did not record, or on an empty-sky decoy.</p>
    <ul class="dw-tally" aria-label="Results">${counts.map((o) => `<li class="dw-${o}"><i></i><b class="mono">${t[o]}</b>${BADGE[o]}</li>`).join('')}<li class="dw-decoys">${alarmLine(t, decoys).replace(/^(\d+)/, '<b class="mono">$1</b>')}</li></ul>
    ${panels.length ? `<div class="dw-panels">${panels.join('')}</div>` : ''}

    <p class="dw-hint-line dw-rule">HINT: a signal, but not all nine checks pass; each card names the failed checks. Not visible: S/N &lt; 5 even at the true position, so the object was not detectable in these images.</p>
    <ol class="dw-grid" aria-label="${plural(t.total, 'test object')}, found first">${cases.map((c, i) => card(c, i, !!orbits[i], xrefText(c, mainBy.get(orbitKey(c.name))))).join('')}</ol>
    <p class="dw-hint-line">Each card shows the object's orbit (Earth's orbit dotted). Hover or tap for the result.</p>

    <ol class="dw-how" aria-label="How the test works">
      <li>${svg('hide')}<span><b>Truncate the arc</b>Fit an orbit from only the first 20 to 45 days of a known object's MPC observations, as if it had just been discovered.</span></li>
      <li>${svg('search')}<span><b>Blind search</b>Shift-and-stack up to 40 SPHEREx images from the 20 days before that date along the short-arc prediction, and apply the nine checks.</span></li>
      <li>${svg('check')}<span><b>Compare</b>Measure the same images at the true JPL Horizons positions. A miss costs completeness; a false FOUND would cost trust.</span></li>
    </ol>

    <div class="dw-folds">
      ${firstTestHtml(data.v1)}
      ${skipped ? `<details class="dw-fold"><summary>${plural(skipped, 'more case')} could not be tested</summary><p>${esc(data.summary?.unusable_note ?? 'These had no usable blind test: ' + all.filter((c) => !usable(c)).map((c) => c.name).join(', ') + '.')}</p></details>` : ''}
      ${data.summary?.method ? `<details class="dw-fold"><summary>How the test was run, exactly</summary><p>${esc(methodText(data.summary.method))}</p></details>` : ''}
      <!-- numbers from the Kaggle runs: MAIN/data/kaggle/SUMMARY.md, K2 -->
      <details class="dw-fold"><summary>Where we used machine learning</summary><p>On held-out sky, a small CNN separated known asteroids from injected artifacts with accuracy 0.974 (gradient boosting: 0.931). The negatives are injected, so this does not measure performance on real artifacts. A U-Net that predicts the static sky did not beat the plain reference image (about twice the false alarms near bright stars) and is not used. No verdict rule uses either model.</p></details>
    </div>
    <div class="dw-foot">${provenance(sample, 'Rewind test on NASA SPHEREx')}${data.summary?.label ? chip(data.summary.label) : ''}<span class="hint">Orbits: JPL Small-Body Database. Reference positions: JPL Horizons.</span></div>`;

  // flip: hover on a mouse, tap or Enter anywhere; one card open at a time on touch.
  // Hover and taps land on the static <li>, never on the rotating button: its hit area narrows
  // mid-flip, which made the card flip back and forth near its edges.
  const flips = [...body.querySelectorAll<HTMLButtonElement>('.dw-flip')];
  const set = (b: HTMLButtonElement, on: boolean) => {
    b.setAttribute('aria-pressed', String(on));
    b.querySelector('.dw-back')?.setAttribute('aria-hidden', String(!on));
  };
  flips.forEach((b) => {
    const li = b.closest('li')!;
    let leave = 0;
    li.addEventListener('click', () => {
      const on = b.getAttribute('aria-pressed') !== 'true';
      flips.forEach((x) => x !== b && set(x, false));
      set(b, on);
    });
    li.addEventListener('pointerenter', (e) => {
      if (e.pointerType !== 'mouse') return;
      clearTimeout(leave);
      set(b, true);
    });
    li.addEventListener('pointerleave', (e) => {
      if (e.pointerType === 'mouse') leave = window.setTimeout(() => set(b, false), 120);
    });
  });

  const items: OrbitMini[] = [];
  body.querySelectorAll<HTMLLIElement>('.dw-grid .dw-card').forEach((li, i) => {
    const canvas = li.querySelector('canvas');
    if (canvas && orbits[i]) items.push({ canvas, el: orbits[i]!, mjd0: cases[i].hidden_until_iso ? mjdFromIso(cases[i].hidden_until_iso!) : orbits[i]!.epoch_mjd, color: COLOR[outcome(cases[i])] });
  });
  return animateOrbits(items);
};
