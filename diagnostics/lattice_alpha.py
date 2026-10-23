#!/usr/bin/env python3
"""E2 main experiment: lattice-aligned vs linear binning.

Reads the raw leading-jet azimuth float32 bit patterns written by
lattice_extract.py and compares:

  A  linear b=8 and b=12 controls          (must reproduce 7.8413 and 11.3098)
  B  linear b=13 and b=14                  (beat-suppressed intermediate points)
  C  empirical alphabet: signed phi bit patterns (the lattice-aligned construction)
  S  synthetic truth: 5.211e6 uniform phi on (-pi, pi] quantized to the same
     12-bit lattice (signed canonical)

The empirical-alphabet CP bound uses a fixed reference alphabet B_ref (the
signed synthetic B_eff) so that a smaller real-data B_eff cannot inflate the
result. The two-stage arm uses a seeded random interleave (not a sequential
split).

Signed canonical (amendment 3): the paper's b=8/b=12 measurement is over signed
phi; folding is a 2-to-1 map and loses exactly one bit, so the folded arm is
kept only as a pipeline self-check (`C_folded_selfcheck`), never as the primary
judgment.

Usage:
  python3 diagnostics/lattice_alpha.py --lattice-dir latticeG \
      --out diagnostics/lattice-alpha.json --fig diagnostics/lattice-alpha.png
  python3 diagnostics/lattice_alpha.py --synthetic-only --synthetic-seeds 10 \
      --out /tmp/synthetic-calibration.json
"""

import argparse
import glob
import json
import math
import os

import numpy as np
from scipy.stats import beta

ALPHA = 1e-6
B_REF = 78400          # signed reference alphabet (10-seed B_eff 78,210-78,530)
B_REF_FOLDED = 39200   # folded reference, for the self-check only
SPLIT_SEED = 20261023


def cp_h(counts, n, alpha=ALPHA, B=None):
    k = int(counts.max())
    if k >= n:
        return 0.0, k, n
    if B is None:
        B = len(counts)
    p_hi = beta.ppf(1.0 - alpha / B, k + 1, n - k)
    return -math.log2(p_hi), k, n


def linear_counts(phi, b):
    u = (phi + math.pi) / (2.0 * math.pi)
    idx = np.floor(u * (1 << b)).astype(np.int64)
    idx = np.clip(idx, 0, (1 << b) - 1)
    return np.bincount(idx, minlength=1 << b)


def empirical_signed(phi):
    """Signed phi bit patterns: the primary lattice-aligned construction."""
    u = np.ascontiguousarray(phi.astype(np.float32)).view(np.uint32)
    return np.unique(u, return_counts=True)


def empirical_folded(phi):
    """Folded |phi| bit patterns: pipeline self-check only (loses one bit)."""
    a = np.abs(phi).astype(np.float32)
    u = np.ascontiguousarray(a).view(np.uint32)
    return np.unique(u, return_counts=True)


def two_stage_h(vals, alpha=ALPHA, split_seed=SPLIT_SEED):
    """Split-half with a seeded random interleave.

    A sequential split would confound the estimate with time-dependent
    luminosity/acceptance; the permutation makes the halves exchangeable.
    """
    n = len(vals)
    n1 = n // 2
    perm = np.random.default_rng(split_seed).permutation(n)
    a = vals[perm[:n1]]
    b = vals[perm[n1:]]
    uniq, counts = np.unique(a, return_counts=True)
    mode = uniq[int(np.argmax(counts))]
    k = int((b == mode).sum())
    n2 = len(b)
    if k >= n2:
        return 0.0, k, n2, int(mode)
    p_hi = beta.ppf(1.0 - alpha, k + 1, n2 - k)
    return -math.log2(p_hi), k, n2, int(mode)


def quantize_lattice(x):
    """Round float64 x (signed or positive) to a 12-bit-mantissa float32 value."""
    x = np.asarray(x, dtype=np.float64)
    out = np.zeros_like(x, dtype=np.float32)
    m = x != 0
    xm = np.abs(x[m])
    _, e = np.frexp(xm)
    ulp = np.exp2((e - 13).astype(np.float64))
    q = np.round(xm / ulp) * ulp
    out[m] = (np.sign(x[m]) * q).astype(np.float32)
    return out


