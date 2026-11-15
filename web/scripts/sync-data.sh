#!/usr/bin/env bash
# Copy the engine's site data (MAIN/data/site/) into web/public/data/.
# The app prefers public/data/ and falls back to public/data-sample/.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
MAIN="${REWIND_MAIN:-/Users/rahmanbazarov/Data/programming/SpaceApps2026-Rewind}"
SRC="$MAIN/data/site"
DST="$HERE/../public/data"
if [ ! -f "$SRC/index.json" ]; then
  echo "No engine output at $SRC/index.json yet; the site will use data-sample/." >&2
  exit 1
fi
mkdir -p "$DST"
rsync -a --delete "$SRC/" "$DST/"
echo "Synced $(du -sh "$DST" | cut -f1) from $SRC to $DST"

# Extra real assets for the Challenge stars page (blink GIFs, decades montages, light curves, summaries, and the tables behind the charts).
TT="$MAIN/data/05-test-targets"
EXTRA="$HERE/../public/extra/stars"
if [ -d "$TT/png" ]; then
  mkdir -p "$EXTRA"
  for t in barnard eps_indi_b wise0855 rw_aur r_dra; do
    for f in "$TT/png/${t}_decades_montage.png" "$TT/png/${t}_spherex_blink.gif" "$TT/png/${t}_lightcurve.png" "$TT/results/${t}_summary.json" "$TT/results/${t}_decades_positions.csv" "$TT/results/${t}_lightcurve.csv"; do
      [ -f "$f" ] && cp "$f" "$EXTRA/"
    done
  done
  echo "Copied challenge-star extras to $EXTRA"
fi
