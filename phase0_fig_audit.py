#!/usr/bin/env python3
# phase0_fig_audit.py — Phase 0 audit figure v0: measured × predicted.
# Panel A: phi spectra — real (67 files pooled) vs MC (Pythia8+Delphes 400k, pt20),
#          ratio-to-uniform, with uniformity stats and the pre-registered
#          diagnostic for real-MC differences ("real data vs MC -> detector modeling").
# Panel B: min-entropy vs n — per-file real points + MC points + finite-sample
#          model curve (uniform null, Clopper-Pearson + Bonferroni, alpha=1e-6)
#          + the pre-registered interval [6.0,6.5] at n~5.4k.
import glob, json, math, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats

ALPHA = 1e-6
NB = 256

def cp_hmin(counts):
    n = int(counts.sum())
    x = int(counts.max())
    if x >= n: return 0.0
    p = float(stats.beta.ppf(1 - ALPHA / NB, x + 1, n - x))
    return -math.log2(p)

# ---------- assemble data ----------
real_counts = np.zeros(NB, dtype=np.int64)
real_points = []
for mp in sorted(glob.glob("runG/f[0-9][0-9].manifest.json")):
    m = json.load(open(mp))
    bits = np.frombuffer(open(m["outputs"]["bits_file"], "rb").read(), dtype=np.uint8)
    c = np.bincount(bits, minlength=NB)
    real_counts += c
    real_points.append((m["events_with_bits"], m["results"]["min_entropy_bits_per_event"]))
Nreal = int(real_counts.sum())
h_real_pooled = cp_hmin(real_counts)

mc = json.load(open("mc/mc400k_pt20.manifest.json"))
mc_bits_path = mc["outputs"]["bits_file"]
if not os.path.exists(mc_bits_path):  # manifest recorded a cwd-relative path
    mc_bits_path = os.path.join("mc", os.path.basename(mc_bits_path))
mc_bits = np.frombuffer(open(mc_bits_path, "rb").read(), dtype=np.uint8)
mc_counts = np.bincount(mc_bits, minlength=NB)
Nmc = int(mc_counts.sum())
mc_points = [(Nmc, mc["results"]["min_entropy_bits_per_event"])]
for lbl in ("mc_full_pt30", "mc_full_pt20", "mc_full_pt50"):
    m = json.load(open(f"mc/{lbl}.manifest.json"))
    mc_points.append((m["events_with_bits"], m["results"]["min_entropy_bits_per_event"]))

# chi2/KS of pooled real (bin-level for KS on pooled; the per-file manifests carry exact KS)
chi2_r = float(((real_counts - Nreal / NB) ** 2).sum() / (Nreal / NB))
chi2p_r = float(1 - stats.chi2.cdf(chi2_r, NB - 1))
cdf_r = np.cumsum(real_counts) / Nreal
ks_r = float(np.max(np.abs(cdf_r - (np.arange(1, NB + 1)) / NB)))
# two-sample chi2 real vs MC
tot = Nreal + Nmc
E1 = Nreal * (real_counts + mc_counts) / tot
E2 = Nmc * (real_counts + mc_counts) / tot
chi2_2s = float((((real_counts - E1) ** 2) / np.maximum(E1, 1e-9)).sum()
                + (((mc_counts - E2) ** 2) / np.maximum(E2, 1e-9)).sum())
mask = np.ones(NB, bool); mask[227:235] = False            # excluding deficit region
E1e = Nreal * (real_counts + mc_counts)[mask] / tot
E2e = Nmc * (real_counts + mc_counts)[mask] / tot
chi2_2s_ex = float((((real_counts[mask] - E1e) ** 2) / np.maximum(E1e, 1e-9)).sum()
                   + (((mc_counts[mask] - E2e) ** 2) / np.maximum(E2e, 1e-9)).sum())

# ---------- figure ----------
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(19.5, 6.9),
                               gridspec_kw={"width_ratios": [1.35, 1]})
phi_deg = (np.arange(NB) + 0.5) / NB * 360 - 180

# Panel A
ratio_r = real_counts / (Nreal / NB)
band_r = np.sqrt(real_counts) / (Nreal / NB)
ax1.fill_between(phi_deg, ratio_r - band_r, ratio_r + band_r, color="#5b79b0",
                 alpha=0.30, lw=0, label="real ±1σ (stat)")
ax1.step(phi_deg, ratio_r, where="mid", color="#2b5f8f", lw=0.9,
         label=f"real: CMS ZeroBias Run2016G, 67 files (n={Nreal:,})")
