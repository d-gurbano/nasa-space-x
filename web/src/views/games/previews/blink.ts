// Hub preview for Blink!: the stars stay put while one dot jumps back and forth, then a ring finds it.
// Animated with SVG <animate>, since the game's own stylesheet is not loaded on the hub.
const stars = [[22, 30], [150, 22], [96, 64], [40, 96], [170, 88], [128, 108], [70, 18], [58, 58], [182, 50]]
  .map(([x, y]) => `<circle class="pv-star" cx="${x}" cy="${y}" r="1.6"/>`).join('');

export const preview = `<svg viewBox="0 0 200 120" aria-hidden="true">${stars}
  <circle cx="118" cy="42" r="2.6" fill="#ffd98a"><animate attributeName="cx" values="118;132;118" keyTimes="0;0.5;1" calcMode="discrete" dur="1.2s" repeatCount="indefinite"/><animate attributeName="cy" values="42;50;42" keyTimes="0;0.5;1" calcMode="discrete" dur="1.2s" repeatCount="indefinite"/></circle>
  <circle cx="125" cy="46" r="15" fill="none" stroke="#f2b544" stroke-width="1.5" opacity="0"><animate attributeName="opacity" values="0;0;1;1;0" keyTimes="0;0.55;0.65;0.92;1" dur="4.8s" repeatCount="indefinite"/></circle>
</svg>`;
