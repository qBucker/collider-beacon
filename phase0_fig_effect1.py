#!/usr/bin/env python3
# phase0_fig_effect1.py — Effect #1 (acceptance deficit at phi ~ +145 deg): stability & shape.
# Four pre-registered probes (draw, do not assert):
#   A. run-dependence  — per-file region ratio across all 67 files (expect stable)
#   B. shape           — pooled ratio zoom around the deficit
#   C. pT-dependence   — region ratio vs leading-jet pT threshold (on the local f01 copy)
#   D. ATLAS interface — reserved slot for the future detector-specificity probe
import glob, json, math
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import phase0_extract as P

REG = slice(227, 235)  # bins 227-234

def region_ratio(counts):
    n = counts.sum()
    return counts[REG].sum() / (8 * n / 256), np.sqrt(counts[REG].sum()) / (8 * n / 256)

# ---- A: per-file ----
per_file = []
for mp in sorted(glob.glob("runG/f[0-9][0-9].manifest.json")):
    m = json.load(open(mp))
    bits = np.frombuffer(open(m["outputs"]["bits_file"], "rb").read(), dtype=np.uint8)
    c = np.bincount(bits, minlength=256)
    r, e = region_ratio(c)
    per_file.append((mp.split("/")[-1][:3], m["events_with_bits"], r, e))
pf = np.array([(i, r) for i, (_, _, r, _) in enumerate(per_file)])

# ---- B: pooled shape ----
pooled = np.zeros(256, dtype=np.int64)
for mp in sorted(glob.glob("runG/f[0-9][0-9].manifest.json")):
    m = json.load(open(mp))
    pooled += np.bincount(np.frombuffer(open(m["outputs"]["bits_file"], "rb").read(), dtype=np.uint8), minlength=256)
N = pooled.sum()
ratio = pooled / (N / 256)
band = np.sqrt(pooled) / (N / 256)

# ---- C: pT thresholds on local f01 ----
FP = "data/nano_data2016_1-1.root"
pts = []
for th in (15.0, 20.0, 30.0, 50.0):
    phis = list(P.iter_leading_phi([FP], False, th, 2.5, "200 MB", 0, False))
    c = np.bincount([P.bits_of_phi(p, 8) for p in phis], minlength=256)
    r, e = region_ratio(c)
    pts.append((th, len(phis), r, e))

# ---- figure ----
fig, axes = plt.subplots(2, 2, figsize=(17.5, 10.5))
ax = axes[0][0]
ax.errorbar(pf[:, 0] + 1, [p[2] for p in per_file], yerr=[p[3] for p in per_file],
            fmt="o", ms=3.5, lw=0.8, color="#2b5f8f")
ax.axhline(0.895, color="crimson", ls="--", lw=1, label="pooled 0.895")
ax.text(0.02, 0.05, "thirds: 0.898 / 0.896 / 0.890   (stable, no run trend)",
        transform=ax.transAxes, fontsize=11, color="darkred")
ax.set_xlabel("file index (f01..f67)", fontsize=14)
ax.set_ylabel("region ratio (bins 227–234)", fontsize=13)
ax.set_title("A. Run-dependence — all 67 files", fontsize=15)
ax.legend(fontsize=11); ax.grid(alpha=0.25)

ax = axes[0][1]
z = slice(196, 256)
deg = (np.arange(256) + 0.5) / 256 * 360 - 180
ax.fill_between(deg[z], (ratio - band)[z], (ratio + band)[z], color="#5b79b0", alpha=0.3, lw=0)
ax.step(deg[z], ratio[z], where="mid", color="#2b5f8f", lw=1.1)
ax.axhline(1.0, color="k", lw=0.8, alpha=0.5)
ax.axvspan(139, 150, color="red", alpha=0.10)
ax.set_ylim(0.85, 1.09)
ax.annotate("−10.5% plateau\n(≈11° wide)", xy=(144.5, 0.905), xytext=(112, 0.87),
            fontsize=11, color="darkred", arrowprops=dict(arrowstyle="->", color="darkred"))
ax.set_xlabel("φ [deg] (bins 196–255 shown)", fontsize=13)
ax.set_ylabel("ratio to uniform", fontsize=13)
ax.set_title("B. Shape — pooled 67 files (zoom)", fontsize=15)
ax.grid(alpha=0.25)

ax = axes[1][0]
th = [p[0] for p in pts]; rr = [p[2] for p in pts]; ee = [p[3] for p in pts]
ax.errorbar(th, rr, yerr=ee, fmt="o-", color="#2b5f8f", lw=1.5, ms=6, capsize=4)
for t, n, r, e in pts:
    ax.annotate(f"n={n:,}", (t, r + e), textcoords="offset points", xytext=(0, 8),
                ha="center", fontsize=10)
ax.axhline(1.0, color="k", lw=0.8, alpha=0.5)
ax.set_xlabel("leading-jet pT threshold [GeV]", fontsize=13)
ax.set_ylabel("region ratio (bins 227–234)", fontsize=13)
ax.set_title("C. pT-dependence — f01 local (single file, 153,011 events)", fontsize=15)
ax.grid(alpha=0.25)
ax.set_ylim(0.7, 1.15)

ax = axes[1][1]
ax.axis("off")
ax.text(0.5, 0.74, "D. ATLAS interface — reserved", ha="center", fontsize=16, color="0.35")
ax.text(0.5, 0.42, "Detector-specificity probe (planned):\n"
                   "same extractor on ATLAS open data —\n"
                   "deficit expected to differ shape/position\n"
                   "if it is CMS geometry; absent if physics",
        ha="center", fontsize=12, color="0.45")
ax.add_patch(plt.Rectangle((0.08, 0.08), 0.84, 0.76, fill=False, ec="0.7", ls="--", lw=1.2, transform=ax.transAxes))

fig.suptitle("Effect #1 — localized acceptance deficit at φ ≈ +145°: pre-registered probes "
             "(all measured; Run2016G ZeroBias)", fontsize=16)
fig.tight_layout(rect=(0, 0, 1, 0.96))
out = "runG/effect1_shape_probes.png"
fig.savefig(out, dpi=100)
print(f"saved {out}")
print("per-file region ratio: mean =", round(float(np.mean([p[2] for p in per_file])), 4),
      " std =", round(float(np.std([p[2] for p in per_file])), 4))
print("pT scan:", [(t, n, round(r, 3), round(e, 3)) for t, n, r, e in pts])
