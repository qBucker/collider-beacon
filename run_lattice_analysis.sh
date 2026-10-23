#!/bin/bash
# run_lattice_analysis.sh — integrity gate, then E2 analysis, after the batch.
# Waits for the main batch and the sweep unit, requires 67/67 integrity, then
# writes the analysis JSON before the figure.
set -u
cd "$(dirname "$0")" || exit 1
LOG=lattice-analysis.log
echo "$(date -Is) [analysis] waiting for batch units" >> "$LOG"
while systemctl --user is-active --quiet phase0-lattice || \
      systemctl --user is-active --quiet phase0-lattice-sweep; do
  sleep 60
done
echo "$(date -Is) [analysis] batch units finished" >> "$LOG"

python3 diagnostics/lattice_integrity.py --lattice-dir latticeG \
  --require-complete --expected-files 67 --expected-n 5211771 \
  --out diagnostics/lattice-integrity.json > lattice-integrity.log 2>&1
rc=$?
echo "$(date -Is) [analysis] integrity rc=$rc" >> "$LOG"
if [ "$rc" -ne 0 ]; then
  echo "$(date -Is) [analysis] stop: integrity gate failed" >> "$LOG"
  exit "$rc"
fi

python3 diagnostics/lattice_alpha.py --lattice-dir latticeG \
  --out diagnostics/lattice-alpha.json --fig diagnostics/lattice-alpha.png \
  > lattice-alpha.log 2>&1
rc=$?
echo "$(date -Is) [analysis] alpha rc=$rc" >> "$LOG"
exit "$rc"
