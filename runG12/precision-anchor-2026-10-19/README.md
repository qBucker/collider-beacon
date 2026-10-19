# Precision anchor for the b=12 storage floor (2026-10-19)

Purpose: anchor the mechanism statement "12 explicit mantissa bits" to measurable metadata and
upstream data. The statement is a measurement on the public files, not a quoted specification.

## Findings

- **File and branch compression are lossless.** The NanoAOD file (CERN Open Data record 31316)
  reports compression settings 209 at file level and for every checked branch
  (`TFile::GetCompressionSettings`, `TBranch::GetCompressionSettings`, ROOT 6.40.04);
  209 decodes to LZMA level 9.
- **Stored float branches carry reduced mantissas.** For the sampled entries:
  `Jet_phi`, `Jet_eta`, `MET_phi`, `Electron_phi`, `Muon_phi`, `Photon_phi` have at least
  11 trailing zero mantissa bits for 100% of values (12 explicit mantissa bits, 13 significant
  bits); `Jet_pt` and `Jet_mass` have at least 13 (10 explicit bits, float16-equivalent);
  `MET_pt` is full float32.
- **The upstream MiniAOD file is full precision.** The `pat::Jet` four-vector components in
  CERN Open Data record 30516 have minimum trailing-zero count 0 for all components.
- **The production configuration sets no precision option.** Record 12504
  (`PFNanoProducerTool`, `pfnano_data_2016UL_OpenData.py`, lines 48-49) sets
  `compressionAlgorithm = LZMA`, `compressionLevel = 9` only.

Conclusion: the rounding is applied by the NanoAOD production layer; it is neither ROOT
compression nor an upstream MiniAOD property. No public format document specifying the rule was
found in the sources consulted.

## Reproduce

```bash
python3 check_nanoad_precision.py <nanoaod.root> 8000
python3 check_miniaod_precision.py <miniaod-xrootd-uri> 3000
root -l -b -q 'check_compression_settings.C("<nanoaod.root>")'
```

Captured outputs: `nanoaod_precision.txt`, `miniaod_precision.txt`, `compression_settings.txt`.

## References

- Dataset: https://opendata.cern.ch/record/31316
- Upstream MiniAOD: https://opendata.cern.ch/record/30516
- Production software: https://opendata.cern.ch/record/12504
- Production configuration: https://github.com/cms-opendata-analyses/PFNanoProducerTool
