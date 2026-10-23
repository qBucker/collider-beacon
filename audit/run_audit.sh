#!/bin/bash
# Re-run the Geant4 audit demonstration.
# Prerequisite: a built ./build/g4audit and a sourced Geant4 11.4 environment.
set -euo pipefail

BIN=${BIN:-./build/g4audit}
N=${N:-2000}

$BIN events/z_events.txt out/z_hits.csv "$N"
$BIN events/h_events.txt out/h_hits.csv "$N"

python3 reconstruct.py --hits out/z_hits.csv --channel z --out out/z_reco.csv
python3 reconstruct.py --hits out/h_hits.csv --channel h --out out/h_reco.csv

# 5% calibration drift: tracker field 3.99 T, ECAL energy scale 1.05
python3 reconstruct.py --hits out/z_hits.csv --channel z --bfield 3.99 \
    --out out/z_reco_tamper.csv
python3 reconstruct.py --hits out/h_hits.csv --channel h --ecal-scale 1.05 \
    --out out/h_reco_tamper.csv

python3 audit_plot.py --z out/z_reco.csv --h out/h_reco.csv \
    --z-tampered out/z_reco_tamper.csv --h-tampered out/h_reco_tamper.csv \
    --out out/audit_peaks.png --summary out/audit_summary.json
