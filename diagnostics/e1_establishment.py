#!/usr/bin/env python3
"""E1: establishment-law exponent on nested subsamples of the b = 8 stream.

Pre-registered in predictions/2026-10-24-e1-establishment-law.md (commit
time = the card's hash). Prediction: eps_CP(n) ~ n^-1/2; acceptance band
[-0.55, -0.45].

Method (fixed in the card):
  - pooled b = 8 symbols from runG/f01..f67.bits.bin (5,211,771 symbols);
  - 20 seeds, each a permutation of the pooled array; nested prefixes at
    n in {10^3, 10^4, 10^5, 10^6, 5,211,771};
  - 256-bin histogram, one-sided Clopper-Pearson at alpha = 1e-6 with
    Bonferroni over B = 256; eps_CP = log2(p_hi / p_hat_max);
  - OLS slope of log eps_CP on log n.

Usage:
  python3 diagnostics/e1_establishment.py --bits-dir runG
"""

import argparse
import glob
import math
import os

import numpy as np
from scipy.stats import beta

ALPHA = 1e-6
B = 256
SIZES = [1000, 10000, 100000, 1000000, 0]      # 0 means the full stream
SEED0 = 20261024
N_SEEDS = 20
BAND = (-0.55, -0.45)


def load_symbols(bits_dir):
    paths = sorted(glob.glob(os.path.join(bits_dir, "f[0-9][0-9].bits.bin")))
    if len(paths) != 67:
        raise SystemExit("expected 67 bit files, found %d" % len(paths))
    return np.concatenate([np.fromfile(p, dtype=np.uint8) for p in paths])


def eps_cp(symbols):
    counts = np.bincount(symbols, minlength=B)
    n = len(symbols)
    k = int(counts.max())
    p_hat = k / float(n)
    p_hi = beta.ppf(1.0 - ALPHA / B, k + 1, n - k)
    return math.log2(p_hi / p_hat), k


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bits-dir", default="runG")
    args = ap.parse_args()

    symbols = load_symbols(args.bits_dir)
    n_total = len(symbols)
    print("pooled symbols: %d" % n_total)
    sizes = [n_total if s == 0 else s for s in SIZES]

    slopes = []
    print("\nper-seed curves (eps_CP in bits):")
    header = "seed    " + "  ".join("n=%-8d" % s for s in sizes) + "  slope"
    print(header)
    for i in range(N_SEEDS):
        seed = SEED0 + i
        rng = np.random.default_rng(seed)
        perm = rng.permutation(n_total)
        eps = []
        for n in sizes:
            e, k = eps_cp(symbols[perm[:n]])
            eps.append(e)
        slope = float(np.polyfit(np.log(sizes), np.log(eps), 1)[0])
        slopes.append(slope)
        print("%-7d " % seed + "  ".join("%9.5f" % e for e in eps) + "  %+.4f" % slope)

    slopes = np.array(slopes)
    print("\nslope summary:")
    print("  mean   %+.4f" % slopes.mean())
    print("  sd     %.4f" % slopes.std(ddof=1))
    print("  min    %+.4f" % slopes.min())
    print("  max    %+.4f" % slopes.max())
    inside = np.mean((slopes >= BAND[0]) & (slopes <= BAND[1]))
    print("  inside %s: %.2f" % (str(BAND), inside))

    # aggregate curve: mean eps at each size, and its fit
    print("\naggregate curve (all seeds):")
    curves = []
    for i in range(N_SEEDS):
        rng = np.random.default_rng(SEED0 + i)
        perm = rng.permutation(n_total)
        curves.append([eps_cp(symbols[perm[:n]])[0] for n in sizes])
    curves = np.array(curves)
    for j, n in enumerate(sizes):
        print("  n=%-9d mean eps=%.5f  sd=%.5f" % (n, curves[:, j].mean(), curves[:, j].std(ddof=1)))
    agg = np.polyfit(np.log(sizes), np.log(curves.mean(axis=0)), 1)[0]
    print("  aggregate slope: %+.4f" % agg)

    full = curves[0, -1]
    print("\nconsistency gate: full-n eps = %.5f (target 0.05588 +/- 0.001)" % full)
    print("verdict: %s" % ("PASS" if BAND[0] <= slopes.mean() <= BAND[1] else "FAIL"))


if __name__ == "__main__":
    main()
