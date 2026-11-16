// Pulse reader: step through real SPHEREx seasons of R Draconis, a Mira variable, and find how long
// one pulse takes by laying a sine over our measured points. Then RW Aurigae, a young star that dims
// without a rhythm. The points are wing photometry of real L2 stamps (web/scripts/games/pulse-photometry.py).
import '../../styles/game-pulse.css';
import { icon } from '../../ui/components';
import { esc, provenance } from '../../ui/dom';
import { reducedMotion } from '../../state';
import { confetti } from './confetti';
import type { View } from '../page';
import { buildRounds, fitSine, gradePeriod, isoToMjd, mjdToIso, points, type Band, type Bin, type Grade, type PulseData, type Round, type Season } from './pulse-logic';

type Star = 'rdra' | 'rwaur';
const BAND: Record<Band, string> = { short: '0.75 to 2.4 µm', long: '2.4 to 5 µm' };
const NAME: Record<Star, string> = { rdra: 'R Draconis', rwaur: 'RW Aurigae' };
const P_MIN = 100, P_MAX = 500;

// chart geometry, in SVG units
const W = 640, H = 300, X0 = 44, X1 = 620, Y0 = 24, Y1 = 250;
const MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const day = (iso: string) => { const [y, m, d] = iso.split('-').map(Number); return `${d} ${MON[m - 1]} ${y}`; };
const mag = (v: number) => `${Math.abs(v).toFixed(2)} mag`;

