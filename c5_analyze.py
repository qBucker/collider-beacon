#!/usr/bin/env python3
"""C5 hadronic extension: offline aggregation and pre-registered checks.

Reads c5G/fNN.npz + manifests, computes per-arm pooled statistics, CP bounds,
seam-band ratios, storage-precision census, and Fourier amplitudes.

Usage:
  python3 c5_analyze.py --glob 'c5G/f[0-9][0-9].npz' --out c5-aggregate.json
"""

import argparse
import glob
import json
import math
import os
import time

import numpy as np
from scipy import stats

ALPHA = 1e-6
B8, B12 = 8, 12
SEAM_LO, SEAM_HI = 227, 234          # inclusive, at b=8 (paper's seam band)
SIDEBAND_WIDTHS = (4, 16, 32)


def bits_of_phi(phi, b):
    u = (phi + math.pi) / (2 * math.pi)
    u = np.clip(u, 1e-15, 1.0 - 1e-15)
    return np.minimum((u * (1 << b)).astype(np.int64), (1 << b) - 1)


def cp_hmin(counts, alpha=ALPHA):
    n = int(counts.sum())
    nbins = counts.size
    x = int(counts.max())
    if n == 0:
        return None
    if x >= n:
        return 0.0
    p_ub = float(stats.beta.ppf(1 - alpha / nbins, x + 1, n - x))
    return -math.log2(p_ub)


def uniformity(phi, b):
    if phi.size == 0:
        return None
    counts = np.bincount(bits_of_phi(phi, b), minlength=1 << b).astype(np.int64)
    n = int(counts.sum())
    exp = n / (1 << b)
    chi2 = float(((counts - exp) ** 2).sum() / exp)
    chi2_p = float(stats.chi2.sf(chi2, (1 << b) - 1))
    u = (phi.astype(np.float64) + math.pi) / (2 * math.pi)
    ks = stats.kstest(u, "uniform")
    return {
        "n": n,
        "bins": 1 << b,
        "h_min_CP_bonferroni": cp_hmin(counts),
        "max_bin_count": int(counts.max()),
        "chi2": chi2,
        "chi2_p": chi2_p,
        "ks_stat": float(ks.statistic),
        "ks_p": float(ks.pvalue),
        "counts": counts.tolist(),
    }


def seam_ratio(phi):
    """Band mean over sideband mean at b=8, with three sideband widths."""
    if phi.size == 0:
        return None
    counts = np.bincount(bits_of_phi(phi, 8), minlength=256).astype(np.float64)
    band = counts[SEAM_LO:SEAM_HI + 1].mean()
    out = {}
    for w in SIDEBAND_WIDTHS:
        left = counts[SEAM_LO - w:SEAM_LO]
        right = counts[SEAM_HI + 1:SEAM_HI + 1 + w]
        side = np.concatenate([left, right]).mean()
        out["w%d" % w] = float(band / side) if side else None
    return out


def precision_census(phi):
    """Trailing-zero census of the float32 mantissa (storage-precision probe)."""
    if phi.size == 0:
        return None
    bits = phi.astype(np.float32).view(np.uint32)
    mant = (bits & np.uint32(0x7FFFFF)).astype(np.uint64)
    lowbit = mant & (~mant + np.uint64(1))
    tz = np.where(mant == 0, 23,
                  np.floor(np.log2(np.maximum(lowbit, 1))).astype(np.int64))
    vals, cnts = np.unique(tz, return_counts=True)
    return {"tz_histogram": {int(v): int(c) for v, c in zip(vals, cnts)},
            "fraction_tz_ge_11": float((tz >= 11).mean()),
            "fraction_tz_ge_15": float((tz >= 15).mean())}


def fourier_amplitudes(phi, b=12, kmax=24):
    if phi.size == 0:
        return None
    counts = np.bincount(bits_of_phi(phi, b), minlength=1 << b).astype(np.float64)
    n = counts.sum()
    spec = np.fft.rfft(counts) / n
    amps = np.abs(spec)
    sig = np.sqrt(n) * amps[1:kmax + 1]
    return {"b": b,
            "n": float(n),
            "amplitude": {int(k): float(amps[k]) for k in range(1, kmax + 1)},
            "significance": {int(k): float(sig[k - 1]) for k in range(1, kmax + 1)}}


