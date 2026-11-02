# Interval sensitivity of the certified floor (2026-11-02)

Script: `precision_interval_sensitivity.py`; output
`precision-interval-sensitivity-2026-11-02.json`. Inputs: CMS PFNanoAOD
leading-jet and secondary-vertex azimuths (67 files) and ATLAS Open Data
leading-jet azimuths (16 arrays, n = 597,965).

For each product and resolution b, the maximum bin count k is fixed and the
certified floor is recomputed with three upper confidence limits at the same
tail budget alpha/m (alpha = 1e-6, m = 2^b): Clopper-Pearson (the paper's
choice), Jeffreys, and Blaker.

| product | b | h_CP (bit) | dh Jeffreys | dh Blaker |
|---|---|---|---|---|
| CMS lead | 8 | 7.8413 | +0.0000 | -0.0011 |
| CMS lead | 12 | 11.3098 | +0.0004 | -0.0037 |
| CMS lead | 16 | 12.9425 | +0.0013 | -0.0061 |
| CMS vertices | 8 | 7.7584 | +0.0000 | -0.0012 |
| CMS vertices | 12 | 11.2638 | +0.0004 | -0.0039 |
| CMS vertices | 16 | 12.8912 | +0.0014 | -0.0064 |
| ATLAS lead | 8 | 7.7148 | +0.0003 | -0.0032 |
| ATLAS lead | 12 | 10.9507 | +0.0029 | -0.0102 |
| ATLAS lead | 16 | 12.9860 | +0.0162 | -0.0202 |

Worst case: 0.016 bit (Jeffreys) and 0.020 bit (Blaker) at the smallest
counts (ATLAS b = 16, k = 24). The CMS branches stay within 0.007 bit. The
method constant b_stat - log2 n is unchanged at the reported precision.

Implementation note: the Blaker upper limit is computed from the exact
likelihood-sum p-value with a continuous opposite-side boundary; the outer
root is bracketed in [k/n, 0.1] to avoid the extreme-p numerical region of
the incomplete-beta evaluation. Reruns are byte-identical.
