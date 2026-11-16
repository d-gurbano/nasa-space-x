// Hub preview for Star speedometer: a star creeps away from a dashed ring while a gold marker
// follows it, a small looping SVG (200 x 120) moved with CSS.
const stars = [[22, 30], [160, 24], [40, 96], [176, 92], [130, 106], [70, 16]].map(([x, y]) => `<circle class="pv-star" cx="${x}" cy="${y}" r="1.4"/>`).join('');

export const preview = `<svg viewBox="0 0 200 120" aria-hidden="true">${stars}
  <style>
    .pvs-ring { fill: none; stroke: var(--blue-2); stroke-width: 1.3; stroke-dasharray: 3 3; }
    .pvs-star { fill: #e8ecf4; filter: drop-shadow(0 0 5px rgba(232, 236, 244, 0.8)); animation: pvs-move 3.6s var(--ease) infinite; }
    .pvs-mark { fill: none; stroke: var(--gold); stroke-width: 1.6; animation: pvs-mark 3.6s var(--ease) infinite; }
    @keyframes pvs-move { 0%, 15% { transform: none; } 50%, 100% { transform: translate(6px, -30px); } }
    @keyframes pvs-mark { 0%, 45% { transform: translate(14px, 10px); opacity: 0; } 60% { opacity: 1; } 75%, 100% { transform: translate(6px, -30px); opacity: 1; } }
    @media (prefers-reduced-motion: reduce) { .pvs-star, .pvs-mark { animation: none; transform: translate(6px, -30px); } }
  </style>
  <circle class="pvs-ring" cx="96" cy="78" r="10"/>
  <circle class="pvs-star" cx="96" cy="78" r="4.5"/>
  <circle class="pvs-mark" cx="96" cy="78" r="9"/>
</svg>`;
