// Planetary defense desk: a newly found asteroid comes with a large position uncertainty. Choose what
// to do first (search older images, ask for more telescope nights, or wait) and see the uncertainty
// drawn to scale against Earth and the Moon's orbit. Only the precovery numbers are ours (COMPUTED).
import '../../styles/game-defense.css';
import { getJson } from '../../lib/data';
import { icon } from '../../ui/components';
import { esc } from '../../ui/dom';
import type { View } from '../page';
import { confetti } from './confetti';
import { APOPHIS, best, EARTH_KM, fmtKm, MOON_KM, precoveryRound, score, type Action, type DefRound, type Impact } from './defense-logic';

interface Page { name: string; story?: { discovered_iso?: string }; facts?: { sentry?: boolean }; impact?: Impact }

const ACTIONS: { id: Action; name: string; tell: string; key: string }[] = [
  { id: 'archive', name: 'Search older archive images', tell: 'Look for the object in images taken before it was found.', key: '1' },
  { id: 'nights', name: 'Ask for more telescope nights', tell: 'Observe it again over the coming nights.', key: '2' },
  { id: 'wait', name: 'Wait and see', tell: 'Do nothing new for now.', key: '3' },
];

export const view: View = async (body, ctx) => {
  const idx = ctx.source.index.objects;
  const load = async (slug: string) => {
    const o = idx.find((x) => x.slug === slug);
    if (!o) return null;
    const p = await getJson<Page>(ctx.source.base + o.page).catch(() => null);
    return p ? precoveryRound(p.name, slug, p.story?.discovered_iso ?? o.discovered?.iso ?? '', p.impact, p.facts?.sentry ?? null) : null;
  };
  const [st20, yh5] = await Promise.all([load('2025st20'), load('2025yh5')]);
  const empty = (o: (typeof idx)[number] | undefined): DefRound | null =>
    o ? { kind: 'empty', name: o.name, slug: o.slug, discovered: o.discovered?.iso ?? '', n_frames: o.n_frames ?? 0, best_snr: o.best_snr ?? null } : null;
  const faint = empty(idx.find((o) => o.kind === 'neo' && o.verdict === 'TOO_FAINT' && (o.n_frames ?? 0) >= 100));
  const none = empty(idx.find((o) => o.kind === 'neo' && o.verdict === 'NO_PHOTOS'));
  const rounds = [st20, faint, yh5, none, APOPHIS].filter((r): r is DefRound => !!r);
  let pts: number[] = [];

  body.innerHTML = `
    <div class="pd">
      <header class="gm-bar">
        <h2 class="gm-title">Planetary defense desk</h2>
        <ol class="gm-prog" aria-label="Rounds"></ol>
        <p class="gm-score"><span class="mono">Score</span><b class="mono pd-pts">0</b></p>
      </header>
      <p class="gm-sub pd-intro">A newly found near-Earth asteroid has a short orbit arc, so we do not yet know well where it will be. Choose the action that shrinks the uncertainty most, first.</p>
      <div class="gm-stage">
        <figure class="pd-map">
          <p class="pd-who"><span class="mono pd-n"></span><b class="pd-name"></b></p>
          <svg class="pd-svg" viewBox="-110 -80 220 160" role="img"></svg>
          <figcaption class="pd-cap"></figcaption>
        </figure>
        <div class="gm-side">
          <div class="pd-ask">
            <p class="pd-brief"></p>
            <p class="gm-q">What do you do <b>first</b>?</p>
            <div class="pd-acts">${ACTIONS.map((a) => `<button class="pd-a" data-a="${a.id}"><span><b>${a.name}</b><small>${a.tell}</small></span><kbd class="mono">${a.key}</kbd></button>`).join('')}</div>
          </div>
          <div class="pd-reveal" hidden></div>
        </div>
      </div>
    </div>
    <div class="gm-end" hidden></div>`;
  const q = <T extends Element = HTMLElement>(s: string) => body.querySelector(s) as T;
  const svg = q<SVGSVGElement>('.pd-svg'), ask = q('.pd-ask'), reveal = q('.pd-reveal');
  let choose: (a: Action) => void = () => {}, done = false;

  /** The uncertainty to scale. A circle of the 3σ size, with Earth and the Moon's orbit at the centre for scale. */
  const drawCloud = (r: Extract<DefRound, { kind: 'precovery' }>, after: boolean) => {
    const u = 70 / r.before_km, moon = MOON_KM * u, earth = Math.max(0.9, EARTH_KM * u);
    svg.setAttribute('aria-label', `Uncertainty ${fmtKm(r.before_km)}${after ? ` shrinking to ${fmtKm(r.after_km)}` : ''}, with the Moon's orbit for scale`);
    svg.innerHTML = `
      <circle class="pd-before" r="70"/><text class="pd-lab" y="-74">${esc(fmtKm(r.before_km))} at discovery</text>
      ${after ? `<circle class="pd-after" r="${(r.after_km * u).toFixed(2)}"/><text class="pd-lab pd-lab-after" y="${(-r.after_km * u - 4).toFixed(1)}">${esc(fmtKm(r.after_km))} with SPHEREx</text>` : ''}
      <circle class="pd-moon" r="${moon.toFixed(2)}"/><circle class="pd-earth" r="${earth.toFixed(2)}"/>
      <text class="pd-lab pd-lab-s" x="${(moon + 3).toFixed(1)}" y="${(moon + 8).toFixed(1)}" text-anchor="start">Earth and the Moon’s orbit, for scale</text>`;
    q('.pd-cap').textContent = `The circle shows the 3σ size of the region where it could be on ${r.at_iso}, one year after discovery. The real region is a long thin ellipse along the orbit. The asteroid is not near Earth then.`;
  };
  /** Apophis in 2029: the range of possible miss distances from Earth's centre. */
  const drawApophis = (r: Extract<DefRound, { kind: 'apophis' }>, after: boolean) => {
    const u = 200 / 170000, X = (km: number) => -110 + (km + 60000) * u;
    const band = (km: number, cls: string, h: number) => `<rect class="${cls}" x="${X(r.miss_km - km).toFixed(1)}" y="${-h / 2}" width="${(2 * km * u).toFixed(1)}" height="${h}" rx="2"/>`;
    svg.setAttribute('aria-label', `Apophis 2029 miss distance ${fmtKm(r.miss_km)}, plus or minus ${fmtKm(r.before_km)}${after ? `, then plus or minus ${fmtKm(r.after_km)}` : ''}`);
    svg.innerHTML = `
      ${band(r.before_km, 'pd-before', 36)}<text class="pd-lab" x="${X(r.miss_km)}" y="-24">±${esc(fmtKm(r.before_km))}</text>
      ${after ? `${band(r.after_km, 'pd-after', 22)}<text class="pd-lab pd-lab-after" x="${X(r.miss_km)}" y="32">±${esc(fmtKm(r.after_km))}</text>` : ''}
      <circle class="pd-earth" cx="${X(0)}" r="${(EARTH_KM * u).toFixed(2)}"/><text class="pd-lab pd-lab-s" x="${X(0)}" y="18">Earth</text>
      <line class="pd-axis" x1="${X(0)}" x2="105" y1="50" y2="50"/><text class="pd-lab pd-lab-s" x="${X(r.miss_km)}" y="62">${esc(fmtKm(r.miss_km))} from Earth’s centre (2004 data)</text>
      <text class="pd-lab pd-lab-s" x="104" y="-60" text-anchor="end">Moon’s orbit is ${esc(fmtKm(MOON_KM))} out, off this view</text>`;
    q('.pd-cap').textContent = 'Earth is drawn to scale. The bands show the range of possible miss distances on 13 April 2029, from the 2004 observations alone.';
  };
  const draw = (r: DefRound, after: boolean) => {
    q('.pd-map').classList.toggle('blank', r.kind === 'empty');
    if (r.kind === 'precovery') drawCloud(r, after);
    else if (r.kind === 'apophis') drawApophis(r, after);
    else {
      svg.setAttribute('aria-label', 'No computed uncertainty for this object');
      svg.innerHTML = `<text class="pd-lab" y="-4">No computed uncertainty for this object</text><text class="pd-lab pd-lab-s" y="12">in our data.</text>`;
      q('.pd-cap').textContent = '';
    }
  };

  const brief = (r: DefRound) => {
    if (r.kind === 'precovery') return `${esc(r.name)} was discovered on ${esc(r.discovered)}. After its first ${r.first_days} days there were ${r.n_obs} observations. SPHEREx imaged its path in the ${r.days} days before discovery.`;
    if (r.kind === 'apophis') return 'It is 2004. Apophis was found in June, and its 2029 close approach is still uncertain. Older survey images from March 2004 exist.';
    return r.n_frames
      ? `${esc(r.name)} was discovered on ${esc(r.discovered)}. SPHEREx imaged its path ${r.n_frames} times before discovery. We stacked those images and found nothing above the noise (best S/N ${r.best_snr?.toFixed(1) ?? 'none'}).`
      : `${esc(r.name)} was discovered on ${esc(r.discovered)}. SPHEREx did not image its path in the days before discovery.`;
  };
  const why = (r: DefRound, a: Action) => {
    const nights = 'More telescope nights help, but slowly. Each night adds a little to the arc, and the orbit firms up over weeks.';
    const wait = 'Waiting adds no new data. The object moves and fades, and every lost night makes follow-up harder.';
    if (r.kind === 'empty') {
      if (a === 'archive') return r.n_frames ? 'We already searched the SPHEREx images and the object was too faint in them, so the archive adds no positions here. More telescope nights are the way forward.' : 'There are no SPHEREx images of its path to search, so the archive adds nothing here. More telescope nights are the way forward.';
      return a === 'nights' ? `Right choice. ${nights} With no usable archive images, new observations are what helps.` : `${wait} With no usable archive images, more telescope nights help most.`;
    }
    const gain = r.kind === 'precovery'
      ? `Our ${r.positions === 1 ? 'one SPHEREx position' : `${r.positions} SPHEREx positions`} from up to ${r.days} days before discovery stretch the arc back at once. The one-year uncertainty falls from ${fmtKm(r.before_km)} to ${fmtKm(r.after_km)}, about ${r.factor} times smaller.`
      : `The real 15 March 2004 precovery stretched the arc back three months. The 2029 miss-distance uncertainty fell from about ±${fmtKm(r.before_km)} to about ±${fmtKm(r.after_km)}, about 25 times smaller.`;
    return a === 'archive' ? gain : `${a === 'nights' ? nights : wait} Searching older images would have helped more first. ${gain}`;
  };

  const play = (k: number) => {
    const r = rounds[k];
    done = false;
    q('.pd').hidden = false;
    q('.gm-end').hidden = true;
    q('.gm-prog').innerHTML = rounds.map((_, i) => `<li class="${i < k ? (pts[i] ? 'ok' : 'no') : i === k ? 'now' : ''}"></li>`).join('');
    q('.pd-n').textContent = `Case ${k + 1} of ${rounds.length}`;
    q('.pd-name').textContent = r.name;
    q('.pd-brief').innerHTML = brief(r);
    draw(r, false);
    ask.hidden = false;
    reveal.hidden = true;
    q<HTMLButtonElement>('.pd-a').focus({ preventScroll: true });
    choose = (a) => {
      if (done) return;
      done = true;
      pts[k] = score(r, a);
      q('.pd-pts').textContent = String(pts.reduce((s, x) => s + x, 0));
      draw(r, r.kind !== 'empty');
      const last = k + 1 === rounds.length;
      const ok = a === best(r);
      ask.hidden = true;
      reveal.hidden = false;
      reveal.innerHTML = `
        <p class="pd-label mono">${r.kind === 'empty' ? 'From our search' : 'COMPUTED scenario'}</p>
        <p class="gm-q">${ok ? 'Good call.' : 'Not the best first step.'} <span class="pd-plus mono">+${pts[k]}</span></p>
        <p class="pd-say">${esc(why(r, a))}</p>
        <div class="gm-row"><button class="btn btn-primary pd-next">${last ? 'See my score' : 'Next case'}${icon('arrow')}</button>${'slug' in r ? `<a class="btn btn-ghost" href="#/object/${esc(r.slug)}">Open ${esc(r.name)}</a>` : ''}</div>`;
      if (ok) confetti(q('.pd-reveal .gm-q'));
      const btn = q<HTMLButtonElement>('.pd-next');
      btn.onclick = () => (last ? end() : play(k + 1));
      btn.focus({ preventScroll: true });
    };
  };

  const end = () => {
    done = true;
    const sum = pts.reduce((s, x) => s + x, 0);
    q('.pd').hidden = true;
    const fin = q('.gm-end');
    fin.hidden = false;
    body.closest('.page')?.scrollTo(0, 0);
    const notSentry = rounds.filter((r) => r.kind === 'precovery' && r.sentry === false).map((r) => r.name);
    fin.innerHTML = `
      <p class="kicker">Planetary defense desk</p>
      <h2 class="gm-end-h"><b class="mono">${sum}</b> of ${rounds.length * 10}</h2>
      <p class="gm-end-lead">When older images hold the object, searching them first stretches the orbit arc back at once. That shrinks the uncertainty more than new nights can in the same time.</p>
      <ol class="gm-list">${rounds.map((r, i) => `<li><span>${esc(r.name)}</span><span class="gm-list-n">${r.kind === 'empty' ? 'no archive positions' : `${fmtKm(r.before_km)} to ${fmtKm(r.after_km)}`}</span><span class="mono">+${pts[i] ?? 0}</span></li>`).join('')}</ol>
      <p class="gm-sub pd-safe">These are computed scenarios, not forecasts. None of these objects is predicted to hit Earth.${notSentry.length ? ` ${esc(notSentry.join(' and '))} ${notSentry.length > 1 ? 'are' : 'is'} not on JPL’s Sentry list of possible impactors.` : ''} Apophis will pass about ${fmtKm(APOPHIS.kind === 'apophis' ? APOPHIS.today_km : 0)} from Earth’s centre in April 2029 (JPL).</p>
      <div class="gm-row"><button class="btn btn-primary gm-again">Play again</button><button class="btn btn-ghost" data-game="hub">All games</button></div>
      <p class="gm-sub">Where the data comes from: our orbit fits with and without our SPHEREx positions (the at-discovery scenario in each object’s object.json), and our Apophis test with its 2004 observations and the 15 March 2004 precovery. Telescope nights and waiting are described, not computed.</p>`;
    q<HTMLButtonElement>('.gm-again').onclick = start;
    q<HTMLButtonElement>('.gm-again').focus({ preventScroll: true });
  };

  const start = () => {
    pts = [];
    q('.pd-pts').textContent = '0';
    play(0);
  };
  q('.pd-acts').addEventListener('click', (e) => {
    const b = (e.target as Element).closest<HTMLElement>('[data-a]');
    if (b) choose(b.dataset.a as Action);
  });
  const onKey = (e: KeyboardEvent) => {
    if (e.metaKey || e.ctrlKey || e.altKey || q('.pd').hidden || done) return;
    const a = ACTIONS.find((x) => x.key === e.key);
    if (a) choose(a.id);
  };
  document.addEventListener('keydown', onKey);
  start();
  return () => document.removeEventListener('keydown', onKey);
};
