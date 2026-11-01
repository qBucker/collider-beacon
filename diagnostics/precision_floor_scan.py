#!/usr/bin/env python3
"""Scan the certified min-entropy floor against the storage-lattice cap.

For b = 8..16, bin the raw azimuths (c5G/*.npz) into 2^b uniform bins,
apply the same Clopper-Pearson + Bonferroni bound as the Phase 0 extractor
(alpha = 1e-6, per-bin alpha / 2^b), and report

    h_floor(b) = -log2( cp_upper(max_count, n, alpha/2^b) )
    h_cap(b)   = log2( 2*pi / 2^{-(b-1)} ) = b + log2(2*pi) - 1
    eta(b)     = h_floor / h_cap

The b = 8 and b = 12 points must reproduce the published pooled floors
(7.8413 and 11.3098 bits/event); the b-scan tests whether eta is a
product-independent precision efficiency or a product fingerprint.

Writes diagnostics/precision-floor-scan-2026-11-01.json.
"""

import glob
import json
import math
import os
import time

import numpy as np
from scipy import stats

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(HERE, "precision-floor-scan-2026-11-01.json")
ALPHA = 1e-6
BS = (8, 9, 10, 11, 12, 13, 14, 15, 16)


def cp_upper(x, n, alpha):
    if x >= n:
        return 1.0
    return float(stats.beta.ppf(1 - alpha, x + 1, n - x))


def h_floor(vals, b):
    nb = 1 << b
    u = (vals + math.pi) / (2 * math.pi)
    k = np.minimum((u * nb).astype(np.int64), nb - 1)
    counts = np.bincount(k, minlength=nb)
    n = int(counts.sum())
    h = -math.log2(cp_upper(int(counts.max()), n, ALPHA / nb))
    cap = b + math.log2(2 * math.pi) - 1
    return {
        "b": b, "n": n, "bins": nb, "max_count": int(counts.max()),
        "h_floor": h, "h_cap": cap, "eta": h / cap,
        "ratio_to_cap": h / cap,
    }


def load_key(key):
    xs = []
    files = sorted(glob.glob(os.path.join(ROOT, "c5G", "*.npz")))
    for p in files:
        d = np.load(p)
        if key in d:
            xs.append(d[key].astype(np.float64))
    return np.concatenate(xs) if xs else np.array([])


def main():
    t0 = time.time()
    out = {"date": "2026-11-01", "alpha": ALPHA, "keys": {}}
    for key, published in (("lead_phi", 7.8413), ("sv_phi", None)):
        vals = load_key(key)
        rows = [h_floor(vals, b) for b in BS]
        out["keys"][key] = {"n": int(len(vals)), "rows": rows,
                            "published_b8": published}
        print(f"\n{key}: n={len(vals)}")
        print("  b   n        max_count  h_floor  h_cap   eta")
        for r in rows:
            print(f"  {r['b']:2d}  {r['n']:8d}  {r['max_count']:8d}  "
                  f"{r['h_floor']:8.4f}  {r['h_cap']:7.4f}  {r['eta']:.4f}")
    out["wall_s"] = round(time.time() - t0, 1)
    tmp = OUT + ".tmp"
    json.dump(out, open(tmp, "w"), indent=1)
    os.replace(tmp, OUT)
    print("\nwrote", OUT, f"{out['wall_s']} s")


if __name__ == "__main__":
    main()
