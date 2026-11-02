# Non-circular floor scan: result (2026-11-02)

Prediction card: `predictions/2026-11-02-noncircular-floor.md` (commit
`fdfc98c`), written before this run. Code: `diagnostics/noncircular_floor.py`
(same commit). Outputs: `noncircular-pt-2026-11-02.json`,
`noncircular-mass-2026-11-02.json`.

## Data and lattice

| variable | range | n (inside) | excluded | b_m | on-grid |
|---|---|---|---|---|---|
| sv_pt | [1, 50) GeV | 4,468,245 | 596 | 10 | 1.0000 |
| sv_mass | [0.1, 5) GeV | 4,468,299 | 542 | 10 | 1.0000 |

The lattice scan passes P1 for both variables: the storage lattice is
recovered unchanged from the azimuth case, so the lattice audit is
variable-independent.

## Floor model residuals

Signed residual = h_meas - h_pred (positive means the model predicts a lower
floor than measured).

### sv_pt

| b | N_max | h_meas | h_pred | residual |
|---|---|---|---|---|
| 8 | 376,385 | 3.5565 | 3.5565 | 0.000 |
| 9 | 189,123 | 4.5432 | 4.5470 | -0.004 |
| 10 | 96,846 | 5.5004 | 5.5334 | -0.033 |
| 11 | 50,449 | 6.4299 | 6.4865 | -0.057 |
| 12 | 27,067 | 7.3129 | 7.4059 | -0.093 |
| 13 | 15,561 | 8.0931 | 8.2675 | -0.174 |
| 14 | 7,833 | 9.0522 | 9.0367 | +0.016 |
| 15 | 4,021 | 9.9715 | 9.9572 | +0.014 |
| 16 | 4,021 | 9.9692 | 10.3801 | -0.411 |

Max |residual| = 0.411 bit (b = 16). P2 (<= 0.15 bit) fails.

### sv_mass

| b | N_max | h_meas | h_pred | residual |
|---|---|---|---|---|
| 8 | 233,301 | 4.2427 | 4.2427 | 0.000 |
| 9 | 120,833 | 5.1846 | 5.2141 | -0.030 |
| 10 | 61,818 | 6.1411 | 6.1957 | -0.055 |
| 11 | 33,280 | 7.0210 | 7.1707 | -0.150 |
| 12 | 19,136 | 7.8030 | 8.1353 | -0.332 |
| 13 | 12,686 | 8.3801 | 8.8384 | -0.458 |
| 14 | 7,925 | 9.0360 | 9.3894 | -0.353 |
| 15 | 6,502 | 9.3091 | 9.9739 | -0.665 |
| 16 | 6,502 | 9.3073 | 9.9716 | -0.664 |

Max |residual| = 0.665 bit (b = 15). P3 (<= 0.15 bit for b = 9-14, >= 0.10
at 15-16) fails in the range b = 11-14 as well as at the freeze.

## Interpretation

The failure is the calibration, not the lattice or the estimator.

- One global density scale is fixed at b = 8. It absorbs the error of the
  flat-density approximation at the coarsest bin. For a nearly uniform
  azimuth that error is small at every b; for a curved density the calibrated
  scale is 0.69 (pT) and 0.58 (mass), and it does not transfer to finer bins.
  The model then under-predicts p_max and over-predicts the floor.
- At b = 15-16 the measured floor freezes at the atom count (N_max identical
  at both b for pT and for mass), which the model does not reproduce.
- The residuals are one-sided in the transition region (all negative for
  mass from b = 9 to 16), a signature of the calibration ansatz rather than
  of noise.

## Consequence

For a near-uniform source the closed form predicts the whole curve from one
parameter (azimuths: max residual 0.09 bit). For a strongly non-uniform
variable the certified floor must be measured; the model is a
near-uniform-source model. This is the boundary the prediction card asked
for, and it is reported as measured.
