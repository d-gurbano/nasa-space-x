#!/bin/bash
# A8 v2 background fetch: waits until the v1 fetch (fetch1) has finished, then fetches a larger, evenly
# spaced selection (select_v2, 8x the v1 per-cluster counts, capped by availability). Resumable: rerun this
# script after any interruption; existing raw/*.npz are skipped. Stop cleanly: touch data/08-ai-training/STOP_FETCH
cd "$(dirname "$0")/../.."
source env.sh
LOG=data/08-ai-training/logs
until grep -q "^final" $LOG/fetch1.log 2>/dev/null || [ -f data/08-ai-training/V1_FROZEN_START_V2 ]; do sleep 30; done
python code/A8/build_patches.py select_v2 8 > $LOG/select_v2.log 2>&1
python code/A8/build_patches.py fetch 900 10 frames_selected_v2.parquet >> $LOG/fetch_v2.log 2>&1
echo "v2 fetch exited $(date)" >> $LOG/fetch_v2.log
