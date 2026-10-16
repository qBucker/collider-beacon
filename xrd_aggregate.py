#!/usr/bin/env python3
# xrd_aggregate.py — pool Phase 0 real-data runs (runG/f*.manifest.json + bits).
# Rebuilds per-file bin counts from the bits files (b=8 -> 1 byte/event, MSB-first),
# re-derives per-file h_min (audit vs manifest), then pools counts across files
# and applies the same Clopper-Pearson + Bonferroni bound as the extractor.
# Usage: python3 xrd_aggregate.py
import glob, json, math, os
import numpy as np
from scipy import stats

def cp_upper(x, n, alpha):
    if x >= n: return 1.0
    return float(stats.beta.ppf(1 - alpha, x + 1, n - x))

mans = sorted(glob.glob("runG/f[0-9][0-9].manifest.json"))  # exclude f01-local etc.
if not mans:
    raise SystemExit("no runG/fNN.manifest.json found")

rows, pooled = [], np.zeros(256, dtype=np.int64)
mismatch = 0
for mp in mans:
    m = json.load(open(mp))
    bits = np.frombuffer(open(m["outputs"]["bits_file"], "rb").read(), dtype=np.uint8)
    counts = np.bincount(bits, minlength=256)
    n = int(counts.sum())
    hmin = -math.log2(cp_upper(int(counts.max()), n, m["params"]["alpha"] / 256))
    ok = abs(hmin - m["results"]["min_entropy_bits_per_event"]) < 1e-9 and n == m["events_with_bits"]
    mismatch += (not ok)
    pooled += counts
    rows.append((os.path.basename(mp)[:-13], n, hmin, m["results"]["chi2_p"], m["results"]["ks_p"], ok))

print(f"{'file':6} {'n':>7} {'h_min':>7} {'chi2_p':>8} {'ks_p':>7}  recheck")
for f, n, h, c2, ks, ok in rows:
    print(f"{f:6} {n:>7} {h:>7.4f} {c2:>8.4f} {ks:>7.4f}  {'OK' if ok else 'MISMATCH'}")

N = int(pooled.sum()); nb = 256
x = int(pooled.max())
alpha = json.load(open(mans[0]))["params"]["alpha"]
H = -math.log2(cp_upper(x, N, alpha / nb))
chi2 = float(((pooled - N / nb) ** 2).sum() / (N / nb))
chi2_p = float(1 - stats.chi2.cdf(chi2, nb - 1))
print(f"\nPOOLED: files={len(rows)} events={N:,} total_bits={N*8:,}")
print(f"        max_bin={x}  h_min={H:.4f} bits/event  chi2_p={chi2_p:.4f}")
print(f"        h_min gate (>=6): {'PASS' if H >= 6 else 'FAIL'}   recheck mismatches: {mismatch}")
print(f"        STS/dieharder (>=1e6 bits): {'READY' if N*8 >= 10**6 else f'not yet ({N*8:,} bits)'}")
