#!/bin/bash
# xrd_lattice_sweep.sh — finish the E2 raw-phi batch after the main unit ends.
# Retries every missing file with a 2400 s timeout, up to three passes.
# Acceptance is manifest + lattice file presence; the integrity gate is the
# final authority. Exit codes from timeout are recorded but not trusted.
set -u
cd "$(dirname "$0")" || exit 1
LOG=lattice-sweep.log
TOTAL=$(wc -l < uris.txt)

count_done() {
  ls latticeG/f[0-9][0-9].manifest.json 2>/dev/null | wc -l
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
    out="latticeG/f$n"
    if [ -f "$out.manifest.json" ]; then
      continue
    fi
    xrd="${u/https:\/\/opendata.cern.ch\//root:\/\/eospublic.cern.ch\/\/}"
    echo "$xrd" > "/tmp/uris-lattice-f$n.txt"
    echo "$(date -Is) [pass $pass start] $out" >> "$LOG"
    timeout 2400 python3 xrd_run.py lattice_extract.py \
      --files "/tmp/uris-lattice-f$n.txt" --out "$out" --pt-min 20 >> "$LOG" 2>&1
    rc=$?
    if [ -f "$out.manifest.json" ] && [ -f "$out.lattice.bin" ]; then
      echo "$(date -Is) [pass $pass done ] $out" >> "$LOG"
    else
      echo "$(date -Is) [pass $pass FAIL ] $out (rc=$rc)" >> "$LOG"
    fi
    sleep 5
  done < uris.txt
  done_after=$(count_done)
  echo "$(date -Is) [pass $pass end] done=$done_after" >> "$LOG"
  [ "$done_after" -ge "$TOTAL" ] && break
done
done_final=$(count_done)
echo "$(date -Is) [sweep end] done=$done_final total=$TOTAL" >> "$LOG"
[ "$done_final" -ge "$TOTAL" ]