def fold_test(phi, k, nbins=30):
    """Post-hoc: fold the azimuth modulo 2*pi/k and report the profile."""
    if phi.size == 0:
        return None
    period = 2 * math.pi / k
    fold = np.mod(phi + math.pi, period)
    counts, _ = np.histogram(fold, bins=nbins, range=(0.0, period))
    n = counts.sum()
    exp = n / nbins
    chi2 = float(((counts - exp) ** 2).sum() / exp)
    return {"k": k, "period_deg": 360.0 / k, "bins": nbins,
            "chi2": chi2, "dof": nbins - 1,
            "p": float(stats.chi2.sf(chi2, nbins - 1)),
            "profile_over_mean": [float(c / exp) for c in counts],
            "min_over_mean": float(counts.min() / exp),
            "max_over_mean": float(counts.max() / exp)}


def summarize(name, phi):
    return {
        "name": name,
        "b8": uniformity(phi, B8),
        "b12": uniformity(phi, B12),
        "seam_ratio": seam_ratio(phi),
        "precision": precision_census(phi),
        "fourier": fourier_amplitudes(phi),
        "fold": {str(k): fold_test(phi, k) for k in (12, 18)},
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--glob", default="c5G/f[0-9][0-9].npz")
    ap.add_argument("--out", default="c5-aggregate.json")
    args = ap.parse_args()

    files = sorted(glob.glob(args.glob))
    if not files:
        raise SystemExit("no files match %s" % args.glob)

    arms = {}
    per_file = []
    counters_total = {}
    for path in files:
        z = np.load(path)
        man_path = path[:-4] + ".manifest.json"
        man = json.load(open(man_path)) if os.path.exists(man_path) else {}
        for k, v in man.get("counters", {}).items():
            counters_total[k] = counters_total.get(k, 0) + int(v)
        per_file.append({"file": os.path.basename(path),
                         "counters": man.get("counters", {}),
                         "npz_sha256": man.get("outputs", {}).get("npz_sha256")})
        for arm in ("lead_phi", "sub_phi", "third_phi", "btag_phi",
                    "btag080_phi", "dimuon_phi", "sv_phi"):
            if arm not in z.files:
                continue
            arms.setdefault(arm, []).append(z[arm].astype(np.float64))

    results = {"generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               "files": len(files),
               "counters": counters_total,
               "arms": {},
               "per_file": per_file}
    for arm, chunks in arms.items():
        phi = np.concatenate(chunks) if chunks else np.zeros(0)
        result = summarize(arm, phi)
        # per-file tercile stability for the seam ratio and b8 h_min
        idx = np.array_split(np.arange(len(chunks)), 3) if len(chunks) >= 3 else []
        terciles = []
        for t, sel in enumerate(idx):
            p = np.concatenate([chunks[i] for i in sel]) if len(sel) else np.zeros(0)
            r = seam_ratio(p)
            u8 = uniformity(p, B8)
            terciles.append({"tercile": t, "n": int(p.size),
                             "seam_ratio_w16": (r or {}).get("w16"),
                             "h_min_b8": (u8 or {}).get("h_min_CP_bonferroni")})
        result["terciles"] = terciles
        # per-file Fourier stability at the storage-beat and high-order lines
        pf = {}
        for k in (7, 12, 18):
            zs = []
            for chunk in chunks:
                if chunk.size < 1000:
                    continue
                f = fourier_amplitudes(chunk)
                zs.append(f["significance"][k])
            if zs:
                zs = np.array(zs)
                pf[str(k)] = {"median_z": float(np.median(zs)),
                              "min_z": float(zs.min()), "max_z": float(zs.max()),
                              "files": int(zs.size),
                              "files_z_gt_3": int((zs > 3).sum())}
        result["per_file_fourier"] = pf
        results["arms"][arm] = result

    tmp = args.out + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(results, fh)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, args.out)
    print(json.dumps({k: {"n_b8": v["b8"]["n"] if v["b8"] else 0,
                          "h_min_b8": v["b8"]["h_min_CP_bonferroni"] if v["b8"] else None,
                          "h_min_b12": v["b12"]["h_min_CP_bonferroni"] if v["b12"] else None,
                          "seam_w16": (v["seam_ratio"] or {}).get("w16")}
                      for k, v in results["arms"].items()}, indent=1))


if __name__ == "__main__":
    main()
