# Collider Beacon — Phase 0 Engineering

Engineering stack for the Collider Beacon project: certified public randomness from
symmetry and quantum measurement. Phase 0 covers the complete processing chain from
CMS Open Data to audited random bits, including a bit-identical dual implementation
(Python and C++/ROOT) and a complete evidence record.

## Measured results (2026-10-16)

- Input: CMS ZeroBias Run2016G NanoAOD open data (CC0-1.0); 67/67 files; remote read via XRootD.
- Sample: n = 5,211,771 qualifying events; 41,694,168 bits.
- Certified output entropy: 7.8413 bits/event (98% of the b = 8 ceiling); Clopper–Pearson
  upper bound with Bonferroni correction, alpha = 1e-6.
- Extractor definition: per event, leading-jet azimuth (maximum pT); |eta| < 2.5;
  pT > 20 GeV; 256 uniform bins; MSB-first packing; one byte per event at b = 8.
- Quality gates: KS 67/67; NIST STS zero flags over the full 41.7 Mbit stream.
- Systematic effect: localized acceptance deficit of −10.5% (bins 227–234,
  phi ≈ +139°..+150°), stable across all 67 files and terciles, unchanged under
  tight-jetId selection. The entropy bound absorbs this effect conservatively;
  details are reported in the companion paper.

## Repository layout

- `phase0_extract.py` — extractor P (reference implementation).
- `phase0_extract_v1_1.py` — round-2 variant with corrected tight-jetId bitmask test
  (`(jetId & 2) == 2`).
- `phase0_extract_legacy-f8622c70.py` — pre-R3 frozen bytes (round-1 manifests record this
  `code_sha256`).
- `phase0_verify.py` — independent manifest re-check (hashes, entropy recomputation, gates).
- `xrd_*.py`, `*.sh` — XRootD pipeline: batch extraction, resumable file fetch with
  watchdog, portal reconciliation (adler32), provenance, aggregation.
- `twin/` — C++/ROOT twin of the extractor (bit-identical target), edge-case battery,
  and single-command runner.
- `runG/`, `runG2/`, `refix-2026-10-16/` — evidence: per-file manifests, bit outputs,
  checksums, aggregates, round-2 sample, R3 re-verification and twin battery outputs.
- `mc/` — Pythia8 command cards and prediction-side evidence; large `.root` files are
  excluded and are regenerated from the cards.

## Reproduction procedure

```bash
pip install uproot awkward scipy numpy fsspec xrootd fsspec-xrootd   # use a mirror that carries xrootd
python3 xrd_run.py phase0_extract.py --files uris-local-f01.txt --out out/f01 --pt-min 20
python3 phase0_verify.py out/f01.manifest.json
```

Prerequisites: battery cells 1–3 require large inputs that are not stored in this
repository — `data/nano_data2016_1-1.root` (CMS Open Data; file list in
`uris-local-f01.txt`, fetch tooling in `xrd_fetch_resume.py`) and
`mc/minbias_delphes.root` (regenerate with `mc/minbias.cmnd`: Pythia8 8.317 with the
Delphes CMS card). Cells 4–5 are self-contained; cells with missing inputs are skipped
with an explanatory message.

C++/ROOT twin (ROOT 6.40.04 from CVMFS; the script configures the required environment
settings listed below):

```bash
bash twin/twin_run.sh
```

The battery compares the twin against the frozen Python reference outputs, byte by byte:

| Cell | Scope | Criterion | Result |
|---|---|---|---|
| 1 | f01, b = 8, real data | identical to `runG/f01.bits.bin` (sha256 `6bc096b7…`) | pass |
| 2 | f01, b = 5 | residual-bit path (6 residual bits discarded) | pass |
| 3 | MC Delphes, b = 5 | prediction-side tree | pass |
| 4 | Edge cases | pT ties (first-maximum selection), NaN masking, exact bin edges (±1 ULP), ±π clamp | pass |
| 5 | NaN-phi input | both implementations reject (Python exception; twin exit code 3) | pass |

## Environment configuration

The following settings are required; they are configured in `twin/twin_run.sh` and were
established during commissioning:

- LCG ROOT's Cling startup probes `x86_64-linux-gnu-g++-11` (the compiler name recorded
  by the LCG build). Without it, interpreter creation fails; a symlink to the system
  C++ compiler under that name resolves this.
- ROOT external libraries (TBB, PCRE2) are not included in `root-config --libs`; their
  LCG release paths must be added to `LD_LIBRARY_PATH` at link and run time.
- CVMFS lazy loading of `.pcm` and `.so` files can stall on mmap page faults; a one-time
  prewarm of the ROOT library directory is required (command in the script header).
- XRootD: URIs require the `root://host//eos/...` form (double slash); XRootD 6.x
  pybind11 rejects numpy integer types — the adapter `xrd_compat.py` handles this.
- uproot >= 5.7: classic TTree output requires `wf.mktree(name, {col: "var * float32"})`
  followed by `.extend()`; plain dict assignment produces an RNTuple.

## Evidence and integrity

Each reported number is traceable to a per-file manifest containing the run parameters,
`code_sha256`, `bits_sha256`, and gate results. The evidence directories `runG/`,
`runG2/`, `refix-2026-10-16/`, and `mc/` contain `SHA256SUMS` files (400 entries total).
Verification: `cd <dir> && sha256sum -c SHA256SUMS`.

Input data: CMS Open Data (CC0-1.0). Large input files are not stored in this repository.

## License

MIT (see `LICENSE`). Companion repository:
[vmc-rsep-xmss](https://github.com/qBucker/vmc-rsep-xmss) (monotone accountability / VMC).

