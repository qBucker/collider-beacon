# Prediction card — herwig-minbias-13TeV

- Date (UTC): 2026-10-21
- Author: Junchen Zhu
- Run / sample: Herwig++ 2.7.1 minimum-bias sample (MEMinBias, Gieseke–Kirchgaesser–Loshaj soft-interaction model), pp collisions at 13 TeV, 400,000 events produced in 8 chunks of 50,000 with fixed seeds 20261101–20261108. Generator build: CVMFS LCG `herwigpp/2.7.1-da362/x86_64-slc6-gcc49-opt`; repository file relocated locally (the shipped `.rpo` names a non-existent `MCGenerators/herwig++/2.7.1-da362` path; only that path prefix is corrected). Detector simulation: Delphes 3.5.1 with the CMS card used for the PYTHIA reference sample (`cards/delphes_card_CMS.tcl`, sha256 `e363da8be306a024159b52547a80045bc48b770424fb5372ffc2ff8f1f5028c0`), via `DelphesHepMC2`.
  - Revision note (pre-run): the seed range was changed from 20261021–20261028 to 20261101–20261108 before the production run, so the formal sample is disjoint from the 10,000-event engineering smoke (seed 20261021). No formal events existed when this revision was committed; the earlier card commit is `3d7a9b7`.
- Analysis code: `phase0_extract.py`, sha256 `9272d4dfb2d420cb7cc46ef156c6f179161da8c023b11d34fa76b9c48f4d1f3e`, invoked with `--mc <merged Delphes file> --out mc_hpp_400k --pt-min 20` (b = 8, |η| < 2.5, no jetId requirement).
- Status: frozen (committed before the 400,000-event sample exists)

## Predictions (fixed before data inspection)

1. **Jet acceptance.** The fraction of generated events with at least one jet passing pT > 20 GeV and |η| < 2.5 is predicted to lie in **[0.9%, 1.7%]**, central value approximately 1.2%. Basis: a 10,000-event engineering smoke of the same chain gave 121/10,000 = 1.21%; the PYTHIA 8.317 reference sample gives 1.29% at 100k events and 1.36% at 400k events.
2. **φ uniformity.** The leading-jet φ distribution over 256 equal-width bins is predicted to pass the extractor's χ² gate (p > 1e−6) and KS gate, with no structure beyond finite-sample fluctuations. Basis: the partonic azimuth is isotropic and the Delphes response is φ-symmetric.
3. **Finite-sample min-entropy.** At the expected n ≈ 4,800 selected events, the pooled per-event min-entropy (Clopper–Pearson upper bound on the maximum bin probability, Bonferroni α = 1e−6 over 256 bins) is predicted to lie in **[5.5, 6.5] bits**. Basis: the PYTHIA reference points are 4.8437 bits at n = 1,289 (100k sample) and 6.0554 bits at n = 5,430 (400k sample); the same estimator applied to uniform samples of matched size gives the scaling between them.
4. **Seam band (pipeline check).** The ratio of the summed counts in bins 227–234 (φ ≈ +139°..+150°, the CMS-specific deficit region) to a ±32-bin sideband baseline is predicted to be **1.00 ± 0.20** (two standard deviations). Statistical note: at n ≈ 4,800 the band contains ≈ 150 events, so the ratio has a statistical uncertainty of ≈ 9%; this check is a pipeline consistency test and has limited power to exclude a 10% deficit (≈ 1.2σ).
5. **Gate pattern.** χ² and KS are predicted to pass; the finite-sample h_min is below 10 bits by construction (b = 8 ceiling is 8 bits; sample size limits the bound further). No claim of a ≥ 10-bit gate is made for this sample.

## Analysis choices (fixed)

- Bins: 256 equal-width bins over φ ∈ (−π, π], b = 8, MSB-first packing, 8 bits per event.
- Selection: leading jet, maximum pT, |η| < 2.5, pT > 20 GeV; no jetId requirement (identical to the PYTHIA sample).
- Estimator: Bonferroni-corrected Clopper–Pearson upper bound on the maximum bin probability, α = 1e−6 over 256 bins.
- Pooling: all chunks merged into one Delphes ROOT file (`hadd`); the extractor runs once on the merged file.
- Generator settings: every tune parameter at the shipped `LHC-MB.in` default except the beam energy, set to 13 TeV (the shipped card sets 8 TeV); fixed seeds; no event filtering.
- Sample size and stopping rule: exactly 8 × 50,000 events; no early stopping and no re-generation based on results.
- Engineering smokes (1,000 and 10,000 events) were run before this card to validate the chain. Their numbers are disclosed above and are not part of the formal sample.

## Decision rule

- All gates pass and acceptance in [0.9%, 1.7%] → the Herwig cell is reported as consistent with the uniformity prediction; the prediction side is generator-independent within the measured sample.
- χ² or KS gate fails → reported as such and investigated before any claim; no re-analysis of the formal sample beyond the declared diagnostics.
- Seam-band ratio outside [0.80, 1.20] → reported as a pipeline inconsistency requiring investigation.
- Acceptance outside [0.9%, 1.7%] → reported as a generator-model difference; the uniformity conclusion is not adjusted.
- Any outcome outside the stated intervals is reported as such.

## Post-hoc notes (append only after the run)

- Result manifest: `mc/herwig/run400k/mc_hpp_400k.manifest.json` (sha256
  `56bfef1bd37ffc7264cfab9dd03709377c9d203939f3c93bf89700518ebf44b6`); bits
  `mc_hpp_400k.bits.bin` (sha256 `b915ef7e6a98572c7e46362121a1c892962dcdb5cd91d64e7a1419e560cb4ae3`).
  Merged Delphes file sha256 `070a5a0d18b54da0f6f3cfe2be32c939ac494723c3a26f19eb66173ea5b2de53`
  (9.6 GB, kept locally, not committed).
- Outcome versus prediction:
  1. **Acceptance 1.448%** (5,791/400,000) — inside [0.9%, 1.7%].
  2. **chi-square p = 0.869, KS p = 0.546** — both gates pass; no structure beyond
     finite-sample fluctuations.
  3. **h_min = 6.0972 bits** — inside [5.5, 6.5]; the uniform-sample null at n = 5,791 has
     median 6.097 (5-95%: 6.002-6.174), so the measurement sits at the null median.
  4. **Seam-band ratio 1.0177 +- 0.0790** — inside 1.00 +- 0.20; the PYTHIA reference at
     n = 5,430 gives 0.9357 +- 0.0777. Both are consistent with the phi-symmetric Delphes
     response.
  5. **Gate pattern as predicted** — chi-square/KS pass; h_min is below 10 bits by
     construction at b = 8 and this n.
- No outcome falls outside the stated intervals. The cell is reported consistent with the
  uniformity prediction; the prediction side is generator-independent within the measured
  precision.
- Seeds 20261101-20261108 (8 x 50,000); generator 198.7 s per chunk, Delphes 85.5 s per
  chunk, merge 21 s, extraction 60 s. Evidence: `mc/herwig/run400k/`.
- 2026-10-26 (R4): path fields in this manifest were normalized to repository-relative
  paths; the payload hashes above are unchanged. The manifest now hashes to
  `15c617068b88d38ac9fd3e8207f5d7f46af91bd2e27f391129339c651a43e175` (previous
  `56bfef1b…` retained above as the as-run record). See the R4 ledger entry in `README.md`.