def fingerprint(counts):
    c = counts.astype(np.float64)
    c = c / c.mean()
    f = np.abs(np.fft.rfft(c - 1.0))
    f[0] = 0
    peak = int(np.argmax(f))
    lag7 = float(np.corrcoef(c[:-7], c[7:])[0, 1])
    return {"fft_peak_cycles_per_circle": peak, "lag7_autocorr": lag7}


def synthetic_arm(n, seed, b_ref, split_seed=SPLIT_SEED):
    rng = np.random.default_rng(seed)
    x = rng.uniform(-math.pi, math.pi, n)   # signed canonical
    q = quantize_lattice(x)
    uq, cq = np.unique(np.ascontiguousarray(q).view(np.uint32), return_counts=True)
    h1, k1, _ = cp_h(cq, len(q), B=b_ref)
    qb = np.ascontiguousarray(q).view(np.uint32)
    h2, k2, n2, mode2 = two_stage_h(qb, split_seed=split_seed)
    uf, cf = empirical_folded(q)
    hf, kf, _ = cp_h(cf, len(q), B=B_REF_FOLDED)
    raw_signed = -math.log2(k1 / len(q))
    raw_folded = -math.log2(kf / len(q))
    return {
        "seed": int(seed),
        "S1_h_inf": h1,
        "S1_B_eff": int(len(uq)),
        "S1_max_count": k1,
        "S2_h_inf": h2,
        "S2_certify_count": k2,
        "S2_n_certify": int(n2),
        "S2_selected_phi": float(np.array([mode2], dtype=np.uint32).view(np.float32)[0]),
        "F_h_inf": hf,
        "F_B_eff": int(len(uf)),
        "F_max_count": kf,
        "folded_minus_signed_raw": raw_folded - raw_signed,
        "folded_minus_signed_cp": hf - h1,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lattice-dir", default="latticeG")
    ap.add_argument("--out", required=True)
    ap.add_argument("--fig")
    ap.add_argument("--synthetic-events", type=int, default=5211771)
    ap.add_argument("--seed", type=int, default=20261023)
    ap.add_argument("--synthetic-seeds", type=int, default=10)
    ap.add_argument("--B-ref", type=int, default=B_REF)
    ap.add_argument("--split-seed", type=int, default=SPLIT_SEED)
    ap.add_argument("--synthetic-only", action="store_true")
    args = ap.parse_args()

    seeds = [synthetic_arm(args.synthetic_events, args.seed + i, args.B_ref,
                           args.split_seed)
             for i in range(args.synthetic_seeds)]
    s1 = np.array([s["S1_h_inf"] for s in seeds])
    s2 = np.array([s["S2_h_inf"] for s in seeds])
    bands = {
        "B_ref": int(args.B_ref),
        "split_seed": int(args.split_seed),
        "n_seeds": int(args.synthetic_seeds),
        "S1_mean": float(s1.mean()),
        "S1_std": float(s1.std(ddof=1)),
        "S1_band_2sigma": [float(s1.mean() - 2 * s1.std(ddof=1)),
                           float(s1.mean() + 2 * s1.std(ddof=1))],
        "S2_mean": float(s2.mean()),
        "S2_std": float(s2.std(ddof=1)),
        "S2_band_2sigma": [float(s2.mean() - 2 * s2.std(ddof=1)),
                           float(s2.mean() + 2 * s2.std(ddof=1))],
        "folded_selfcheck": {
            "raw_mean": float(np.mean([s["folded_minus_signed_raw"] for s in seeds])),
            "raw_std": float(np.std([s["folded_minus_signed_raw"] for s in seeds], ddof=1)),
            "raw_band_2sigma": [
                float(np.mean([s["folded_minus_signed_raw"] for s in seeds]) -
                      2 * np.std([s["folded_minus_signed_raw"] for s in seeds], ddof=1)),
                float(np.mean([s["folded_minus_signed_raw"] for s in seeds]) +
                      2 * np.std([s["folded_minus_signed_raw"] for s in seeds], ddof=1))],
            "cp_mean": float(np.mean([s["folded_minus_signed_cp"] for s in seeds])),
            "cp_std": float(np.std([s["folded_minus_signed_cp"] for s in seeds], ddof=1)),
            "cp_band_2sigma": [
                float(np.mean([s["folded_minus_signed_cp"] for s in seeds]) -
                      2 * np.std([s["folded_minus_signed_cp"] for s in seeds], ddof=1)),
                float(np.mean([s["folded_minus_signed_cp"] for s in seeds]) +
                      2 * np.std([s["folded_minus_signed_cp"] for s in seeds], ddof=1))],
            "note": "distribution-level relation is -1 bit; these bands are the "
                    "estimator-level acceptance intervals",
        },
        "seeds": seeds,
    }

    if args.synthetic_only:
        json.dump(bands, open(args.out, "w"), indent=1)
        print(json.dumps(bands, indent=1))
        return

    files = sorted(glob.glob(os.path.join(args.lattice_dir, "f[0-9][0-9].lattice.bin")))
    if not files:
        raise SystemExit("no lattice files in %s" % args.lattice_dir)
    vals = np.concatenate([np.fromfile(f, dtype=np.uint32) for f in files])
    phi = vals.view(np.float32)
    n = len(phi)

    res = {"files": [os.path.basename(f) for f in files], "n_leading": int(n),
           "synthetic_bands": bands}

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

    u, counts = empirical_signed(phi)
    hC, kC, _ = cp_h(counts, n, B=args.B_ref)
    arg = int(np.argmax(counts))
    res["C_empirical_signed"] = {
        "h_inf": hC,
        "B_eff_real": int(len(u)),
        "B_ref": int(args.B_ref),
        "max_count": kC,
        "max_count_over_n": float(kC / n),
        "argmax_phi": float(np.array([u[arg]], dtype=np.uint32).view(np.float32)[0]),
    }

    ua = np.ascontiguousarray(phi.astype(np.float32)).view(np.uint32)
    h2, k2, n2, mode2 = two_stage_h(ua, split_seed=args.split_seed)
    res["C_two_stage"] = {
        "h_inf": h2,
        "n_select": int(len(ua) // 2),
        "n_certify": int(n2),
        "certify_count": k2,
        "selected_phi": float(np.array([mode2], dtype=np.uint32).view(np.float32)[0]),
    }

    # Folded self-check: distribution-level relation is exactly one bit, but the
    # CP estimator adds a penalty asymmetry; the acceptance band is calibrated
    # on the synthetic ensemble (see predictions/...-amendment-3.md).
    uf, cf = empirical_folded(phi)
    hF, kF, _ = cp_h(cf, n, B=B_REF_FOLDED)
    raw_signed = -math.log2(kC / n)
    raw_folded = -math.log2(kF / n)
    res["C_folded_selfcheck"] = {
        "h_inf_folded": hF,
        "B_eff_folded": int(len(uf)),
        "B_ref_folded": B_REF_FOLDED,
        "h_folded_minus_signed_cp": hF - hC,
        "h_folded_minus_signed_raw": raw_folded - raw_signed,
        "note": "distribution-level difference is -1 bit; estimator-level bands "
                "are the synthetic 2-sigma intervals, not -1.00 +/- 0.02",
    }

    json.dump(res, open(args.out, "w"), indent=1)
    print(json.dumps(res, indent=1))

    if args.fig:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        labels = ["b=8", "b=12", "b=13", "b=14", "empirical (signed)", "2-stage",
                  "synth S1", "synth S2"]
        hs = [res["A_linear_b8"]["h_inf"], res["A_linear_b12"]["h_inf"],
              res["B_linear_b13"]["h_inf"], res["B_linear_b14"]["h_inf"],
              res["C_empirical_signed"]["h_inf"], res["C_two_stage"]["h_inf"],
              bands["S1_mean"], bands["S2_mean"]]
        fig, ax = plt.subplots(figsize=(9, 4.4))
        ax.bar(labels, hs, color=["#8c8c8c", "#2b5d8a", "#5a8fbf", "#8fb8d9",
                                  "#b23a2f", "#d97b6c", "#d9a441", "#e8c37a"])
        ax.axhline(bands["S1_mean"], color="#b23a2f", ls="--", lw=1,
                   label="S1 synthetic mean %.2f" % bands["S1_mean"])
        ax.axhline(bands["S2_mean"], color="#d9a441", ls=":", lw=1,
                   label="S2 synthetic mean %.2f" % bands["S2_mean"])
        ax.axhline(11.3098, color="#2b5d8a", ls=":", lw=1, label="linear b=12, 11.31")
        ax.set_ylabel(r"$h_\infty$ [bit/event]")
        ax.set_title("E2: lattice-aligned vs linear binning")
        ax.legend(frameon=False, fontsize=8)
        fig.tight_layout()
        fig.savefig(args.fig, dpi=160)
        print("figure ->", args.fig)


if __name__ == "__main__":
    main()
