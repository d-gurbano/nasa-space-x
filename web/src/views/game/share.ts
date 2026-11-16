// The share card: a 1200x630 picture with the stack the player tuned and their time.
// Shared as a file where the browser can (phones), else downloaded.

interface Card {
  stack: HTMLCanvasElement | null;
  time: string;
  stars: number;
  days: number;
  sample: boolean;
  yh5: boolean; // the last round the player tuned was the real 2025 YH5
}

export async function drawCard(c: Card): Promise<HTMLCanvasElement> {
  await document.fonts?.ready;
  const W = 1200, H = 630;
  const cv = Object.assign(document.createElement('canvas'), { width: W, height: H });
  const g = cv.getContext('2d')!;
  g.fillStyle = '#030407';
  g.fillRect(0, 0, W, H);
  // the stack, pixel-sharp, with a gold ring on the dot at its centre of light
  const S = 470, x0 = 80, y0 = 80;
  if (c.stack) {
    g.imageSmoothingEnabled = false;
    g.drawImage(c.stack, x0, y0, S, S);
  }
  g.strokeStyle = 'rgba(255,255,255,0.18)';
  g.lineWidth = 2;
  g.strokeRect(x0, y0, S, S);
  const gold = '#f2b544';
  g.fillStyle = gold;
  g.font = '500 18px "Geist Mono", monospace';
  g.fillText('TUNE THE REWIND', 630, 128);
  g.fillStyle = '#f3f1ec';
  g.font = '400 64px "Instrument Serif", serif';
  (c.yh5 ? ['I rewound 2025 YH5,', 'a hazardous asteroid'] : ['I tuned the Rewind', 'on SPHEREx photos']).forEach((l, i) => g.fillText(l, 630, 205 + i * 66));
  g.fillStyle = '#b7b9c0';
  g.font = '400 26px "Instrument Sans", sans-serif';
  (c.yh5 ? ['in NASA SPHEREx photos from', `${c.days} days before its first sighting.`] : ['the way Rewind recovered 2025 YH5,', `${c.days} days before its first sighting.`]).forEach((l, i) => g.fillText(l, 630, 330 + i * 36));
  g.fillStyle = '#f3f1ec';
  g.font = '400 56px "Instrument Serif", serif';
  g.fillText(c.time, 630, 472);
  for (let i = 0; i < 3; i++) {
    g.fillStyle = i < c.stars ? gold : 'rgba(255,255,255,0.16)';
    g.beginPath();
    g.arc(645 + i * 34, 510, 9, 0, Math.PI * 2);
    g.fill();
  }
  g.fillStyle = '#868a96';
  g.font = '400 18px "Geist Mono", monospace';
  g.fillText(c.sample ? 'REWIND / SAMPLE ROUNDS' : 'REWIND / NASA SPACE APPS 2026', 630, 552);
  return cv;
}

export async function shareCard(c: Card, btn: HTMLButtonElement): Promise<void> {
  const label = btn.textContent;
  const cv = await drawCard(c);
  const blob = await new Promise<Blob | null>((ok) => cv.toBlob(ok, 'image/png'));
  if (!blob) return;
  const file = new File([blob], 'rewind-card.png', { type: 'image/png' });
  const text = c.yh5 ? `I rewound 2025 YH5 in ${c.time}. Can you?` : `I tuned the Rewind: ${c.time}. Can you?`;
  try {
    if (navigator.canShare?.({ files: [file] })) {
      await navigator.share({ files: [file], text, url: location.href });
      return;
    }
  } catch {
    // cancelled or refused: fall back to a download
  }
  const a = Object.assign(document.createElement('a'), { href: URL.createObjectURL(blob), download: 'rewind-card.png' });
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 4000);
  btn.textContent = 'Card saved';
  setTimeout(() => (btn.textContent = label), 2000);
}
