#!/usr/bin/env python3
"""Drift of the sample-boundary constant with the sample size.

The sample boundary b_stat is the analysis resolution at which the
statistical inflation epsilon equals one bit:

    epsilon(b) = (G(2^b) + z_{1-alpha/2^b}) / sqrt(n M 2*pi / 2^b) = 1,

with G the Gumbel location and M the maximum source density. Solving for b
gives b_stat, and c = b_stat - log2(n). Because G and z grow slowly with the
bin count, c is not exactly constant in n; this script quantifies the drift.

Writes diagnostics/bstat-drift-2026-11-02.json (no timestamps).
"""

import json
import math
import os

from scipy import stats

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "bstat-drift-2026-11-02.json")
ALPHA = 1e-6
M_CMS = 0.16594
M_ATLAS = 0.16450
N_GRID = (1e5, 3e5, 6e5, 1e6, 3e6, 5.2e6, 1e7, 1e8)


def gumbel_loc(m):
    lm = math.log(m)
    return math.sqrt(2 * lm) - (math.log(lm) + math.log(4 * math.pi)) / (
        2 * math.sqrt(2 * lm)
    )


def b_stat(M, n, alpha=ALPHA):
    def eps(b):
        m = 2.0 ** b
        lam = n * M * (2 * math.pi / m)
        z = float(stats.norm.ppf(1 - alpha / m))
        return (gumbel_loc(m) + z) / math.sqrt(lam)

    lo, hi = 4.0, 40.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if eps(mid) > 1.0:
            hi = mid
        else:
            lo = mid
    return 0.5 * (lo + hi)


def rows(M, ns=N_GRID):
    out = []
    for n in ns:
        b = b_stat(M, n)
        out.append({"n": n, "log2_n": round(math.log2(n), 6),
                    "b_stat": round(b, 6),
                    "c": round(b - math.log2(n), 6)})
    return out


def main():
    cms = rows(M_CMS)
    atlas = rows(M_ATLAS, (3e5, 597965.0, 5.2e6))
    drift = cms[-1]["c"] - cms[0]["c"]
    per_decade = drift / (math.log10(cms[-1]["n"]) - math.log10(cms[0]["n"]))
    out = {
        "date": "2026-11-02",
        "alpha": ALPHA,
        "M_cms": M_CMS,
        "M_atlas": M_ATLAS,
        "grid_cms": cms,
        "grid_atlas": atlas,
        "drift_decades": round(cms[-1]["c"] - cms[0]["c"], 6),
        "drift_per_decade": round(per_decade, 6),
        "cms_at_5.2M": [r["c"] for r in cms if r["n"] == 5.2e6][0],
        "atlas_at_597965": [r["c"] for r in atlas if r["n"] == 597965.0][0],
        "measured_difference": round(
            [r["c"] for r in cms if r["n"] == 5.2e6][0]
            - [r["c"] for r in atlas if r["n"] == 597965.0][0], 6),
    }
    tmp = OUT + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(out, fh, indent=1)
    os.replace(tmp, OUT)
    print(f"{'n':>10} {'log2 n':>7} {'b_stat':>7} {'c':>8}")
    for r in cms:
        print(f"{r['n']:10.0f} {r['log2_n']:7.3f} {r['b_stat']:7.3f} {r['c']:+8.3f}")
    print(f"drift {drift:+.3f} bit over "
          f"{math.log10(cms[-1]['n']) - math.log10(cms[0]['n']):.0f} decades "
          f"({per_decade:+.3f} bit/decade)")
    print(f"CMS c(5.2M)={out['cms_at_5.2M']:+.3f}  "
          f"ATLAS c(597965)={out['atlas_at_597965']:+.3f}  "
          f"difference={out['measured_difference']:+.3f} bit")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
