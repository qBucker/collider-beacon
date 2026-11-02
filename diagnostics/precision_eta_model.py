#!/usr/bin/env python3
"""Closed-form model for the certified entropy floor eta(b).

The floor scan (`precision_floor_scan.py`) measures, for b = 8..16,

    h_floor(b) = -log2( cp_upper(N_max(b), n, alpha/2^b) ),
    h_cap(b)   = b - 1 + log2(2*pi),
    eta(b)     = h_floor / h_cap.

This script predicts the whole curve from one source parameter, the maximum
azimuth density M (per radian), calibrated at the coarsest resolution b = 8
where the statistical and lattice corrections are smallest.

Model (see beacon-paper/precision-passport/eta-closed-form-2026-11-02.md):

  * the product stores float32 values with b_m = 12 explicit mantissa bits,
    so the atom width in octave e is u_e = 2^(e - b_m);
  * a uniform b-bit analysis bin has width Delta = 2*pi/2^b and holds
    ceil(r_e) atoms, r_e = Delta/u_e; its maximum probability is
    p_max(b) = max_e M * u_e * ceil(r_e);
  * the observed maximum count is a Gumbel maximum over the bins that hold
    ceil(r_e) atoms, m_eff = (r_e - floor(r_e)) * 2^b,
        N_max ~ lambda + sqrt(lambda) * G(m_eff),  lambda = n * p_max;
  * the certified value is the Clopper-Pearson upper bound at alpha/2^b.

Output: diagnostics/precision-eta-model-2026-11-02.json (no timestamps;
byte-identical reruns), plus a table on stdout.

Usage: python3 diagnostics/precision_eta_model.py [--glob 'c5G/*.npz']
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
OUT = os.path.join(HERE, "precision-eta-model-2026-11-02.json")
ALPHA = 1e-6
BM = 12
BS = tuple(range(8, 17))
E_MIN, E_MAX = -8, 1  # azimuths satisfy |phi| < pi < 4, so the largest octave is 1


def cp_upper(k, n, alpha):
    if k >= n:
        return 1.0
    return float(stats.beta.ppf(1 - alpha, k + 1, n - k))


def gumbel_loc(m):
    """First-order location of the maximum of m standard-normal draws."""
    lm = math.log(m)
    return math.sqrt(2 * lm) - (math.log(lm) + math.log(4 * math.pi)) / (
        2 * math.sqrt(2 * lm)
    )


def octave_cells(e, b, bm=BM):
    """(r, k_max, m_eff, u) for octave e at analysis resolution b."""
    u = 2.0 ** (e - bm)
    r = (2 * math.pi / (1 << b)) / u
    k = math.ceil(r)
    if abs(r - round(r)) < 1e-12:
        k = int(round(r))
    frac = 1.0 if r == int(r) else r - math.floor(r)
    return r, k, max(frac * (1 << b), 2.0), u


def model_curve(M, n, bs=BS, bm=BM):
    """Predicted (h, eta, N, octave) for each b."""
    rows = []
    for b in bs:
        best = None
        for e in range(E_MIN, E_MAX + 1):
            r, k, meff, u = octave_cells(e, b, bm)
            lam = n * M * u * k
            N = lam + math.sqrt(lam) * gumbel_loc(meff)
            if best is None or N > best[0]:
                best = (N, e, r, k, meff, lam)
        N, e, r, k, meff, lam = best
        N_int = int(round(N))
        h = -math.log2(cp_upper(N_int, n, ALPHA / (1 << b)))
        cap = b - 1 + math.log2(2 * math.pi)
        rows.append(
            {
                "b": b,
                "n_pred_max": N_int,
                "lambda": lam,
                "octave": e,
                "r": r,
                "k_atoms": k,
                "m_eff": meff,
                "h_pred": h,
                "h_cap": cap,
                "eta_pred": h / cap,
            }
        )
    return rows


def measure_curve(x, n, bs=BS):
    rows = []
    for b in bs:
        nb = 1 << b
        k = np.minimum(((x + math.pi) / (2 * math.pi) * nb).astype(np.int64), nb - 1)
        counts = np.bincount(k, minlength=nb)
        nmax = int(counts.max())
        h = -math.log2(cp_upper(nmax, n, ALPHA / nb))
        rows.append({"b": b, "n_max": nmax, "h_meas": h})
    return rows


def calibrate_M(x, n, bm=BM):
    """Single-parameter calibration: match h_pred(b=8) to h_meas(b=8)."""
    meas8 = measure_curve(x, n, (8,))[0]["h_meas"]
    lo, hi = 0.05, 0.30
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        pred8 = model_curve(mid, n, (8,), bm)[0]["h_pred"]
        if pred8 > meas8:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi), meas8


def boundaries(M, n, alpha=ALPHA, bm=BM, e_peak=1):
    """Lattice and statistical boundaries, in bits.

    b_lat: analysis resolution where the uniform bin equals the atom width
           of the coarsest octave (r = 1).
    b_stat: analysis resolution where the statistical inflation epsilon = 1,
           ignoring the lattice; solved by bisection.
    """
    b_lat = bm + math.log2(2 * math.pi) - e_peak

    def eps(b):
        m = 2.0 ** b
        lam = n * M * (2 * math.pi / m)  # smooth-source limit, kappa -> 1
        g = gumbel_loc(m)
        z = float(stats.norm.ppf(1 - alpha / m))
        return (g + z) / math.sqrt(lam)

    lo, hi = 4.0, 40.0
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if eps(mid) > 1.0:
            hi = mid
        else:
            lo = mid
    b_stat = 0.5 * (lo + hi)
    return {"b_lat": b_lat, "b_stat": b_stat, "b_star": min(b_lat, b_stat)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--glob", default=os.path.join(ROOT, "c5G", "*.npz"))
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--bm", type=int, default=BM)
    args = ap.parse_args()

    paths = sorted(glob.glob(args.glob))
    out = {
        "date": "2026-11-02",
        "alpha": ALPHA,
        "b_mantissa": args.bm,
        "model": "p_max = M u_e ceil(r_e); N = lam + sqrt(lam) G(m_eff); CP alpha/2^b",
        "keys": {},
    }
    for key in ("lead_phi", "sv_phi"):
        xs = []
        for p in paths:
            d = np.load(p)
            if key in d:
                xs.append(d[key].astype(np.float64))
        if not xs:
            continue
        x = np.concatenate(xs)
        n = int(len(x))
        meas = measure_curve(x, n)
        M, h8 = calibrate_M(x, n, args.bm)
        pred = model_curve(M, n, bm=args.bm)
        for pm, mm in zip(pred, meas):
            pm["h_meas"] = mm["h_meas"]
            pm["n_max_meas"] = mm["n_max"]
            pm["dh"] = pm["h_pred"] - mm["h_meas"]
            pm["eta_meas"] = mm["h_meas"] / pm["h_cap"]
            pm["eta_resid"] = pm["eta_pred"] - pm["eta_meas"]
        out["keys"][key] = {
            "n": n,
            "M": M,
            "h8_meas": h8,
            "rows": pred,
            "max_abs_dh": max(abs(r["dh"]) for r in pred),
            "max_abs_deta": max(abs(r["eta_resid"]) for r in pred),
            "boundaries": boundaries(M, n, bm=args.bm),
        }
        print(f"\n{key}: n={n}  M={M:.5f}  "
              f"max|dh|={out['keys'][key]['max_abs_dh']:.4f} bit  "
              f"max|deta|={out['keys'][key]['max_abs_deta']:.4f}")
        print("  b  N_pred  N_meas  h_pred  h_meas    dh    eta_p  eta_m  eta_r")
        for r in pred:
            print(f"  {r['b']:2d} {r['n_pred_max']:7d} {r['n_max_meas']:8d} "
                  f"{r['h_pred']:7.4f} {r['h_meas']:7.4f} {r['dh']:+.4f}  "
                  f"{r['eta_pred']:.4f} {r['eta_meas']:.4f} {r['eta_resid']:+.4f}")
        bd = out["keys"][key]["boundaries"]
        print(f"  boundaries: b_lat={bd['b_lat']:.3f}  b_stat={bd['b_stat']:.2f}  "
              f"b_star={bd['b_star']:.3f}")

    tmp = args.out + ".tmp"
    with open(tmp, "w") as f:
        json.dump(out, f, indent=1)
    os.replace(tmp, args.out)
    print("\nwrote", args.out)


if __name__ == "__main__":
    main()
