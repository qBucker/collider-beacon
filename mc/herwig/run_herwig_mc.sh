#!/bin/bash
# Produce the Herwig++ 2.7.1 minimum-bias prediction-side sample and run the
# frozen extractor on it.
#
# Layout: 8 chunks x 50,000 events, seeds 20261101-20261108, each chunk
# generated (Herwig++) and processed (DelphesHepMC2, CMS card) in its own
# directory. HepMC files are removed after the Delphes step; the chunk ROOT
# files are merged with hadd and removed, then phase0_extract.py runs on the
# merged file. Logs and the final checksums are kept in run400k/.
#
# Pre-registered in predictions/2026-10-21-herwig-minbias.md (commit 500f375).

set -euo pipefail
LEG_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
RUN=${RUN_DIR:-$LEG_DIR/run400k}
COLLIDER=${COLLIDER_SIM:-$HOME/projects/deepseekharness/collider-sim}
DELPHES_CARD=$COLLIDER/env/delphes/cards/delphes_card_CMS.tcl
EXTRACTOR=${PHASE0_EXTRACTOR:-$(cd "$LEG_DIR/../.." && pwd)/phase0_extract.py}
NCHUNK=${NCHUNK:-8}
NPER=${NPER:-50000}
SEED0=${SEED0:-20261101}

log() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*"; }

mkdir -p "$RUN"
cd "$RUN"

source "$LEG_DIR/herwig_env.sh"
export HERWIGPATH="$LEG_DIR/hpp-share"

if [ ! -f "$RUN/LHC-MB-13TeV.run" ]; then
    log "reading input file -> run file"
    Herwig++ read --repo="$HERWIGPATH/HerwigDefaults-local.rpo" \
        "$LEG_DIR/LHC-MB-13TeV-HepMC-hpp271.in" > "$RUN/read.log" 2>&1
fi

for i in $(seq 0 $((NCHUNK - 1))); do
    n=$(printf %02d "$i")
    d="$RUN/chunk_$n"
    seed=$((SEED0 + i))
    if [ -s "$d/herwig_delphes.root" ]; then
        log "chunk $n: already complete, skipping"
        continue
    fi
    mkdir -p "$d"

    log "chunk $n: generating $NPER events (seed $seed)"
    ( cd "$d" && /usr/bin/time -f 'wall_s=%e maxrss_kb=%M' \
        Herwig++ run --repo="$HERWIGPATH/HerwigDefaults-local.rpo" \
        "$RUN/LHC-MB-13TeV.run" -N "$NPER" -s "$seed" > gen.log 2>&1 )

    nevents=$(grep -c '^E ' "$d/herwig_minbias.hepmc" || true)
    if [ "$nevents" -ne "$NPER" ]; then
        log "chunk $n: ERROR event count $nevents != $NPER"
        exit 1
    fi

    log "chunk $n: Delphes"
    ( env -u LD_LIBRARY_PATH -u HERWIGPATH -u HERWIG_HOME -u THEPEG_HOME \
        -u LHAPDF_HOME -u LHAPDF_DATA_PATH -u THEPEGPATH \
        bash -c "cd '$COLLIDER' && source scripts/env.sh >/dev/null 2>&1 && cd env/delphes && /usr/bin/time -f 'wall_s=%e' ./DelphesHepMC2 '$DELPHES_CARD' '$d/herwig_delphes.root' '$d/herwig_minbias.hepmc'" \
        > "$d/delphes.log" 2>&1 )

    if [ ! -s "$d/herwig_delphes.root" ]; then
        log "chunk $n: ERROR no Delphes output"
        exit 1
    fi

    mkdir -p "$RUN/logs"
    cp "$d/gen.log" "$RUN/logs/chunk_$n.gen.log"
    cp "$d/delphes.log" "$RUN/logs/chunk_$n.delphes.log"
    for f in LHC-MB-13TeV.log LHC-MB-13TeV.out LHC-MB-13TeV.tex; do
        [ -f "$d/$f" ] && cp "$d/$f" "$RUN/logs/chunk_$n.$f"
    done

    rm -f "$d/herwig_minbias.hepmc"
    log "chunk $n: done ($(du -h "$d/herwig_delphes.root" | cut -f1))"
done

log "merging chunk files"
( env -u LD_LIBRARY_PATH bash -c "cd '$COLLIDER' && source scripts/env.sh >/dev/null 2>&1 && hadd -f '$RUN/herwig_delphes_400k.root' $RUN/chunk_*/herwig_delphes.root" > "$RUN/hadd.log" 2>&1 )
if [ ! -s "$RUN/herwig_delphes_400k.root" ]; then
    log "ERROR merge failed"
    exit 1
fi
log "merged file: $(du -h "$RUN/herwig_delphes_400k.root" | cut -f1)"

log "running the frozen extractor"
( env -u LD_LIBRARY_PATH /usr/bin/python3 "$EXTRACTOR" \
    --mc "$RUN/herwig_delphes_400k.root" --out "$RUN/mc_hpp_400k" \
    --pt-min 20 > "$RUN/extract.log" 2>&1 )
log "extractor done"

sha256sum "$RUN/herwig_delphes_400k.root" "$RUN/mc_hpp_400k.manifest.json" \
    "$RUN/mc_hpp_400k.bits.bin" > "$RUN/SHA256SUMS"
rm -rf "$RUN"/chunk_*
log "complete"
