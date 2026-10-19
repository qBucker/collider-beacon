#!/usr/bin/env python3
# Measure the same quantity on the upstream MiniAOD file.
# Dataset: CERN Open Data record 30516 (ZeroBias MINIAOD, Run2016G).
# Usage: python3 check_miniaod_precision.py <xrootd-uri> [entry_stop]
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
import xrd_compat  # noqa: F401  (patches fsspec-xrootd integer coercion)
import uproot
import numpy as np

uri = sys.argv[1]
stop = int(sys.argv[2]) if len(sys.argv) > 2 else 3000
base = ("patJets_slimmedJets__PAT./patJets_slimmedJets__PAT.obj/"
        "patJets_slimmedJets__PAT.obj.m_state.p4Polar_.fCoordinates.f")

def trailing_zeros(values):
    bits = values.astype(np.float32).view(np.uint32).astype(np.uint64)
    return np.where(bits == 0, 32,
                    np.log2((bits & (~bits + 1)).astype(np.float64)).astype(int))

f = uproot.open(uri)
t = f["Events"]
print(f"file: {uri}")
print(f"{'component':10s} {'n':>7s} {'min_tz':>6s} {'median':>6s}")
for comp in ["Pt", "Phi", "Eta", "M"]:
    vals = []
    for arr in t[base + comp].array(entry_stop=stop, library="ak"):
        a = np.asarray(arr, dtype=np.float32).ravel()
        if len(a):
            vals.append(a)
    v = np.concatenate(vals)
    tz = trailing_zeros(v)
    print(f"{comp:10s} {len(v):7d} {tz.min():6d} {int(np.median(tz)):6d}")
