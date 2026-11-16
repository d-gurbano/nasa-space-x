// Connect the dots: detections from three SPHEREx frame times in one patch of sky. Stars sit still,
// noise comes and goes, and a real asteroid moves in a straight line at a steady rate. Pick one dot
// per time that belong to one moving object, then check the line. This is the linking problem.
import '../../styles/game-dots.css';
import { icon } from '../../ui/components';
import { esc, provenance } from '../../ui/dom';
import type { View } from '../page';
import { confetti } from './confetti';
import { buildField, checkPick, rng, type Det, type DotsData } from './dots-logic';

const shapeSvg = (t: number, x: number, y: number, s: number) =>
  t === 0 ? `<circle cx="${x}" cy="${y}" r="${s}"/>`
    : t === 1 ? `<rect x="${x - s * 0.9}" y="${y - s * 0.9}" width="${s * 1.8}" height="${s * 1.8}"/>`
      : `<path d="M${x} ${y - s * 1.15}L${x + s * 1.05} ${y + s * 0.75}H${x - s * 1.05}Z"/>`;

export const view: View = async (body, ctx) => {
  const { data, sample } = await ctx.load<DotsData>('games/dots/rounds.json');
  if (!data.rounds?.length) {
    body.innerHTML = `<p class="muted">No rounds are available yet.</p>`;
    return;
  }
  const rounds = data.rounds, total = rounds.reduce((s, r) => s + r.movers.length, 0);
  let found: number[] = [], seed = Date.now() % 100000;

  body.innerHTML = `
    <div class="cd">
      <header class="gm-bar">
        <h2 class="gm-title">Connect the dots</h2>
        <ol class="gm-prog" aria-label="Rounds"></ol>
        <p class="gm-score"><span class="mono">Score</span><b class="mono cd-pts">0</b></p>
      </header>
      <p class="gm-sub cd-intro">Survey software sees dots, not asteroids. Pick three dots, one from each time, that are one object moving in a straight line at a steady rate.</p>
      <div class="gm-stage">
        <figure class="cd-field">
          <svg class="cd-svg" role="group" aria-label="Detections from three times"></svg>
          <p class="cd-scale mono"><i></i><span></span></p>
        </figure>
        <div class="gm-side">
          <ul class="cd-legend"></ul>
          <div class="cd-ask">
            <p class="gm-q cd-goal"></p>
            <p class="gm-sub cd-msg" aria-live="polite"></p>
            <div class="gm-row"><button class="btn btn-primary cd-check" disabled>Check the line</button><button class="btn btn-ghost cd-clear">Clear</button></div>
          </div>
          <div class="cd-reveal" hidden></div>
        </div>
      </div>
    </div>
    <div class="gm-end" hidden></div>`;
  const q = <T extends Element = HTMLElement>(s: string) => body.querySelector(s) as T;
  const svg = q<SVGSVGElement>('.cd-svg'), ask = q('.cd-ask'), reveal = q('.cd-reveal'), msg = q('.cd-msg');

  const play = (k: number) => {
    const r = rounds[k], dets: Det[] = buildField(r, k, rng(seed + k));
    const H = r.half_arcsec * 1.04, s = H * 0.022;
    const done = new Set<number>();
    let pick: (number | null)[] = [null, null, null], over = false;
    q('.cd').hidden = false;
    q('.gm-end').hidden = true;
    q('.gm-prog').innerHTML = rounds.map((_, i) => `<li class="${i < k ? (found[i] === rounds[i].movers.length ? 'ok' : found[i] ? 'half' : 'no') : i === k ? 'now' : ''}"></li>`).join('');
    svg.setAttribute('viewBox', `${-H} ${-H} ${2 * H} ${2 * H}`);
    // north up, east left, as on the sky
    const X = (x: number) => -x, Y = (y: number) => -y;
    svg.innerHTML = `<g class="cd-tracks"></g>` + dets.map((d) => d.kind === 'star'
      ? `<g class="cd-d cd-star" data-i="${d.id}" tabindex="0" role="button" aria-label="Fixed source"><circle cx="${X(d.x)}" cy="${Y(d.y)}" r="${s * 1.2}"/><circle class="cd-hit" cx="${X(d.x)}" cy="${Y(d.y)}" r="${s * 2.4}"/></g>`
      : `<g class="cd-d cd-t${d.t} cd-k-${d.kind}" data-i="${d.id}" tabindex="0" role="button" aria-pressed="false" aria-label="Time ${d.t + 1} detection">${shapeSvg(d.t, X(d.x), Y(d.y), s)}<circle class="cd-hit" cx="${X(d.x)}" cy="${Y(d.y)}" r="${s * 2.4}"/></g>`).join('');
    const bar = [10, 30, 60, 120, 300, 600].find((b) => b / (2 * H) > 0.12) ?? 600;
    q<HTMLElement>('.cd-scale i').style.width = `${(bar / (2 * H)) * 100}%`;
    q('.cd-scale span').textContent = bar >= 60 ? `${bar / 60} arcmin` : `${bar} arcsec`;
    const short = (iso: string) => iso.slice(5).replace('-', '/') + ' UT';
    q('.cd-legend').innerHTML = r.iso.map((t, i) => `<li><svg viewBox="-6 -6 12 12" class="cd-t${i}" aria-hidden="true">${shapeSvg(i, 0, 0, 4)}</svg>Time ${i + 1}, ${esc(short(t))}</li>`).join('') +
      `<li><svg viewBox="-6 -6 12 12" class="cd-star" aria-hidden="true"><circle r="4.5"/></svg>Fixed source (star or galaxy), same place each time</li><li class="cd-note">Some dots are simulated noise.</li>`;
    const need = r.movers.length;
    const goal = () => (q('.cd-goal').innerHTML = need === 1 ? 'Find the <b>moving object</b>.' : `Find <b>${need - done.size === 2 ? 'both' : 'the second'}</b> moving object${need - done.size === 2 ? 's' : ''}.`);
    goal();
    msg.textContent = `Round ${k + 1} of ${rounds.length}. ${dets.length} dots in a patch ${Math.round((2 * r.half_arcsec) / 60)} arcmin across.`;
    ask.hidden = false;
    reveal.hidden = true;

    const sync = () => {
      svg.querySelectorAll<SVGGElement>('.cd-d').forEach((g) => {
        const on = pick.includes(+g.dataset.i!);
        g.classList.toggle('on', on);
        if (!g.classList.contains('cd-star')) g.setAttribute('aria-pressed', String(on));
      });
      q<HTMLButtonElement>('.cd-check').disabled = pick.some((p) => p == null);
    };
    const line = (pts: [number, number][], cls: string) => `<polyline class="${cls}" points="${pts.map(([x, y]) => `${X(x)},${Y(y)}`).join(' ')}"/>`;
    const toggle = (i: number) => {
      if (over) return;
      const d = dets[i];
      if (d.kind === 'star') {
        msg.textContent = 'That source sits in the same place at all three times, so it is a star or galaxy, not a moving object.';
        return;
      }
      pick[d.t] = pick[d.t] === i ? null : i;
      msg.textContent = `${pick.filter((p) => p != null).length} of 3 picked. You need one dot from each time.`;
      sync();
    };
    const finish = (lastOk: boolean) => {
      over = true;
      found[k] = done.size;
      // show what every dot was
      q('.cd-tracks').innerHTML += r.movers.map((m, i) => (done.has(i) ? '' : line(m.pts, 'cd-true'))).join('');
      svg.classList.add('done');
      const last = k + 1 === rounds.length;
      const m = r.movers.map((x) => `${esc(x.name)} (predicted V ${x.v})`).join(' and ');
      ask.hidden = true;
      reveal.hidden = false;
      reveal.innerHTML = `
        <p class="gm-q">${done.size === need ? 'Linked.' : done.size ? 'One of two.' : 'Not linked.'} <span class="cd-plus mono">+${done.size * 10}</span></p>
        <p class="cd-say">${need > 1 ? 'These were' : 'This was'} ${m}. ${k === 0 ? 'A real object keeps a steady speed and direction, so its three dots fall on one line with spacing that matches the times.' : k < 3 ? 'With more dots, many triples line up by chance. Survey software tests every pair and keeps only lines that a third dot confirms.' : 'Slow movers barely shift between times, so stars and noise crowd their path. This is the linking problem, and it grows fast with the number of dots.'}</p>
        <p class="gm-sub">Faded dots were simulated noise. Hollow dots were other known asteroids seen at only one or two of these times.</p>
        <div class="gm-row"><button class="btn btn-primary cd-next">${last ? 'See my score' : 'Next round'}${icon('arrow')}</button></div>`;
      if (lastOk) confetti(q('.cd-reveal .gm-q'));
      const btn = q<HTMLButtonElement>('.cd-next');
      btn.onclick = () => (last ? end() : play(k + 1));
      btn.focus({ preventScroll: true });
      q('.cd-pts').textContent = String(found.reduce((a, x) => a + x, 0) * 10);
    };
    svg.onclick = (e) => {
      const g = (e.target as Element).closest<SVGGElement>('.cd-d');
      if (g) toggle(+g.dataset.i!);
    };
    svg.onkeydown = (e) => {
      const g = (e.target as Element).closest<SVGGElement>('.cd-d');
      if (g && (e.key === 'Enter' || e.key === ' ')) {
        e.preventDefault();
        toggle(+g.dataset.i!);
      }
    };
    q<HTMLButtonElement>('.cd-clear').onclick = () => {
      pick = [null, null, null];
      sync();
      msg.textContent = 'Cleared.';
    };
    q<HTMLButtonElement>('.cd-check').onclick = () => {
      if (over || pick.some((p) => p == null)) return;
      const c = checkPick(dets, pick as number[], r.mjd);
      const chosen = (pick as number[]).map((i) => dets[i]).sort((a, b) => a.t - b.t).map((d) => [d.x, d.y] as [number, number]);
      if (c.ok && !done.has(c.track)) {
        done.add(c.track);
        q('.cd-tracks').innerHTML += line(chosen, 'cd-ok');
        q('.cd-pts').textContent = String((found.reduce((a, x) => a + x, 0) + done.size) * 10);
        pick = [null, null, null];
        sync();
        if (done.size === need) return finish(true);
        confetti(q('.cd-goal'));
        msg.textContent = `Right, that is ${r.movers[c.track].name}. One more is moving in this patch.`;
        goal();
        return;
      }
      q('.cd-tracks').innerHTML += line(chosen, 'cd-bad');
      msg.textContent = c.ok ? 'You already linked that one.' : c.why === 'line'
        ? `Those three are not on a steady straight line. The middle dot is ${Math.round((c.off ?? 0) * 100)}% of the track length away from where steady motion puts it.`
        : 'Those three line up, but by chance. They are not one real object.';
      if (!c.ok) finish(false);
    };
  };

  const end = () => {
    const sum = found.reduce((a, x) => a + x, 0);
    q('.cd').hidden = true;
    const fin = q('.gm-end');
    fin.hidden = false;
    body.closest('.page')?.scrollTo(0, 0);
    fin.innerHTML = `
      <p class="kicker">Connect the dots</p>
      <h2 class="gm-end-h"><b class="mono">${sum * 10}</b> of ${total * 10}</h2>
      <p class="gm-end-lead">You linked ${sum} of ${total} moving objects. Surveys link millions of detections this way every night. Rewind turns the problem around: it starts from a known orbit and goes back to look where the object must have been.</p>
      <ol class="gm-list">${rounds.map((r, i) => `<li><span>${esc(r.movers.map((m) => m.name).join(', '))}</span><span class="gm-list-n">${r.field === 'NEP' ? 'north ecliptic pole' : 'ecliptic field'}</span><span class="mono">${found[i] ?? 0} of ${r.movers.length}</span></li>`).join('')}</ol>
      <div class="gm-row"><button class="btn btn-primary gm-again">Play again</button><button class="btn btn-ghost" data-game="hub">All games</button></div>
      <div class="tr-foot">${provenance(sample, 'Real SPHEREx frames and answer key')}<p class="gm-sub">Where the data comes from: asteroid positions are from our answer key of known objects in real SPHEREx frames (JPL orbits at each frame time). Stars are the brightest fixed sources we measured in the middle frame of each round, from the public SPHEREx images on AWS. Noise dots are simulated.</p></div>`;
    q<HTMLButtonElement>('.gm-again').onclick = () => {
      found = [];
      seed++;
      q('.cd-pts').textContent = '0';
      play(0);
    };
    q<HTMLButtonElement>('.gm-again').focus({ preventScroll: true });
  };
  play(0);
};
