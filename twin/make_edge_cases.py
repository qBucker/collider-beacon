#!/usr/bin/env python3
"""make_edge_cases.py — synthetic micro-ROOT files for the Python<->C++ twin edge battery.

Creates (NanoAOD-style "Events" tree, float32 branches):
  twin/edge_cases.root  — the bit-compare battery:
    - pT ties (equal maxima -> FIRST occurrence must win)
    - mask boundaries (pt == 20.0 exactly -> dropped; next-float32 above -> passes;
      |eta| == 2.5 exactly -> dropped; next-float32 inside -> passes)
    - NaN in pt/eta (must be filtered by the mask, never reach the argmax)
    - bin-edge azimuths: phi straddling (m/2^b)*2pi - pi grid points (ULP stepping)
    - phi at +-pi boundaries (clamp path)
    - empty-jet and all-failing events (dropped)
  twin/edge_nanphi.root — single event, NaN phi (undefined input; both sides must refuse)
"""
import numpy as np
import awkward as ak
import uproot


def f32(x):
    return np.float32(x)


def nxt(x, dn):
    """n ULP up/down in float32."""
    x = np.float32(x)
    y = np.float32(np.inf) if dn > 0 else np.float32(-np.inf)
    for _ in range(abs(dn)):
        x = np.nextafter(x, y, dtype=np.float32)
    return x


events = []  # each: list of (pt, eta, phi)
# 1-2) pT ties
events.append([(25.0, 0.1, 0.5), (25.0, 0.2, 2.0)])              # tie -> first (phi=0.5)
events.append([(30.0, 0.0, 1.0), (30.0, 0.3, 2.0), (10.0, 0.0, -1.0)])
# 3-6) mask boundaries
events.append([(20.0, 0.0, 0.5)])                                # pt == 20.0 -> event dropped
events.append([(float(nxt(20.0, +1)), 0.0, 0.5)])                # just above -> passes
events.append([(40.0, 2.5, 0.5)])                                # |eta| == 2.5 -> dropped
events.append([(40.0, float(nxt(2.5, -1)), 0.5)])                # just inside -> passes
# 7-9) NaN filtering
events.append([(np.nan, 0.0, 1.0), (30.0, 0.2, 0.7)])            # NaN jet skipped
events.append([(np.nan, 0.0, 1.0)])                              # all-NaN -> dropped
events.append([(30.0, np.nan, 1.0)])                             # NaN eta -> dropped
# 10+) bin-edge azimuths (b=8 grid; the same file is also used at b=5)
for m in (0, 1, 2, 63, 64, 128, 200, 254, 255):
    base = (m / 256.0) * 2 * np.pi - np.pi
    for d in (0, -1, +1, -2, +2):
        ph = float(base) if d == 0 else float(nxt(base, d))
        events.append([(35.0, 0.3, ph)])
# clamp-path: phi = +-pi and neighbors
for ph in (np.pi, -np.pi, float(nxt(np.pi, -1)), float(nxt(-np.pi, +1))):
    events.append([(35.0, 0.3, ph)])
# empty / all-failing
events.append([])
events.append([(5.0, 0.0, 1.0), (10.0, 3.0, 2.0)])

pt = ak.Array([[f32(j[0]) for j in ev] for ev in events])
eta = ak.Array([[f32(j[1]) for j in ev] for ev in events])
phi = ak.Array([[f32(j[2]) for j in ev] for ev in events])
with uproot.recreate("twin/edge_cases.root") as f:
    # uproot 5.7.7: dict-assignment writes an RNTuple; mktree+extend writes a classic TTree
    f.mktree("Events", {"Jet_pt": "var * float32", "Jet_eta": "var * float32", "Jet_phi": "var * float32"})
    f["Events"].extend({"Jet_pt": pt, "Jet_eta": eta, "Jet_phi": phi})


def passes(j):
    p, e, x = j
    return (not np.isnan(p)) and (not np.isnan(e)) and (p > 20.0) and (abs(e) < 2.5)


exp = sum(1 for ev in events if any(passes(j) for j in ev))
print(f"wrote twin/edge_cases.root: events={len(events)}, expected events_with_bits={exp}")

with uproot.recreate("twin/edge_nanphi.root") as f:
    f.mktree("Events", {"Jet_pt": "var * float32", "Jet_eta": "var * float32", "Jet_phi": "var * float32"})
    f["Events"].extend({
        "Jet_pt": ak.Array([[f32(35.0)]]),
        "Jet_eta": ak.Array([[f32(0.3)]]),
        "Jet_phi": ak.Array([[f32(np.nan)]]),
    })
print("wrote twin/edge_nanphi.root: 1 event, NaN phi (refusal test)")
