// Hub preview for Pulse reader: a star whose core swells and shrinks, with a sine drawn through measured dots.
const dots = [[20, 92], [40, 80], [58, 66], [78, 72], [98, 90], [118, 96], [138, 84], [158, 68], [178, 70]]
  .map(([x, y], i) => `<circle class="pvp-dot" cx="${x}" cy="${y}" r="2.6" style="--i:${i}"/>`).join('');
export const preview = `<svg viewBox="0 0 200 120" aria-hidden="true">
  <style>
    .pvp-glow { fill: #f2b544; opacity: 0.25; transform-box: fill-box; transform-origin: center; animation: pvp-beat 3.6s ease-in-out infinite; }
    .pvp-core { fill: #fff6df; transform-box: fill-box; transform-origin: center; animation: pvp-beat 3.6s ease-in-out infinite; }
    .pvp-dot { fill: #7fb2ff; opacity: 0; animation: pvp-dot 3.6s ease-out infinite; animation-delay: calc(var(--i) * 120ms); }
    .pvp-sine { fill: none; stroke: #ffd98a; stroke-width: 2; stroke-linecap: round; stroke-dasharray: 220; animation: pvp-draw 3.6s ease-out infinite; }
    @keyframes pvp-beat { 0%, 100% { transform: scale(0.55); } 50% { transform: scale(1); } }
    @keyframes pvp-dot { 0%, 8% { opacity: 0; } 20%, 90% { opacity: 1; } 100% { opacity: 0; } }
    @keyframes pvp-draw { 0%, 30% { stroke-dashoffset: 220; } 75%, 100% { stroke-dashoffset: 0; } }
    @media (prefers-reduced-motion: reduce) { .pvp-glow, .pvp-core, .pvp-dot, .pvp-sine { animation: none; opacity: 1; stroke-dashoffset: 0; } }
  </style>
  <circle class="pv-star" cx="30" cy="20" r="1.3"/><circle class="pv-star" cx="168" cy="26" r="1.3"/><circle class="pv-star" cx="186" cy="104" r="1.2"/>
  <circle class="pvp-glow" cx="100" cy="34" r="20"/><circle class="pvp-core" cx="100" cy="34" r="9"/>
  <path class="pvp-sine" d="M14 96C34 84 46 62 64 66S92 96 112 96 140 72 158 66 184 74 192 80"/>
  ${dots}</svg>`;
