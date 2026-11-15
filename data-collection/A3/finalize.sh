#!/bin/bash
# Detached finalizer: re-combine tables every 10 min until MOST and deep slices finish, then retry failed deep slices once.
cd /Users/rahmanbazarov/Data/programming/SpaceApps2026-Rewind && source env.sh
for i in $(seq 1 60); do
  python code/A3/combine_most.py > data/03-spherex/logs/combine_most.log 2>&1
  python code/A3/combine_sia.py > data/03-spherex/logs/combine_sia.log 2>&1
  python code/A3/verify_cal.py > data/03-spherex/logs/verify_cal.log 2>&1
  n=$(wc -l < data/03-spherex/logs/most_status.csv)
  [ "$n" -ge 903 ] && [ -f data/03-spherex/logs/.deep_done ] && break
  sleep 600
done
# one retry pass of failed deep slices
rm -f data/03-spherex/frames/deep_tslices/*.fail
python code/A3/run_deep_tslices.py >> data/03-spherex/logs/deep_tslices_retry.log 2>&1
python code/A3/combine_sia.py > data/03-spherex/logs/combine_sia.log 2>&1
echo done > data/03-spherex/logs/finalize_done
