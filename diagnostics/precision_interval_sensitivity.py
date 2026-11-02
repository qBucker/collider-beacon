#!/usr/bin/env python3
"""Sensitivity of the certified floor to the confidence-interval choice.

For each product and analysis resolution b, take the maximum bin count k and
compare the certified floor obtained from three upper confidence limits at the
same tail budget alpha/m:

  * Clopper-Pearson (current): Beta^{-1}(1-alpha/m; k+1, n-k);
  * Jeffreys: Beta^{-1}(1-alpha/m; k+1/2, n-k+1/2);
  * Blaker: the upper endpoint of the Blaker interval, computed from the
    likelihood-sum p-value with a continuous lower-tail boundary.

Outputs the floor difference relative to Clopper-Pearson.

Writes diagnostics/precision-interval-sensitivity-2026-11-02.json.
"""

import argparse
import glob
import json
import math
import os

import numpy as np
from scipy import stats
from scipy.optimize import brentq
from scipy.special import gammaln

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "precision-interval-sensitivity-2026-11-02.json")
ALPHA = 1e-6
BS = (8, 12, 16)


def counts(values, b):
    nb = 1 << b
    k = np.minimum(((values + math.pi) / (2 * math.pi) * nb).astype(np.int64),
                   nb - 1)
    c = np.bincount(k, minlength=nb)
    return int(c.max()), int(len(values))


def cp_upper(k, n, tail):
    return float(stats.beta.ppf(1 - tail, k + 1, n - k))


def jeffreys_upper(k, n, tail):
    return float(stats.beta.ppf(1 - tail, k + 0.5, n - k + 0.5))


def _logpmf(x, n, p):
    return (gammaln(n + 1) - gammaln(x + 1) - gammaln(n - x + 1)
            + x * math.log(p) + (n - x) * math.log1p(-p))


def _boundary(k, n, p):
    """Opposite-side boundary where pmf equals pmf(k); returns (side, x)."""
    mode = n * p
    target = _logpmf(k, n, p)
    if k >= mode:
        hi = min(mode, k - 1.0)
        if hi <= 0:
            return "lower", 0.0
        f = lambda a: _logpmf(a, n, p) - target
        if f(0.0) >= 0:
            return "lower", 0.0
        if f(hi) <= 0:
            return "lower", hi
        return "lower", brentq(f, 0.0, hi)
    lo = max(mode, k + 1.0)
    hi = float(n)
    if lo >= hi:
        return "upper", hi
    f = lambda b: _logpmf(b, n, p) - target
    if f(lo) <= 0:
        return "upper", lo
    if f(hi) >= 0:
        return "upper", hi
    return "upper", brentq(f, lo, hi)


def blaker_p(k, n, p):
    side, x = _boundary(k, n, p)
    if side == "lower":
        gamma = float(stats.binom.cdf(math.floor(x), n, p)) + float(
            stats.binom.sf(k - 1, n, p))
    else:
        gamma = float(stats.binom.cdf(k, n, p)) + float(
            stats.binom.sf(math.ceil(x) - 1, n, p))
    return min(1.0, gamma)


def blaker_upper(k, n, tail):
    f = lambda p: blaker_p(k, n, p) - tail
    lo = k / n * (1 + 1e-9)
    hi = min(0.9, max(0.1, 10.0 * k / n))
    return float(brentq(f, lo, hi))


def analyse(name, values):
    rows = []
    for b in BS:
        k, n = counts(values, b)
        tail = ALPHA / (1 << b)
        p_cp = cp_upper(k, n, tail)
        p_j = jeffreys_upper(k, n, tail)
        try:
            p_b = blaker_upper(k, n, tail)
        except Exception as exc:  # numerical failure is recorded, not hidden
            p_b = float("nan")
        h_cp = -math.log2(p_cp)
        h_j = -math.log2(p_j)
        h_b = -math.log2(p_b) if p_b == p_b else float("nan")
        rows.append({
            "b": b, "n": n, "k": k, "tail": tail,
            "h_cp": h_cp, "h_jeffreys": h_j, "h_blaker": h_b,
            "dh_jeffreys": h_j - h_cp, "dh_blaker": h_b - h_cp,
        })
    return {"name": name, "n": len(values), "rows": rows}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--atlas-glob", default="")
    args = ap.parse_args()
    out = {"date": "2026-11-02", "alpha": ALPHA, "products": []}
    # CMS branches
    for key in ("lead_phi", "sv_phi"):
        xs = []
        for p in sorted(glob.glob(os.path.join(HERE, "..", "c5G", "*.npz"))):
            d = np.load(p)
            if key in d:
                xs.append(d[key].astype(np.float64))
        if xs:
            out["products"].append(analyse("CMS " + key, np.concatenate(xs)))
    print("CMS products done")
    if args.atlas_glob:
        files = sorted(glob.glob(args.atlas_glob))
        xs = [np.load(p).astype(np.float64) for p in files]
        if xs:
            out["products"].append(analyse("ATLAS lead_phi", np.concatenate(xs)))
            print("ATLAS product done")
    tmp = OUT + ".tmp"
    with open(tmp, "w") as f:
        json.dump(out, f, indent=1)
    os.replace(tmp, OUT)
    for prod in out["products"]:
        print(prod["name"])
        for r in prod["rows"]:
            print(f"  b={r['b']:2d} h_CP={r['h_cp']:.4f} "
                  f"dh_Jeff={r['dh_jeffreys']:+.4f} "
                  f"dh_Blaker={r['dh_blaker']:+.4f}")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
