#!/usr/bin/env python3
# phase0_verify.py — independent re-check of a Phase 0 manifest
# Recomputes: bits-file hash, manifest internal consistency,
# and re-derives the entropy bound from reported counts.
# Usage: python3 phase0_verify.py run1.manifest.json [twin.bits.bin]
import hashlib, json, math, sys

def sha(b): return hashlib.sha256(b).hexdigest()

m = json.load(open(sys.argv[1]))
ok = True

# 1. bits file hash
bits = open(m["outputs"]["bits_file"], "rb").read()
h = sha(bits)
match = (h == m["outputs"]["bits_sha256"])
ok &= match
print(f"[{'OK' if match else 'FAIL'}] bits sha256: {h[:16]}...")

# 2. optional twin comparison (C++/ROOT reproduction)
if len(sys.argv) > 2:
    twin = open(sys.argv[2], "rb").read()
    same = (twin == bits)
    ok &= same
    print(f"[{'OK' if same else 'FAIL'}] twin bit-identical reproduction")

# 3. recompute min-entropy from reported numbers
r = m["results"]; p = m["params"]
n = m["events_with_bits"]; nb = m["bins"]
from scipy import stats
alpha_corr = p["alpha"] / nb
x = r["max_bin_count"]
U = 1.0 if x >= n else float(stats.beta.ppf(1 - alpha_corr, x + 1, n - x))
hmin = -math.log2(U)
close = abs(hmin - r["min_entropy_bits_per_event"]) < 1e-9
ok &= close
print(f"[{'OK' if close else 'FAIL'}] min-entropy recompute: {hmin:.4f} bits/event")

# 4. pass/fail against Phase 0 thresholds (program v2.0 section 2.4)
_min_bits = 10 if p["b"] >= 10 else p["b"] - 2   # R2: truthful gate label (b-2 rule for b<10)
gates = {
    f"min_entropy>={_min_bits} bits/event": hmin >= _min_bits,
    "chi2_p>1e-6": r["chi2_p"] > 1e-6,
    "ks_p>1e-6": r["ks_p"] > 1e-6,
}
for k, v in gates.items():
    ok &= v
    print(f"[{'OK' if v else 'FAIL'}] gate: {k}")

print("\nVERDICT:", "ALL GREEN" if ok else "RED — fix before writing results chapter")
sys.exit(0 if ok else 1)
