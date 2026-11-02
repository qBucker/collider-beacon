#!/usr/bin/env python3
"""Audit the ATLAS random-offset resample and compare with the contiguous smoke.

Reports the effect-1 band ratio (bins 227-234, local sidebands +/-8), the
chi-square/KS-free floor, and the certified floor at b = 8, 12, 16.

Usage: python3 atlas_resample_audit.py <resample_dir>
"""

import json
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "passport"))
from pp_audit import core


def main():
    d = sys.argv[1]
    x = np.load(os.path.join(d, "lead_phi.npy"))
    n = int(len(x))
    nb = 256
    k = np.minimum(((x + math.pi) / (2 * math.pi) * nb).astype(np.int64), nb - 1)
    c = np.bincount(k, minlength=nb)
    lo, hi = 227, 234
    band = float(c[lo:hi + 1].sum())
    side = float(np.concatenate([c[lo - 8:lo], c[hi + 1:hi + 9]]).mean()) * (hi - lo + 1)
    ratio = band / side if side > 0 else float("nan")
    # Poisson error on the ratio (band and sideband counts)
    side_sum = float(np.concatenate([c[lo - 8:lo], c[hi + 1:hi + 9]]).sum())
    mean_side = side_sum / 16.0
    err = ratio * math.sqrt(1.0 / band + 1.0 / (16.0 * mean_side)) if band > 0 else float("nan")
    floors = core.floor_scan(x, (8, 16), 1e-6)
    out = {
        "n": n, "band_count": band, "band_ratio": ratio,
        "band_ratio_err": err,
        "floors": {str(r["b"]): r for r in floors},
        "contiguous_reference": {"band_ratio": 1.0024, "band_ratio_err": 0.0072,
                                 "h_floor_b8": 7.7148},
    }
    path = os.path.join(d, "audit.json")
    with open(path, "w") as fh:
        json.dump(out, fh, indent=1)
    print(f"n={n} band_ratio={ratio:.4f} +/- {err:.4f} "
          f"(contiguous 1.0024 +/- 0.0072)")
    for b in (8, 12, 16):
        r = [q for q in floors if q["b"] == b][0]
        print(f"  b={b}: h_floor={r['h_floor']:.4f} eta={r['eta']:.4f} "
              f"nmax={r['n_max']}")
    print("wrote", path)


if __name__ == "__main__":
    main()
