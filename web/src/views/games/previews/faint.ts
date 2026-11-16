// Hub preview for Too faint?: noisy frames stack up and a faint dot appears.
const noise = Array.from({ length: 40 }, (_, i) => `<circle class="pv-star" cx="${(i * 37) % 180 + 10}" cy="${(i * 53) % 100 + 10}" r="${0.6 + ((i * 7) % 5) / 5}" opacity="0.5"/>`).join('');
export const preview = `<svg viewBox="0 0 200 120" aria-hidden="true">${noise}
  <g class="pv-bar">${[0, 1, 2, 3].map((i) => `<rect x="${150 + i * 4}" y="${20 + i * 4}" width="34" height="24" rx="2" fill="none" stroke="#8f97a8" style="--i:${i * 4}"/>`).join('')}</g>
  <circle class="pv-pop" cx="96" cy="60" r="5"/><circle class="pv-lock" cx="96" cy="60" r="15"/></svg>`;
