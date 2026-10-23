#!/usr/bin/env python3
"""E2 integrity gate: verify every lattice file against its manifest.

Checks, per file:
  - manifest and lattice file both exist;
  - file size == 4 * n_leading (uint32 patterns);
  - sha256(lattice file) == manifest.lattice_sha256;
  - every value is a finite float32 with |phi| <= pi (no NaN, no range escape);
  - n_leading is in a broad plausibility range;
  - params record pt_min=20, eta_max=2.5.
Also reports orphan lattice files, duplicate digests, and the extractor code
hash groups (a mid-run write-path change creates two groups; data semantics are
unchanged).

Exit code 0 only if every manifest passes. Use --require-complete to also
require the expected file count and pooled n.

Usage:
  python3 diagnostics/lattice_integrity.py --lattice-dir latticeG \
      --out diagnostics/lattice-integrity.json
  python3 diagnostics/lattice_integrity.py --lattice-dir latticeG \
      --require-complete --expected-files 67 --expected-n 5211771
"""

import argparse
import glob
import hashlib
import json
import math
import os

import numpy as np

PT_MIN = 20.0
ETA_MAX = 2.5
N_MIN = 1000
N_MAX = 200000
PI = math.pi
# Jet_phi is stored with a 12-bit mantissa; the grid point above pi is
# 3.1416015625 (pi + 8.8e-6), so a tolerance of one storage ULP is required.
PI_TOL = 1e-3


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def check_one(manifest_path):
    with open(manifest_path) as fh:
        man = json.load(fh)
    base = manifest_path[:-len(".manifest.json")]
    bin_path = os.path.join(os.path.dirname(manifest_path),
                            man.get("lattice_file", os.path.basename(base) + ".lattice.bin"))
    out = {"manifest": os.path.basename(manifest_path), "errors": []}
    n = man.get("n_leading")
    out["n_leading"] = n
    out["code_sha256"] = man.get("code_sha256", {})

    if not os.path.exists(bin_path):
        out["errors"].append("missing lattice file")
        return out
    size = os.path.getsize(bin_path)
    out["size"] = size
    if not isinstance(n, int) or n <= 0:
        out["errors"].append("bad n_leading")
    elif size != 4 * n:
        out["errors"].append("size %d != 4*n_leading %d" % (size, 4 * n))
    if not (N_MIN <= (n or 0) <= N_MAX):
        out["errors"].append("n_leading %s outside [%d,%d]" % (n, N_MIN, N_MAX))

    sha = sha256_file(bin_path)
    out["sha256"] = sha
    if sha != man.get("lattice_sha256"):
        out["errors"].append("sha256 mismatch")

    params = man.get("params", {})
    if params.get("pt_min") != PT_MIN:
        out["errors"].append("pt_min != %s" % PT_MIN)
    if params.get("eta_max") != ETA_MAX:
        out["errors"].append("eta_max != %s" % ETA_MAX)

    if size % 4 == 0 and size > 0:
        bits = np.fromfile(bin_path, dtype=np.uint32)
        phi = bits.view(np.float32)
        finite = np.isfinite(phi)
        out["nonfinite"] = int((~finite).sum())
        out["beyond_pi"] = int((np.abs(phi[finite]) > PI).sum())
        out["range_escape"] = int((np.abs(phi[finite]) > PI + PI_TOL).sum())
        if out["nonfinite"]:
            out["errors"].append("non-finite values")
        if out["range_escape"]:
            out["errors"].append("values outside [-pi-tol,pi+tol]")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lattice-dir", default="latticeG")
    ap.add_argument("--out", required=True)
    ap.add_argument("--expected-files", type=int, default=0)
    ap.add_argument("--expected-n", type=int, default=0)
    ap.add_argument("--require-complete", action="store_true")
    args = ap.parse_args()

    manifests = sorted(glob.glob(os.path.join(args.lattice_dir, "f[0-9][0-9].manifest.json")))
    bins = sorted(glob.glob(os.path.join(args.lattice_dir, "f[0-9][0-9].lattice.bin")))
    results = [check_one(m) for m in manifests]

    bad = [r for r in results if r["errors"]]
    ns = [r.get("n_leading", 0) for r in results if isinstance(r.get("n_leading"), int)]
    total_n = int(sum(ns))
    sha_seen = {}
    for r in results:
        if r.get("sha256"):
            sha_seen.setdefault(r["sha256"], []).append(r["manifest"])
    dup = {k: v for k, v in sha_seen.items() if len(v) > 1}
    orphans = sorted(set(os.path.basename(b) for b in bins) -
                     set(r["manifest"].replace(".manifest.json", ".lattice.bin") for r in results))
    code_groups = {}
    for r in results:
        key = r.get("code_sha256", {}).get("lattice_extract.py", "missing")
        code_groups.setdefault(key, []).append(r["manifest"])

    report = {
        "lattice_dir": args.lattice_dir,
        "n_manifests": len(results),
        "n_bins": len(bins),
        "n_pass": len(results) - len(bad),
        "n_fail": len(bad),
        "total_leading": total_n,
        "total_bytes": 4 * total_n,
        "failures": bad,
        "orphan_lattice_files": orphans,
        "duplicate_digests": dup,
        "code_sha256_groups": {k: {"count": len(v), "files": v} for k, v in code_groups.items()},
        "files": results,
    }

    complete_errors = []
    if args.expected_files and len(results) != args.expected_files:
        complete_errors.append("manifests %d != expected %d" % (len(results), args.expected_files))
    if args.expected_n and total_n != args.expected_n:
        complete_errors.append("total_leading %d != expected %d" % (total_n, args.expected_n))
    report["completeness"] = {"expected_files": args.expected_files,
                              "expected_n": args.expected_n,
                              "errors": complete_errors}

    with open(args.out, "w") as fh:
        json.dump(report, fh, indent=1)
    print("manifests=%d pass=%d fail=%d total_leading=%d"
          % (len(results), report["n_pass"], report["n_fail"], total_n))
    for e in complete_errors:
        print("completeness: " + e)
    if bad:
        for r in bad:
            print("FAIL %s: %s" % (r["manifest"], "; ".join(r["errors"])))
    if orphans:
        print("orphans: %s" % ", ".join(orphans))
    if dup:
        print("duplicate digests: %d groups" % len(dup))

    ok = not bad and not complete_errors
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
