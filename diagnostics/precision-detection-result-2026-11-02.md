# Detection bound for the on-grid profile test (2026-11-02)

The audit rejects a sparse deviation when the number of off-grid values
exceeds k* = ceil((1 - tau) n). Under an off-grid fraction eps,
X ~ Binomial(n, eps). For tau = 0.999 and n = 5,211,771, k* = 5,212.

| eps | power |
|---|---|
| 1e-5 | 0.0000 |
| 5e-5 | 0.0000 |
| 1e-4 | 0.0000 |
| 5e-4 | 0.0000 |
| 1e-3 | 0.5006 |
| 2e-3 | 1.0000 |
| 5e-3 | 1.0000 |

Smallest detectable fraction: **1.023e-3 at 95% power**, 1.033e-3 at 99%.
Size under a benign off-grid fraction eps0 = 1e-4: 0. The T4 counts
(k = 1,000 not detected, k = 10,000 detected) fall on either side of the
bound, as expected. A Monte Carlo at n = 1e5 (40 seeds) agrees with the
exact binomial within binomial noise.

The rounding mode is different: without a reference no test has power above
size (identifiability, Proposition 2); with a reference of m matched values
the residual-mean test needs m ~ ((z_{1-a}+z_{1-b}) sigma/(u/2))^2, about 13
for a uniform residual at 95% power and alpha = 1e-6. The B1 comparison
(102,977 jets) is the empirical instance.

Script: `precision_detection_bound.py`; JSON:
`precision-detection-bound-2026-11-02.json`.
