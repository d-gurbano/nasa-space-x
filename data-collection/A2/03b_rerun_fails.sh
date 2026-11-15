#!/bin/bash
# wait for first pass, then retry failed obs downloads with corrected comet keys
cd "$(dirname "$0")/../.."; source env.sh
while [ ! -f data/02-orbits/candidates_orbit_summary.csv ]; do sleep 10; done
rm -f data/02-orbits/obs/*.fail; python code/A2/03_sbdb_mpcobs.py
