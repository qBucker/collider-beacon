# Herwig++ minimum-bias prediction-side sample

Second-generator cross-check of the Phase 0 prediction side. The reference
sample uses PYTHIA 8.317 (`mc/minbias_400k.cmnd`). This leg produces the same
kind of sample with Herwig++ 2.7.1, passes it through the same Delphes 3.5.1
CMS card, and runs the frozen extractor (`phase0_extract.py`, sha256
`9272d4df...`) on the result. The prediction card is
`predictions/2026-10-21-herwig-minbias.md`.

## Sample

- Generator: Herwig++ 2.7.1, minimum-bias model (MEMinBias,
  Gieseke–Kirchgaesser–Loshaj soft-interaction model), pp at 13 TeV.
- Settings: the shipped `LHC-MB.in` tune parameters with the beam energy set
  to 13 TeV (the shipped card sets 8 TeV), fixed seeds, no event filtering.
- Size: 8 chunks x 50,000 events, seeds 20261101–20261108.
- Detector simulation: Delphes 3.5.1, `cards/delphes_card_CMS.tcl`,
  `DelphesHepMC2` reader.

## Build and relocation notes

The CVMFS LCG build is `herwigpp/2.7.1-da362/x86_64-slc6-gcc49-opt`. Two
defects of that installation are handled locally by
`prepare_herwig_share.sh`:

1. `HerwigDefaults.rpo` stores data and library paths under
   `MCGenerators/herwig++/2.7.1-da362`, but the installation directory is
   `MCGenerators/herwigpp/2.7.1-da362`. The generator then fails to open the
   diffraction PDF tables (`ENOENT` on files that exist). The script copies
   the 11 MB share tree and rewrites only that path prefix.
2. The binary requires `libreadline.so.6`, which the build does not ship. A
   compatibility link to the system readline 8 is created under `compat-libs/`.

`herwig_env.sh` sets the dependency paths explicitly (the LCG wrapper relies
on `lcgenv`, which requires Python 2, absent on the host). The GCC 4.9.1
runtime is taken from the matching LCG compiler release.

The generator and Delphes stages use separate library environments; mixing
the GCC 4.9.1 `libstdc++` with the ROOT build breaks the latter
(`CXXABI_1.9`/`GLIBCXX_3.4.3x` missing). `run_herwig_mc.sh` runs each stage in
a subshell with the appropriate environment and unsets `LD_LIBRARY_PATH` for
the extractor.

## Run

```
bash prepare_herwig_share.sh
bash run_herwig_mc.sh          # 8 x 50,000; reads the prediction card
```

Progress and per-chunk generator/Delphes logs are written to `run400k/` on the run
machine. Intermediate HepMC files are removed after the Delphes step; chunk ROOT
files are merged with `hadd` and removed after a successful extraction. The
repository keeps the result manifest, bit file, evaluation, and checksums, not the
intermediate logs or the merged ROOT file.

## Result

400,000 events produced (8 x 50,000, seeds 20261101-20261108); 5,791 selected jets;
acceptance 1.448%; chi-square p = 0.869, KS p = 0.546; h_min = 6.0972 bits
(uniform-sample null median 6.097 at this n); seam-band ratio 1.0177 +- 0.0790.
All five pre-registered predictions are met. Details in `run400k/RESULT.md` and in
the post-hoc notes of the prediction card.
