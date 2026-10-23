#!/usr/bin/env python3
"""E2 main experiment: lattice-aligned vs linear binning.

Reads the raw leading-jet azimuth float32 bit patterns written by
lattice_extract.py and compares:

  A  linear b=8 and b=12 controls          (must reproduce 7.8413 and 11.3098)
  B  linear b=13 and b=14                  (beat-suppressed intermediate points)
  C  empirical alphabet: |phi| bit patterns (the lattice-aligned construction)
  S  synthetic truth: 5.211e6 uniform |phi| quantized to the same 12-bit lattice

The CP bound uses the Clopper-Pearson upper limit with Bonferroni over the
alphabet size, alpha = 1e-6.

Usage:
  python3 diagnostics/lattice_alpha.py --lattice-dir latticeG \
      --out diagnostics/lattice-alpha.json --fig diagnostics/lattice-alpha.png
"""

import argparse
import glob
import json
import math
import os

import numpy as np
from scipy.stats import beta

ALPHA = 1e-6
Z = 5.8


def cp_h(counts, n, alpha=ALPHA):
    k = int(counts.max())
    if k >= n:
        return 0.0, k, n
    p_hi = beta.ppf(1.0 - alpha / len(counts), k + 1, n - k)
    return -math.log2(p_hi), k, n


def linear_counts(phi, b):
    u = (phi + math.pi) / (2.0 * math.pi)
    idx = np.floor(u * (1 << b)).astype(np.int64)
    idx = np.clip(idx, 0, (1 << b) - 1)
    return np.bincount(idx, minlength=1 << b)


def empirical_abs(phi):
    a = np.abs(phi).astype(np.float32)
    u = np.ascontiguousarray(a).view(np.uint32)
    return np.unique(u, return_counts=True)


def two_stage_h(vals, alpha=ALPHA):
    """Split-half: select the mode on the first half, certify on the second."""
    n = len(vals)
    n1 = n // 2
    a, b = vals[:n1], vals[n1:]
    uniq, counts = np.unique(a, return_counts=True)
    mode = uniq[int(np.argmax(counts))]
    k = int((b == mode).sum())
    n2 = len(b)
    if k >= n2:
        return 0.0, k, n2, int(mode)
    p_hi = beta.ppf(1.0 - alpha, k + 1, n2 - k)
    return -math.log2(p_hi), k, n2, int(mode)


def quantize_lattice(x):
    """Round positive float64 x to a 12-bit-mantissa float32 value."""
    x = np.asarray(x, dtype=np.float64)
    out = np.zeros_like(x, dtype=np.float32)
    m = x > 0
    xm = x[m]
    _, e = np.frexp(xm)
    ulp = np.exp2((e - 13).astype(np.float64))
    q = np.round(xm / ulp) * ulp
    out[m] = q.astype(np.float32)
    return out


