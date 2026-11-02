#!/usr/bin/env python3
"""Two further tamper scenarios for the precision audit.

Complements precision_tamper_test.py without modifying it:

  T5  mixed per-octave truncation: octave 0 truncated to 11 bits and octave 1
      to 10 bits, other octaves kept at 12. The global read-out stays at 12;
      the per-octave scan resolves the mixture.
  T6  localized uniform quantizer: octave 1 replaced by a uniform 1000-bin
      quantizer over [1, 2). No float mantissa count fits that octave; the
      other octaves still read 12.

Deterministic; no timestamps. Writes
diagnostics/precision-tamper-extra-2026-11-02.json.

Usage: python3 diagnostics/precision_tamper_extra.py [--glob 'c5G/*.npz']
"""

import argparse
import glob
import json
import math
import os

import numpy as np

import precision_tamper_test as base

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(HERE, "precision-tamper-extra-2026-11-02.json")


def _octave(x):
    ax = np.abs(x)
    e = np.zeros_like(ax, dtype=int)
    nz = ax > 0
    e[nz] = np.floor(np.log2(ax[nz])).astype(int)
    return ax, e


def mixed_truncate(x):
    """Octave 0 to 11 bits, octave 1 to 10 bits, others unchanged."""
    _, e = _octave(x)
    y = x.copy()
    for target, to_b in ((0, 11), (1, 10)):
        m = e == target
        y[m] = base.truncate_bits(x[m], 12, to_b)
    return y


def local_uniform(x, nbins=1000):
    """Quantize octave 1 (|x| in [2, 4)) on a uniform grid over that octave."""
    ax, e = _octave(x)
    y = x.copy()
    m = e == 1
    lo, hi = 2.0, 4.0
    delta = (hi - lo) / nbins
    q = np.round((ax[m] - lo) / delta) * delta + lo
    q = np.clip(q, lo, hi - delta)
    y[m] = np.sign(x[m]) * q
    return y


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--glob", default=os.path.join(ROOT, "c5G", "*.npz"))
    args = ap.parse_args()
    xs = []
    for p in sorted(glob.glob(args.glob)):
        with np.load(p) as d:
            xs.append(d["lead_phi"].astype(np.float64))
    x = np.concatenate(xs)
    out = {"date": "2026-11-02", "n": int(len(x)),
           "scenarios": {}}
    for name, fn in (("T5_mixed_per_octave_truncation", mixed_truncate),
                     ("T6_localized_uniform_quantizer", local_uniform)):
        y = fn(x)
        s = base.summarise(y)
        out["scenarios"][name] = {
            "b_global": s["b_global"],
            "octave_0": s["octaves"].get("0"),
            "octave_1": s["octaves"].get("1"),
            "octave_2": s["octaves"].get("2"),
        }
        print(name, "b_global =", s["b_global"],
              "| octave 0:", s["octaves"].get("0"),
              "| octave 1:", s["octaves"].get("1"))
    tmp = OUT + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(out, fh, indent=1)
    os.replace(tmp, OUT)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
