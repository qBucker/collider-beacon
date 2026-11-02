#!/usr/bin/env python3
"""Detection bound for the on-grid profile test.

The audit rejects a sparse deviation when the number of off-grid values
exceeds k* = ceil((1 - tau) n). Under a deviation with off-grid fraction eps,
X ~ Binomial(n, eps). This script computes the exact size and power, the
smallest detectable eps at 95% and 99% power, and checks the Monte Carlo
frequency at n = 1e5.

Writes diagnostics/precision-detection-bound-2026-11-02.json.
"""

import json
import math
import os

import numpy as np
from scipy import stats
from scipy.optimize import brentq

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "precision-detection-bound-2026-11-02.json")
N = 5211771
TAU = 0.999
ALPHA_GRID = (1e-5, 5e-5, 1e-4, 5e-4, 1e-3, 2e-3, 5e-3)


def power(eps, n, kstar):
    if eps <= 0:
        return 0.0
    return float(stats.binom.sf(kstar - 1, n, eps))


def detectable(n, kstar, target):
    return float(brentq(lambda e: power(e, n, kstar) - target, 1e-9, 0.5))


def main():
    kstar = int(math.ceil((1 - TAU) * N))
    rows = []
    for eps in ALPHA_GRID:
        rows.append({"eps": eps, "power": power(eps, N, kstar)})
    eps95 = detectable(N, kstar, 0.95)
    eps99 = detectable(N, kstar, 0.99)
    # Size under a benign off-grid fraction eps0 (e.g. a second rounding)
    eps0 = 1e-4
    size = power(eps0, N, kstar)
    # Monte Carlo sanity at n = 1e5
    rng = np.random.default_rng(20261102)
    n_mc = 100000
    k_mc = int(math.ceil((1 - TAU) * n_mc))
    mc = []
    for eps in (5e-4, 1e-3, 2e-3):
        hits = 0
        for _ in range(40):
            x = rng.binomial(n_mc, eps)
            hits += int(x > k_mc)
        mc.append({"eps": eps, "mc_power": hits / 40.0,
                   "exact_power": power(eps, n_mc, k_mc)})
    out = {
        "date": "2026-11-02", "n": N, "tau": TAU, "kstar": kstar,
        "rows": rows, "eps_95": eps95, "eps_99": eps99,
        "size_eps0_1e-4": size, "monte_carlo_n1e5": mc,
    }
    tmp = OUT + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(out, fh, indent=1)
    os.replace(tmp, OUT)
    print(f"n={N} tau={TAU} k*={kstar}")
    for r in rows:
        print(f"  eps={r['eps']:.0e} power={r['power']:.4f}")
    print(f"  eps_95={eps95:.3e} eps_99={eps99:.3e} "
          f"size(eps0=1e-4)={size:.3e}")
    for m in mc:
        print(f"  MC n=1e5 eps={m['eps']:.0e}: {m['mc_power']:.3f} "
              f"(exact {m['exact_power']:.3f})")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
