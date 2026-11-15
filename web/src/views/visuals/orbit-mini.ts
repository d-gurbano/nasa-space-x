// A small top-down drawing of one orbit: the Sun, Earth's orbit, the object's orbit and both
// moving. One shared animation loop draws every canvas that is on screen; with reduced motion
// each canvas is drawn once, at its "pretend discovery" date.
import { basis, orbitPolyline, positionAt, type Elements } from '../../lib/kepler';

export interface OrbitMini {
  canvas: HTMLCanvasElement;
  el: Elements;
  /** The date the drawing starts at (and stays at with reduced motion). */
  mjd0: number;
  color: string;
}

const DAYS_PER_SEC = 90;
const TRAIL_DAYS = 160;
const VIEW_AU = 7; // the drawing never shows more than this far from the Sun
const LOOP_DAYS = 1400; // an orbit that leaves the drawing replays its pass by the Sun

type Path = { pts: [number, number][]; open: boolean };

// The whole ellipse, or for a long orbit (a comet from far out) only the arc near the Sun.
function pathOf(el: Elements): Path {
  if (el.e < 1 && el.a * (1 + el.e) <= VIEW_AU) return { pts: orbitPolyline(el, 160).map(([x, y]) => [x, y]), open: false };
  const p = Math.abs(el.a * (1 - el.e * el.e));
  const nuMax = Math.acos(Math.max(-1, Math.min(1, (p / (VIEW_AU * 1.6) - 1) / el.e)));
  const { P, Q } = basis(el.i, el.node, el.peri);
  const pts: [number, number][] = [];
  for (let k = -80; k <= 80; k++) {
    const nu = (k / 80) * nuMax;
    const r = p / (1 + el.e * Math.cos(nu));
    const x = r * Math.cos(nu), y = r * Math.sin(nu);
    pts.push([x * P[0] + y * Q[0], x * P[1] + y * Q[1]]);
  }
  return { pts, open: true };
}

// Earth on a circle, from its mean longitude: good enough for a picture
const earthXY = (mjd: number): [number, number] => {
  const L = ((100.46 + 0.9856474 * (mjd - 51544.5)) * Math.PI) / 180;
  return [Math.cos(L), Math.sin(L)];
};

function draw(o: OrbitMini, path: Path, mjd: number) {
  const c = o.canvas;
  const dpr = Math.min(2, window.devicePixelRatio || 1);
  const w = c.clientWidth, h = c.clientHeight;
  if (!w || !h) return;
  if (c.width !== Math.round(w * dpr)) {
    c.width = Math.round(w * dpr);
    c.height = Math.round(h * dpr);
  }
  const g = c.getContext('2d');
  if (!g) return;
  g.setTransform(dpr, 0, 0, dpr, 0, 0);
  g.clearRect(0, 0, w, h);
  const Q = path.open ? VIEW_AU : o.el.a * (1 + o.el.e);
  const s = (Math.min(w, h) / 2 - 10) / Math.max(Q, 1.1);
  const cx = w / 2, cy = h / 2;
  const P = (x: number, y: number): [number, number] => [cx + x * s, cy - y * s];

  // Earth's orbit, then the object's
  g.lineWidth = 1;
  g.strokeStyle = 'rgba(166, 210, 255, 0.28)';
  g.setLineDash([2, 3]);
  g.beginPath();
  g.arc(cx, cy, s, 0, Math.PI * 2);
  g.stroke();
  g.setLineDash([]);
  g.strokeStyle = 'rgba(255, 255, 255, 0.16)';
  g.beginPath();
  path.pts.forEach(([x, y], k) => (k ? g.lineTo(...P(x, y)) : g.moveTo(...P(x, y))));
  if (!path.open) g.closePath();
  g.stroke();

  // the Sun
  const sun = g.createRadialGradient(cx, cy, 0, cx, cy, 9);
  sun.addColorStop(0, 'rgba(255, 236, 190, 1)');
  sun.addColorStop(0.35, 'rgba(242, 181, 68, 0.55)');
  sun.addColorStop(1, 'rgba(242, 181, 68, 0)');
  g.fillStyle = sun;
  g.beginPath();
  g.arc(cx, cy, 9, 0, Math.PI * 2);
  g.fill();

  // a fading trail behind the object
  const steps = 24;
  for (let k = steps; k > 0; k--) {
    const a = positionAt(o.el, mjd - (TRAIL_DAYS * k) / steps);
    const b = positionAt(o.el, mjd - (TRAIL_DAYS * (k - 1)) / steps);
    g.strokeStyle = o.color;
    g.globalAlpha = 0.7 * (1 - k / steps);
    g.lineWidth = 1.6;
    g.beginPath();
    g.moveTo(...P(a[0], a[1]));
    g.lineTo(...P(b[0], b[1]));
    g.stroke();
  }
  g.globalAlpha = 1;

  // Earth
  const [ex, ey] = P(...earthXY(mjd));
  g.fillStyle = '#a6d2ff';
  g.beginPath();
  g.arc(ex, ey, 2.4, 0, Math.PI * 2);
  g.fill();

  // the object, with a soft glow
  const [x, y] = P(...(positionAt(o.el, mjd).slice(0, 2) as [number, number]));
  const glow = g.createRadialGradient(x, y, 0, x, y, 8);
  glow.addColorStop(0, o.color);
  glow.addColorStop(1, 'rgba(0, 0, 0, 0)');
  g.globalAlpha = 0.5;
  g.fillStyle = glow;
  g.beginPath();
  g.arc(x, y, 8, 0, Math.PI * 2);
  g.fill();
  g.globalAlpha = 1;
  g.fillStyle = o.color;
  g.beginPath();
  g.arc(x, y, 2.8, 0, Math.PI * 2);
  g.fill();
}

/** Start drawing. Returns a stop function. */
export function animateOrbits(items: OrbitMini[]): () => void {
  const paths = items.map((o) => pathOf(o.el));
  const still = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const visible = new Set<number>();
  let raf = 0;
  const t0 = performance.now();
  const frame = (now: number) => {
    const days = ((now - t0) / 1000) * DAYS_PER_SEC;
    visible.forEach((k) => draw(items[k], paths[k], items[k].mjd0 + (paths[k].open ? (days % LOOP_DAYS) - LOOP_DAYS / 4 : days)));
    raf = requestAnimationFrame(frame);
  };
  const io = new IntersectionObserver((es) => {
    for (const e of es) {
      const k = items.findIndex((o) => o.canvas === e.target);
      if (e.isIntersecting) visible.add(k);
      else visible.delete(k);
      if (still) draw(items[k], paths[k], items[k].mjd0);
    }
  });
  items.forEach((o) => io.observe(o.canvas));
  const onResize = () => items.forEach((o, k) => still && draw(o, paths[k], o.mjd0));
  addEventListener('resize', onResize);
  if (!still) raf = requestAnimationFrame(frame);
  return () => {
    cancelAnimationFrame(raf);
    io.disconnect();
    removeEventListener('resize', onResize);
  };
}
