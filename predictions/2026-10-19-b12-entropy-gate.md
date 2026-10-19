# Prediction card — b12-entropy-gate

- Date (UTC): 2026-10-19
- Author: Junchen Zhu
- Run / sample: CMS Open Data record 31316 (Run2016G ZeroBias PFNanoAOD, 29-Feb-24), files f01–f67 exactly as listed in `uris.txt`; one pass.
- Analysis code: `phase0_extract.py`, sha256 `9272d4dfb2d420cb7cc46ef156c6f179161da8c023b11d34fa76b9c48f4d1f3e`, invoked with `--b 12 --pt-min 20`. The commit that adds this card is the timestamp.
- Status: frozen (committed before any b=12 data exist)

## Predictions (fixed before data inspection)

1. **Pooled per-event min-entropy at b=12.** Predicted interval **[11.50, 11.65] bits/event**, central value approximately 11.58.
   Basis: the published b=8 pooled distribution (round 1, 67 files, 5,211,771 events) is upsampled by splitting each 256-bin count into 16 equal fine bins; Poisson samples at the same N are drawn; the same estimator is applied (Clopper–Pearson upper bound on the maximum bin probability, Bonferroni α = 1e−6 over 4096 bins). Monte-Carlo (1,000 draws): mean 11.581, 5–95% [11.554, 11.600]. The interval is widened to [11.50, 11.65] to allow for modulation curvature inside a b=8 bin; the flat-within-bin assumption is the model under test.
2. **Gate.** The program gate (pooled h_min ≥ 10.0 bits/event) is predicted to PASS, with approximately 1.5-bit margin under the model.
3. **Seam band persists.** The CMS deficit at b=8 bins 227–234 (φ ≈ +139°..+150°; pooled ratio 0.8947) maps to b=12 bins 3632–3759 (128 bins). Predicted pooled ratio in that band: **0.895 ± 0.01** (statistical σ ≈ 0.0025; the interval is widened for shape uncertainty). A ratio outside [0.85, 0.94] would indicate the b=8 seam is a binning artifact.
4. **χ²/KS pattern.** Per-file χ² (p > 1e−6) is expected to fail on the larger files and pass on the smaller, as in round 1 (23/67 failed at b=8); per-file KS is expected to pass 67/67. These are diagnostics, not gates for this card. The χ² approximation is unreliable for the smallest files at 4096 bins (expected counts below 5); the warning applies to both directions.
5. **Per-file h_min.** Expected to be much lower than pooled (finite sample plus Bonferroni at 4096 bins): approximately 8.7 at n ≈ 23k, 9.8 at n ≈ 78k, 10.2 at n ≈ 130k, with a spread of roughly 7–10.5 across the sample. Per-file h_min is not the gate.

## Analysis choices (fixed)

- Bins: 4096 equal-width bins over φ ∈ (−π, π], b = 12, MSB-first packing, 12 bits per event.
- Selection: leading jet, maximum pT, |η| < 2.5, pT > 20 GeV; no jetId requirement (identical to round 1).
- Estimator: Bonferroni-corrected Clopper–Pearson upper bound on the maximum bin probability, α = 1e−6 over 4096 bins (identical to round 1).
- Pooling: sum counts over all 67 files; the gate is computed on the pooled count vector.
- Sample: all 67 files, single pass; transport failures retried by the self-healing runner; no early stopping and no data-dependent file selection.
- Bit-file caveat: the extractor writes only complete bytes. For an odd event count the final 4 bits of the last 12-bit symbol are not written. The manifest's h_min is computed in memory over all events and is authoritative per file; the aggregator reconstructs all but at most one symbol per odd-n file (≤ 67 events, ≤ 0.0013% of the sample).

## Decision rule

