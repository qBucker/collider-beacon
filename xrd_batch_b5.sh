#!/bin/bash
# xrd_batch_b5.sh — B5 secondary-vertex stratification batch over XRootD
# (durable, systemd user). One pass per file, outputs b5G/fNN.npz + manifest.
set -u
cd "$(dirname "$0")" || exit 1
mkdir -p b5G
LOG=b5-batch.log
ok=0; skip=0; fail=0; consec=0
i=0
while IFS= read -r u; do
  i=$((i+1))
  n=$(printf "%02d" "$i")
  out="b5G/f$n"
  if [ -f "$out.manifest.json" ]; then
    echo "$(date -Is) [skip ] $out (manifest exists)" >> "$LOG"
    skip=$((skip+1)); continue
  fi
  xrd="${u/https:\/\/opendata.cern.ch\//root:\/\/eospublic.cern.ch\/\/}"
  echo "$xrd" > "/tmp/uris-b5-f$n.txt"
  echo "$(date -Is) [start] $out :: $xrd" >> "$LOG"
  if timeout 1800 python3 xrd_run.py b5_extract.py \
       --file "/tmp/uris-b5-f$n.txt" --out "$out" >> "$LOG" 2>&1; then
    echo "$(date -Is) [done ] $out" >> "$LOG"
    ok=$((ok+1)); consec=0
  else
    echo "$(date -Is) [FAIL ] $out (rc=$?)" >> "$LOG"
    fail=$((fail+1)); consec=$((consec+1))
    if [ "$consec" -ge 3 ]; then
      echo "$(date -Is) [ABORT] 3 consecutive failures" >> "$LOG"
      break
    fi
  fi
  sleep 2
done < uris.txt
echo "$(date -Is) [batch end] ok=$ok fail=$fail skip=$skip" >> "$LOG"
