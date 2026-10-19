#!/usr/bin/env python3
# xrd_aggregate_b12.py — pool Phase 0 b=12 runs (runG12/f*.manifest.json + bits).
# Decodes 12-bit symbols MSB-first from the packed bit files, re-derives per-file
# h_min (audit vs manifest), pools counts across files, and applies the same
# Clopper-Pearson + Bonferroni bound as the extractor.
# Gates follow predictions/2026-10-19-b12-entropy-gate.md.
# Usage: python3 xrd_aggregate_b12.py
import glob, json, math, sys, time
import numpy as np
from scipy import stats

DIR = sys.argv[1] if len(sys.argv) > 1 else "runG12"
BITS = 12
NB = 1 << BITS

def cp_upper(x, n, alpha):
    if x >= n: return 1.0
    return float(stats.beta.ppf(1 - alpha, x + 1, n - x))

def decode_symbols(path, bits_per_symbol=BITS):
    raw = np.frombuffer(open(path, "rb").read(), dtype=np.uint8)
    if raw.size == 0:
        return np.empty(0, dtype=np.int64)
    bits = np.unpackbits(raw)
    nsym = bits.size // bits_per_symbol
    codes = bits[:nsym * bits_per_symbol].reshape(nsym, bits_per_symbol).astype(np.int64)
    weights = (1 << np.arange(bits_per_symbol - 1, -1, -1)).astype(np.int64)
    return codes @ weights

mans = sorted(glob.glob(f"{DIR}/f[0-9][0-9].manifest.json"))
if not mans:
    raise SystemExit(f"no {DIR}/fNN.manifest.json found")

alpha = json.load(open(mans[0]))["params"]["alpha"]
rows, pooled = [], np.zeros(NB, dtype=np.int64)
trunc = 0          # files where the final (partial) symbol is not in the bit file
mismatch = 0       # files where the decoded count differs by more than the one truncated symbol
recheck_dmax = 0.0

for mp in mans:
    m = json.load(open(mp))
    if m["params"]["b"] != BITS:
        mismatch += 1
        continue
    vals = decode_symbols(m["outputs"]["bits_file"])
    counts = np.bincount(vals, minlength=NB)
    n_dec = int(counts.sum())
    n_man = int(m["events_with_bits"])
    if n_dec == n_man - 1:
        trunc += 1
    elif n_dec != n_man:
        mismatch += 1
    h_dec = -math.log2(cp_upper(int(counts.max()), n_dec, alpha / NB)) if n_dec else float("nan")
    h_man = m["results"]["min_entropy_bits_per_event"]
    dh = abs(h_dec - h_man)
    recheck_dmax = max(recheck_dmax, dh)
    pooled += counts
    rows.append((mp.split("/")[-1][:-14], n_man, n_dec, h_man, h_dec, dh,
                 m["results"]["chi2_p"], m["results"]["ks_p"]))

N = int(pooled.sum())
x = int(pooled.max())
H = -math.log2(cp_upper(x, N, alpha / NB))
chi2 = float(((pooled - N / NB) ** 2).sum() / (N / NB))
chi2_p = float(1 - stats.chi2.cdf(chi2, NB - 1))
c2_fail = sum(1 for r in rows if r[6] <= 1e-6)
ks_fail = sum(1 for r in rows if r[7] <= 1e-6)

# seam band: b=8 bins 227-234 -> b=12 bins 3632-3759
lo, hi = 227 * 16, 235 * 16
seam_ratio = float(pooled[lo:hi].sum() / ((hi - lo) * N / NB))

H8 = 8.0  # reference ceiling at b=8 (round 1)
out = []
out.append(f"Phase 0 b=12 entropy-gate summary — generated {time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
out.append(f"source: {DIR}/fNN.manifest.json ({len(rows)} files), extractor P v1, pt>20, b=12, alpha={alpha:g}")
out.append("")
out.append(f"{'file':5} {'n_man':>7} {'n_dec':>7} {'h_man':>8} {'h_dec':>8} {'dh':>7} {'chi2_p':>10} {'ks_p':>10}")
for f, n_man, n_dec, h_man, h_dec, dh, c2, ks in rows:
    out.append(f"{f:5} {n_man:>7} {n_dec:>7} {h_man:>8.4f} {h_dec:>8.4f} {dh:>7.1e} {c2:>10.3e} {ks:>10.3e}")
out.append("")
out.append(f"POOLED: files={len(rows)} events={N:,} total_bits={N * BITS:,}")
out.append(f"        max_bin={x}  h_min={H:.4f} bits/event  chi2_p={chi2_p:.3e}")
out.append(f"        h_min gate (>=10.0): {'PASS' if H >= 10.0 else 'FAIL'}")
out.append(f"        flat-model consistency [11.0, 12.0]: {'PASS' if 11.0 <= H <= 12.0 else 'FAIL'}")
out.append(f"        seam band bins {lo}-{hi - 1}: ratio={seam_ratio:.4f}  "
           f"predicted 0.895+/-0.01 -> {'PASS' if 0.85 <= seam_ratio <= 0.94 else 'FAIL'}")
out.append(f"        per-file chi2 gate (p>1e-6): {len(rows) - c2_fail}/{len(rows)} pass, {c2_fail} fail (diagnostic)")
out.append(f"        per-file KS gate  (p>1e-6): {len(rows) - ks_fail}/{len(rows)} pass (diagnostic)")
out.append(f"        recheck: truncated final symbols={trunc}  mismatches={mismatch}  max|dh|={recheck_dmax:.2e}")
out.append(f"        STS/dieharder (>=1e6 bits): {'READY' if N * BITS >= 10**6 else 'not yet'}")

txt = "\n".join(out)
path = f"{DIR}/aggregate-b12-{time.strftime('%Y-%m-%d')}.txt"
with open(path, "w") as fh:
    fh.write(txt + "\n")
print(txt)
print(f"\nwritten -> {path}")
