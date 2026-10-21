#!/usr/bin/env python3
"""Evaluate the Herwig++ prediction card against the extracted result.

Reads the extractor manifest and bit file, then reports each pre-registered
prediction with its measured value:

  1. acceptance n/N against [0.9%, 1.7%]
  2. chi-square and KS gates (p > 1e-6)
  3. finite-sample min-entropy against [5.5, 6.5] bits, with a uniform-sample
     null distribution at the same n (post-hoc diagnostic)
  4. seam-band ratio (bins 227-234) against a +-32-bin sideband baseline,
     against 1.00 +- 0.20, with the same statistic on the PYTHIA reference
     bits file for context.

Usage:
  python3 evaluate_card.py --manifest run400k/mc_hpp_400k.manifest.json \
      --bits run400k/mc_hpp_400k.bits.bin --generated 400000 \
      [--pythia-bits ../../mc/mc400k_pt20.bits.bin]
"""

import argparse
import json
from collections import Counter

import numpy as np

BINS = 256
BAND = list(range(227, 235))          # phi ~ +139..+150 deg at b=8
SIDEBAND_HALF = 32


def band_ratio(counts):
    band = [b % BINS for b in BAND]
    side = [(b % BINS) for b in range(BAND[0] - SIDEBAND_HALF, BAND[-1] + 1 + SIDEBAND_HALF)
            if (b % BINS) not in band]
    nb = sum(counts[b] for b in band)
    ns = sum(counts[b] for b in side)
    ratio = (nb / len(band)) / (ns / len(side))
    sigma = ratio * np.sqrt(1.0 / max(nb, 1) + 1.0 / max(ns, 1))
    return ratio, sigma, nb, ns, len(side)


def null_hmin(n, draws=1000, seed=20261021):
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(draws):
        c = np.bincount(rng.integers(0, BINS, n), minlength=BINS)
        # Clopper-Pearson upper bound on the maximum bin probability,
        # Bonferroni alpha = 1e-6 over 256 bins, matching the extractor.
        from scipy.stats import beta
        alpha = 1e-6 / BINS
        k = int(c.max())
        p_hi = beta.ppf(1 - alpha, k + 1, n - k) if k < n else 1.0
        out.append(-np.log2(p_hi))
    return np.percentile(out, [5, 50, 95])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--bits", required=True)
    ap.add_argument("--generated", type=int, required=True)
    ap.add_argument("--pythia-bits", default=None)
    a = ap.parse_args()

    m = json.load(open(a.manifest))
    r = m["results"]
    n = m["events_with_bits"]
    acc = 100.0 * n / a.generated

    data = np.fromfile(a.bits, dtype=np.uint8)
    counts = np.bincount(data, minlength=BINS)

    ratio, sigma, nb, ns, nside = band_ratio(counts)

    print(f"generated            : {a.generated}")
    print(f"selected events n    : {n}")
    print(f"acceptance           : {acc:.3f}%   (card: [0.9, 1.7]%)")
    print(f"chi2 p               : {r['chi2_p']:.6g}   (gate p > 1e-6)")
    print(f"KS p                 : {r['ks_p']:.6g}   (gate p > 1e-6)")
    print(f"h_min                : {r['min_entropy_bits_per_event']:.4f} bits   (card: [5.5, 6.5])")
    print(f"max bin              : {r['max_bin_count']}")
    print(f"seam band ratio      : {ratio:.4f} +- {sigma:.4f}   (card: 1.00 +- 0.20)")
    print(f"  band counts {nb} over {len(BAND)} bins; sideband {ns} over {nside} bins")

    lo, med, hi = null_hmin(n)
    print(f"uniform null at n={n}: h_min 5-50-95% = {lo:.3f} / {med:.3f} / {hi:.3f} bits")

    if a.pythia_bits:
        pdata = np.fromfile(a.pythia_bits, dtype=np.uint8)
        pcounts = np.bincount(pdata, minlength=BINS)
        pr, ps, pnb, pns, pside = band_ratio(pcounts)
        print(f"PYTHIA reference     : n={len(pdata)}, seam band ratio {pr:.4f} +- {ps:.4f}")


if __name__ == "__main__":
    main()