export const view: View = async (body, ctx) => {
  const { data, sample } = await ctx.load<PulseData>('games/pulse/pulse.json');
  const seasons: Record<Star, Season[]> = { rdra: data.rdra.seasons, rwaur: data.rwaur.seasons };
  const rounds = buildRounds(data, seasons.rdra);
  const P_TRUE = data.rdra.vsx.period;
  const max = rounds.length * 10;
  let k = 0, score = 0, turn = 0, done = false, playing = 0;
  let grades: Grade[] = [];
  let star: Star = 'rdra', si = 0;

  body.innerHTML = `
    <div class="pu">
      <header class="gm-bar">
        <h2 class="gm-title">Pulse reader</h2>
        <ol class="gm-prog" aria-label="Rounds"></ol>
        <p class="gm-score"><span class="mono">Score</span><b class="mono pu-pts">0</b></p>
      </header>
      <p class="gm-sub pu-intro">Some stars swell and fade in a steady rhythm. Step through real SPHEREx images taken months apart, then find how long one pulse takes.</p>
      <div class="gm-stage">
        <figure class="pu-fig">
          <p class="pu-who"><span class="mono pu-kind"></span><b class="pu-name"></b></p>
          <div class="pu-view">
            <div class="pu-imgbox"><img class="pu-img" alt="" width="488" height="488"/><span class="pu-tag pu-tag-a mono" hidden>A</span><span class="pu-tag pu-tag-b mono" hidden>B</span></div>
            <div class="pu-scrub">
              <p class="pu-date"><b class="mono pu-d"></b><span class="pu-n"></span></p>
              <label class="pu-lab" for="pu-season">Season</label>
              <input id="pu-season" class="pu-range" type="range" min="0" value="0" step="1"/>
              <button type="button" class="btn btn-ghost pu-play">Play</button>
              <p class="pu-cap">Each image stacks the exposures of one season. White pixels are saturated, so a bigger white core means a brighter star.</p>
            </div>
          </div>
          <svg class="pu-svg" viewBox="0 0 ${W} ${H}" role="img" aria-label="Measured brightness change over time; brighter is up">
            <g class="pu-grid"></g><g class="pu-sine"></g><g class="pu-pts-g"></g><g class="pu-mark"></g>
          </svg>
        </figure>
        <div class="gm-side"><div class="pu-ask"></div><div class="pu-reveal" hidden></div></div>
      </div>
      <div class="tr-foot">${provenance(sample, 'Real SPHEREx images, brightness measured by our team')}</div>
    </div>
    <div class="gm-end" hidden></div>`;
  const q = <T extends Element = HTMLElement>(s: string) => body.querySelector(s) as T;
  const ask = q('.pu-ask'), reveal = q('.pu-reveal'), range = q<HTMLInputElement>('.pu-range'), img = q<HTMLImageElement>('.pu-img');

  // chart scale for the star on screen
  let X = (m: number) => m, Y = (v: number) => v, span: [number, number] = [0, 1];
  const binsOf = (r: Round): Bin[] => (r.star === 'rdra' ? data.rdra[r.type === 'period' ? r.band : 'short'] : data.rwaur.long);
  const scale = (r: Round) => {
    const all = r.star === 'rdra' ? [...data.rdra.short, ...data.rdra.long] : data.rwaur.long;
    const sm = seasons[r.star].map((s) => isoToMjd(s.iso));
    span = [Math.min(...all.map((b) => b.mjd), ...sm) - 12, Math.max(...all.map((b) => b.mjd), ...sm) + 12];
    const vs = all.flatMap((b) => [b.dmag - b.err, b.dmag + b.err]);
    const lo = Math.min(...vs, -0.4) - 0.1, hi = Math.max(...vs, 0.4) + 0.1;
    X = (m) => X0 + ((m - span[0]) / (span[1] - span[0])) * (X1 - X0);
    Y = (v) => Y0 + ((v - lo) / (hi - lo)) * (Y1 - Y0); // fainter (larger magnitude) is down
    let g = `<line class="pu-zero" x1="${X0}" x2="${X1}" y1="${Y(0)}" y2="${Y(0)}"/>`;
    const s0 = new Date((span[0] - 40587) * 864e5);
    for (let d = new Date(Date.UTC(s0.getUTCFullYear(), s0.getUTCMonth() + 1, 1)); isoToMjd(d.toISOString()) < span[1]; d.setUTCMonth(d.getUTCMonth() + 1)) {
      if (d.getUTCMonth() % 3) continue;
      const x = X(isoToMjd(d.toISOString().slice(0, 10)));
      g += `<line x1="${x}" x2="${x}" y1="${Y0}" y2="${Y1}"/><text x="${x}" y="${Y1 + 20}">${MON[d.getUTCMonth()]} ${d.getUTCFullYear()}</text>`;
    }
    g += `<text class="pu-axis" x="${X0}" y="${Y0 - 8}">brighter is up</text><text class="pu-axis pu-axis-r" x="${X1}" y="${Y1 + 42}">magnitude change, same wavelength channel</text>`;
    q('.pu-grid').innerHTML = g;
  };
  const drawPoints = (bins: Bin[], cls = '') =>
    (q('.pu-pts-g').innerHTML = bins.map((b) => `<line class="pu-err" x1="${X(b.mjd)}" x2="${X(b.mjd)}" y1="${Y(b.dmag - b.err)}" y2="${Y(b.dmag + b.err)}"/><circle class="pu-pt ${cls}" cx="${X(b.mjd)}" cy="${Y(b.dmag)}" r="4.5"><title>${mjdToIso(b.mjd)}: ${b.dmag >= 0 ? '+' : ''}${b.dmag.toFixed(2)} mag, ${b.n} exposures</title></circle>`).join(''));
  const drawSine = (bins: Bin[], P: number, cls = 'pu-s-guess') => {
    const f = fitSine(bins.map((b) => b.mjd), bins.map((b) => b.dmag), bins.map((b) => b.err), P);
    let d = '';
    for (let i = 0; i <= 240; i++) {
      const m = span[0] + ((span[1] - span[0]) * i) / 240;
      d += `${i ? 'L' : 'M'}${X(m).toFixed(1)} ${Y(f.at(m)).toFixed(1)}`;
    }
    q('.pu-sine').insertAdjacentHTML('beforeend', `<path class="pu-s ${cls}" d="${d}"/>`);
    return f;
  };
  const marks = (extra = '') => {
    const s = seasons[star][si], x = X(isoToMjd(s.iso));
    q('.pu-mark').innerHTML = extra + `<line class="pu-now" x1="${x}" x2="${x}" y1="${Y0}" y2="${Y1}"/>`;
  };

  let markExtra = '';
  const showSeason = (i: number) => {
    si = i;
    const s = seasons[star][i];
    range.value = String(i);
    range.setAttribute('aria-valuetext', `${day(s.iso)}, ${s.n_frames} exposures`);
    img.src = ctx.source.base + `stars/${star}/${s.png}`;
    img.alt = `SPHEREx season stack of ${NAME[star]}, ${day(s.iso)}`;
    q('.pu-d').textContent = day(s.iso);
    q('.pu-n').textContent = `${s.n_frames} exposures`;
    const r = rounds[k];
    const ab = r?.type === 'compare' ? (i === r.a ? 'a' : i === r.b ? 'b' : '') : '';
    q('.pu-tag-a').hidden = ab !== 'a';
    q('.pu-tag-b').hidden = ab !== 'b';
    marks(markExtra);
  };
  const stopPlay = () => { clearInterval(playing); playing = 0; q('.pu-play').textContent = 'Play'; };
  range.oninput = () => { stopPlay(); showSeason(+range.value); };
  q<HTMLButtonElement>('.pu-play').onclick = () => {
    if (playing) return stopPlay();
    q('.pu-play').textContent = 'Pause';
    playing = window.setInterval(() => showSeason((si + 1) % seasons[star].length), reducedMotion ? 1400 : 650);
  };

  let answer: (a: string) => void = () => {};
  const prog = () => (q('.gm-prog').innerHTML = rounds.map((_, i) => `<li class="${i < k ? grades[i] === 'half' ? 'half' : grades[i] : i === k ? 'now' : ''}"></li>`).join(''));
  const choices = (opts: [string, string][]) => `<div class="pu-answers">${opts.map(([id, t], i) => `<button class="btn btn-ghost pu-a" data-a="${id}"><span>${t}</span><kbd class="mono">${i + 1}</kbd></button>`).join('')}</div>`;

  const play = () => {
    const me = ++turn, r = rounds[k];
    done = false;
    stopPlay();
    q('.pu').hidden = false;
    q('.gm-end').hidden = true;
    prog();
    star = r.star;
    range.max = String(seasons[star].length - 1);
    q('.pu-kind').textContent = `Round ${k + 1} of ${rounds.length}`;
    q('.pu-name').textContent = NAME[star] + (r.type === 'period' ? `, ${BAND[r.band]}` : r.star === 'rwaur' ? `, ${BAND.long}` : '');
    q('.pu-fig').classList.toggle('pu-dim', r.star === 'rwaur');
    scale(r);
    q('.pu-sine').innerHTML = '';
    ask.hidden = false;
    reveal.hidden = true;
    const bins = binsOf(r);
    markExtra = '';
    let slider = '';
    if (r.type === 'compare') {
      q('.pu-pts-g').innerHTML = '';
      const A = seasons.rdra[r.a], B = seasons.rdra[r.b];
      markExtra = [[A, 'A'], [B, 'B']].map(([s, l]) => `<line class="pu-ab" x1="${X(isoToMjd((s as Season).iso))}" x2="${X(isoToMjd((s as Season).iso))}" y1="${Y0}" y2="${Y1}"/><text class="pu-ab-t" x="${X(isoToMjd((s as Season).iso))}" y="${Y0 + 14}">${l}</text>`).join('');
      ask.innerHTML = `<p class="gm-q">Was the star <b>brighter</b> in season A or season B?</p>
        <p class="gm-sub">A is ${day(A.iso)}. B is ${day(B.iso)}. Move the season slider or use the buttons to compare the two images.</p>
        <div class="gm-row"><button type="button" class="btn btn-ghost pu-go" data-i="${r.a}">Show A</button><button type="button" class="btn btn-ghost pu-go" data-i="${r.b}">Show B</button></div>
        ${choices([['a', 'A was brighter'], ['b', 'B was brighter']])}`;
      showSeason(r.a);
    } else if (r.type === 'period' || r.type === 'few') {
      drawPoints(bins);
      slider = `<div class="pu-per"><label for="pu-p">Your period guess <b class="mono pu-pv"></b></label>
        <input id="pu-p" class="pu-range pu-p" type="range" min="${P_MIN}" max="${P_MAX}" step="1" value="150"/>
        <p class="pu-fitq mono"></p></div>`;
      ask.innerHTML = r.type === 'period'
        ? `<p class="gm-q">How many days does <b>one pulse</b> take?</p>
           <p class="gm-sub">Each dot is our measurement from many SPHEREx exposures. Drag the period until the curve runs through the dots.</p>
           ${slider}<div class="gm-row"><button type="button" class="btn btn-primary pu-lock">Lock in</button></div>`
        : `<p class="gm-q">Can three SPHEREx passes find a <b>period</b> for RW Aurigae?</p>
           <p class="gm-sub">Try a few periods on these dots first.</p>${slider}
           ${choices([['yes', 'Yes, one period fits best'], ['no', 'No, many periods fit']])}`;
      const p = q<HTMLInputElement>('.pu-p');
      const upd = () => {
        q('.pu-sine').innerHTML = '';
        const f = drawSine(bins, +p.value);
        q('.pu-pv').textContent = `${p.value} days`;
        p.setAttribute('aria-valuetext', `${p.value} days`);
        q('.pu-fitq').textContent = `Typical miss from the dots ${f.rms.toFixed(2)} mag`;
      };
      p.oninput = upd;
      upd();
      if (r.type === 'period') q<HTMLButtonElement>('.pu-lock').onclick = () => answer(p.value);
      showSeason(0);
    } else {
      drawPoints(bins);
      ask.innerHTML = `<p class="gm-q">What did RW Aurigae do over the <b>three passes</b>?</p>
        <p class="gm-sub">Each dot compares exposures at the same wavelength. Up is brighter. The images barely change by eye, so read the dots.</p>
        ${choices([['fade', 'It faded each time'], ['brighten', 'It brightened each time'], ['none', 'No clear change']])}`;
      showSeason(0);
    }
    ask.querySelectorAll<HTMLButtonElement>('.pu-go').forEach((b) => (b.onclick = () => { stopPlay(); showSeason(+b.dataset.i!); }));
    ask.querySelector<HTMLElement>('.pu-a, .pu-p')?.focus({ preventScroll: true });

    answer = (a) => {
      if (done || me !== turn) return;
      done = true;
      stopPlay();
      let g: Grade = 'no', head = '', say = '', note = '';
      const fit = r.type === 'period' ? data.rdra[r.band === 'short' ? 'fit_short' : 'fit_long'] : null;
      if (r.type === 'compare') {
        g = a === r.truth ? 'ok' : 'no';
        drawPoints(binsOf(r));
        const diff = Math.abs(r.da - r.db);
        head = `${r.truth.toUpperCase()} was brighter, by about ${mag(diff)} in our measurements at ${BAND.short}.`;
        say = 'A Mira variable like R Draconis is a cool giant star that swells and shrinks. It is brightest when its outer layers are hottest, then fades for months.';
        note = 'R Draconis saturates almost every SPHEREx exposure, so we measured the glow around the saturated core instead.';
      } else if (r.type === 'period') {
        g = gradePeriod(+a, P_TRUE);
        q('.pu-sine').innerHTML = '';
        drawSine(binsOf(r), +a);
        drawSine(binsOf(r), P_TRUE, 'pu-s-true');
        head = `You chose ${a} days. The catalogue period is ${P_TRUE} days.`;
        say = r.band === 'short'
          ? `Our best sine through these dots has a period of ${fit!.best} days (${fit!.lo} to ${fit!.hi}). SPHEREx covered ${fit!.span_days} days, about two pulses, so it pins the period to a few percent but not to the day.`
          : `At longer wavelengths our best fit is ${fit!.best} days (${fit!.lo} to ${fit!.hi}), close to the catalogue value. The swing is smaller than in visible light, where R Draconis changes by about 6.5 magnitudes.`;
        note = 'A real Mira pulse is not a perfect sine, and our dots scatter more than their error bars, so treat the fit range as approximate.';
      } else if (r.type === 'trend') {
        g = a === r.truth ? 'ok' : 'no';
        const p = r.passes;
        markExtra = p.map((x) => `<circle class="pu-pass" cx="${X(x.mjd)}" cy="${Y(x.dmag)}" r="9"/>`).join('');
        marks(markExtra);
        head = r.truth === 'fade' ? `It faded each time, by ${mag(p[1].dmag - p[0].dmag)} and then ${mag(p[2].dmag - p[1].dmag)}.` : r.truth === 'brighten' ? 'It brightened each time.' : 'There was no clear change.';
        say = 'RW Aurigae is a young star still wrapped in gas and dust. Clumps of dust that pass in front of it dim the light, with no fixed rhythm.';
        note = `These numbers are indicative. RW Aurigae is saturated in most frames, and a separate fit by our team found larger fades (0.45 and 1.10 mag), so the size is uncertain but the direction agrees.`;
      } else {
        g = a === 'no' ? 'ok' : 'no';
        head = 'No. Many different periods run through so few dots.';
        say = 'Finding a period takes many visits spread over more than one cycle. R Draconis sits near the north ecliptic pole, where SPHEREx looks almost every week, so its pulse shows up.';
        note = 'Catalogues list RW Aurigae as an irregular young star, not a periodic one.';
      }
      const pts = points(g);
      grades[k] = g;
      score += pts;
      q('.pu-pts').textContent = String(score);
      prog();
      const last = k + 1 === rounds.length;
      ask.hidden = true;
      reveal.hidden = false;
      reveal.innerHTML = `
        <p class="gm-q">${g === 'ok' ? 'Right.' : g === 'half' ? 'Close.' : 'Not quite.'} <span class="pu-plus mono">+${pts}</span></p>
        <p class="pu-say"><b>${esc(head)}</b></p>
        <p class="pu-say">${esc(say)}</p>
        <p class="gm-sub">${esc(note)}</p>
        ${r.type === 'period' ? `<p class="pu-key mono"><span class="pu-k-g"></span>your period <span class="pu-k-t"></span>catalogue, AAVSO VSX</p>` : ''}
        <div class="gm-row"><button class="btn btn-primary pu-next">${last ? 'See my score' : 'Next'}${icon('arrow')}</button></div>`;
      if (g === 'ok') confetti(reveal.querySelector<HTMLElement>('.gm-q') ?? reveal);
      const btn = q<HTMLButtonElement>('.pu-next');
      btn.onclick = () => { if (last) end(); else { k++; play(); } };
      btn.focus({ preventScroll: true });
    };
  };

  const end = () => {
    turn++;
    stopPlay();
    q('.pu').hidden = true;
    const fin = q('.gm-end');
    fin.hidden = false;
    body.closest('.page')?.scrollTo(0, 0);
    const label = (r: Round) => r.type === 'compare' ? `R Draconis, brighter season` : r.type === 'period' ? `R Draconis period, ${BAND[r.band]}` : r.type === 'trend' ? 'RW Aurigae, three passes' : 'RW Aurigae, can we find a period?';
    fin.innerHTML = `
      <p class="kicker">Pulse reader</p>
      <h2 class="gm-end-h"><b class="mono">${score}</b> of ${max}</h2>
      <p class="gm-end-lead">R Draconis pulses every ${P_TRUE} days. From ${data.rdra.n_used} saturated SPHEREx exposures we measured ${data.rdra.fit_long.best} days at 2.4 to 5 µm and ${data.rdra.fit_short.best} days at 0.75 to 2.4 µm.</p>
      <ol class="gm-list">${rounds.map((r, i) => `<li><span>${label(r)}</span><span class="mono">+${points(grades[i])}</span></li>`).join('')}</ol>
      <p class="gm-sub pu-src">Where the data comes from: SPHEREx Level 2 images from NASA/IPAC IRSA (${data.rdra.n_stamps} stamps of R Draconis, ${data.rwaur.n_stamps} of RW Aurigae), brightness measured by our team. ${esc(data.method)} Catalogue period from AAVSO VSX.</p>
      <div class="gm-row"><button class="btn btn-primary gm-again">Play again</button><button class="btn btn-ghost" data-game="hub">All games</button></div>`;
    q<HTMLButtonElement>('.gm-again').onclick = start;
  };

  const start = () => {
    k = 0;
    score = 0;
    grades = [];
    q('.pu-pts').textContent = '0';
    play();
  };

  ask.addEventListener('click', (e) => {
    const b = (e.target as Element).closest<HTMLElement>('[data-a]');
    if (b) answer(b.dataset.a!);
  });
  const onKey = (e: KeyboardEvent) => {
    if (e.metaKey || e.ctrlKey || e.altKey || q('.pu').hidden || done || ask.hidden) return;
    const bs = ask.querySelectorAll<HTMLElement>('[data-a]');
    const n = +e.key;
    if (n >= 1 && n <= bs.length) answer(bs[n - 1].dataset.a!);
  };
  document.addEventListener('keydown', onKey);
  if (!rounds.length) {
    body.innerHTML = `<p class="muted">No rounds are available yet.</p>`;
    return;
  }
  start();
  return () => {
    turn++;
    stopPlay();
    document.removeEventListener('keydown', onKey);
  };
};
