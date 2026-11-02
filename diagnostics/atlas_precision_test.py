#!/usr/bin/env python3
"""ATLAS precision cross-test: mantissa count, floor scan, eta model.

Input: raw leading-jet azimuth arrays (*.phis.npy) from the ATLAS Open Data
smoke sample (record 93933), written by atlas/atlas_extract.py.  The arrays
are float64, exact conversions of the delivered float32 values.

The script repeats the CMS measurement (`precision_constants.py`,
`precision_floor_scan.py`) on the ATLAS product and applies the closed-form
model of `precision_eta_model.py`:

  1. octave scan b = 8..24: the smallest mantissa count whose grid puts at
     least 99.9% of the values on grid;
  2. certified floor h_floor(b) for b = 8..16 (alpha = 1e-6, Bonferroni);
  3. eta(b) = h_floor / h_cap and the two boundaries b_lat, b_stat;
  4. one-parameter calibration of the source density M at b = 8, then
     predictions for b = 9..16.

Writes diagnostics/atlas-precision-2026-11-02.json (no timestamps;
byte-identical reruns).

Usage:
  python3 diagnostics/atlas_precision_test.py --glob '<dir>/*.phis.npy'
"""

import argparse
import glob
import json
import math
import os

import numpy as np

from precision_eta_model import (
    ALPHA,
    BS,
    boundaries,
    cp_upper,
    model_curve,
    measure_curve,
    calibrate_M,
)

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "atlas-precision-2026-11-02.json")
B_CANDIDATES = tuple(range(8, 25))
MIN_UNIQUE = 30


def octave_scan(x):
    """Smallest b (8..24) with on-grid fraction >= 0.999, per octave."""
    ax = np.abs(x)
    ax = ax[ax > 0]
    e_all = np.floor(np.log2(ax)).astype(int)
    out = {}
    for e in range(-8, 2):
        vals = np.unique(x[e_all == e])
        if len(vals) < MIN_UNIQUE:
            continue
        best = None
        for b in B_CANDIDATES:
            step = math.exp2(e - b)
            y = vals / step
            r = np.abs(y - np.round(y))
            frac = float(np.mean(r < 1e-3))
            if frac >= 0.999:
                best = {"b": b, "on_grid_fraction": frac,
                        "n_unique": int(len(vals))}
                break
        if best is None:
            scored = []
            for b in B_CANDIDATES:
                step = math.exp2(e - b)
                y = vals / step
                r = np.abs(y - np.round(y))
                scored.append((float(np.mean(r < 1e-3)), b))
            frac, b = max(scored)
            best = {"b": b, "on_grid_fraction": frac,
                    "n_unique": int(len(vals)), "no_pass_in_range": True}
        out[str(int(e))] = best
    return out


def ongrid_at(x, e_target, b):
    ax = np.abs(x)
    ax = ax[ax > 0]
    e_all = np.floor(np.log2(ax)).astype(int)
    vals = np.unique(x[e_all == e_target])
    step = math.exp2(e_target - b)
    y = vals / step
    r = np.abs(y - np.round(y))
    return {"b": b, "octave": e_target, "on_grid_fraction": float(np.mean(r < 1e-3)),
            "n_unique": int(len(vals))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--glob", required=True)
    ap.add_argument("--out", default=OUT)
    args = ap.parse_args()

    paths = sorted(glob.glob(args.glob))
    xs = [np.load(p).astype(np.float64) for p in paths]
    x = np.concatenate(xs) if xs else np.zeros(0)
    n = int(len(x))

    octaves = octave_scan(x)
    meas = measure_curve(x, n)

    b_global = None
    counts = {}
    for e, m in octaves.items():
        if int(e) >= -4 and not m.get("no_pass_in_range"):
            counts[m["b"]] = counts.get(m["b"], 0) + 1
    if counts:
        b_global = max(counts, key=counts.get)
    bm = b_global if b_global is not None else 23

    M, h8 = calibrate_M(x, n, bm)
    pred = model_curve(M, n, bm=bm)
    for pm, mm in zip(pred, meas):
        pm["h_meas"] = mm["h_meas"]
        pm["n_max_meas"] = mm["n_max"]
        pm["dh"] = pm["h_pred"] - mm["h_meas"]
        pm["eta_meas"] = mm["h_meas"] / pm["h_cap"]
        pm["eta_resid"] = pm["eta_pred"] - pm["eta_meas"]

    out = {
        "date": "2026-11-02",
        "alpha": ALPHA,
        "n_files": len(paths),
        "files": [os.path.basename(p) for p in paths],
        "n": n,
        "octaves": octaves,
        "b_global": b_global,
        "b_mantissa_model": bm,
        "ongrid_b12_octave1": ongrid_at(x, 1, 12),
        "floor": pred,
        "M": M,
        "h8_meas": h8,
        "max_abs_dh": max(abs(r["dh"]) for r in pred),
        "max_abs_deta": max(abs(r["eta_resid"]) for r in pred),
        "boundaries": boundaries(M, n, bm=bm),
    }

    print(f"ATLAS: {len(paths)} files, n = {n}")
    print("octave scan (smallest b with >=0.999 on grid):")
    for e, m in sorted(octaves.items(), key=lambda kv: int(kv[0])):
        print(f"  e={e:>3s} b={m['b']} on_grid={m['on_grid_fraction']:.5f}"
              f"{' (NO PASS <=24)' if m.get('no_pass_in_range') else ''}")
    print(f"b_global = {b_global}")
    print(f"on-grid at b=12, octave 1: {out['ongrid_b12_octave1']['on_grid_fraction']:.5f}")
    print(f"\nM = {M:.5f}  max|dh| = {out['max_abs_dh']:.4f} bit  "
          f"max|deta| = {out['max_abs_deta']:.4f}")
    print("  b  N_pred  N_meas  h_pred  h_meas    dh    eta_p  eta_m  eta_r")
    for r in pred:
        print(f"  {r['b']:2d} {r['n_pred_max']:7d} {r['n_max_meas']:8d} "
              f"{r['h_pred']:7.4f} {r['h_meas']:7.4f} {r['dh']:+.4f}  "
              f"{r['eta_pred']:.4f} {r['eta_meas']:.4f} {r['eta_resid']:+.4f}")
    bd = out["boundaries"]
    print(f"boundaries: b_lat={bd['b_lat']:.3f}  b_stat={bd['b_stat']:.2f}  "
          f"b_star={bd['b_star']:.3f}")

    tmp = args.out + ".tmp"
    with open(tmp, "w") as f:
        json.dump(out, f, indent=1)
    os.replace(tmp, args.out)
    print("\nwrote", args.out)


if __name__ == "__main__":
    main()
