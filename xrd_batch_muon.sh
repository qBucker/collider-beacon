#!/bin/bash
# xrd_batch_muon.sh — corrected dimuon arm (muon branches only) over XRootD.
set -u
cd "$(dirname "$0")" || exit 1
mkdir -p muonG
LOG=muon-batch.log
ok=0; skip=0; fail=0; consec=0
i=0
while IFS= read -r u; do
  i=$((i+1))
  n=$(printf "%02d" "$i")
  out="muonG/f$n"
  if [ -f "$out.manifest.json" ]; then
    skip=$((skip+1)); continue
  fi
  xrd="${u/https:\/\/opendata.cern.ch\//root:\/\/eospublic.cern.ch\/\/}"
  echo "$xrd" > "/tmp/uris-muon-f$n.txt"
  echo "$(date -Is) [start] $out" >> "$LOG"
  if timeout 1200 python3 xrd_run.py c5_muon_count.py \
       --file "/tmp/uris-muon-f$n.txt" --out "$out" >> "$LOG" 2>&1; then
    echo "$(date -Is) [done ] $out" >> "$LOG"
    ok=$((ok+1)); consec=0
  else
    echo "$(date -Is) [FAIL ] $out" >> "$LOG"
    fail=$((fail+1)); consec=$((consec+1))
    [ "$consec" -ge 3 ] && { echo "$(date -Is) [ABORT]" >> "$LOG"; break; }
  fi
  sleep 2
done < uris.txt
echo "$(date -Is) [batch end] ok=$ok fail=$fail skip=$skip" >> "$LOG"
