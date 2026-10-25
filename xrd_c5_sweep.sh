#!/bin/bash
# xrd_c5_sweep.sh — finish a partial C5 batch. Retries every missing file with a
# 3600 s timeout, up to three passes. Acceptance: manifest + npz presence; the
# integrity gate is the final authority.
set -u
cd "$(dirname "$0")" || exit 1
LOG=c5-sweep.log
TOTAL=$(wc -l < uris.txt)

count_done() {
  ls c5G/f[0-9][0-9].manifest.json 2>/dev/null | wc -l
}

echo "$(date -Is) [sweep start] total=$TOTAL done=$(count_done)" >> "$LOG"
for pass in 1 2 3; do
  done_before=$(count_done)
  if [ "$done_before" -ge "$TOTAL" ]; then
    echo "$(date -Is) [sweep end] all $TOTAL manifests present" >> "$LOG"
    exit 0
  fi
  echo "$(date -Is) [pass $pass] done=$done_before missing=$((TOTAL-done_before))" >> "$LOG"
  i=0
  while IFS= read -r u; do
    i=$((i+1))
    n=$(printf "%02d" "$i")
    out="c5G/f$n"
    if [ -f "$out.manifest.json" ]; then
      continue
    fi
    xrd="${u/https:\/\/opendata.cern.ch\//root:\/\/eospublic.cern.ch\/\/}"
    echo "$xrd" > "/tmp/uris-c5-f$n.txt"
    echo "$(date -Is) [pass $pass start] $out" >> "$LOG"
    timeout 3600 python3 xrd_run.py c5_extract.py \
      --file "/tmp/uris-c5-f$n.txt" --out "$out" >> "$LOG" 2>&1
    rc=$?
    if [ -f "$out.manifest.json" ] && [ -f "$out.npz" ]; then
      echo "$(date -Is) [pass $pass done ] $out" >> "$LOG"
    else
      echo "$(date -Is) [pass $pass FAIL ] $out (rc=$rc)" >> "$LOG"
    fi
    sleep 2
  done < uris.txt
done
echo "$(date -Is) [sweep end] done=$(count_done)/$TOTAL" >> "$LOG"
