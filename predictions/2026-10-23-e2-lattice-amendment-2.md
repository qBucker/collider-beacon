# E2 lattice-aligned pre-registration — amendment 2

- Timestamp: **2026-10-23T21:44:58+08:00** (calibration artifact frozen; this
  amendment is committed immediately after, before unblinding)
- Base: amendment 1, sha256
  `59eaf953f2130c3ce42e766209f9759b7f734b87d963161894128e325909cb35`
- Status: the main batch is running. No real-data histogram or entropy estimate
  has been read. Only per-file leading-jet counts (f01-f05) have been logged.

## Reason for this amendment

Amendment 1 fixed the outcome bands from one synthetic seed. The estimator has
seed-to-seed sampling noise, so the bands are now the mean +/- 2 standard
deviations of ten independent synthetic runs. In addition, the real-data
empirical alphabet can have a different size B_eff from the synthetic one; the
Clopper-Pearson penalty is therefore fixed at one reference alphabet B_ref for
both arms, so that a smaller real B_eff cannot inflate the result.

## Calibration record

- Command:
  `python3 diagnostics/lattice_alpha.py --synthetic-only --synthetic-seeds 10 --out /tmp/e2-synthetic-calibration.json`
- Analysis script sha256:
  `4cbe32f7e8f35471762e35f5585009753058338808eb8ee18cc237512487aca9`
  (`diagnostics/lattice_alpha.py`)
- Seeds: 20261023 through 20261032 (10 seeds), n = 5,211,771 per seed
- Split rule: seeded random interleave, split_seed 20261023 (a permutation of
  the sample, not sequential halves)
- Fixed reference alphabet: **B_ref = 43,363**
- Synthetic B_eff over the ten seeds: 43,220 to 43,393 (mean 43,287.8, median
  43,277.5)

| arm | 10-seed mean | 1 sigma | 2 sigma band |
|---|---|---|---|
| S1 single-stage CP + Bonferroni | **12.1749** | 0.0190 | **[12.1369, 12.2129]** |
| S2 split-half CP, no Bonferroni | **12.3156** | 0.0691 | **[12.1774, 12.4538]** |

Per-seed S1: 12.186, 12.169, 12.178, 12.180, 12.165, 12.130, 12.169, 12.182,
12.198, 12.193.
Per-seed S2: 12.287, 12.420, 12.309, 12.263, 12.451, 12.236, 12.318, 12.257,
12.312, 12.303.

The S2 band is wider because the split-half certificate uses n/2 = 2,605,886
events and the selected mode is itself random. A real S2 outside the S1 band is
not, by itself, evidence against the lattice model.

## Amended bands (supersede amendment 1)

- **S1: [12.1369, 12.2129]** (was [12.05, 12.30])
- **S2: [12.1774, 12.4538]** (was [12.20, 12.42])

The pre-registered point values remain **12.18** (S1) and **12.31** (S2). The
ten-seed means are 12.1749 and 12.3156, within 0.006 bit of the points. The
reference seed 20261023 gives S1 = 12.186 and S2 = 12.287; the S2 value moved
from the amendment-1 single-seed value 12.272 because the split is now a seeded
interleave rather than sequential halves. The analytic point 12.31 is unchanged.

## B_eff normalization

- The real empirical arm C and the synthetic arm S1 both use **B_ref = 43,363**
  in the Bonferroni factor `alpha/B`.
- The measured real `B_eff` will be reported next to `B_ref`.
- A real B_eff smaller than B_ref makes the bound more conservative. Over the
  synthetic range [43,220, 43,393] the B_ref choice changes h by at most
  0.006 bit.
- The max-bin count is the same measured quantity in both arms; only the
  multiplicity penalty is normalized.

## Frozen judging order

0. Integrity gate `diagnostics/lattice_integrity.py`: all 67 manifests pass
   (size = 4 n_leading, sha256 match, finite values in range, duplicate and
   orphan checks). Do not proceed on any failure.
1. All 67 manifests present; pooled n = 5,211,771 or missing files documented.
2. A-controls: b=8 = 7.8413 +/- 0.02, b=12 = 11.3098 +/- 0.02, b=12 beat
   fingerprint 7.06 bins / 581 cycles per circle / lag-7 autocorrelation 0.836.
3. Write the analysis JSON before drawing any figure.
4. Judge C/S1 and S2 against the amendment-2 bands above.
5. Report the section 7.2 numbers: 12.651 floor, 12.18 single-stage ceiling,
   12.31 two-stage, and 12.18 minus the measured value as the non-lattice
   excess.

## Integrity and provenance notes

- f03 timed out in the main batch at 21:25 (900 s). The retry unit with a
  2400 s timeout completed at 21:39: n = 30,921, manifest present.
- f04 timed out in the main batch at 21:40. A retry unit with a 2400 s timeout
  was launched at 21:44.
- `lattice_extract.py` now writes the lattice file and the manifest through
  atomic `.tmp` files followed by rename, with the manifest last. The numerical
  output is unchanged; only the write ordering changed. Manifests f01-f03 carry
  the old extractor hash `be44f5f4...`; files extracted after the change carry
  `95a6d030...`. The integrity report lists both groups.
- Exit codes from `xrd_batch_lattice.sh` are not trusted (`rc=0` logging bug);
  a file is accepted only on manifest plus sha256 plus the integrity gate.
- f01 is included in the pool. Its raw float32 values are not subject to the
  31-symbol truncation of the b=12 packed stream; every leading jet contributes
  one value.
- Values at |phi| = 3.1416015625 are one storage-lattice step above pi (12-bit
  mantissa, step 2^-11) and are accepted within the gate tolerance; the
  synthetic quantizer produces the same grid point from x near pi.

## What is not amended

- The estimator definitions: single-stage Clopper-Pearson with Bonferroni for
  S1; split-half Clopper-Pearson without Bonferroni for S2.
- The zero-gain branch: h_inf(C) = 11.31 +/- 0.02 (production pre-quantization).
- The better/worse criteria: better if above the upper band; worse if below
  11.9.
