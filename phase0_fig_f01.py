#!/usr/bin/env python3
# phase0_fig_f01.py — first REAL-DATA phi figure (Phase 0, file f01).
# Reads the local immutable copy; uses the frozen extractor's own iterator
# (imported module) so the plotted numbers are the extraction numbers.
import math
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import uproot
from scipy import stats
import phase0_extract as P  # frozen v1 code path

FP = "data/nano_data2016_1-1.root"
with uproot.open(FP) as f:
    n_total = f["Events"].num_entries

phis = np.array(list(P.iter_leading_phi([FP], False, 20.0, 2.5, "200 MB", 0, False)))
n = len(phis)
# counts from the extractor's own binning (exact match with the manifest numbers)
counts = np.bincount([P.bits_of_phi(p, 8) for p in phis], minlength=256)
exp = n / 256.0
sig = math.sqrt(exp)
chi2 = float(((counts - exp) ** 2).sum() / exp)
chi2_p = float(1 - stats.chi2.cdf(chi2, 255))
ks = stats.kstest((phis + math.pi) / (2 * math.pi), "uniform")

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(19.5, 6.9),
                               gridspec_kw={"width_ratios": [1.4, 1]})
x = np.arange(256)
ax1.bar(x, counts, width=1.0, color="#5b79b0", align="center")
ax1.axhspan(exp - 3 * sig, exp + 3 * sig, color="red", alpha=0.10, label="±3σ")
ax1.axhline(exp, color="crimson", lw=1.5, ls="--", label=f"uniform exp. {exp:.1f}")
ax1.set_xlabel("φ bin (0–255, width 24.5 mrad)", fontsize=17)
ax1.set_ylabel("events", fontsize=17)
ax1.set_title("Leading-jet φ — CMS ZeroBias Run2016G (real data)\n"
              f"pT>20, n={n:,}, χ²p={chi2_p:.3f}, KS p={ks.pvalue:.3f}", fontsize=18)
ax1.legend(fontsize=13)
ax1.tick_params(labelsize=13)

ths = [15, 20, 30, 50]
ns = []
for t in ths:
    c = sum(1 for _ in P.iter_leading_phi([FP], False, float(t), 2.5, "200 MB", 0, False))
    ns.append(c)
ax2.plot(ths, ns, "o-", color="#2b5f8f", lw=2)
ax2.set_yscale("log")
ax2.set_xlabel("leading-jet pT threshold [GeV]", fontsize=17)
ax2.set_ylabel(f"qualifying events / {n_total:,} (this file)", fontsize=15)
ax2.set_title(f"Acceptance scan ({n_total:,} ZeroBias events)", fontsize=18)
ax2.tick_params(labelsize=13)
for t, c in zip(ths, ns):
    ax2.annotate(f"{c:,}", (t, c), textcoords="offset points", xytext=(0, 10),
                 ha="center", fontsize=12)

fig.tight_layout()
out = "runG/f01_phi_histogram.png"
fig.savefig(out, dpi=100)
print(f"saved {out} | n={n} chi2_p={chi2_p:.4f} ks_p={ks.pvalue:.4f} | scan={dict(zip(ths, ns))}")
