#!/bin/bash
# A2: build Find_Orb (Bill Gray / Project Pluto, GPL-2) CLI "fo" from GitHub sources, read-only clone.
set -e
cd "$(dirname "$0")/../../data/02-orbits/findorb"
for r in lunar jpl_eph sat_code find_orb miscell; do [ -d $r ] || git clone --depth 1 https://github.com/Bill-Gray/$r.git; done
export INSTALL_DIR=$PWD/install; mkdir -p $INSTALL_DIR/include $INSTALL_DIR/lib $INSTALL_DIR/bin
(cd lunar && make CLANG=Y INSTALL_DIR=$INSTALL_DIR && make CLANG=Y INSTALL_DIR=$INSTALL_DIR install)
(cd jpl_eph && make CLANG=Y INSTALL_DIR=$INSTALL_DIR libjpl.a && make CLANG=Y INSTALL_DIR=$INSTALL_DIR install)
(cd lunar && make CLANG=Y INSTALL_DIR=$INSTALL_DIR integrat && cp integrat $INSTALL_DIR/bin/ || true)
(cd sat_code && make CLANG=Y INSTALL_DIR=$INSTALL_DIR && make CLANG=Y INSTALL_DIR=$INSTALL_DIR install)
(cd miscell && make CLANG=Y INSTALL_DIR=$INSTALL_DIR || true)
(cd find_orb && make CLANG=Y INSTALL_DIR=$INSTALL_DIR fo && cp fo $INSTALL_DIR/bin/)
ls -la $INSTALL_DIR/bin
