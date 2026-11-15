#!/bin/bash
# A2: download MPC bulk orbit files (read-only, public). Re-runnable.
cd "$(dirname "$0")/../../data/02-orbits/mpc"
for u in \
 https://minorplanetcenter.net/iau/MPCORB/MPCORB.DAT.gz \
 https://minorplanetcenter.net/iau/MPCORB/NEA.txt \
 https://minorplanetcenter.net/iau/MPCORB/CometEls.txt \
 https://minorplanetcenter.net/iau/lists/ObsCodes.html \
 https://minorplanetcenter.net/Extended_Files/mpcorb_extended.json.gz ; do
  f=$(basename $u); curl -sS -L --retry 3 --retry-delay 5 -o "$f" "$u"; echo "$f $(stat -f%z "$f")"; sleep 2
done
curl -sS -L --retry 3 -o obscodes_api.json "https://data.minorplanetcenter.net/api/obscodes" -X GET -H 'Content-Type: application/json' -d '{}' ; echo obscodes_api $(stat -f%z obscodes_api.json)
