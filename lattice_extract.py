#!/usr/bin/env python3
"""E2 raw extraction: leading-jet azimuth float32 bit patterns.

Runs the frozen leading-jet selection of phase0_extract.py and stores the raw
float32 values (as uint32 bit patterns) instead of quantized b-bit symbols. The
output is the empirical alphabet used by the lattice-aligned E2 experiment.

Usage:
  python3 lattice_extract.py --files uris.txt --out latticeG/f01 --pt-min 20
"""

import argparse
import hashlib
import json
import os
import time

import numpy as np

from phase0_extract import iter_leading_phi


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--files", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--pt-min", type=float, default=20.0)
    ap.add_argument("--eta-max", type=float, default=2.5)
    ap.add_argument("--batch", type=int, default=50000)
    ap.add_argument("--max-events", type=int, default=0)
    args = ap.parse_args()

    sources = [line.strip() for line in open(args.files) if line.strip()]
    vals = []
    for src in sources:
        for v in iter_leading_phi([src], False, args.pt_min, args.eta_max,
                                  args.batch, args.max_events, False):
            vals.append(np.float32(v))

    arr = np.asarray(vals, dtype=np.float32)
    bits = np.ascontiguousarray(arr).view(np.uint32)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    bin_path = args.out + ".lattice.bin"
    bits.tofile(bin_path)

    manifest = {
        "extractor": "leading-jet phi, raw float32 bit patterns (uint32, native order)",
        "params": {
            "files": sources,
            "pt_min": args.pt_min,
            "eta_max": args.eta_max,
            "batch": args.batch,
            "max_events": args.max_events,
        },
        "n_leading": int(len(arr)),
        "lattice_file": os.path.basename(bin_path),
        "lattice_sha256": sha256_file(bin_path),
        "code_sha256": {
            "lattice_extract.py": sha256_file(__file__),
            "phase0_extract.py": sha256_file(os.path.join(os.path.dirname(__file__), "phase0_extract.py")),
        },
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    with open(args.out + ".manifest.json", "w") as fh:
        json.dump(manifest, fh, indent=1)
    print("%s: %d leading jets" % (args.out, len(arr)))


if __name__ == "__main__":
    main()
