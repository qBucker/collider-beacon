# Precision efficiency eta and the sample boundary — results (2026-11-02)

Companion to `predictions/2026-11-02-atlas-precision-crosstest.md` and to the
derivation `beacon-paper/precision-passport/eta-closed-form-2026-11-02.md`.
Scripts: `precision_eta_model.py`, `atlas_precision_test.py`.
Outputs: `precision-eta-model-2026-11-02.json`,
`atlas-precision-2026-11-02.json`.

## Measurement

- CMS PFNano (c5G, 67 files): leading-jet and secondary-vertex azimuths,
  n = 5,211,771 and 4,468,841. Floor scan b = 8..16 as in
  `precision-floor-scan-2026-11-01.json`.
- ATLAS Open Data (record 93933, 16 arrays from the effect-1 smoke):
  leading-jet azimuths, n = 597,965, float32 delivered values.

## Model in one line

`p_max(b) = max_e M u_e ceil(r_e)` with `u_e = 2^(e - b_m)`,
`r_e = 2*pi*2^(b_m-b-e)`; `N_max = lambda + sqrt(lambda) G(m_eff)` with
`lambda = n p_max`, `m_eff = (r - floor(r)) 2^b`; the certified floor is the
Clopper-Pearson upper limit at `alpha/2^b`. One source parameter per branch
(`M`, the maximum azimuth density), calibrated at b = 8 only.

## CMS validation (reproduction)

| branch | n | M | max abs dh (b=9..16) | max abs d(eta) |
|---|---|---|---|---|
| leading jet | 5,211,771 | 0.16594 | 0.0351 bit | 0.0033 |
| secondary vertex | 4,468,841 | 0.17527 | 0.0726 bit | 0.0053 |

The model reproduces the eta plateau (0.83), the onset of the drop at b = 15
and the frozen floor at 12.94 bits. Boundaries: `b_lat = 13.651`,
`b_stat = 15.5` (leading), 15.4 (secondary). The observed boundary is the
lattice: `b_star = 13.651` (product fingerprint).

## ATLAS cross-test

| quantity | value |
|---|---|
| mantissa scan | b = 23 in every octave e = -8..1, on-grid 1.00000 |
| on-grid at b = 12, octave 1 | 0.00222 (CMS: 1.0000) |
| floor b = 8..16 | 7.7148, 8.6054, 9.4805, 10.2444, 10.9507, 11.5816, 12.1870, 12.5799, 12.9860 |
| M (calibrated at b = 8) | 0.16450 |
| max abs dh (b=9..16) | 0.0924 bit |
| max abs d(eta) | 0.0055 |
| b_lat / b_stat / b_star | 24.651 / 12.62 / **12.62** |

## Prediction verdicts

| id | prediction | measured | verdict |
|---|---|---|---|
| P1 | full float32; smallest on-grid b = 22-23; on-grid(b=12) <= 0.01 | b = 23; 0.00222 | **PASS** |
| P2 | no freeze: dh(14-12) >= 0.5, dh(16-14) >= 0.5 | 1.236, 0.799 | **PASS** |
| P3 | b_stat in [11.5,14]; b_stat - log2 n in [-7.8,-5.8] | 12.62; -6.57 (CMS -6.78) | **PASS** |
| P4 | model residual <= 0.10 bit | 0.0924 | **PASS** (margin 0.008) |
| P5 | eta(12) in [0.73,0.84] | 0.8022 | **PASS** |

## What the cross-test establishes

1. The 12-bit mantissa lattice is a **CMS product choice**, not a HEP-wide
   convention: the ATLAS product is full float32 (b = 23) and shows no
   lattice freeze in the measured range.
2. The **sample boundary is a method constant**: `b_stat - log2(n)` is
   -6.78 (CMS) and -6.57 (ATLAS), a 0.21-bit difference across experiments,
   branches and an order of magnitude in n.
3. The observed boundary is `min(b_lat, b_stat)`: the CMS scan freezes on its
   lattice (13.65), the ATLAS scan on its sample (12.6).
4. The same one-parameter model predicts both curves to <= 0.09 bit.

## Provenance

- CMS data: `c5G/*.npz`, 67 files; same values as the 2026-11-01 precision
  measurement.
- ATLAS data: `beacon-paper/phase0/atlas/smoke2.partial/*.phis.npy`, 16
  arrays, n = 597,965, produced 2026-10-17 by `atlas/atlas_extract.py` from
  record 93933 (CC0-1.0).
- Deterministic reruns: both JSON outputs are byte-identical.
- Checksums: `diagnostics/SHA256SUMS`.

## Caveats

- The ATLAS sample is trigger-selected (not random) and covers the first
  50,000 entries of each of 16 files; precision is a storage property and is
  expected to be selection-independent, but this is not tested separately.
- The ATLAS product belongs to one open-data release; a second product
  (e.g. PHYSLITE) would test the format-family claim.
- The model's 0.09-bit residual at the smallest counts is dominated by the
  Gumbel approximation (see the derivation note, honest boundaries).
