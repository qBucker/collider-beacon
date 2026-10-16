#!/bin/bash
# xrd_batch2.sh — Phase 0 round-2 batch: --require-jetid (tight, bit1), extractor v1.1.
# Round-2 outputs live in runG2/; per-file diff vs runG/ (round 1, bare) goes to the
# robustness section of the paper. NOT auto-launched: run after round 1 completes
# and round-1 results have been eyeballed.
#   systemd-run --user --unit=phase0-xrd-batch2 --collect \
#     --working-directory=/home/shuix/projects/deepseekharness/beacon-paper/phase0 \
#     /bin/bash /home/shuix/projects/deepseekharness/beacon-paper/phase0/xrd_batch2.sh
set -u
cd /home/shuix/projects/deepseekharness/beacon-paper/phase0 || exit 1
LIST="${1:-uris.txt}"   # optional: pass a shorter file list, e.g. uris-2v.txt (5-file sample)
LOG="xrd-batch2-$(basename "$LIST" .txt).log"
mkdir -p runG2
ok=0; skip=0; fail=0; consec=0
i=0
while IFS= read -r u; do
  i=$((i+1))
  n=$(printf "%02d" "$i")
  out="runG2/f$n"
  if [ -f "$out.manifest.json" ]; then
    echo "$(date -Is) [skip ] $out (manifest exists)" >> "$LOG"
    skip=$((skip+1)); continue
  fi
  xrd="${u/https:\/\/opendata.cern.ch\//root:\/\/eospublic.cern.ch\/\/}"
  echo "$xrd" > "uris-xrd2-f$n.txt"
  echo "$(date -Is) [start] $out :: tight" >> "$LOG"
  if timeout 900 python3 xrd_run.py phase0_extract_v1_1.py --files "uris-xrd2-f$n.txt" --out "$out" --pt-min 20 --require-jetid >> "$LOG" 2>&1; then
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
done < "$LIST"
echo "$(date -Is) [batch2 end] ok=$ok fail=$fail skip=$skip" >> "$LOG"
