// A small, short confetti burst over an element when a round is solved. Skipped for reduced motion.
import { reducedMotion } from '../../state';

export function confetti(anchor: HTMLElement): void {
  if (reducedMotion || !anchor.isConnected) return;
  const r = anchor.getBoundingClientRect(), pad = 90, dpr = Math.min(2, devicePixelRatio || 1);
  const w = r.width + pad * 2, h = r.height + pad * 2;
  const c = document.createElement('canvas');
  c.width = w * dpr;
  c.height = h * dpr;
  c.setAttribute('aria-hidden', 'true');
  Object.assign(c.style, { position: 'fixed', left: `${r.left - pad}px`, top: `${r.top - pad}px`, width: `${w}px`, height: `${h}px`, pointerEvents: 'none', zIndex: '50' });
  document.body.append(c);
  const g = c.getContext('2d')!;
  g.scale(dpr, dpr);
  const css = getComputedStyle(document.documentElement);
  const cols = ['--gold', '--gold-2', '--blue-2', '--ink'].map((v) => css.getPropertyValue(v).trim() || '#f2b544');
  const ps = Array.from({ length: 48 }, (_, i) => {
    const a = -Math.PI / 2 + (Math.random() - 0.5) * 2.2, v = 2 + Math.random() * 2.5;
    return { x: w / 2 + (Math.random() - 0.5) * r.width * 0.6, y: pad + r.height * 0.4, vx: Math.cos(a) * v, vy: Math.sin(a) * v, s: 2 + Math.random() * 2.5, rot: Math.random() * 6, vr: (Math.random() - 0.5) * 0.3, col: cols[i % cols.length] };
  });
  const t0 = performance.now(), T = 1200;
  const frame = (t: number) => {
    const e = (t - t0) / T;
    if (e >= 1 || !anchor.isConnected) return c.remove();
    g.clearRect(0, 0, w, h);
    g.globalAlpha = 1 - e * e;
    for (const p of ps) {
      p.vy += 0.12;
      p.vx *= 0.985;
      p.x += p.vx;
      p.y += p.vy;
      p.rot += p.vr;
      g.save();
      g.translate(p.x, p.y);
      g.rotate(p.rot);
      g.fillStyle = p.col;
      g.fillRect(-p.s / 2, -p.s / 4, p.s, p.s / 2);
      g.restore();
    }
    requestAnimationFrame(frame);
  };
  requestAnimationFrame(frame);
}
