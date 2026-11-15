#!/bin/bash
# A8: (1) after the v1 freeze finishes, write NUMBERS-v1.md; (2) after the v2 background fetch exits (budget,
# time limit or STOP_FETCH), build all v2 products from every raw frame (A8_VERSION=v2 -> index/v2, patches_v2,
# baselines_v2, labeled_v2, injected_test_v2, tables_v2, figs_v2) and write NUMBERS-v2.md. Resumable: rerun.
cd "$(dirname "$0")/../.."
source env.sh
D=data/08-ai-training; LOG=$D/logs/build_v2.log
until [ -f $D/V1_FROZEN ]; do sleep 30; done
A8_VERSION=v1 python code/A8/report_numbers.py > /dev/null 2>> $LOG
until grep -q "v2 fetch exited" $D/logs/fetch_v2.log 2>/dev/null; do sleep 60; done
df -h . >> $LOG
export A8_VERSION=v2
for step in "build_patches.py consolidate" "known_movers.py" "splits_baselines.py splits" "splits_baselines.py staticref" \
            "splits_baselines.py km_check" "inject.py build_testset" "labeled_set.py" "make_figs.py" "make_manifest.py" "report_numbers.py"; do
  echo "== $step $(date)" >> $LOG
  python code/A8/$step >> $LOG 2>&1 || echo "FAILED $step" >> $LOG
done
touch $D/V2_BUILT
echo "done $(date)" >> $LOG
