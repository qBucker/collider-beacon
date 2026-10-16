# Collider Beacon — Phase 0 (engineering)

Engineering stack behind **The Collider Beacon** — certified public randomness from
symmetry and quantum measurement. Phase 0 ("first light"): the full chain from CMS
Open Data to audited random bits, with a bit-exact dual implementation
(Python / C++·ROOT) and a complete evidence trail.

## First light, measured (2026-10-16)

- CMS ZeroBias Run2016G NanoAOD open data (CC0-1.0), **67/67 files**, XRootD remote read
- n = **5,211,771** qualifying events · **41,694,168** bits
- pooled certified min-entropy **7.8413 bits/event** — 98% of the b = 8 ceiling
  (Clopper–Pearson × Bonferroni, α = 1e-6; per-event leading-jet azimuth, pT > 20 GeV, |η| < 2.5)
- gates: KS 67/67 · NIST STS zero flags on the full 41.7 Mbit stream
- **measured detector seam**: −10.5% localized acceptance deficit (bins 227–234, φ ≈ +139°..+150°),
  stable across all 67 files and terciles; unchanged under tight-jetId selection —
  absorbed conservatively by the entropy bound (the paper's "honest accounting" line)

## Layout

- `phase0_extract.py` — extractor **P** (reference): per event → leading jet (max pT) → φ → uniform 2^b bins (MSB-first)
- `phase0_extract_v1_1.py` — round-2 variant (tight-jetId bitmask fix: `(jetId & 2) == 2`)
- `phase0_extract_legacy-f8622c70.py` — pre-R3 frozen bytes (round-1 manifests record this `code_sha256`)
- `phase0_verify.py` — independent manifest re-check (hashes, entropy recompute, gates)
- `xrd_*.py` / `*.sh` — XRootD pipeline: batch extraction, resumable full-file fetch + watchdog,
  portal reconciliation (adler32), provenance, aggregation
- `twin/` — **C++/ROOT twin** (bit-exact mirror of the Python extractor) + edge-case battery + one-command runner
- `runG/`, `runG2/`, `refix-2026-10-16/` — evidence: per-file manifests, bits, SHA256SUMS, aggregates,
  round-2 sample, R3 re-verification and twin battery outputs
- `mc/` — Pythia8 command cards + prediction-side evidence (large `.root` files excluded; regenerate with the cards)

## Reproduce

```bash
pip install uproot awkward scipy numpy fsspec xrootd fsspec-xrootd   # use a mirror that carries xrootd
python3 xrd_run.py phase0_extract.py --files uris-local-f01.txt --out out/f01 --pt-min 20
python3 phase0_verify.py out/f01.manifest.json
```

C++/ROOT twin (ROOT 6.40.04 from CVMFS; the script bakes in the environment fixes below):

```bash
bash twin/twin_run.sh
```

The battery compares the twin against the frozen Python references, bit for bit:

| cell | surface | result |
|---|---|---|
| 1. f01, b = 8 | real-data main pipeline | identical to `runG/f01.bits.bin` (sha256 `6bc096b7…`) |
| 2. f01, b = 5 | residual-bit path (6 residual bits discarded) | identical |
| 3. MC Delphes, b = 5 | prediction-side tree | identical |
| 4. edge battery | pT ties (first-max), NaN mask, exact bin edges (±1 ULP), ±π clamp | identical |
| 5. NaN-φ | undefined input | both refuse (Python raises; twin exits 3) |

## Environment notes (encountered live; now baked into `twin/twin_run.sh`)

- LCG ROOT's Cling probes `x86_64-linux-gnu-g++-11` at startup; without it, interpreter
  creation fails (workaround: symlink any system g++ under that name).
- ROOT externals (TBB, PCRE2) are **not** in `root-config --libs`; add the LCG release
  paths to `LD_LIBRARY_PATH` at link and run time.
- CVMFS lazy-pull of `.pcm` / `.so` files can D-stall mmap page faults
  (`folio_wait_bit_common`); prewarm the ROOT lib directory once
  (`find $ROOT/lib -maxdepth 1 -type f | xargs -P 8 -I{} sh -c 'cat {} > /dev/null'`).
- XRootD: URIs need `root://host//eos/...` (double slash); XRootD 6.x pybind11 rejects
  numpy integer types — a one-byte-width shim (`xrd_compat.py`) handles this.
- uproot ≥ 5.7: writing a classic TTree needs `wf.mktree(name, {col: "var * float32"})`
  + `.extend()`; plain dict assignment produces an **RNTuple**.

## Evidence discipline

Every number in the companion paper traces to a manifest here
(`params` + `code_sha256` + `bits_sha256` + gates + `SHA256SUMS`). Data: CMS Open Data,
CC0-1.0. No large binary data is stored in this repository.

## License

MIT — see `LICENSE`. Companion repository:
[vmc-rsep-xmss](https://github.com/qBucker/vmc-rsep-xmss) (monotone accountability / VMC).

