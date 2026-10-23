#!/usr/bin/env python3
"""Per-file certified h_min distribution for the b=12 run.

Reads the 67 runG12 manifests and reports the per-file CP+Bonferroni certified
values, which are already stored as `min_entropy_bits_per_event`. The pooled
value is 11.3098 bits/event; the per-file values are lower because the
finite-sample term at n ~ 78,000 and B = 4096 is about one bit.

Usage:
  python3 diagnostics/b12_perfile.py --manifests runG12 \
      --out diagnostics/b12-perfile-2026-10-23.txt
"""

import argparse
import glob
import json
import os

import numpy as np


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifests", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    files = sorted(glob.glob(os.path.join(args.manifests, "f[0-9][0-9].manifest.json")))
    rows = []
    for f in files:
        m = json.load(open(f))
        r = m["results"]
        rows.append((os.path.basename(f).split(".")[0], m["events_with_bits"],
                     r["max_bin_count"], r["min_entropy_bits_per_event"]))

    h = np.array([r[3] for r in rows])
    n = np.array([r[1] for r in rows])
    lines = ["b=12 per-file certified h_min (CP + Bonferroni over B=4096)",
             "files: %d, total events: %d" % (len(rows), int(n.sum())),
             "h_min: min %.4f  p5 %.4f  median %.4f  mean %.4f  max %.4f" %
             (h.min(), np.percentile(h, 5), np.median(h), h.mean(), h.max()),
             "files below 10 bits: %d/%d" % (int((h < 10).sum()), len(h)),
             "n range: %d .. %d" % (n.min(), n.max()),
             "",
             "file     n     max_bin   h_min"]
    for name, nn, k, hv in rows:
        lines.append("%-5s %7d %7d   %.4f" % (name, nn, k, hv))

    text = "\n".join(lines) + "\n"
    with open(args.out, "w") as fh:
        fh.write(text)
    print(text)


if __name__ == "__main__":
    main()
