#!/bin/sh
# A5: wait (max 3 h) for the NEOWISE-S3 and unWISE jobs, then rebuild summaries/PNGs and the manifest.
D=/Users/rahmanbazarov/Data/programming/SpaceApps2026-Rewind/data/05-test-targets
i=0
while [ $i -lt 1080 ]; do
  a=0; grep -q "r_dra visits" $D/logs/neowise.log 2>/dev/null && a=1
  b=0; grep -q "^done" $D/logs/unwise.log 2>/dev/null && b=1
  [ $a = 1 ] && [ $b = 1 ] && break
  sleep 10; i=$((i+1))
done
echo "jobs finished or timeout at $(date)"
python 09_summary.py
python 13_manifest.py
echo "finalize done $(date)"
