#!/usr/bin/env bash
# twin_run.sh — build & run the C++/ROOT twin battery against the frozen Python references.
# Cells: (1) f01 b=8 main pipeline; (2) f01 b=5 residual path; (3) MC Delphes b=5;
#        (4) edge battery (ties/NaN/bin-edges/clamp); (5) NaN-phi refusal behaviour.
#
# Environment lessons baked in (2026-10-16, all encountered live):
#   - LCG ROOT's Cling needs `x86_64-linux-gnu-g++-11` on PATH (compiler probe at startup;
#     without it CI creation fails / stale-interpreter paths misbehave) -> symlink g++-13.
#   - Externals tbb/pcre2 from LCG releases must be on LD_LIBRARY_PATH (root-config --libs
#     does not carry them).
#   - CVMFS lazy-pull on .pcm/.so can D-stall mmap page faults (folio_wait_bit_common).
#     Prewarm once before running:
#       find $R/lib -maxdepth 1 -type f | xargs -P 8 -I{} sh -c 'cat "{}" > /dev/null'
set -euo pipefail
cd "$(dirname "$0")/.."          # phase0/

ROOT_DIR=/cvmfs/sft.cern.ch/lcg/releases/ROOT/6.40.04-866e3/x86_64-ubuntu2204-gcc11-opt
TB=/cvmfs/sft.cern.ch/lcg/releases/tbb/2022.2.0-d78b7/x86_64-ubuntu2204-gcc11-opt/lib
PC=/cvmfs/sft.cern.ch/lcg/releases/pcre2/10.48-4b59c/x86_64-ubuntu2204-gcc11-opt/lib
OUTDIR=refix-2026-10-16/twin
mkdir -p "$OUTDIR"

# compiler-name shim for Cling (idempotent)
mkdir -p "$HOME/.local/twinbin"
[ -e "$HOME/.local/twinbin/x86_64-linux-gnu-g++-11" ] || ln -sf /usr/bin/x86_64-linux-gnu-g++-13 "$HOME/.local/twinbin/x86_64-linux-gnu-g++-11"
[ -e "$HOME/.local/twinbin/x86_64-linux-gnu-gcc-11" ] || ln -sf /usr/bin/x86_64-linux-gnu-gcc-13 "$HOME/.local/twinbin/x86_64-linux-gnu-gcc-11"
export PATH="$HOME/.local/twinbin:$PATH"
export LD_LIBRARY_PATH="$ROOT_DIR/lib:$TB:$PC${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"

echo "== build =="
g++ -O2 -std=c++17 $("$ROOT_DIR/bin/root-config" --cflags) twin/phase0_extract_twin.cpp -o twin/twin_bin \
    -L"$TB" -L"$PC" $("$ROOT_DIR/bin/root-config" --libs) -ltbb -Wl,-rpath,"$TB" -Wl,-rpath,"$PC"
echo "build ok"

pass=0; fail=0
check() { if cmp -s "$2" "$3"; then echo "MATCH  $1 ✅"; pass=$((pass+1)); else echo "MISMATCH $1 ❌"; fail=$((fail+1)); fi; }

echo "== (1) f01 b=8 (main pipeline) =="
twin/twin_bin data/nano_data2016_1-1.root "$OUTDIR/f01" --b 8 --pt-min 20
check "f01-b8 vs frozen runG/f01.bits.bin" runG/f01.bits.bin "$OUTDIR/f01.bits.bin"

echo "== (2) f01 b=5 (residual path, 6 bits discarded) =="
twin/twin_bin data/nano_data2016_1-1.root "$OUTDIR/f01b5" --b 5 --pt-min 20
check "f01-b5 vs python ref" refix-2026-10-16/f01b5.bits.bin "$OUTDIR/f01b5.bits.bin"

echo "== (3) MC Delphes b=5 =="
twin/twin_bin mc/minbias_delphes.root "$OUTDIR/mc-b5" --mc --b 5 --pt-min 20
check "mc-b5 vs python ref" refix-2026-10-16/mc-b5.bits.bin "$OUTDIR/mc-b5.bits.bin"

echo "== (4) edge battery (ties / NaN / bin-edges / clamp) =="
twin/twin_bin twin/edge_cases.root "$OUTDIR/edge-twin" --b 8 --pt-min 20
check "edge vs python ref" refix-2026-10-16/twin/edge-py2.bits.bin "$OUTDIR/edge-twin.bits.bin"

echo "== (5) NaN-phi refusal (expect rc=3; Python raises) =="
if twin/twin_bin twin/edge_nanphi.root /tmp/nanphi-twin >/dev/null 2>&1; then
  echo "refusal ❌ (exited 0)"; fail=$((fail+1))
else
  rc=$?
  if [ "$rc" = "3" ]; then echo "refusal ✅ (rc=3)"; pass=$((pass+1)); else echo "refusal rc=$rc ⚠️"; fail=$((fail+1)); fi
fi

echo; echo "BATTERY: $pass pass / $fail fail"
[ "$fail" = "0" ] && echo "Result: all cells bit-identical (main + residual + MC + edge + refusal)"
