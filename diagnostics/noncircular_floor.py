#!/usr/bin/env python3
"""Floor scan and closed-form model on a non-circular stored variable.

The azimuth audit bins the circle into m = 2^b equal bins. This script
applies the same audit to a bounded linear variable (p_T or mass): values are
restricted to a fixed range [lo, hi], binned into m = 2^b equal bins, and the
certified floor is the Clopper-Pearson upper limit on the maximum bin
probability (Bonferroni over m bins).

The atom-grain model is the same as for azimuths, with the source density
measured per octave instead of a single peak density:

    p_max(b) = max_e M_e * u_e * ceil(r_e),   u_e = 2^(e - b_m),
    r_e = Delta / u_e,  Delta = (hi - lo) / 2^b,

where M_e is the maximum density (per unit of the variable) inside octave e.
The observed maximum is modelled as a Gumbel selection over m_eff bins,
and one global scale on M_e is calibrated at b = 8.

Deterministic: no timestamps, fixed inputs.

Usage:
  python3 diagnostics/noncircular_floor.py --key sv_pt --lo 1 --hi 50 \
      --out diagnostics/noncircular-pt-2026-11-02.json
"""

import argparse
import glob
import json
import math
import os

import numpy as np
from scipy import stats

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ALPHA = 1e-6
MIN_UNIQUE = 30
NDENS = 1024


def gumbel_loc(m):
    lm = math.log(m)
    return math.sqrt(2 * lm) - (math.log(lm) + math.log(4 * math.pi)) / (
        2 * math.sqrt(2 * lm)
    )


def cp_upper(k, n, alpha):
    if k >= n:
        return 1.0
    return float(stats.beta.ppf(1 - alpha, k + 1, n - k))


def measure_floor(x, lo, hi, bs):
    rows = []
    for b in bs:
        m = 1 << b
        k = np.minimum(((x - lo) / (hi - lo) * m).astype(np.int64), m - 1)
        counts = np.bincount(k, minlength=m)
        nmax = int(counts.max())
        h = -math.log2(cp_upper(nmax, len(x), ALPHA / m))
        rows.append({"b": b, "n_max": nmax, "h_meas": h})
    return rows


def octave_scan(x, lo, hi):
    """Coarsest b in 8..16 with on-grid fraction >= 0.999, per octave."""
    ax = np.abs(x)
    nz = ax > 0
    out = {}
    e_lo = int(math.floor(math.log2(max(lo, 1e-12))))
    e_hi = int(math.floor(math.log2(hi)))
    for e in range(e_lo, e_hi + 1):
        lo_e = max(lo, math.exp2(e))
        hi_e = min(hi, math.exp2(e + 1))
        if hi_e <= lo_e:
            continue
        sel = nz & (ax >= lo_e) & (ax < hi_e)
        vals = np.unique(x[sel])
        if len(vals) < MIN_UNIQUE:
            continue
        best = None
        for b in range(8, 17):
            step = math.exp2(e - b)
            r = np.abs(vals / step - np.round(vals / step))
            frac = float(np.mean(r < 1e-3))
            if frac >= 0.999:
                best = {"b": b, "on_grid": frac, "n_unique": int(len(vals))}
                break
        if best is None:
            best = {"b": None, "on_grid": 0.0, "n_unique": int(len(vals))}
        out[str(e)] = best
    return out


def density_per_octave(x, lo, hi, b_m):
    """Maximum density (per unit variable) inside each octave."""
    n = len(x)
    dens = {}
    for e in range(int(math.floor(math.log2(max(lo, 1e-12)))),
                   int(math.floor(math.log2(hi))) + 1):
        lo_e = max(lo, math.exp2(e))
        hi_e = min(hi, math.exp2(e + 1))
        if hi_e <= lo_e:
            continue
        sel = x[(x >= lo_e) & (x < hi_e)]
        if len(sel) < MIN_UNIQUE:
            continue
        counts, _ = np.histogram(sel, bins=NDENS, range=(lo_e, hi_e))
        width = (hi_e - lo_e) / NDENS
        dens[str(e)] = float(counts.max() / (n * width))
    return dens


