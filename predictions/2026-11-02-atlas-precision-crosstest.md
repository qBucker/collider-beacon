# ATLAS precision cross-test — pre-registered predictions (2026-11-02)

Written **before** the precision scan of the ATLAS sample. The arrays existed
since 2026-10-17 (effect-1 smoke), but no octave or floor measurement has been
run on them. Prior exposure: the arrays were loaded once to verify the count
(597,965); the first three values were printed and appear full precision.
This is consistent with P1 but is not the measurement.

## Question

Is the 12-bit mantissa lattice a CMS product choice, or a HEP-wide storage
convention? The precision passport needs a cross-product test: the same audit
on a product from a different experiment.

## Data

- 16 arrays `*.phis.npy` from `beacon-paper/phase0/atlas/smoke2.partial/`
  (ATLAS Open Data record 93933, CC0-1.0; CERN Open Data DOI
  10.7483/OPENDATA.ATLAS.VV3I.0WJE).
- Each array: leading-jet azimuths (pT > 20 GeV, |eta| < 2.5) from the first
  50,000 entries of one file; stored as float64, exact conversions of the
  delivered float32 values.
- Total n = 597,965 (matches `atlas/smoke2.manifest.json`).
- Caveat: the sample is trigger-selected and not random; precision is a
  storage property and is expected to be selection-independent.

## Predictions

- **P1 (mantissa count).** ATLAS `jet_phi` is full float32: the smallest
  `b` in 8..24 with an on-grid fraction >= 0.999 in the coarsest octave is
  22 or 23 (the float32 mantissa has 23 explicit bits). At b = 12 the
  on-grid fraction is <= 0.01 (CMS: 1.0000).
- **P2 (no lattice freeze).** The certified floor does not freeze below
  b = 14: `h_floor(14) - h_floor(12) >= 0.5` bit and
  `h_floor(16) - h_floor(14) >= 0.5` bit (CMS: 1.63 and +0.0004, frozen).
- **P3 (sample boundary).** The observed boundary is the sample boundary:
  the model's `b_stat` (inflation epsilon = 1) lies in [11.5, 14.0], and
  `b_stat - log2(n)` lies in [-7.8, -5.8] (CMS: -6.78 at n = 5.2M).
- **P4 (eta model).** With `M` calibrated at b = 8 only, the closed-form
  model predicts `h_floor(b)` for b = 9..16 to within 0.10 bit (CMS lead:
  0.035; CMS secondary vertices: 0.073).
- **P5 (eta value).** `eta(12) in [0.73, 0.84]`; the model prediction with
  the calibrated `M` is the point value.

## Gates

- G1: all 16 arrays load; no missing file.
- G2: n = 597,965 exactly.
- G3: a rerun reproduces the JSON byte-for-byte.
- G4: the octave scan covers e = -8..1 with at least 30 unique values per
  octave, as in the CMS measurement.

## Falsification

Every prediction is reported as measured. The decisive case is P1/P2: if the
ATLAS product is also a 12-bit lattice (P1 fails, P2 fails), the "CMS
product choice" interpretation is wrong and the lattice is a
collaboration-wide storage convention; the lattice constant `log2(pi)` is
then a property of the open-data format family, not of one product.

If P3 fails (the boundary is not the sample boundary), the two-boundary model
of `eta-closed-form-2026-11-02.md` is falsified for full-precision products.

## Run

`python3 diagnostics/atlas_precision_test.py --glob '<path>/*.phis.npy'`
(writes `diagnostics/atlas-precision-2026-11-02.json`). Results appended
below after the run.

## Results (appended 2026-11-02, after the run)

Data: 16 arrays, n = 597,965, all loaded (G1, G2 PASS). Deterministic rerun
byte-identical (G3 PASS). Octave scan covered e = -8..1 with >= 30 unique
values (G4 PASS). Full record: `diagnostics/precision-eta-result-2026-11-02.md`.

| id | measured | verdict |
|---|---|---|
| P1 | b = 23 in every octave; on-grid(b=12) = 0.00222 | PASS |
| P2 | h(14)-h(12) = 1.236; h(16)-h(14) = 0.799 | PASS |
| P3 | b_stat = 12.62; b_stat - log2 n = -6.57 (CMS -6.78) | PASS |
| P4 | max abs dh = 0.0924 bit (threshold 0.10) | PASS |
| P5 | eta(12) = 0.8022 | PASS |

Model with b_m = 23 (the measured mantissa count): b_lat = 24.651,
b_star = b_stat = 12.62. The observed boundary is the sample boundary, as
predicted; the CMS product freezes on its 12-bit lattice instead.

Note on P4: the first model run used b_m = 12 (the CMS value) by mistake and
residuals reached 1.0 bit at b = 15-16; parameterizing b_m to the measured 23
reduced the maximum residual to 0.0924 bit. The near-miss margin (0.008 bit)
is recorded as measured.
