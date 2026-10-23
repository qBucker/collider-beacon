#!/usr/bin/env python3
"""E2 pre-diagnostic: stored float32 lattice of the leading-jet azimuth.

Checks the assumptions behind the lattice-aligned E2 prediction:
  - trailing-zero count of the stored float32 values (12-bit explicit mantissa);
  - occupied binades and their ULP (the coarsest occupied octave sets p_max);
  - the empirical alphabet size, max count, and argmax value.

No extraction is performed: the script reads the same Jet_pt/Jet_eta/Jet_phi
branches and applies the same leading-jet selection as the frozen extractor.

Usage:
  python3 diagnostics/lattice_precheck.py --root /path/to/nano_data.root \
      --out diagnostics/lattice-precheck-f01.json
"""

import argparse
import json
import math

import awkward as ak
import numpy as np
import uproot


def trailing_zeros(u):
    u = u.astype(np.uint64)
    low = u & (~u + 1)
    tz = np.where(u == 0, 32, np.floor(np.log2(np.maximum(low, 1)))).astype(int)
    return tz


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--pt-min", type=float, default=20.0)
    ap.add_argument("--eta-max", type=float, default=2.5)
    ap.add_argument("--batch", type=int, default=50000)
    ap.add_argument("--max-events", type=int, default=0)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    vals = []
    n_seen = 0
    with uproot.open(args.root) as f:
        tree = f["Events"]
        for arrs in tree.iterate(["Jet_phi", "Jet_pt", "Jet_eta"],
                                 step_size=args.batch, library="ak"):
            pt, eta, phi = arrs["Jet_pt"], arrs["Jet_eta"], arrs["Jet_phi"]
            mask = (abs(eta) < args.eta_max) & (pt > args.pt_min)
            pt_m = pt[mask]
            phi_m = phi[mask]
            idx = ak.argmax(pt_m, axis=1, keepdims=True)
            lead = ak.flatten(phi_m[idx], axis=None)
            vals.append(np.asarray(ak.to_numpy(lead), dtype=np.float32))
            n_seen += len(pt)
            if args.max_events and n_seen >= args.max_events:
                break

    phi = np.concatenate(vals)
    phi = phi[np.isfinite(phi)]
    u = np.ascontiguousarray(phi).view(np.uint32)
    n = len(phi)

    tz = trailing_zeros(u)
    tz_hist = {int(k): int(v) for k, v in zip(*np.unique(tz, return_counts=True))}

    exp = ((u >> 23) & 0xFF).astype(int) - 127
    uniq, counts = np.unique(u, return_counts=True)
    arg = int(np.argmax(counts))
    arg_u = int(uniq[arg])
    arg_phi = float(np.array([arg_u], dtype=np.uint32).view(np.float32)[0])

    octaves = []
    for e in sorted(set(exp.tolist())):
        sel = exp == e
        octaves.append({
            "binade": e,
            "range": [2.0 ** e, 2.0 ** (e + 1)],
            "events": int(sel.sum()),
            "distinct": int(np.unique(u[sel]).size),
            "ulp": 2.0 ** (e - 12),
            "pmax_if_uniform": (2.0 ** (e - 12)) / math.pi,
        })

    p_theory = max(o["pmax_if_uniform"] for o in octaves) if octaves else None
    h_floor = -math.log2(p_theory) if p_theory else None
    # CP penalty at the full-run n=5.211e6 and p_theory
    n_full = 5211771
    z = 5.8
    eps_cp = (z / math.log(2)) * math.sqrt(1.0 / (n_full * p_theory)) if p_theory else None
    h_pred = h_floor - eps_cp if h_floor is not None and eps_cp is not None else None

    out = {
        "root": args.root,
        "events_seen": n_seen,
        "leading_jets": n,
        "alphabet_distinct": int(len(uniq)),
        "max_count": int(counts[arg]),
        "max_count_over_n": float(counts[arg] / n),
        "argmax_phi": arg_phi,
        "argmax_bits": format(arg_u, "032b"),
        "trailing_zero_hist": tz_hist,
        "octaves": octaves,
        "pmax_theory": p_theory,
        "h_floor_single_value": h_floor,
        "eps_cp_full_run": eps_cp,
        "h_pred_full_run": h_pred,
        "note": "h_pred uses p_max = ULP/pi of the coarsest occupied octave and n=5.211e6; the empirical alphabet uses B_eff and the measured max.",
    }
    with open(args.out, "w") as fh:
        json.dump(out, fh, indent=1)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