- Pooled h_min ≥ 10.0 → gate PASS; claim b=12 yields at least 10 bits/event on this sample.
- Pooled h_min in [11.0, 12.0] → consistent with the flat-within-bin model; report the measured value.
- Pooled h_min < 11.0 → the flat-within-bin model is rejected; fine structure below 24.5 mrad exists; report as a physical finding and investigate its shape.
- Seam band ratio in [0.85, 0.94] → the b=8 seam persists under finer binning; outside → report as a binning artifact.
- Any outcome outside the stated intervals is reported as such. No re-analysis after inspection except the diagnostics declared above.

## Post-hoc notes (append only after the run)

- Result manifest: `runG12/` (67 per-file manifests and bit files); aggregate at `runG12/aggregate-b12-2026-10-19.txt`.
- Commit: `61b1518` (prediction card and pipeline); result commit: this commit.
- Outcome versus prediction:
  1. **Pooled h_min = 11.3098 bits/event** (N = 5,211,740 decoded events; max bin 1,777). Gate ≥ 10.0: **PASS** (margin 1.31 bits). The value lies inside the decision band [11.0, 12.0] but **below the point-prediction interval [11.50, 11.65]**; the flat-within-bin central value is not met.
  2. **Cause of the shortfall (post-hoc diagnostic).** The CMS PFNanoAOD files store jet four-vectors with reduced mantissa precision: `Jet_phi` carries 12 explicit mantissa bits (13 significant bits; minimum 11 trailing zeros, steps 2^-11..2^-13 rad depending on |φ|), and `Jet_pt` carries 10. At b = 12 the bin width is 1.534 mrad. For |φ| ∈ [2, 4) the ratio of bin width to storage step is exactly π (1.534 mrad / 0.488 mrad), so the fractional part 0.1416 produces an occupancy beat with period ≈ 7.06 bins. The pooled counts show exactly this comb: FFT peak at 581 cycles per circle (period 7.05 bins), lag-7 autocorrelation 0.836, and all top fine bins fall in |φ| ∈ [2, 4) (φ ≈ ±172°..±178°, +120°, −148°). The shortfall is a **storage-precision floor of the public data product**, not fine physical structure. The truncation pattern is consistent with lossy float compression; the exact production setting is not recorded in the file.
  3. **Scope.** 11.31 bits/event is a lower bound supported by the public files. Increasing b beyond 12 cannot exceed the file's numeric-precision floor; claims are scoped to the data product, not to detector physics.
  4. **Seam band** (bins 3632–3759): ratio **0.8947** versus predicted 0.895 ± 0.01 → PASS. The b=8 seam persists unchanged at 16× finer binning; it is not a binning artifact.
  5. **Per-file diagnostics:** χ² gate (p > 1e−6) 17/67 pass, 50 fail (round 1: 44/67 pass); KS 67/67 pass. The higher χ² failure rate is consistent with the resolved quantization structure.
  6. **Recheck:** 31 files have one truncated final symbol (odd event count); 0 mismatches; max |Δh| = 4.9e−4 bits. Decoded N is 31 events below the manifest total.
  7. **STS (optional diagnostic, post-hoc).** NIST STS 2.1.2 on the pooled stream (62 × 10^6 bits; input sha256 `cdeda9761f93e9f58c1579e9a766989c96e45ea3557096e69425bbd5b0eddad5`): **6 flagged lines**. Four NonOverlappingTemplate lines have proportion 58/62 (minimum 59); one NonOverlappingTemplate line carries a p-value-uniformity flag at 59/62; **ApproximateEntropy fails** (p = 0, 53/62). The b=8 stream had zero flags (41 streams). The contrast is the expected consequence of the quantization comb: the min-entropy bound absorbs the comb at the symbol level (11.31 < 12), but the raw b=12 bit stream is not bit-level IID uniform and would require conditioning before use as a random bit source. Evidence: `runG12/sts-2026-10-19/`.
- **Transport note:** f57, f64 and f67 hit the runner's 900 s timeout in the main pass and were rerun with a 2400 s timeout; all completed. Sample, selection and analysis choices are unchanged.
