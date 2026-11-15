#!/bin/bash
# A4: rerun all summaries after the long background jobs (03_catch, 06_most_ztf, 09_most_spitzer, 10_decam, 11_tess) finish. Safe to rerun.
cd /Users/rahmanbazarov/Data/programming/SpaceApps2026-Rewind && source env.sh >/dev/null 2>&1
python -u code/A4/12_catch_summary.py; python -u code/A4/13_ztf_summary.py; python -u code/A4/16_decam_summary.py; python -u code/A4/14_cutouts.py; python -u code/A4/15_manifest.py