def model_curve(x, lo, hi, b_m, dens, bs, n):
    """Predicted (h, lambda, octave) per b for a given density map."""
    rows = []
    for b in bs:
        delta = (hi - lo) / (1 << b)
        best = None
        for e, M in dens.items():
            u = math.exp2(int(e) - b_m)
            r = delta / u
            k = math.ceil(r)
            if abs(r - round(r)) < 1e-12:
                k = int(round(r))
            frac = 1.0 if r == int(r) else r - math.floor(r)
            meff = max(frac * (1 << b), 2.0)
            lam = n * M * u * k
            N = lam + math.sqrt(lam) * gumbel_loc(meff)
            if best is None or N > best[0]:
                best = (N, int(e), meff, lam, r, k)
        N, e, meff, lam, r, k = best
        N_int = int(round(N))
        h = -math.log2(cp_upper(N_int, n, ALPHA / (1 << b)))
        rows.append({"b": b, "n_pred_max": N_int, "lambda": lam,
                     "octave": e, "r": r, "k_atoms": k,
                     "m_eff": meff, "h_pred": h})
    return rows


def calibrate(x, lo, hi, b_m, dens, bs, n):
    """Scale on the density that matches h_pred(b=8) to h_meas(b=8)."""
    meas8 = measure_floor(x, lo, hi, (8,))[0]["h_meas"]
    lo_s, hi_s = 0.05, 20.0
    for _ in range(200):
        mid = 0.5 * (lo_s + hi_s)
        scaled = {k: v * mid for k, v in dens.items()}
        pred8 = model_curve(x, lo, hi, b_m, scaled, (8,), n)[0]["h_pred"]
        if pred8 > meas8:
            lo_s = mid
        else:
            hi_s = mid
    return 0.5 * (lo_s + hi_s), meas8


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--glob", default=os.path.join(ROOT, "b5G", "*.npz"))
    ap.add_argument("--key", default="sv_pt")
    ap.add_argument("--lo", type=float, required=True)
    ap.add_argument("--hi", type=float, required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    xs = []
    for p in sorted(glob.glob(args.glob)):
        with np.load(p) as d:
            xs.append(d[args.key].astype(np.float64))
    x_all = np.concatenate(xs)
    n_total = len(x_all)
    finite = np.isfinite(x_all)
    inside = finite & (x_all >= args.lo) & (x_all < args.hi)
    x = x_all[inside]
    n = len(x)
    octs = octave_scan(x, args.lo, args.hi)
    passing = [v["b"] for v in octs.values() if v["b"] is not None]
    b_m = int(np.bincount(passing).argmax()) if passing else None
    dens = density_per_octave(x, args.lo, args.hi, b_m)
    bs = tuple(range(8, 17))
    meas = measure_floor(x, args.lo, args.hi, bs)
    scale, meas8 = calibrate(x, args.lo, args.hi, b_m, dens, bs, n)
    dens_s = {k: v * scale for k, v in dens.items()}
    pred = model_curve(x, args.lo, args.hi, b_m, dens_s, bs, n)
    rows = []
    for mrow, prow in zip(meas, pred):
        rows.append({"b": mrow["b"], "n_max": mrow["n_max"],
                     "h_meas": mrow["h_meas"], "h_pred": prow["h_pred"],
                     "residual": mrow["h_meas"] - prow["h_pred"],
                     "octave": prow["octave"], "m_eff": prow["m_eff"]})
    out = {
        "date": "2026-11-02", "key": args.key,
        "lo": args.lo, "hi": args.hi,
        "n_total": int(n_total), "n_inside": int(n),
        "octave_scan": octs, "b_m": b_m,
        "density_scale": scale, "density_at_b8": meas8,
        "rows": rows,
        "max_abs_residual": max(abs(r["residual"]) for r in rows),
    }
    tmp = args.out + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(out, fh, indent=1)
    os.replace(tmp, args.out)
    print(f"{args.key}: n_total={n_total} n_inside={n} b_m={b_m} "
          f"scale={scale:.4f}")
    print(f"{'b':>3} {'Nmax':>10} {'h_meas':>8} {'h_pred':>8} {'resid':>8}")
    for r in rows:
        print(f"{r['b']:3d} {r['n_max']:10d} {r['h_meas']:8.4f} "
              f"{r['h_pred']:8.4f} {r['residual']:+8.4f}")
    print(f"max |residual| = {out['max_abs_residual']:.4f} bit")
    print("wrote", args.out)


if __name__ == "__main__":
    main()
