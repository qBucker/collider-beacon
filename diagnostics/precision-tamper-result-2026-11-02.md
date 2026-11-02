# Precision audit: tamper response and overhead (2026-11-02)

Script: `precision_tamper_test.py`; output
`precision-tamper-2026-11-02.json` (deterministic, byte-identical reruns).
Data: CMS PFNano leading-jet azimuths, n = 5,211,771, declared profile
b_m = 12, step law u(e) = 2^(e-12), on-grid threshold 0.999.

## Tamper cases

| case | operation | audit reading | verdict |
|---|---|---|---|
| honest | none | b = 12 in every octave, on-grid 1.0000 | matches profile |
| T1 | 12-bit values truncated to the 11-bit grid | b = 11 in every octave | **detected** (declared 12) |
| T2 | re-quantized on a uniform 4096-bin grid | no b in 8..16 passes; best on-grid 0.0000-0.0123 | **detected** (no lattice fit) |
| T3 | octave 1 shifted by half a 12-bit quantum | octave 1 reads b = 13; other octaves 12 | **detected** per octave |
| T4 | k values shifted off-grid | on-grid at b = 12: k=100 0.999981, k=1,000 0.999808, k=10,000 0.998081 | k=10,000 detected; k<=1,000 not |

T3 carries a design lesson: the whole-circle majority read-out is still
b = 12, so a **global-b check alone would miss a localized step-law
violation**. R2 soundness requires the per-octave comparison, not only the
global mode.

## Detection limit for sparse tampering

With the declared threshold 0.999 on the on-grid fraction, the audit
tolerates up to `(1 - 0.999) n = 5,212` off-grid values out of 5.2M before
flagging. Sparse tampering below this level is invisible to the precision
audit **by construction**: the audit certifies the profile (a statistical
property of the whole product), not the identity of every value. Byte-level
integrity is the job of `C_data` (the content hash), which catches any
change regardless of size.

This is the precise scope of requirement R2: the precision audit detects
*profile deviations* (mantissa count, step law, quantizer, rounding at the
product level); `C_data` detects *content deviations*.

## Overhead

Single-threaded, on the same 5.2M + 4.5M values:

| step | wall time (median of 3) | peak RSS |
|---|---|---|
| precision constants (`precision_constants.py`) | 0.83 s | 256 MB |
| floor scan (`precision_floor_scan.py`) | 1.61 s | 253 MB |
| eta model (`precision_eta_model.py`) | 1.77 s | ~260 MB |
| **full audit** | **~4.2 s** | **~260 MB** |
| tamper suite (5 scenarios) | 3.2 s | — |

The audit is seconds against an extraction that took hours (67 files,
4 h 21 min in the 2026-10-16 batch) and against the measurement it
certifies. R5 (overhead) holds with a large margin. The 260 MB peak comes
from holding both branches as float64; a streaming implementation would
reduce it by the batch size, and is not required for the current products.

## Provenance

- Input: `c5G/*.npz`, 67 files; same values as the 2026-11-01 precision
  measurement.
- Determinism: rerunning `precision_tamper_test.py` reproduces the JSON
  byte for byte (sha256 41d56edd...).
- Checksums: `diagnostics/SHA256SUMS`.
