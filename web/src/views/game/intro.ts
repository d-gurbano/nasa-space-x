// The 3-second "how it works" film, drawn on a 2D canvas: six photos fan out (the dot is too
// faint in each), slide back along the dot's path so the dots line up, and add up into one bright dot.
import { rng } from './stack';

const N = 6;
const PX = 36; // native pixels per photo in the film
const STEP: [number, number] = [3.2, -1.6]; // the dot's motion per photo, in native pixels

function gauss(r: () => number): number {
  return Math.sqrt(-2 * Math.log(r() || 1e-12)) * Math.cos(2 * Math.PI * r());
}

/** One photo (or the stack of all, when `stacked`) as a tiny canvas. */
function photo(i: number, stacked: boolean): HTMLCanvasElement {
  const c = Object.assign(document.createElement('canvas'), { width: PX, height: PX });
  const g = c.getContext('2d')!;
  const img = g.createImageData(PX, PX);
  const r = rng(11 + (stacked ? 99 : i));
  const at = (k: number) => [PX / 2 + STEP[0] * (k - (N - 1) / 2), PX / 2 + STEP[1] * (k - (N - 1) / 2)];
  for (let y = 0; y < PX; y++)
    for (let x = 0; x < PX; x++) {
      const dot = (k: number) => {
        const [dx, dy] = stacked ? [PX / 2, PX / 2] : at(k);
        return Math.exp(-((x + 0.5 - dx) ** 2 + (y + 0.5 - dy) ** 2) / 1.4);
      };
      // a single photo: noise of 1 and a dot of 1.3; the stack of six: noise of 1/sqrt(6) and the same dot
      const v = stacked ? gauss(r) / Math.sqrt(N) + 1.6 * dot(0) : gauss(r) + 1.6 * dot(i);
      const s = Math.max(0, Math.min(255, 46 + v * (stacked ? 64 : 34)));
      const k = (y * PX + x) * 4;
      img.data[k] = s * 0.92;
      img.data[k + 1] = s * 0.96;
      img.data[k + 2] = Math.min(255, s * 1.05 + 6);
      img.data[k + 3] = 255;
    }
  g.putImageData(img, 0, 0);
  return c;
}

const ease = (t: number) => (t <= 0 ? 0 : t >= 1 ? 1 : 1 - Math.pow(1 - t, 3));
const clamp = (t: number) => Math.max(0, Math.min(1, t));

export const INTRO_LINES = ['Here are six images. The asteroid is too faint to see in any of them.', 'Shift each image back along the asteroid’s path.', 'Added together, the six faint dots make one clear dot.'];

/**
 * Play the film into `canvas`; `caption(i)` is told which line to show. Resolves when it ends or
 * when `stop()` is called. With reduced motion it shows only the last picture.
 */
export function playIntro(canvas: HTMLCanvasElement, caption: (i: number) => void, still: boolean): { done: Promise<void>; stop(): void } {
  const g = canvas.getContext('2d')!;
  const photos = Array.from({ length: N }, (_, i) => photo(i, false));
  const sum = photo(0, true);
  let raf = 0, stopped = false, line = -1;
  let finish: () => void = () => {};
  const done = new Promise<void>((ok) => (finish = ok));

  const frame = (ms: number) => {
    const dpr = Math.min(2, window.devicePixelRatio || 1);
    const W = canvas.clientWidth, H = canvas.clientHeight;
    if (canvas.width !== Math.round(W * dpr)) (canvas.width = Math.round(W * dpr)), (canvas.height = Math.round(H * dpr));
    g.setTransform(dpr, 0, 0, dpr, 0, 0);
    g.clearRect(0, 0, W, H);
    g.imageSmoothingEnabled = false;
    const S = Math.min(H * 0.5, W * 0.4, 260); // photo size on screen
    const u = S / PX;
    const cx = W / 2, cy = H / 2;
    const fan = ease(ms / 900) * (1 - ease((ms - 1000) / 800)); // 0 pile, 1 spread
    const align = ease((ms - 1000) / 800); // slide back along the path
    const add = ease((ms - 2000) / 600); // fade into the stack
    const want = ms < 1000 ? 0 : ms < 2000 ? 1 : 2;
    if (want !== line) caption((line = want));

    for (let i = 0; i < N; i++) {
      const k = i - (N - 1) / 2;
      const x = cx + k * S * 0.5 * fan - k * STEP[0] * u * align;
      const y = cy + k * S * 0.08 * fan - k * STEP[1] * u * align;
      g.globalAlpha = (1 - add) * (align > 0 ? 1 / (1 + align * 1.4) : 1);
      g.drawImage(photos[i], x - S / 2, y - S / 2, S, S);
      g.strokeStyle = 'rgba(255,255,255,0.22)';
      g.lineWidth = 1;
      g.strokeRect(x - S / 2 + 0.5, y - S / 2 + 0.5, S - 1, S - 1);
    }
    if (add > 0) {
      g.globalAlpha = add;
      g.drawImage(sum, cx - S / 2, cy - S / 2, S, S);
      g.strokeStyle = 'rgba(242,181,68,0.5)';
      g.strokeRect(cx - S / 2 + 0.5, cy - S / 2 + 0.5, S - 1, S - 1);
      // a gold ring that closes in on the dot
      const ring = clamp((ms - 2300) / 500);
      if (ring > 0) {
        g.globalAlpha = 1 - ring * 0.3;
        g.strokeStyle = '#f2b544';
        g.lineWidth = 2;
        g.beginPath();
        g.arc(cx, cy, S * (0.32 - 0.18 * ease(ring)), 0, Math.PI * 2);
        g.stroke();
      }
    }
    g.globalAlpha = 1;
    if (stopped) return;
    if (ms < 3400) raf = requestAnimationFrame((t) => frame(t - start));
    else if (!still) finish();
  };
  const start = performance.now();
  if (still) {
    requestAnimationFrame(() => frame(3400));
    setTimeout(finish, 2600);
  } else raf = requestAnimationFrame((t) => frame(t - start));
  return {
    done,
    stop() {
      stopped = true;
      cancelAnimationFrame(raf);
      finish();
    },
  };
}
