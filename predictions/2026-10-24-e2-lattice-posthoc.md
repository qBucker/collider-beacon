# E2 lattice-aligned pre-registration — post-hoc record

- Timestamp: 2026-10-24T11:07:03+08:00 (after unblinding)
- Judged against: amendment 4, sha256
  `8b81b1b191d6fa34500fc3d8a1f04888c6eb9818618efb954a944b5d5479fab8`
  (commit `dc69e6f`, 2026-10-24T01:55:49+08:00)
- Unblinding: analysis completed 2026-10-24T02:32:16+08:00 (integrity gate rc=0
  at 02:32:10, estimators rc=0 at 02:32:16)
- Full result: `diagnostics/lattice-result-2026-10-24.md`

This file is append-only. Amendments 1-4 are unchanged and their sidecars verify.

## Outcome against the pre-registered judgments

| item | pre-registered | measured | verdict |
|---|---|---|---|
| integrity gate | 67/67, pooled n = 5,211,771 | 67/67, n = 5,211,771 | pass |
| b = 8 control | 7.8413 +/- 0.02 | 7.841257 | pass |
| b = 12 control | 11.3098 +/- 0.02 | 11.309796 | pass |
| beat fingerprint | 7.06 bins, 581 cycles, lag-7 0.836 | fundamental 580 cycles per 2*pi, lag-7 0.8365 | pass |
| S1 real | 12.915, band [12.85, 12.99] | 12.9409 | in band |
| S2 real | 13.168, band [13.10, 13.24] | 13.1349 | in band |
| folded self-check, CP path | band [-0.857571, -0.771819] | -0.819867 | in band |
| folded self-check, raw path | band [-0.979566, -0.882839] | -0.934816 | in band |

- Realized physical excess: S1 0.0448 bit, S2 0.1034 bit (predicted
  0.0707 +/- 0.03).
- Gain over the b = 12 linear arm: +1.6311 bit (pre-registered statement
  +1.61 bit).
- Falsification conditions: none triggered. S1 did not exceed 12.99 and S2 did
  not exceed 13.24 (no bug indicator); S1 did not fall below 12.85 and S2 did
  not fall below 13.10 (no excess above 0.14 bit).

## Notes recorded after unblinding

1. **Beat fingerprint peak.** The pre-registered 581 cycles per circle is the
   fundamental of the 7.06-bin comb. In the pooled 4096-bin histogram the
   largest FFT component sits at 1160 cycles (second harmonic), with the
   fundamental at 580 (power 59.4) and a third harmonic at 1740. The second
   harmonic dominates because the per-bin occupancy alternates between 3 and 4
   lattice values at half the comb period. Lag-7 autocorrelation 0.8365 matches
   the pre-registered 0.836; no judged quantity depends on the peak ordering.
2. **Two extractor code groups.** f01-f03 ran before commit `f7d29da`, f04-f67
   after it. The diff is write atomicity only (`.tmp` + fsync + `os.replace`);
   selection, quantization and stored values are unchanged. Recorded in the
   result document.
3. **Determinism.** Re-running both analysis scripts on 2026-10-24 produced
   byte-identical integrity JSON, alpha JSON and figure.
4. **Not stored in the repository.** `latticeG/*.lattice.bin` (about 20 MB) are
   regenerable with `xrd_batch_lattice.sh`; each manifest pins the file's
   SHA256 in `lattice_sha256`. The manifests, the analysis outputs and the
   checksums are stored.
5. **Interpretation boundary.** 12.9409 (S1) and 13.1349 (S2) are certified
   lower bounds on the empirical alphabet under the stated estimator and the
   2026-10-23 dependence model; the signed storage floor is 13.65 [computed].
   The numbers are not a claim about physical entropy beyond that model.