nsp = 8
c32 = mc_counts.reshape(32, nsp).sum(axis=1)
r32 = c32 / (Nmc / 32)
e32 = np.sqrt(c32) / (Nmc / 32)
cen32 = (np.arange(32) + 0.5) / 32 * 360 - 180
ax1.errorbar(cen32, r32, yerr=e32, fmt="o", ms=4, color="#c0392b", lw=1,
             label=f"MC: Pythia8 minbias+Delphes, 400k (n={Nmc:,}, 8-bin grouped)")
ax1.axhline(1.0, color="k", lw=0.8, alpha=0.5)
ax1.axvspan(139, 150, color="red", alpha=0.08)
ax1.annotate("deficit −10.5% (all 67 files, stable)\n→ pre-registered diagnosis:\n'measured ≠ MC → detector modeling'\n(Delphes geometry is φ-symmetric)",
             xy=(144.5, 0.885), xytext=(60, 0.80), fontsize=11,
             arrowprops=dict(arrowstyle="->", color="darkred"), color="darkred")
ax1.set_xlabel("leading-jet φ [deg]", fontsize=16)
ax1.set_ylabel("ratio to uniform", fontsize=16)
ax1.set_title("A. Measured × predicted spectra (audit)", fontsize=18)
ax1.set_ylim(0.72, 1.22)
ax1.legend(fontsize=11, loc="upper left")
ax1.tick_params(labelsize=12)
stats_txt = (f"real pooled:  χ²p = {chi2p_r:.2e}   bin-KS = {ks_r:.4f}\n"
             f"MC 400k:      χ²p = {mc['results']['chi2_p']:.3f}   KS p = {mc['results']['ks_p']:.3f}\n"
             f"two-sample χ²/df = {chi2_2s:.0f}/{NB-1}"
             f"   (without bins 227–234: {chi2_2s_ex:.0f})")
ax1.text(0.015, 0.03, stats_txt, transform=ax1.transAxes, fontsize=11,
         family="monospace", bbox=dict(fc="white", ec="0.7", alpha=0.9))

# Panel B — finite-sample model curve (uniform null, Poisson approx)
rng = np.random.default_rng(20261016)
n_grid = np.unique(np.round(np.logspace(np.log10(40), np.log10(6e6), 26)).astype(int))
curve = []
for n in n_grid:
    e = n / NB
    sims = np.max(rng.poisson(e, size=(400, NB)), axis=1)
    hs = [-math.log2(float(stats.beta.ppf(1 - ALPHA / NB, int(x) + 1, n - int(x))))
          if x < n else 0.0 for x in sims]
    curve.append((n, float(np.mean(hs)), float(np.percentile(hs, 5)), float(np.percentile(hs, 95))))
curve = np.array(curve)
ax2.fill_between(curve[:, 0], curve[:, 2], curve[:, 3], color="0.75", alpha=0.6,
                 label="finite-sample model (uniform null, CP+Bonferroni, 5–95%)")
ax2.plot(curve[:, 0], curve[:, 1], color="0.35", lw=1.5)
ax2.add_patch(plt.Rectangle((4200, 6.0), 2600, 0.5, color="green", alpha=0.15))
ax2.annotate("pre-registered [6.0, 6.5] @ n≈5.4k\n→ MC measured 6.0554 (hit)",
             xy=(5500, 6.25), xytext=(2.2e4, 5.0), fontsize=11, color="darkgreen",
             arrowprops=dict(arrowstyle="->", color="darkgreen"))
rp = np.array(real_points)
ax2.scatter(rp[:, 0], rp[:, 1], s=18, color="#2b5f8f", zorder=5, label="real: per-file (67)")
ax2.scatter([Nreal], [h_real_pooled], marker="*", s=260, color="#c0392b", zorder=6,
            label=f"real: pooled 67 files (n={Nreal:,}, h={h_real_pooled:.3f})")
mp_arr = np.array(mc_points)
ax2.scatter(mp_arr[:, 0], mp_arr[:, 1], marker="s", s=42, color="#c0392b", zorder=5,
            label="MC: Pythia8+Delphes points")
ax2.set_xscale("log")
ax2.set_xlabel("events with bits  n", fontsize=16)
ax2.set_ylabel("min-entropy bound [bits/event]", fontsize=16)
ax2.set_title("B. Entropy closure: h_min vs n", fontsize=18)
ax2.legend(fontsize=11, loc="lower right")
ax2.tick_params(labelsize=12)
ax2.grid(alpha=0.25)

fig.tight_layout()
out = "runG/audit_measured_vs_predicted.png"
fig.savefig(out, dpi=100)
print(f"saved {out}")
print(f"real pooled: n={Nreal:,} h={h_real_pooled:.4f} chi2p={chi2p_r:.3e} binKS={ks_r:.4f}")
print(f"two-sample chi2={chi2_2s:.0f} (df {NB-1}); excluding deficit bins: {chi2_2s_ex:.0f}")
