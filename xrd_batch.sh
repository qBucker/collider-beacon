#!/bin/bash
# xrd_batch.sh — Phase 0 real-data batch over XRootD (durable, systemd-run --user).
# Skips files whose manifest exists (self-healing on restart); circuit breaker
# after 3 consecutive failures (politeness: stop instead of hammering CERN).
set -u
cd "$(dirname "$0")" || exit 1
LOG=xrd-batch.log
ok=0; skip=0; fail=0; consec=0
i=0
while IFS= read -r u; do
  i=$((i+1))
  n=$(printf "%02d" "$i")
  out="runG/f$n"
  if [ -f "$out.manifest.json" ]; then
    echo "$(date -Is) [skip ] $out (manifest exists)" >> "$LOG"
    skip=$((skip+1)); continue
  fi
  xrd="${u/https:\/\/opendata.cern.ch\//root:\/\/eospublic.cern.ch\/\/}"
  echo "$xrd" > "uris-xrd-f$n.txt"
  echo "$(date -Is) [start] $out :: $xrd" >> "$LOG"
  if timeout 900 python3 xrd_run.py phase0_extract.py --files "uris-xrd-f$n.txt" --out "$out" --pt-min 20 >> "$LOG" 2>&1; then
    echo "$(date -Is) [done ] $out" >> "$LOG"
    ok=$((ok+1)); consec=0
  else
    echo "$(date -Is) [FAIL ] $out (rc=$?)" >> "$LOG"
    fail=$((fail+1)); consec=$((consec+1))
    if [ "$consec" -ge 3 ]; then
      echo "$(date -Is) [ABORT] 3 consecutive failures — stopping batch" >> "$LOG"
      break
    fi
  fi
  sleep 2
done < uris.txt
echo "$(date -Is) [batch end] ok=$ok fail=$fail skip=$skip" >> "$LOG"
