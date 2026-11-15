#!/bin/bash
# A8 v1 freeze: once the first fetch has finished, snapshot the list of downloaded frames as training set v1 and
# build every derived product from exactly those frames. Each step is idempotent; rerun after an interruption.
cd "$(dirname "$0")/../.."
source env.sh
D=data/08-ai-training; LOG=$D/logs/freeze_v1.log
until grep -q "^final" $D/logs/fetch1.log 2>/dev/null; do sleep 30; done
echo "start $(date)" >> $LOG
if [ ! -f $D/index/v1_frames.txt ]; then
  find $D/raw -name "*.npz" ! -name "*.tmp.npz" -exec basename {} .npz \; | sort > $D/index/v1_frames.txt.tmp && mv $D/index/v1_frames.txt.tmp $D/index/v1_frames.txt
fi
export A8_VERSION=v1 A8_FRAMELIST=$D/index/v1_frames.txt
for step in "build_patches.py consolidate" "known_movers.py" "splits_baselines.py splits" "splits_baselines.py staticref" \
            "splits_baselines.py km_check" "inject.py selftest" "inject.py build_testset" "labeled_set.py" "make_figs.py" "make_manifest.py"; do
  echo "== $step $(date)" >> $LOG
  python code/A8/$step >> $LOG 2>&1 || echo "FAILED $step" >> $LOG
done
touch $D/V1_FROZEN
echo "done $(date)" >> $LOG
