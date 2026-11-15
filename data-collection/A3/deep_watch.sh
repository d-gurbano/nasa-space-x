#!/bin/bash
cd /Users/rahmanbazarov/Data/programming/SpaceApps2026-Rewind/data/03-spherex
last=""; same=0
while [ $same -lt 6 ]; do s=$(stat -f %m logs/deep_tslices.log); [ "$s" = "$last" ] && same=$((same+1)) || same=0; last=$s; sleep 300; done
touch logs/.deep_done
