// Hub preview for Comet or asteroid?: a fuzzy comet beside a sharp asteroid, and a spectrum whose
// last point rises at the 4.26 µm line. Styles are inline because the game's CSS loads only with the game.
const pts = [[24, 92], [44, 88], [64, 90], [84, 86], [104, 89], [124, 87], [144, 90]].map(([x, y]) => `<circle class="pv-cm-pt" cx="${x}" cy="${y}" r="2.6"/>`).join('');
export const preview = `<svg viewBox="0 0 200 120" aria-hidden="true">
  <style>
    .pv-cm-coma{fill:url(#pv-cm-g);transform-box:fill-box;transform-origin:center;animation:pv-cm-breathe 3.6s ease-in-out infinite}
    @keyframes pv-cm-breathe{0%,100%{opacity:.55;transform:scale(.9)}50%{opacity:1;transform:scale(1.12)}}
    .pv-cm-core{fill:var(--gold-2)}.pv-cm-rock{fill:#c9cfdb}.pv-cm-pt{fill:var(--blue-2)}
    .pv-cm-bump{fill:var(--gold-2);animation:pv-cm-bump 3.6s ease-in-out infinite}
    @keyframes pv-cm-bump{0%,30%{transform:translateY(18px);opacity:.4}60%,100%{transform:none;opacity:1}}
    .pv-cm-line{stroke:var(--gold-line);stroke-dasharray:3 3}
    @media (prefers-reduced-motion:reduce){.pv-cm-coma,.pv-cm-bump{animation:none}}
  </style>
  <defs><radialGradient id="pv-cm-g"><stop offset="0" stop-color="#ffd98a" stop-opacity=".7"/><stop offset="1" stop-color="#ffd98a" stop-opacity="0"/></radialGradient></defs>
  <circle class="pv-star" cx="20" cy="18" r="1.3"/><circle class="pv-star" cx="178" cy="26" r="1.3"/><circle class="pv-star" cx="104" cy="12" r="1.1"/>
  <circle class="pv-cm-coma" cx="60" cy="40" r="20"/><circle class="pv-cm-core" cx="60" cy="40" r="3.4"/>
  <circle class="pv-cm-rock" cx="146" cy="42" r="2.8"/>
  <line class="pv-cm-line" x1="170" x2="170" y1="58" y2="110"/>
  ${pts}<circle class="pv-cm-bump" cx="170" cy="70" r="3.4"/>
</svg>`;
