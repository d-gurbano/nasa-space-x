// Hub preview for Real or junk?: a ring over a small patch of sky; a satellite trail, a cosmic-ray
// splash and a round dot take turns inside it. Drawn with SMIL, so it needs no game CSS on the hub.
const stars = [[24, 26], [160, 20], [42, 94], [176, 92], [132, 108], [70, 16], [150, 58]].map(([x, y]) => `<circle class="pv-star" cx="${x}" cy="${y}" r="1.4"/>`).join('');
const turn = (i: number) => `<animate attributeName="opacity" dur="6s" repeatCount="indefinite" values="0;${[0, 1, 2].map((k) => (k === i ? '1;1' : '0;0')).join(';')};0" keyTimes="0;0.05;0.3;0.38;0.63;0.71;0.96;1"/>`;
export const preview = `<svg viewBox="0 0 200 120" aria-hidden="true">${stars}
  <g opacity="0">${turn(0)}<line x1="70" y1="96" x2="132" y2="24" stroke="#aab2c2" stroke-width="2" stroke-linecap="round"/></g>
  <g opacity="0">${turn(1)}<rect x="98" y="58" width="4" height="4" fill="#fff"/><rect x="102" y="62" width="3" height="3" fill="#cfd5e0"/></g>
  <g opacity="0">${turn(2)}<circle cx="100" cy="60" r="4.5" fill="#ffd98a"/></g>
  <circle cx="100" cy="60" r="22" fill="none" stroke="#f2b544" stroke-width="1.5" stroke-dasharray="3 3"/></svg>`;
