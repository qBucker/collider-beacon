#!/usr/bin/env python3
"""Audit the JetHT PFNanoAOD extraction (third product).

Reads jetht5.phis.npy written by the frozen extractor and reports the
per-octave lattice, on-grid fraction and certified floors; compares with the
ZeroBias leading-jet reference.

Usage: python3 jetht_audit.py <dir>
"""

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "passport"))
from pp_audit import core


def main():
    d = sys.argv[1]
    x = np.load(os.path.join(d, "jetht5.phis.npy")).astype(np.float64)
    prof = core.measure_profile(x, "JetHT PFNanoAOD leading jet")
    floors = core.floor_scan(x, (8, 16), 1e-6)
    out = {
        "product": "JetHT PFNanoAOD Run2016G (record 31308)",
        "n": int(len(x)),
        "b_global": prof["mantissa_bits"],
        "octaves": {k: v["b"] for k, v in prof["scan"]["octaves"].items()},
        "floors": {str(r["b"]): r for r in floors},
        "zerobias_reference": {"n": 5211771, "b": 12,
                               "h_floor_8": 7.8413, "h_floor_12": 11.3098},
    }
    with open(os.path.join(d, "audit.json"), "w") as fh:
        json.dump(out, fh, indent=1)
    print("JetHT n=%d b_global=%s" % (len(x), prof["mantissa_bits"]))
    for b in (8, 12, 16):
        r = [q for q in floors if q["b"] == b][0]
        print("  b=%d h_floor=%.4f eta=%.4f nmax=%d"
              % (b, r["h_floor"], r["eta"], r["n_max"]))
    print("wrote", os.path.join(d, "audit.json"))


if __name__ == "__main__":
    main()
