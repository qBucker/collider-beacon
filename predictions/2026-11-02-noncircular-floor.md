# Prediction card: floor model on non-circular variables (2026-11-02)

Status: written before the confirmatory run. Commit of this card is the
timestamp.

## Question

The closed-form floor model (atom-grain maximum, Gumbel selection,
Clopper-Pearson penalty) is calibrated on azimuths, which rotation invariance
makes nearly uniform. Does it transfer to a bounded, strongly non-uniform
stored variable?

## Data

- Source: 67 files of the CMS PFNanoAOD ZeroBias product (CERN Open Data
  record 31316), arrays `sv_pt` and `sv_mass` from `b5G/*.npz`
  (4,468,841 secondary vertices).
- Variable 1: secondary-vertex `sv_pt`, range [1, 50) GeV. Values outside the
  range are excluded and counted.
- Variable 2: secondary-vertex `sv_mass`, range [0.1, 5) GeV.
- Storage lattice: measured by the audit's own octave scan, no assumed value.

## Method (frozen with this card: `diagnostics/noncircular_floor.py`)

Values are binned into m = 2^b equal bins over the declared range, b = 8..16.
The certified floor is the Clopper-Pearson upper limit on the maximum bin
probability at confidence 1 - alpha/m, alpha = 1e-6 (Bonferroni over m bins).

The model uses the measured maximum density per octave M_e:

    p_max(b) = max_e M_e u_e ceil(r_e),  u_e = 2^(e - b_m),
    r_e = Delta / u_e,  Delta = (hi - lo) / 2^b,

with a Gumbel selection over m_eff bins and one global density scale
calibrated at b = 8 (as in the azimuth model, where the single parameter M is
calibrated at b = 8).

## Pilot (disclosed)

One file (`f01`, 21,066 vertices) was used to fix the ranges and to check
that the pipeline runs. No full-sample statistic was computed before this
card. Pilot results: pT max |residual| = 0.089 bit over b = 8-16; mass
0.178 bit at b = 15-16 (measured floor frozen at 44 counts); calibrated
density scale 0.46 (pT) and 0.45 (mass).

## Predictions

- **P1.** The octave scan recovers b_m = 10 in every populated octave, with
  on-grid fraction 1.0000, for both variables.
- **P2 (pT).** Max |residual| over b = 9-16 is at most 0.15 bit.
- **P3 (mass).** Max |residual| over b = 9-14 is at most 0.15 bit. For
  b = 15-16 the measured floor freezes at the atom count while the model does
  not; the residual magnitude is at least 0.10 bit, and the freeze is
  reported as the lattice boundary of the non-circular scan.
- **P4.** The calibrated density scale at b = 8 is below 1 for both
  variables (pilot: 0.46 and 0.45): the peak density measured on fine bins
  overestimates the mass of a coarse bin, which is the flat-density
  approximation failing at b = 8. The scale is one global parameter, not a
  per-b fit.
- **P5.** The residual at b = 8 is zero by construction; the test is b = 9-16.

## Decision rule

The model transfers to the variable if the applicable prediction holds.
A residual outside the stated band is reported as the failure boundary of the
model for that variable, not smoothed away. Both outcomes are results; no
range or bin is changed after this card.

## Non-claims

- The octave identity Delta/u = pi is azimuth-specific and is not tested
  here.
- No entropy claim is made for pT or mass; the certified floor is reported
  as a floor under the stated analysis grid.

## Result (post-hoc, 2026-11-02)

- **P1: pass.** The octave scan recovers b_m = 10 in every populated octave
  with on-grid fraction 1.0000 for both variables.
- **P2 (pT): fail.** Max |residual| = 0.411 bit at b = 16; the transition
  residual reaches -0.174 bit at b = 13.
- **P3 (mass): fail.** Max |residual| = 0.665 bit at b = 15; the b = 9-14
  band also fails (0.458 bit at b = 13).
- **P4: pass.** The calibrated density scale is 0.69 (pT) and 0.58 (mass),
  both below one.
- **P5: as stated.**

Full tables and interpretation: `diagnostics/noncircular-result-2026-11-02.md`.
