# ATLAS random-offset resampling — result (2026-11-02)

Question: is the ATLAS cross-product result an artifact of reading the first
50,000 entries of each file?

Method: `atlas/atlas_resample.py`, 16 files, one independent random
50,000-entry window per file (seed 20261102; starts recorded in the
manifest), leading-jet extraction identical to the contiguous smoke
(pT > 20 GeV, |eta| < 2.5). Wall time 946.3 s. Audit:
`diagnostics/atlas_resample_audit.py` with pp-audit v0.1.0.

| quantity | contiguous (first 50k) | random offset (this run) |
|---|---|---|
| n | 597,965 | 593,434 |
| band ratio (bins 227-234) | 1.0024 +/- 0.0072 | 1.0042 +/- 0.0090 |
| h_floor(8) | 7.7148 | 7.7028 |
| h_floor(12) | 10.9507 | 11.0115 |
| h_floor(16) | 12.9860 | 12.9750 |
| b (every octave) | 23 | 23 |

The band ratio is consistent with the contiguous value (difference 0.0018,
0.16 sigma) and with unity; the floor at b = 8 differs by 0.012 bit. The
entry range is not the source of the result. The small n difference (0.8%)
comes from the random windows, not from a selection change.

Archive: `atlas-resample-2026-11-02/manifest.json` and `audit.json`; the
leading-jet array is regenerable and not archived.
