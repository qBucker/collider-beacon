#!/usr/bin/env python3
"""Audit demonstration: nominal versus a 5% calibration drift.

Reads the reconstructed Z and H mass files, applies a uniform 5% scale to the
tampered sample, and reports the median and the 16-84% width in each window.
The median is robust against the non-Gaussian tracker tail; the shift
significance uses sigma_median ~ 1.253 sigma68 / sqrt(N).

Usage:
  python3 audit_plot.py --z out/z_reco_2000.csv --h out/h_reco_2000.csv \
      --out out/audit_peaks.png --summary out/audit_summary.json
"""

import argparse
import csv
import json

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def load(path):
    return np.array([float(r["mass"]) for r in csv.DictReader(open(path))])


def peak(m, lo, hi):
    sel = m[(m > lo) & (m < hi)]
    med = float(np.median(sel))
    lo68, hi68 = np.percentile(sel, [16, 84])
    sigma = float(0.5 * (hi68 - lo68))
    return med, sigma, len(sel)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--z", required=True)
    ap.add_argument("--h", required=True)
    ap.add_argument("--z-tampered")
    ap.add_argument("--h-tampered")
    ap.add_argument("--out", required=True)
    ap.add_argument("--summary", required=True)
    args = ap.parse_args()

    z = load(args.z)
    h = load(args.h)
    zt = load(args.z_tampered) if args.z_tampered else z * 1.05
    ht = load(args.h_tampered) if args.h_tampered else h * 1.05
    scale = 1.05

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.6))
    summary = {"scale": scale, "channels": {}}

    for ax, m, m_tamp, name, lo, hi, nbins, unit in [
        (axes[0], z, zt, r"$Z\to\mu\mu$", 60, 120, 30, r"$m_{\mu\mu}$ [GeV]"),
        (axes[1], h, ht, r"$H\to\gamma\gamma$", 115, 140, 25, r"$m_{\gamma\gamma}$ [GeV]"),
    ]:
        nominal = m[(m > lo) & (m < hi)]
        tampered = m_tamp[(m_tamp > lo) & (m_tamp < hi)]
        mn, sn, nn = peak(m, lo, hi)
        mt, st, nt = peak(m_tamp, lo, hi)
        ax.hist(nominal, bins=nbins, range=(lo, hi), histtype="step", lw=1.6,
                color="#2b5d8a", label="nominal")
        ax.hist(tampered, bins=nbins, range=(lo, hi), histtype="step", lw=1.6,
                color="#b23a2f", label="5% calibration")
        ax.axvline(mn, color="#2b5d8a", lw=1.0, ls="--")
        ax.axvline(mt, color="#b23a2f", lw=1.0, ls="--")
        ax.set_xlabel(unit)
        ax.set_ylabel("events / bin")
        ax.set_title(name, fontsize=11)
        ax.legend(frameon=False, fontsize=9)
        shift = mt - mn
        sig_mean = 1.253 * sn / np.sqrt(nn)
        ax.text(0.03, 0.92,
                "peak %.2f -> %.2f GeV\nshift %.2f GeV (%.1f$\\sigma_{mean}$)" %
                (mn, mt, shift, abs(shift) / sig_mean if sig_mean > 0 else float("inf")),
                transform=ax.transAxes, va="top", fontsize=8)
        summary["channels"][name] = {
            "n": int(nn),
            "nominal_peak": mn,
            "nominal_sigma68": sn,
            "tampered_peak": mt,
            "shift_gev": float(shift),
            "shift_sigma_mean": float(abs(shift) / sig_mean) if sig_mean > 0 else None,
        }

    fig.tight_layout()
    fig.savefig(args.out, dpi=160)
    json.dump(summary, open(args.summary, "w"), indent=1)
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
