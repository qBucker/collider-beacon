# E1 pre-registration — establishment-law exponent

- Timestamp: 2026-10-24T11:29:00+08:00 (before the run)
- Status: the analysis script has not been executed; no subsample curve has
  been computed or inspected. This card is committed before the run; the
  commit hash is the timestamp.

## Prediction

- The certified error `eps_CP(n)` follows a power law in `n` with exponent
  `-1/2` (Section 5, Corollary 1: `eps_CP ∝ n^{-1/2} B^{-1/2}`).
- **Pre-registered acceptance band: fitted slope in [-0.55, -0.45].**
- Secondary consistency gate: at `n = 5,211,771` the certified error is
  `0.05588 +/- 0.001` bit (the pooled `b = 8` value of the paper). Failure of
  this gate stops the interpretation: it indicates an estimator mismatch.
- Monotonicity: `eps_CP` decreases at every step of `n`.

## Method (fixed before the run)

- Data: pooled `b = 8` symbols from `runG/f01.bits.bin` through
  `runG/f67.bits.bin` (67 files, 5,211,771 symbols; `f01-local.bits.bin` is
  excluded as a duplicate local copy).
- Subsampling: for each seed `s` in 20261024..20261043 (20 seeds), draw a
  permutation of the pooled array and take **nested prefixes** of length
  `n in {10^3, 10^4, 10^5, 10^6, 5,211,771}`.
- Estimator: 256-bin histogram of the prefix; `p_hat_max`; one-sided
  Clopper-Pearson at `alpha = 1e-6`, Bonferroni over `B = 256`;
  `eps_CP = log2(p_hi / p_hat_max)`.
- Fit: ordinary least squares of `log eps_CP` on `log n` over the five sizes;
  the slope is the statistic judged against the band.
- Reported: per-seed slope; mean, standard deviation, minimum and maximum;
  the fraction of seeds inside the band; the aggregate curve and its fit.

## Falsification

- Mean fitted slope outside [-0.55, -0.45]: the establishment law does not hold
  on this stream. Report it as such, separate the small-`n` point (maximum-bin
  selection bias) from the large-`n` points (dependence), and do not
  reinterpret after the fact.
- Full-`n` error outside 0.05588 +/- 0.001 bit: estimator mismatch; stop and
  debug before interpreting the slope.

## Declarations

1. No subsample curve has been computed before this card is committed.
2. The seeds, sample sizes, estimator and fit are fixed; no point is added,
   removed, or reweighted after the run.
3. The analysis script is `diagnostics/e1_establishment.py`; its output is
   stored with the card's result.
