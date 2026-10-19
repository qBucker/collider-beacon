#!/usr/bin/env python3
# Measure the mantissa precision of stored float branches in the CMS PFNanoAOD file.
# Dataset: CERN Open Data record 31316 (ZeroBias PFNanoAOD, Run2016G).
# Usage: python3 check_nanoad_precision.py <file.root> [entry_stop]
import sys
import uproot
import numpy as np

path = sys.argv[1]
stop = int(sys.argv[2]) if len(sys.argv) > 2 else 8000

branches = ["Jet_phi", "Jet_pt", "Jet_eta", "Jet_mass", "MET_pt", "MET_phi",
            "Electron_phi", "Muon_phi", "Photon_phi", "boostedTau_phi"]

def trailing_zeros(values):
    bits = values.astype(np.float32).view(np.uint32).astype(np.uint64)
    return np.where(bits == 0, 32,
                    np.log2((bits & (~bits + 1)).astype(np.float64)).astype(int))

f = uproot.open(path)
t = f["Events"]
print(f"file: {path}")
print(f"file compression settings: {f.file.fCompress}")
print(f"{'branch':16s} {'n':>7s} {'min_tz':>6s} {'median':>6s} {'share>=11':>9s} {'share>=13':>9s}")
for name in branches:
    if name not in t:
        continue
    vals = []
    for arr in t[name].array(library="np", entry_stop=stop):
        a = np.asarray(arr).ravel()
        if len(a):
            vals.append(a)
    if not vals:
        continue
    v = np.concatenate(vals)
    tz = trailing_zeros(v)
    print(f"{name:16s} {len(v):7d} {tz.min():6d} {int(np.median(tz)):6d} "
          f"{float((tz >= 11).mean()):9.3f} {float((tz >= 13).mean()):9.3f}")