def fingerprint(counts):
    c = counts.astype(np.float64)
    c = c / c.mean()
    f = np.abs(np.fft.rfft(c - 1.0))
    f[0] = 0
    peak = int(np.argmax(f))
    lag7 = float(np.corrcoef(c[:-7], c[7:])[0, 1])
    return {"fft_peak_cycles_per_circle": peak, "lag7_autocorr": lag7}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lattice-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--fig", required=True)
    ap.add_argument("--synthetic-events", type=int, default=5211771)
    ap.add_argument("--seed", type=int, default=20261023)
    args = ap.parse_args()

    files = sorted(glob.glob(os.path.join(args.lattice_dir, "f[0-9][0-9].lattice.bin")))
    if not files:
        raise SystemExit("no lattice files in %s" % args.lattice_dir)
    vals = np.concatenate([np.fromfile(f, dtype=np.uint32) for f in files])
    phi = vals.view(np.float32)
    n = len(phi)

    res = {"files": [os.path.basename(f) for f in files], "n_leading": int(n)}

    c8 = linear_counts(phi, 8)
    h8, k8, _ = cp_h(c8, n)
    res["A_linear_b8"] = {"h_inf": h8, "max_count": k8, "B": 256}

    c12 = linear_counts(phi, 12)
    h12, k12, _ = cp_h(c12, n)
    res["A_linear_b12"] = {"h_inf": h12, "max_count": k12, "B": 4096}
    res["beat_fingerprint_b12"] = fingerprint(c12)

    for b in (13, 14):
        c = linear_counts(phi, b)
        h, k, _ = cp_h(c, n)
        res["B_linear_b%d" % b] = {"h_inf": h, "max_count": k, "B": 1 << b}

    u, counts = empirical_abs(phi)
    hC, kC, _ = cp_h(counts, n)
    arg = int(np.argmax(counts))
    res["C_empirical_abs"] = {
        "h_inf": hC,
        "B_eff": int(len(u)),
        "max_count": kC,
        "max_count_over_n": float(kC / n),
        "argmax_phi": float(np.array([u[arg]], dtype=np.uint32).view(np.float32)[0]),
    }

    ua = np.ascontiguousarray(np.abs(phi).astype(np.float32)).view(np.uint32)
    h2, k2, n2, mode2 = two_stage_h(ua)
    res["C_two_stage"] = {
        "h_inf": h2,
        "n_select": int(len(ua) // 2),
        "n_certify": int(n2),
        "certify_count": k2,
        "selected_phi": float(np.array([mode2], dtype=np.uint32).view(np.float32)[0]),
    }

    rng = np.random.default_rng(args.seed)
    x = rng.uniform(0.0, math.pi, args.synthetic_events)
    q = quantize_lattice(x)
    uq, cq = np.unique(np.ascontiguousarray(q).view(np.uint32), return_counts=True)
    hS, kS, _ = cp_h(cq, len(q))
    res["S_synthetic_uniform"] = {
        "h_inf": hS,
        "B_eff": int(len(uq)),
        "max_count": kS,
        "max_count_over_n": float(kS / len(q)),
    }

    qb = np.ascontiguousarray(q).view(np.uint32)
    hS2, kS2, nS2, modeS2 = two_stage_h(qb)
    res["S_two_stage"] = {
        "h_inf": hS2,
        "n_select": int(len(qb) // 2),
        "n_certify": int(nS2),
        "certify_count": kS2,
        "selected_phi": float(np.array([modeS2], dtype=np.uint32).view(np.float32)[0]),
    }

    json.dump(res, open(args.out, "w"), indent=1)
    print(json.dumps(res, indent=1))

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    labels = ["b=8", "b=12", "b=13", "b=14", "empirical", "2-stage", "synthetic", "synth 2-stage"]
    hs = [res["A_linear_b8"]["h_inf"], res["A_linear_b12"]["h_inf"],
          res["B_linear_b13"]["h_inf"], res["B_linear_b14"]["h_inf"],
          res["C_empirical_abs"]["h_inf"], res["C_two_stage"]["h_inf"],
          res["S_synthetic_uniform"]["h_inf"], res["S_two_stage"]["h_inf"]]
    fig, ax = plt.subplots(figsize=(9, 4.4))
    ax.bar(labels, hs, color=["#8c8c8c", "#2b5d8a", "#5a8fbf", "#8fb8d9",
                              "#b23a2f", "#d97b6c", "#d9a441", "#e8c37a"])
    ax.axhline(12.18, color="#b23a2f", ls="--", lw=1, label="S1 ceiling 12.18")
    ax.axhline(12.31, color="#d9a441", ls=":", lw=1, label="S2 point 12.31")
    ax.axhline(11.3098, color="#2b5d8a", ls=":", lw=1, label="linear b=12, 11.31")
    ax.set_ylabel(r"$h_\infty$ [bit/event]")
    ax.set_title("E2: lattice-aligned vs linear binning")
    ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(args.fig, dpi=160)
    print("figure ->", args.fig)


if __name__ == "__main__":
    main()
