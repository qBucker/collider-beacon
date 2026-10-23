# E2 lattice-aligned pre-registration — amendment 3

- Timestamp: **2026-10-24T01:49:35+08:00** (signed calibration frozen; this
  amendment is committed immediately after, before unblinding)
- Base: amendment 2, sha256
  `61f630692b5de7c67d0369e791220b55a93fe819dcd8dfe95f878f5492482da6`
- Status: the main batch is running. **No pooled real-data histogram or entropy
  estimate has been read.** Only the f01 precheck (D5) and per-file
  leading-jet counts have been logged.

## Reason for this amendment

The card mixed two variable conventions:

- the paper's b=8/b=12 measurement and the A-controls use **signed phi**
  (`bits_of_phi`: `u = (phi + pi) / (2 pi)`), whose storage-lattice floor is
  **13.65**;
- the C/S arms use **folded |phi|** (`empirical_abs`), whose floor is **12.65**.

For a symmetric source the fold is a 2-to-1 map, so
`h_inf(folded) = h_inf(signed) - 1`. The card's "zero gain 11.31" applied the
signed b=12 value to a folded arm. The paper's 13.65 is **correct for the
signed variable it actually measures**; the "erratum" (13.65 -> 12.65) is a
convention mismatch, not an arithmetic error. The erratum is withdrawn.

## Decision

**A: signed phi is canonical.** The source model is Haar on the circle; the
paper, the A-controls, and the 7.8413/11.3098/13.65 numbers are all signed; the
sign bit is real entropy. Folded |phi| is retained only as a pipeline
self-check.

## Code changes

`diagnostics/lattice_alpha.py`, sha256
`028ec857c81563b83221fcc7e0c96db85e0f765638ad0ccf6c0ce84de01d1486`:

1. `empirical_abs` -> `empirical_signed` (C arm and two-stage).
2. The synthetic arm draws `uniform(-pi, pi]`, quantizes signed.
3. `B_REF = 78,400` (signed; 10-seed `B_eff` 78,210-78,530);
   `B_REF_FOLDED = 39,200` for the self-check only.
4. Folded self-check added: `h_inf(folded) - h_inf(signed)`, both raw
   max-atom and CP.
5. Split rule unchanged: seeded random interleave, `split_seed = 20261023`.

## 10-seed signed calibration (synthetic only; no real data)

Command:
`python3 diagnostics/lattice_alpha.py --synthetic-only --synthetic-seeds 10 --out predictions/2026-10-23-e2-synthetic-calibration-10seed-signed.json`

Seeds 20261023-20261032, n = 5,211,771 per seed.

- `B_eff`: 78,210-78,530 (mean 78,370).
- **S1: mean 12.9857, sd 0.0124, 2-sigma band [12.9609, 13.0106].**
- **S2: mean 13.2383, sd 0.0711, 2-sigma band [13.0962, 13.3804].**
- Point values: S1 12.986; S2 13.238.

## Folded self-check (synthetic calibration)

- Raw max-atom difference: mean **-0.9312**, sd 0.0242, 2-sigma
  **[-0.9796, -0.8828]**.
- CP difference: mean **-0.8147**, sd 0.0214, 2-sigma
  **[-0.8576, -0.7718]**.

The distribution-level relation is exactly -1 bit; the estimator-level
difference is smaller in magnitude because the folded max atom is twice as
large (`n p = 810` vs 405), so the CP penalty is smaller. The TARGETS v2
acceptance "`-1.00 +/- 0.02`" is a distribution-level statement and cannot be
met by the CP estimator. The self-check acceptance band is the synthetic
2-sigma interval above. This correction is recorded before unblinding.

## Amended bands (supersede amendment 2)

- **S1: [12.9609, 13.0106]** (was [12.1369, 12.2129], folded).
- **S2: [13.0962, 13.3804]** (was [12.1774, 12.4538], folded).
- **Zero gain: 11.31 +/- 0.02** (signed-vs-signed).
- **Better: S1 > 13.2 or S2 > 13.38** (above the synthetic 2-sigma upper band).
- **Worse: S1 < 12.0** (an octave coarser).
- Gain over linear b=12: **+1.67 bit** (S1: 11.31 -> 12.99); **+1.93 bit**
  (S2: 11.31 -> 13.24).

## B_eff normalization

Both judgment arms use the signed `B_ref = 78,400` in `alpha/B`. The measured
real `B_eff` is reported next to `B_ref`; a real `B_eff` smaller than `B_ref`
makes the bound more conservative. The folded self-check uses
`B_ref_folded = 39,200` and reports its own `B_eff`.

## Frozen judging order

0. **Integrity gate** (`diagnostics/lattice_integrity.py`): all 67 manifests
   pass (size = 4 n, sha256 match, finite values in range, duplicate and
   orphan checks). Do not proceed on any failure.
1. All 67 manifests present; pooled n = 5,211,771 (or missing files documented).
2. **A-controls**: b=8 = 7.8413 +/- 0.02, b=12 = 11.3098 +/- 0.02, b=12 beat
   fingerprint 7.06 bins / 581 cycles / lag-7 autocorrelation 0.836.
3. Write the analysis JSON **before** drawing any figure.
4. Judge C/S1 and S2 against the signed bands above.
5. **Folded self-check**: the CP difference must lie in
   [-0.8576, -0.7718]; the raw difference in [-0.9796, -0.8828]. A failure
   means a pipeline `abs`/type bug, not physics.
6. Report the section 7.2 numbers: **13.65** (signed floor), **12.99**
   (single-stage), **13.24** (two-stage), and the measured value; the
   non-lattice excess is `12.99 - h_inf(real)` (signed-vs-signed).

## What is not amended

- Estimator definitions: single-stage Clopper-Pearson with Bonferroni (S1);
  split-half Clopper-Pearson without Bonferroni (S2).
- The integrity gate and the A-controls.
- The zero-gain branch semantics (now signed-vs-signed).
- The data product: raw **signed** float32 bit patterns; no re-extraction is
  needed.

## Amendment declarations

1. The batch was launched 2026-10-23 21:06 CST; no pooled real-data histogram
   or entropy estimate has been read. Only the f01 precheck and per-file
   leading-jet counts are logged.
2. The estimator definitions are unchanged; only the variable convention
   (signed vs folded) and the folded self-check are fixed.
3. The new bands come from synthetic data only (10 seeds); the real data is
   untouched.
4. This amendment's SHA256 sidecar and commit timestamp precede unblinding.
