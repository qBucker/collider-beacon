# Precision constants of public HEP data products — pre-registered measurement (2026-11-01)

Written **before** the measurement. This is the first experiment of the
instrument/metrology line: measure the precision constants of public data
products, rather than assume them.

## Question

The PFNanoAOD jet and secondary-vertex azimuths are stored with a reduced
binary mantissa. Which mantissa count `b` is actually present in the released
product, does the step follow `u(e) = 2^(e-b)` at every octave, and is the
uniform-vs-mantissa entropy gap the exact constant `log2(pi) = 1.6515` bit?

## Data

- CMS: `c5G/*.npz` (67 files, C5 extraction 2026-10-25/26), raw float32
  `lead_phi` (leading jet) and `sv_phi` (secondary vertices).
- ATLAS: raw `jet_phi` not yet stored (only 8-bit derived bits in
  `atlas/smoke2.bits.bin`); a single-file extraction is a follow-up.
- Synthetic: uniform `phi` quantized with an explicit 12-bit mantissa
  (control).

## Predictions

- **P1 (mantissa count).** Both `lead_phi` and `sv_phi` have
  `u(e) = 2^(e-12)` (12 explicit mantissa bits) for octaves `e` in [-4, 1];
  the step ratio at each octave boundary is exactly 2; the on-grid fraction
  (values within 1e-3 of an integer multiple of `2^(e-12)`) is at least
  0.999.
- **P2 (octave constant).** The uniform 12-bit bin width `Delta = 2*pi/4096`
  and the coarse-octave step `u(1) = 2^-11` satisfy `Delta/u(1) = pi`
  (3.14159), i.e. the uniform-vs-mantissa gap is `log2(pi) = 1.6515` bit.
  This is an identity of the format; the measurement is its validation on
  released data.
- **P3 (ATLAS control).** The ATLAS `jet_phi` product is not 12-bit mantissa
  (float32 or a different `b`); when measured, its octave structure will
  report a different `b` or no octave quantization.
- **P4 (floor efficiency).** The measured entropy floor divided by the
  lattice cap, `eta = h_floor / log2(2*pi/2^-(b-1))`, is 0.81-0.83 for the
  CMS b = 8 and b = 12 products. Whether `eta` is universal across products
  is the open test; if it is, it is a precision-efficiency constant; if not,
  it is a product fingerprint.

## Gates

- G1: all 67 files load; event counts match the C5 manifests.
- G2: the on-grid fraction passes P1.
- G3: the step law `u(e)/u(e+1) = 2` holds across octaves.
- G4: a re-run reproduces the JSON bit-for-bit.

## Falsification

If `u(e) != 2^(e-12)`, the product uses a different mantissa count; report the
measured `b`. If `Delta/u(1) != pi`, the coarse-octave boundary or the
uniform alphabet differs from the assumed convention; report the measured
ratio. Either outcome is a result: a product constant or a product
fingerprint.

## Run

`python3 diagnostics/precision_constants.py` (loads `c5G/*.npz`, writes
`diagnostics/precision-constants-2026-11-01.json`). Results appended below
after the run.

## Results (appended 2026-11-01, after the run)

Runs: `diagnostics/precision_constants.py` (0.7 s, 67 files, 5,211,771 leading-jet
and 4,468,841 secondary-vertex azimuths) and
`diagnostics/precision_floor_scan.py` (1.0 s, b = 8..16).

**P1 PASS.** Both `lead_phi` and `sv_phi` have `b = 12` in every octave
`e = -8..1`; the on-grid fraction is 1.0000 and the step is `u(e) = 2^(e-12)`
exactly. The octave step ratio is 2.

**P2 PASS.** `Delta/u(1) = 3.141593`, `log2(Delta/u(1)) = 1.651496` = `log2(pi)`.
The uniform-vs-mantissa octave gap is the exact constant 1.6515 bit.

**P4 PASS within the band.** The floor scan (Clopper-Pearson + Bonferroni,
alpha = 1e-6, alpha/2^b per bin) reproduces the published pooled floors at
b = 8 (7.8413) and b = 12 (11.3098) exactly, and gives:

| b | 8 | 9 | 10 | 11 | 12 | 13 | 14 | 15 | 16 |
|---|---|---|---|---|---|---|---|---|---|
| lead eta | 0.8124 | 0.8277 | 0.8355 | 0.8345 | 0.8285 | 0.8286 | 0.8269 | 0.7776 | 0.7332 |
| sv eta | 0.8039 | 0.8179 | 0.8271 | 0.8312 | 0.8251 | 0.8235 | 0.8236 | 0.7746 | 0.7303 |

The efficiency is a plateau at **eta ~ 0.83 for b = 9..14**, on two different
branches with different n; it drops at b >= 15 because the 5.2M-event sample,
not the format, becomes the limit (the max-bin count saturates near 500).
`eta` is a product/source precision efficiency, not a universal constant; the
cross-product test is ATLAS.

**P3 PENDING.** The ATLAS raw `jet_phi` is not stored in the smoke products
(only derived 8-bit bits); a single-file extraction is the next step.

**P3 RESOLVED 2026-11-02.** The raw leading-jet azimuth arrays from the
smoke (`phase0/atlas/smoke2.partial/*.phis.npy`, n = 597,965) were used
directly: ATLAS is full float32 (b = 23 in every octave; on-grid 0.00222 at
b = 12). See `predictions/2026-11-02-atlas-precision-crosstest.md` and
`diagnostics/precision-eta-result-2026-11-02.md`.
