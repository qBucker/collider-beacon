# Collider Beacon — Phase 0 Engineering

Engineering stack for the Collider Beacon project: certified public randomness from
symmetry and quantum measurement. Phase 0 covers the complete processing chain from
CMS Open Data to audited random bits, including a bit-identical dual implementation
(Python and C++/ROOT) and a complete evidence record.

## Citation

J. Zhu, *The Collider Beacon: Certified Public Randomness from Symmetry and Quantum Measurement*, Zenodo preprint (2026). Version DOI [10.5281/zenodo.23434446](https://doi.org/10.5281/zenodo.23434446); concept DOI [10.5281/zenodo.23434445](https://doi.org/10.5281/zenodo.23434445).

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
- Cross-detector check (2026-10-17): ATLAS Open Data record 93933 (Run 2 2015+2016,
  no skim, CC0-1.0), 16 files, n = 597,965 events, same extractor and binning. The
  CMS −10.5% band does not reproduce: ATLAS local band ratio 1.0024 ± 0.0072; the CMS
  value is excluded at 14.1σ (pooled, conservative estimator comparison). The ATLAS
  sample carries a broad +2.4% acceptance modulation instead. Details:
  `atlas/RESULTS-2026-10-17.md`.
- Symbol-level dependence and stationarity audit (2026-10-23): lag-k mutual information
  0.0090 bits, identical to the shuffled-series floor; 3/67 per-file certified h_min
  outside the 2.5–97.5% uniform-null band, all below by 0.003–0.015 bit; block-wise MCV
  matches the uniform null. Details: `diagnostics/dependence-2026-10-23.txt`.

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
- `atlas/` — cross-detector check on ATLAS Open Data: adapter, parallel-range HTTP source
  (EOS 307 redirect + 16 connections), sample URL lists, result manifest and bits.
- `predictions/` — pre-registered prediction cards, committed before official runs.
- `diagnostics/` — symbol-level dependence and stationarity audit of the b = 8 run
  (lag-k mutual information, per-file certified h_min against the same-n uniform null,
  block-wise MCV), with its result file and checksums.

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
  Direct `XRootD.client.File.read()` calls were observed to hang in this environment;
  reads go through the fsspec-xrootd layer, the same path used by uproot.
- uproot >= 5.7: classic TTree output requires `wf.mktree(name, {col: "var * float32"})`
  followed by `.extend()`; plain dict assignment produces an RNTuple.

## Evidence and integrity

Each reported number is traceable to a per-file manifest containing the run parameters,
`code_sha256`, `bits_sha256`, and gate results. The evidence directories `runG/`,
`runG2/`, `refix-2026-10-16/`, and `mc/` contain `SHA256SUMS` files (400 entries total).
Verification: `cd <dir> && sha256sum -c SHA256SUMS`.

Extractor revision ledger: R1 = tight-jetId bitmask test (`(jetId & 2) == 2`; round-2
variant only). R2 = gate-label fix in `phase0_verify.py` (logic unchanged). R3 =
parameter-derived manifest description string; default `--pt-min` = 20.0. The algorithm is
unchanged across R1–R3; re-verified bit-for-bit (`refix-2026-10-16/f01.bits.bin` matches
`runG/f01.bits.bin`, sha256 `6bc096b7…`). `code_sha256` lineage: round-1 manifests
`f8622c70…` (frozen bytes: `phase0_extract_legacy-f8622c70.py`); current `9272d4df…`.

Input data: CMS Open Data (CC0-1.0). Large input files are not stored in this repository.

## License

MIT (see `LICENSE`). Companion repository:
[vmc-rsep-xmss](https://github.com/qBucker/vmc-rsep-xmss) (monotone accountability / VMC).

