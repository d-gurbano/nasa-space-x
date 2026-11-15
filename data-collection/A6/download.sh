#!/bin/bash
# A6 composition library: repeatable bulk downloads (read-only, anonymous, paced).
# usage: bash code/A6/download.sh [listfile]   (list lines: subdir url)
cd "$(dirname "$0")/../.." || exit 1
[ -f .venv/lib/python3.12/site-packages/certifi/cacert.pem ] && export CURL_CA_BUNDLE=$PWD/.venv/lib/python3.12/site-packages/certifi/cacert.pem
OUT=data/06-composition/raw
MAN=data/06-composition/manifest.csv
[ -f "$MAN" ] || echo "filename,url,bytes,sha256,date" > "$MAN"
LIST=${1:-code/A6/urls.txt}
while read -r sub url name; do
  [ -z "$url" ] && continue; case "$sub" in \#*) continue;; esac
  mkdir -p "$OUT/$sub"; f="$OUT/$sub/${name:-$(basename "${url%%\?*}")}"
  if [ ! -s "$f" ]; then
    for i in 1 2 3 4; do curl -sSfL --retry 3 --max-time 1800 -o "$f" "$url" && break; echo "retry $i $url"; sleep $((i*10)); done
  fi
  if [ -s "$f" ] && ! grep -q ",$url," "$MAN"; then
    echo "${f#data/06-composition/},$url,$(stat -f%z "$f"),$(shasum -a 256 "$f" | cut -d' ' -f1),$(date -u +%Y-%m-%dT%H:%MZ)" >> "$MAN"
  fi
  sleep 2
done < "$LIST"
