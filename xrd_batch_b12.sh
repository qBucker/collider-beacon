#!/bin/bash
# xrd_batch_b12.sh — Phase 0 b=12 entropy-gate batch over XRootD (durable, systemd-run --user).
# Same 67 files and cuts as round 1; the only change is the bin count (b=8 -> b=12).
# Skips files whose manifest exists (self-healing on restart); circuit breaker
# after 3 consecutive failures (politeness: stop instead of hammering CERN).
set -u
cd "$(dirname "$0")" || exit 1
LOG=xrd-batch-b12.log
mkdir -p runG12 /tmp/phase0-b12-uris
ok=0; skip=0; fail=0; consec=0
i=0
while IFS= read -r u; do
  i=$((i+1))
  n=$(printf "%02d" "$i")
  out="runG12/f$n"
  if [ -f "$out.manifest.json" ]; then
    echo "$(date -Is) [skip ] $out (manifest exists)" >> "$LOG"
    skip=$((skip+1)); continue
  fi
  xrd="${u/https:\/\/opendata.cern.ch\//root:\/\/eospublic.cern.ch\/\/}"
  echo "$xrd" > "/tmp/phase0-b12-uris/f$n.txt"
  echo "$(date -Is) [start] $out :: $xrd (b=12)" >> "$LOG"
  if timeout 900 python3 xrd_run.py phase0_extract.py --files "/tmp/phase0-b12-uris/f$n.txt" --out "$out" --pt-min 20 --b 12 >> "$LOG" 2>&1; then
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
