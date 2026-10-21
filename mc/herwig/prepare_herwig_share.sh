#!/bin/bash
# Prepare the local Herwig++ 2.7.1 share tree and compatibility libraries.
#
# The CVMFS LCG build of herwig++ 2.7.1 has two relocation defects:
#   1. its HerwigDefaults.rpo stores data and library paths under
#      "MCGenerators/herwig++/2.7.1-da362", but the installation directory is
#      "MCGenerators/herwigpp/2.7.1-da362"; the generator then cannot open its
#      diffraction PDF tables (ENOENT on an existing file).
#   2. the binary needs libreadline.so.6, which is not shipped with the build.
#
# This script copies the share tree (11 MB), writes a repository file with the
# path prefix corrected, and links the system readline 8 under the soname 6 in
# a local compatibility directory. The source tree is read-only CVMFS content;
# nothing outside this directory is modified.

set -euo pipefail
LEG_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
SRC=/cvmfs/sft.cern.ch/lcg/releases/MCGenerators/herwigpp/2.7.1-da362/x86_64-slc6-gcc49-opt/share/Herwig++
DST=$LEG_DIR/hpp-share

echo "[prepare] copying $SRC -> $DST"
mkdir -p "$DST"
cp -r "$SRC/." "$DST/"

echo "[prepare] writing relocated repository file"
sed 's@MCGenerators/herwig++/2.7.1-da362@MCGenerators/herwigpp/2.7.1-da362@g' \
    "$DST/HerwigDefaults.rpo" > "$DST/HerwigDefaults-local.rpo"
if grep -q "MCGenerators/herwig++/2.7.1-da362" "$DST/HerwigDefaults-local.rpo"; then
    echo "[prepare] ERROR: stale path remains in the relocated repository" >&2
    exit 1
fi

echo "[prepare] creating readline compatibility link"
mkdir -p "$LEG_DIR/compat-libs"
ln -sf /lib/x86_64-linux-gnu/libreadline.so.8 "$LEG_DIR/compat-libs/libreadline.so.6"

echo "[prepare] done"
