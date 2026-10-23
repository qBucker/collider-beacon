#!/usr/bin/env python3
"""Symbol-level dependence and stationarity diagnostics for the b=8 run.

The paper's Stage 1 accounting assumes i.i.d. draws. This script tests that
assumption at the symbol layer, where the measured min-entropy lives, rather
than at the bit layer after conditioning:

  1. lag-k mutual information and chi-square independence tests;
  2. per-file certified h_min against the uniform null at the same n;
  3. block-wise most-common-value (MCV) entropy against the uniform null.

Inputs are the canonical 67 bit files of runG (f01..f67); f01-local is a
provenance copy and is excluded. The certification rule is the one used by the
extractor and the aggregate: Clopper-Pearson upper bound on the maximum bin
probability, Bonferroni alpha = 1e-6 over B bins.

Usage:
  python3 diagnostics/dependence_audit.py --bits-dir runG \
      --out diagnostics/dependence-2026-10-23.txt
"""

import argparse
import glob
import math
import os

import numpy as np
from scipy.stats import beta, chi2 as chi2_dist

BINS = 256
ALPHA = 1e-6
SEED = 20261023


def cp_hmin(counts, n):
    """Clopper-Pearson certified min-entropy from bin counts."""
    k = int(counts.max())
    if k >= n:
        return 0.0
    p_hi = beta.ppf(1.0 - ALPHA / BINS, k + 1, n - k)
    return -math.log2(p_hi)


def mi_lag(data, k):
    """Mutual information (bits) and chi-square for lag k."""
    x = data[:-k].astype(np.int64) * BINS + data[k:].astype(np.int64)
    c = np.bincount(x, minlength=BINS * BINS).reshape(BINS, BINS).astype(np.float64)
    nk = c.sum()
    pi = c.sum(axis=1)
    pj = c.sum(axis=0)
    expected = pi[:, None] * pj[None, :] / nk
    nz = c > 0
    p = c[nz] / nk
    e = expected[nz] / nk
    mi = float(np.sum(p * np.log2(p / e)))
    chi = float(np.sum((c - expected) ** 2 / expected))
    return mi, chi, nk


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bits-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--null-draws", type=int, default=300)
    ap.add_argument("--block-null-draws", type=int, default=2000)
    args = ap.parse_args()

    files = sorted(glob.glob(os.path.join(args.bits_dir, "f[0-9][0-9].bits.bin")))
    if len(files) != 67:
        raise SystemExit("expected 67 canonical bit files, found %d" % len(files))
    data = np.concatenate([np.fromfile(f, dtype=np.uint8) for f in files])
    n = len(data)
    p_uniform = np.full(BINS, 1.0 / BINS)
    rng = np.random.default_rng(SEED)

    lines = []
    lines.append("Symbol-level dependence and stationarity diagnostics")
    lines.append("input: %d files, %d symbols, B=%d, alpha=1e-6 (Bonferroni over B)" % (len(files), n, BINS))
    lines.append("seed: %d" % SEED)
    lines.append("")

    lines.append("1. lag-k mutual information (pooled)")
    lines.append("   k     MI(bits)     chi2        p")
    for k in [1, 2, 3, 4, 8, 16]:
        mi, chi, nk = mi_lag(data, k)
        p = chi2_dist.sf(chi, (BINS - 1) ** 2)
        lines.append("  %2d   %.6f   %.1f   %.4g" % (k, mi, chi, p))
    sh = []
    for _ in range(5):
        d = data.copy()
        rng.shuffle(d)
        sh.append(mi_lag(d, 1)[0])
    lines.append("   shuffled lag-1 MI: mean %.6f, range %.6f-%.6f" % (np.mean(sh), min(sh), max(sh)))
    lines.append("")

    lines.append("2. per-file certified h_min against the uniform null at the same n")
    outside = 0
    hs = []
    for f in files:
        a = np.fromfile(f, dtype=np.uint8)
        nn = len(a)
        h = cp_hmin(np.bincount(a, minlength=BINS), nn)
        null = np.array([cp_hmin(rng.multinomial(nn, p_uniform), nn)
                         for _ in range(args.null_draws)])
        lo, hi = np.percentile(null, [2.5, 97.5])
        hs.append(h)
        if h < lo or h > hi:
            outside += 1
            lines.append("   outside: %s n=%d h=%.4f null=[%.4f, %.4f]" %
                         (os.path.basename(f).split(".")[0], nn, h, lo, hi))
    lines.append("   outside 2.5-97.5%% band: %d/%d" % (outside, len(files)))
    lines.append("   per-file h_min: min %.4f, median %.4f, max %.4f" %
                 (min(hs), float(np.median(hs)), max(hs)))
    lines.append("")

    lines.append("3. block-wise MCV (raw, no certification) against the uniform null")
    for L in [1000, 5000, 10000, 50000]:
        vals = []
        for f in files:
            a = np.fromfile(f, dtype=np.uint8)
            for j in range(len(a) // L):
                c = np.bincount(a[j * L:(j + 1) * L], minlength=BINS)
                vals.append(-math.log2(c.max() / L))
        vals = np.array(vals)
        null = np.array([-math.log2(rng.multinomial(L, p_uniform).max() / L)
                         for _ in range(args.block_null_draws)])
        lines.append("   L=%6d blocks=%4d data median %.3f [5-95 %.3f-%.3f] null median %.3f [5-95 %.3f-%.3f]" %
                     (L, len(vals), np.median(vals), np.percentile(vals, 5), np.percentile(vals, 95),
                      np.median(null), np.percentile(null, 5), np.percentile(null, 95)))
    lines.append("")

    with open(args.out, "w") as fh:
        fh.write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
