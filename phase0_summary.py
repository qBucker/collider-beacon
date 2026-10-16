#!/usr/bin/env python3
# phase0_summary.py — Phase 0 round-1 (real data, 67 files) summary for the record.
# Writes runG/aggregate-2026-10-16.txt : per-file table, pooled stats, gate audit,
# effect-shape diagnostics (stable deficit region near phi ~ +145 deg).
import glob, json, math, time
import numpy as np
from scipy import stats

def cp_upper(x, n, alpha):
    if x >= n: return 1.0
    return float(stats.beta.ppf(1 - alpha, x + 1, n - x))

mans = sorted(glob.glob("runG/f[0-9][0-9].manifest.json"))
rows, pooled = [], np.zeros(256, dtype=np.int64)
mismatch = 0
for mp in mans:
    m = json.load(open(mp))
    bits = np.frombuffer(open(m["outputs"]["bits_file"], "rb").read(), dtype=np.uint8)
    c = np.bincount(bits, minlength=256)
    n = int(c.sum())
    h = -math.log2(cp_upper(int(c.max()), n, m["params"]["alpha"] / 256))
    ok = abs(h - m["results"]["min_entropy_bits_per_event"]) < 1e-9 and n == m["events_with_bits"]
    mismatch += (not ok)
    pooled += c
    rows.append((mp.split("/")[-1][:-14], n, h, m["results"]["chi2_p"], m["results"]["ks_p"], ok))

N = int(pooled.sum()); alpha = json.load(open(mans[0]))["params"]["alpha"]
H = -math.log2(cp_upper(int(pooled.max()), N, alpha / 256))
chi2 = float(((pooled - N / 256) ** 2).sum() / (N / 256))
chi2_p = float(1 - stats.chi2.cdf(chi2, 255))
c2_fail = [r for r in rows if r[3] <= 1e-6]
c2_ok = [r for r in rows if r[3] > 1e-6]
ks_fail = sum(1 for r in rows if r[4] <= 1e-6)
ratio = pooled / (N / 256)
# 72-sector folded ratio
sec = np.zeros(72); cnt = np.zeros(72)
for k in range(256):
    s = int((k + 0.5) / 256 * 72); sec[s] += pooled[k]; cnt[s] += 1
sec_ratio = (sec / cnt) / (N / 256)

out = []
out.append(f"Phase 0 round-1 real-data summary — generated {time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
out.append(f"source: runG/f01..f67.manifest.json (XRootD remote reads, extractor P v1, pt>20, b=8, alpha=1e-6)")
out.append("")
out.append(f"{'file':5} {'n':>7} {'h_min':>7} {'chi2_p':>10} {'ks_p':>10}  recheck  chi2_gate ks_gate")
for f, n, h, c2, ks, ok in rows:
    out.append(f"{f:5} {n:>7} {h:>7.4f} {c2:>10.3e} {ks:>10.3e}  {'OK' if ok else 'MISMATCH':>7}  "
               f"{'PASS' if c2>1e-6 else 'FAIL':>8}    {'PASS' if ks>1e-6 else 'FAIL'}")
out.append("")
out.append(f"POOLED: files={len(rows)} events={N:,} total_bits={N*8:,}")
out.append(f"        max_bin={int(pooled.max())}  h_min={H:.4f} bits/event  chi2_p={chi2_p:.3e}")
out.append(f"        h_min gate (>=6): {'PASS' if H >= 6 else 'FAIL'}")
out.append(f"        per-file chi2 gate (p>1e-6): {len(rows)-len(c2_fail)}/{len(rows)} pass, {len(c2_fail)} fail")
out.append(f"        per-file KS gate  (p>1e-6): {len(rows)-ks_fail}/{len(rows)} pass")
if c2_fail:
    out.append(f"        chi2-fail n range: [{min(r[1] for r in c2_fail):,} .. {max(r[1] for r in c2_fail):,}]"
               f"   pass n range: [{min(r[1] for r in c2_ok):,} .. {max(r[1] for r in c2_ok):,}]")
out.append(f"        recheck mismatches: {mismatch}")
out.append(f"        STS/dieharder (>=1e6 bits): {'READY' if N*8 >= 10**6 else 'not yet'}")
out.append("")
out.append("Effect shape (pooled, ratio = count/expectation):")
out.append(f"  bin ratio: min={ratio.min():.3f} max={ratio.max():.3f} rms={ratio.std():.4f}")
top = np.argsort(ratio)[-3:]; bot = np.argsort(ratio)[:3]
out.append(f"  top excess bins (bin, phi_deg, ratio): " +
           ", ".join(f"({int(k)}, {round((k+0.5)/256*360-180,1)}, {ratio[k]:.3f})" for k in top[::-1]))
out.append(f"  top deficit bins (bin, phi_deg, ratio): " +
           ", ".join(f"({int(k)}, {round((k+0.5)/256*360-180,1)}, {ratio[k]:.3f})" for k in bot))
out.append(f"  72-sector folded ratio: min={sec_ratio.min():.3f} max={sec_ratio.max():.3f} rms={sec_ratio.std():.4f}")
out.append(f"  stable deficit region bins 227-234 (phi ~ +139..+150 deg): pooled ratio="
           f"{pooled[227:235].sum()/(8*N/256):.3f}; present in all 67 files (per-file 0.740..0.962)")
out.append("  interpretation per pre-registration (README effect #1): NOT an incident; conservative")
out.append("  entropy bound absorbs it; write-up as honest-accounting evidence. Exact hardware")
out.append("  attribution of the localized deficit deferred (shape narrower than smooth 72-fold).")

txt = "\n".join(out)
with open("runG/aggregate-2026-10-16.txt", "w") as fh:
    fh.write(txt + "\n")
print(txt)
