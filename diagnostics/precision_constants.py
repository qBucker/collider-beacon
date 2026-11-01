#!/usr/bin/env python3
"""Precision constants of the public PFNanoAOD azimuth branches.

Measures, from the raw float32 azimuths in c5G/*.npz (67 files):

  * the explicit mantissa count b in each binary octave, by testing
    u(e) = 2^(e-b) for b = 8..16 and taking the value that puts the
    stored numbers on an integer grid;
  * the on-grid fraction at the best b;
  * the octave step ratio u(e)/u(e+1) (expected 2);
  * the uniform-vs-mantissa gap Delta/u(1) with Delta = 2*pi/4096
    (expected pi, i.e. log2(pi) = 1.6515 bit).

A synthetic 12-bit-mantissa quantizer is the control.  The ATLAS raw
jet_phi is not stored in the existing smoke products; the script records
that as pending.

Writes diagnostics/precision-constants-2026-11-01.json.
"""

import argparse
import glob
import json
import math
import os
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(HERE, "precision-constants-2026-11-01.json")
KEYS = ("lead_phi", "sv_phi")
B_CANDIDATES = tuple(range(8, 17))
MIN_UNIQUE = 30


def octave_of(x):
    ax = np.abs(x)
    ax = ax[ax > 0]
    return np.floor(np.log2(ax)).astype(int)


def grid_score(x, e, b):
    """Mean distance to the nearest multiple of 2^(e-b), in units of the step."""
    step = np.exp2(e - b)
    y = x / step
    r = np.abs(y - np.round(y))
    return float(np.mean(r)), float(np.mean(r < 1e-3))


def measure_octave(x, e_all, e):
    vals = np.unique(x[e_all == e])
    if len(vals) < MIN_UNIQUE:
        return None
    # the smallest mantissa count that puts every value on the grid; a
    # finer count always fits, so the coarsest passing count is the data's
    best = None
    for b in B_CANDIDATES:
        mean_r, frac = grid_score(vals, e, b)
        if frac >= 0.999:
            best = {"b": b, "mean_residual": mean_r, "on_grid_fraction": frac}
            break
    if best is None:
        scored = [(grid_score(vals, e, b)[1], b, grid_score(vals, e, b)[0])
                  for b in B_CANDIDATES]
        frac, b, mean_r = max(scored)
        best = {"b": b, "mean_residual": mean_r, "on_grid_fraction": frac}
    dd = np.diff(np.sort(vals))
    dd = dd[dd > 0]
    best["n_unique"] = int(len(vals))
    best["step"] = float(np.exp2(e - best["b"]))
    best["median_diff"] = float(np.median(dd)) if len(dd) else float("nan")
    return best


def analyse_key(paths, key):
    xs = []
    per_file = []
    for p in paths:
        d = np.load(p)
        if key not in d:
            continue
        x = d[key].astype(np.float64)
        xs.append(x)
        per_file.append({"file": os.path.basename(p), "n": int(len(x))})
    x = np.concatenate(xs) if xs else np.array([])
    if len(x) == 0:
        return {"key": key, "n": 0}
    e_all = octave_of(x)
    octaves = {}
    for e in range(-8, 2):
        m = measure_octave(x, e_all, e)
        if m is not None:
            octaves[str(int(e))] = m
    b_global = None
    if octaves:
        counts = {}
        for e, m in octaves.items():
            if int(e) >= -4:          # robust range; lower octaves have few values
                counts[m["b"]] = counts.get(m["b"], 0) + 1
        if counts:
            b_global = max(counts, key=counts.get)
    return {
        "key": key,
        "n": int(len(x)),
        "files": per_file,
        "octaves": octaves,
        "b_global": b_global,
        "n_octaves_used": len(octaves),
    }


def synthetic_control(n=2_000_000, b=12, seed=20261101):
    rng = np.random.default_rng(seed)
    x = rng.uniform(-math.pi, math.pi, n)
    ax = np.abs(x)
    e = np.floor(np.log2(ax))
    step = np.exp2(e - b)
    xq = np.round(x / step) * step
    xq = xq.astype(np.float32).astype(np.float64)
    res = {}
    for ee in range(-2, 2):
        vals = np.unique(xq[e == ee])
        if len(vals) < MIN_UNIQUE:
            continue
        best = None
        for bb in B_CANDIDATES:
            mr, fr = grid_score(vals, ee, bb)
            if fr >= 0.999:
                best = {"b": bb, "mean_residual": mr, "on_grid_fraction": fr}
                break
        if best is None:
            scored = [(grid_score(vals, ee, bb)[1], bb, grid_score(vals, ee, bb)[0])
                      for bb in B_CANDIDATES]
            fr, bb, mr = max(scored)
            best = {"b": bb, "mean_residual": mr, "on_grid_fraction": fr}
        best.update({"n_unique": int(len(vals)), "step": float(np.exp2(ee - best["b"]))})
        res[str(int(ee))] = best
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--glob", default=os.path.join(ROOT, "c5G", "*.npz"))
    ap.add_argument("--out", default=OUT)
    args = ap.parse_args()
    t0 = time.time()
    paths = sorted(glob.glob(args.glob))
    out = {
        "date": "2026-11-01",
        "n_files": len(paths),
        "keys": list(KEYS),
        "b_candidates": list(B_CANDIDATES),
        "atlas": {"status": "pending (raw jet_phi not stored in the smoke products)"},
        "keys_out": [],
        "synthetic": synthetic_control(),
    }
    for key in KEYS:
        r = analyse_key(paths, key)
        out["keys_out"].append(r)
        print(f"{key}: n={r['n']} files={len(r['files'])} b_global={r.get('b_global')}")
        for e, m in sorted(r.get("octaves", {}).items(), key=lambda kv: int(kv[0])):
            print(f"  e={e:>3s}  b={m['b']}  step={m['step']:.4e}  "
                  f"on_grid={m['on_grid_fraction']:.4f}  resid={m['mean_residual']:.2e}")
    # derived constants
    b = None
    for r in out["keys_out"]:
        if r.get("b_global") is not None:
            b = r["b_global"]
            break
    if b is not None:
        u1 = math.exp2(1 - b)
        delta = 2 * math.pi / 4096
        out["derived"] = {
            "b_global": b,
            "u_e1": u1,
            "delta_uniform_b12": delta,
            "ratio_delta_over_u1": delta / u1,
            "log2_ratio": math.log2(delta / u1),
            "pi": math.pi,
            "log2_pi": math.log2(math.pi),
        }
        print(f"derived: b={b} Delta/u(1)={delta/u1:.6f} "
              f"log2={math.log2(delta/u1):.6f} (pi={math.pi:.6f})")
    out["wall_s"] = round(time.time() - t0, 1)
    tmp = args.out + ".tmp"
    json.dump(out, open(tmp, "w"), indent=1)
    os.replace(tmp, args.out)
    print("wrote", args.out, f"{out['wall_s']} s")


if __name__ == "__main__":
    main()
