# Herwig++ minimum-bias prediction-side sample — result

Run: 2026-10-21, 8 chunks x 50,000 events, seeds 20261101-20261108.
Prediction card: `predictions/2026-10-21-herwig-minbias.md` (commit `500f375`).

## Sample and pipeline

- Generator: Herwig++ 2.7.1 (CVMFS LCG `herwigpp/2.7.1-da362/x86_64-slc6-gcc49-opt`),
  minimum-bias model MEMinBias, pp at 13 TeV, shipped tune parameters.
- Detector: Delphes 3.5.1, CMS card `delphes_card_CMS.tcl` (sha256
  `e363da8be306a024159b52547a80045bc48b770424fb5372ffc2ff8f1f5028c0`), `DelphesHepMC2`.
- Extractor: `phase0_extract.py` (sha256 `9272d4df...`), `--pt-min 20`, b = 8,
  |eta| < 2.5, no jetId requirement. The extractor ran once on the merged 9.6 GB file.
- Merged Delphes file: sha256 `070a5a0d18b54da0f6f3cfe2be32c939ac494723c3a26f19eb66173ea5b2de53`
  (10,281,525,040 bytes).

## Result against the card

| Quantity | Card | Measured | Verdict |
|---|---|---|---|
| selected events | — | 5,791 | — |
| acceptance | [0.9%, 1.7%] | **1.448%** | pass |
| chi-square gate | p > 1e-6 | p = 0.869 | pass |
| KS gate | p > 1e-6 | p = 0.546 | pass |
| h_min (CP+Bonferroni) | [5.5, 6.5] bits | **6.0972** | pass |
| uniform null at n=5,791 | — | median 6.097 (5-95%: 6.002-6.174) | at the median |
| seam band ratio (bins 227-234) | 1.00 +- 0.20 | **1.0177 +- 0.0790** | pass |
| PYTHIA reference band ratio | — | 0.9357 +- 0.0777 (n=5,430) | — |
| total bits | — | 46,328 (= 5,791 x 8) | — |

No outcome falls outside the pre-registered intervals. The prediction side is
generator-independent within the measured precision: the Herwig sample reproduces the
uniform azimuth, the finite-sample min-entropy curve, and the absence of the CMS seam
(Delphes has no phi segmentation, as expected).

## Timing

- Generation: 198.7 s per 50k chunk (~250 events/s); Delphes: 85.5 s per chunk.
- Merge (`hadd`, 8 files): 21 s; extraction: 60 s.

## Files

- `mc_hpp_400k.manifest.json`, `mc_hpp_400k.bits.bin` (sha256 `b915ef7e...`), `evaluation.txt`.
- `driver.log`, `extract.log`, `hadd.log`, `logs/` (per-chunk generator and Delphes logs),
  `SHA256SUMS`.
- The merged Delphes ROOT file (9.6 GB) is kept locally, not in the repository; its hash is
  recorded above and in the manifest.
