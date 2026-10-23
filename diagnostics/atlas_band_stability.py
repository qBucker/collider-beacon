#!/usr/bin/env python3
"""Event-index stability of the ATLAS band ratio.

The ATLAS adjudication sample is consecutive, not randomly drawn. This script
splits the 597,965-symbol bit stream into ten consecutive blocks and reports the
CMS-band ratio (bins 227-234 against a +-32-bin sideband) per block, plus the
first and second halves. A flat series is the cheap check that event index does
not correlate with azimuth in the sample.

Usage:
  python3 diagnostics/atlas_band_stability.py --bits atlas/smoke2.bits.bin \
      --out diagnostics/atlas-band-stability-2026-10-23.txt
"""

import argparse

import numpy as np

BINS = 256
BAND = set(range(227, 235))
SIDE = set((b % BINS) for b in range(227 - 32, 235 + 32) if (b % BINS) not in BAND)


def band_ratio(counts):
    nb = sum(counts[b] for b in BAND)
    ns = sum(counts[b] for b in SIDE)
    return (nb / len(BAND)) / (ns / len(SIDE))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bits", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    data = np.fromfile(args.bits, dtype=np.uint8)
    n = len(data)
    lines = ["ATLAS band-ratio stability (consecutive blocks)",
             "input: %s, n=%d, B=%d" % (args.bits, n, BINS),
             "block    n      band ratio"]
    for i in range(10):
        a = data[i * n // 10:(i + 1) * n // 10]
        c = np.bincount(a, minlength=BINS)
        lines.append("%5d  %6d  %.4f" % (i, len(a), band_ratio(c)))
    for name, a in [("first half", data[:n // 2]), ("second half", data[n // 2:])]:
        c = np.bincount(a, minlength=BINS)
        lines.append("%-11s %6d  %.4f" % (name, len(a), band_ratio(c)))

    text = "\n".join(lines) + "\n"
    with open(args.out, "w") as fh:
        fh.write(text)
    print(text)


if __name__ == "__main__":
    main()
