# E2 lattice-aligned pre-registration — amendment 1

- Timestamp: **2026-10-23T21:35:39+08:00** (before unblinding)
- Base card: E2 experiment card v1 (2026-10-23), prediction 12.36 ± 0.05
- Status: the main batch is running; no real-data histogram has been read.

## Reason for the amendment

The synthetic truth arm (uniform |phi| quantized to the same 12-bit lattice and
run through the same estimator) gives 12.18, not 12.36. The difference is the
max-bin selection: the empirical alphabet takes the maximum over about 2,338
coarse-octave values, so E[max count] ≈ n p + sqrt(2 n p ln m) = 810 + 112 = 922,
not the per-value n p = 810. The card's 12.36 was a per-value ideal; the
estimator's zero-hypothesis ceiling is 12.18.

## Amendment statements

1. The `phase0-lattice` batch was launched 2026-10-23 21:06 CST. At this
   amendment no real-data histogram has been read or analyzed; only the
   leading-jet counts of f01 (23,006) and f02 (34,023) have been logged.
2. The main arm S1 estimator is unchanged: single-stage Clopper–Pearson with
   Bonferroni over the empirical alphabet. Only the predicted value and band
   are amended: **12.18, band [12.05, 12.30]**.
3. A second arm S2 is added: split-half (select the mode on n/2, certify on the
   other n/2 with CP at alpha, no Bonferroni). Point **12.31, band [12.20,
   12.42]**. The synthetic arm gives 12.27, inside the band.
4. This amendment's SHA256 sidecar and the commit timestamp precede
   unblinding; the commit is the time anchor.

## Three-layer decomposition

| quantity | value | meaning |
|---|---|---|
| lattice floor | **12.651** | -log2(2^-11/pi); distribution property, estimator-independent |
| single-stage ceiling | **12.18** | synthetic-arm output; 0.47 bit below the floor: winner's curse 0.16 + CI 0.31 |
| two-stage (n/2) | **12.31** | removes the curse, pays sqrt(2) in CI; synthetic 12.27 |
| two-stage (n1->0, null only) | 12.41 | not an arm; zero-null limit |

The real-data excess is `12.18 - h_inf(real)`: the non-lattice excess,
attributable to the seam and physics modulation. Zero gain (11.31) means
0.87 bit of non-lattice excess.

## Outcome bands

| outcome | criterion |
|---|---|
| confirm S1 | h_inf(C) in [12.05, 12.30] |
| S2 | h_inf(C2) in [12.20, 12.42] |
| zero gain | h_inf(C) ≈ 11.31 ± 0.02 (production pre-quantization) |
| better | h_inf(C) > 12.40 or h_inf(C2) > 12.42 |
| worse | h_inf(C) < 11.9 (an octave coarser than 2^-11) |

## f01 inclusion and f03 retry

`latticeG/f01.lattice.bin` contains 23,006 full uint32 patterns (not just
counts), written by the remote f01 extraction. The batch skips f01 because its
manifest exists, but the pooled glob includes it. f03 timed out in the main
batch (900 s); retry unit `phase0-lattice-retry-f03` runs with a 2400 s
timeout. No analysis result is final until all 67 manifests exist and the
pooled n = 5,211,771 (or missing files are documented).

## Cross-checks

- b=12 linear must reproduce 11.3098 ± 0.02.
- b=8 linear must reproduce 7.8413 ± 0.02.
- b=12 beat fingerprint: 7.06-bin period, 581 cycles/circle, lag-7 ≈ 0.836.
- Any failure invalidates the E2 conclusions.

## Synthetic arm results

Single-stage seed 0/1/2: 12.186 / 12.182 / 12.169. Two-stage seed 0: 12.272.
