#!/usr/bin/env python3
"""Tamper test for the precision audit.

The audit certifies a declared precision profile (b_m, step law, quantizer).
This script applies four controlled deviations to the delivered CMS PFNano
leading-jet azimuths and records what the audit sees:

  T1  silent mantissa truncation: 12-bit values truncated to the 11-bit grid
      (the coarsest passing b drops from 12 to 11);
  T2  quantizer change: values re-quantized on a uniform 4096-bin grid
      instead of the float octave lattice (no b in 8..16 fits);
  T3  step-law violation localized in octave 1: values shifted by half a
      12-bit quantum (the octave's coarsest passing b moves from 12 to 13);
  T4  sparse off-grid tampering: k = 100, 1,000, 10,000 values shifted by
      half a quantum (the on-grid fraction at b = 12 falls by k/n; the
      declared threshold 0.999 tolerates up to ~0.001 n values).

T4 quantifies the boundary of R2: the precision audit detects systematic
profile deviations, not rare per-value changes; byte-level integrity is the
job of C_data (the content hash), not of the precision audit.

Deterministic: fixed seed, no timestamps in the JSON.

Writes diagnostics/precision-tamper-2026-11-02.json.

Usage: python3 diagnostics/precision_tamper_test.py [--glob 'c5G/*.npz']
"""

import argparse
import glob
import json
import math
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(HERE, "precision-tamper-2026-11-02.json")
B_CANDIDATES = tuple(range(8, 17))
MIN_UNIQUE = 30
THRESHOLD = 0.999
SEED = 20261102


def octave_scan(x):
    """Coarsest b in 8..16 with on-grid fraction >= 0.999, per octave."""
    ax = np.abs(x)
    nz = ax > 0
    e_all = np.full(len(x), -999, dtype=int)
    e_all[nz] = np.floor(np.log2(ax[nz])).astype(int)
    out = {}
    for e in range(-8, 2):
        vals = np.unique(x[nz & (e_all == e)])
        if len(vals) < MIN_UNIQUE:
            continue
        best = None
        for b in B_CANDIDATES:
            step = math.exp2(e - b)
            y = vals / step
            r = np.abs(y - np.round(y))
            frac = float(np.mean(r < 1e-3))
            if frac >= THRESHOLD:
                best = {"b": b, "on_grid_fraction": frac,
                        "n_unique": int(len(vals))}
                break
        if best is None:
            scored = [(float(np.mean(np.abs(vals / math.exp2(e - b) -
                                            np.round(vals / math.exp2(e - b))) < 1e-3)), b)
                      for b in B_CANDIDATES]
            frac, b = max(scored)
            best = {"b": b, "on_grid_fraction": frac,
                    "n_unique": int(len(vals)), "no_pass_in_range": True}
        out[str(int(e))] = best
    b_global = None
    counts = {}
    for e, m in out.items():
        if int(e) >= -4 and not m.get("no_pass_in_range"):
            counts[m["b"]] = counts.get(m["b"], 0) + 1
    if counts:
        b_global = max(counts, key=counts.get)
    return out, b_global


def summarise(x):
    octaves, b_global = octave_scan(x)
    return {"octaves": octaves, "b_global": b_global}


def truncate_bits(x, from_b, to_b):
    """Truncate toward zero from the from_b grid to the to_b grid."""
    out = np.empty_like(x)
    ax = np.abs(x)
    e = np.zeros_like(ax, dtype=int)
    nz = ax > 0
    e[nz] = np.floor(np.log2(ax[nz])).astype(int)
    step = np.exp2(e - to_b)
    out[nz] = np.trunc(x[nz] / step[nz]) * step[nz]
    out[~nz] = x[~nz]
    return out


def uniform_quantize(x, nbins=4096):
    delta = 2 * math.pi / nbins
    k = np.round((x + math.pi) / delta)
    y = k * delta - math.pi
    return np.clip(y, -math.pi, math.pi - delta)


def half_step_shift_octave1(x):
    ax = np.abs(x)
    e = np.zeros_like(ax, dtype=int)
    nz = ax > 0
    e[nz] = np.floor(np.log2(ax[nz])).astype(int)
    shift = np.where(e == 1, np.exp2(e - 12) * 0.5, 0.0)
    return x + shift


def sparse_flips(x, k, seed):
    rng = np.random.default_rng(seed)
    idx = rng.choice(len(x), size=k, replace=False)
    ax = np.abs(x)
    e = np.zeros_like(ax, dtype=int)
    nz = ax > 0
    e[nz] = np.floor(np.log2(ax[nz])).astype(int)
    shift = np.where(nz, np.exp2(e - 12) * 0.5, 0.0)
    y = x.copy()
    y[idx] += shift[idx]
    return y


def on_grid_fraction(x, b=12):
    ax = np.abs(x)
    nz = ax > 0
    e_all = np.full(len(x), 0, dtype=int)
    e_all[nz] = np.floor(np.log2(ax[nz])).astype(int)
    step = np.exp2(e_all[nz] - b)
    xv = x[nz]
    r = np.abs(xv / step - np.round(xv / step))
    return float(np.mean(r < 1e-3))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--glob", default=os.path.join(ROOT, "c5G", "*.npz"))
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--key", default="lead_phi")
    args = ap.parse_args()

    xs = []
    for p in sorted(glob.glob(args.glob)):
        d = np.load(p)
        if args.key in d:
            xs.append(d[args.key].astype(np.float64))
    x = np.concatenate(xs)
    n = int(len(x))

    cases = {}
    cases["honest"] = summarise(x)
    cases["truncate_11bit"] = summarise(truncate_bits(x, 12, 11))
    cases["uniform_quantizer_4096"] = summarise(uniform_quantize(x))
    cases["octave1_half_step"] = summarise(half_step_shift_octave1(x))

    sparse = []
    for k in (100, 1000, 10000):
        y = sparse_flips(x, k, SEED)
        sparse.append({
            "k": k,
            "on_grid_fraction_b12": on_grid_fraction(y),
            "detected_at_threshold": on_grid_fraction(y) < THRESHOLD,
        })

    out = {
        "date": "2026-11-02",
        "key": args.key,
        "n": n,
        "threshold": THRESHOLD,
        "cases": cases,
        "sparse_flips": sparse,
        "detection_limit_k": int(math.ceil((1 - THRESHOLD) * n)),
        "honest_on_grid_b12": on_grid_fraction(x),
    }

    print(f"{args.key}: n = {n}, threshold = {THRESHOLD}")
    for name, r in cases.items():
        print(f"{name}: b_global = {r['b_global']}")
        for e, m in sorted(r["octaves"].items(), key=lambda kv: int(kv[0])):
            flag = " (NO PASS)" if m.get("no_pass_in_range") else ""
            print(f"  e={e:>3s} b={m['b']} on_grid={m['on_grid_fraction']:.4f}{flag}")
    print("\nsparse flips:")
    for r in sparse:
        print(f"  k={r['k']:6d} on_grid_b12={r['on_grid_fraction_b12']:.6f} "
              f"detected={r['detected_at_threshold']}")
    print(f"detection limit k* = (1 - {THRESHOLD}) * n = {out['detection_limit_k']}")

    tmp = args.out + ".tmp"
    with open(tmp, "w") as f:
        json.dump(out, f, indent=1)
    os.replace(tmp, args.out)
    print("\nwrote", args.out)


if __name__ == "__main__":
    main()
