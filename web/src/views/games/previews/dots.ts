// Hub preview for Connect the dots: stars and three-time dots; the moving object's line draws in.
const stars = [[24, 26], [160, 20], [92, 98], [176, 92], [40, 84], [130, 40]].map(([x, y]) => `<circle class="pv-star" cx="${x}" cy="${y}" r="1.6"/>`).join('');
export const preview = `<svg viewBox="0 0 200 120" aria-hidden="true">${stars}
  <circle class="pv-k" cx="58" cy="44" r="3"/><circle class="pv-k" cx="150" cy="64" r="3"/>
  <rect x="96" y="52" width="6" height="6" fill="#f2b544"/><rect x="34" y="104" width="6" height="6" fill="#f2b544"/>
  <path d="M138 92l4 7h-8z" fill="#e98ab5"/><path d="M70 22l4 7h-8z" fill="#e98ab5"/>
  <path class="pv-spec" d="M58 44L99 55L138 66"/><path d="M138 64l4 7h-8z" fill="#e98ab5"/>
  <circle class="pv-lock" cx="99" cy="55" r="16"/></svg>`;
