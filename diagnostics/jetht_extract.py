#!/usr/bin/env python3
"""Extract raw leading-jet azimuths from the JetHT PFNanoAOD product.

Third-product companion to the frozen phase0 extractor: the frozen script
stores only 8-bit bits, while the precision audit needs the delivered float
values. This script reads Jet_pt / Jet_eta / Jet_phi from the same files and
saves the leading-jet phi array (pt > 20 GeV, |eta| < 2.5, leading in pT).

Run through the XRootD shim:
  python3 ../beacon-paper/phase0/xrd_run.py jetht_extract.py \
      --files /tmp/uris-jetht.txt --out jetht-2026-11-02/jetht5
"""

import argparse
import hashlib
import json
import os
import time

import awkward as ak
import numpy as np
import uproot


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--files", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--pt-min", type=float, default=20.0)
    ap.add_argument("--eta-max", type=float, default=2.5)
    ap.add_argument("--step", type=int, default=100000)
    args = ap.parse_args()

    uris = [u.strip() for u in open(args.files) if u.strip()]
    phis = []
    manifest = {"files": uris, "pt_min": args.pt_min,
                "eta_max": args.eta_max, "events": [], "wall_s": None}
    t0 = time.time()
    for i, uri in enumerate(uris):
        t = time.time()
        n = 0
        with uproot.open(uri) as f:
            tree = f["Events"]
            for arrs in tree.iterate(["Jet_pt", "Jet_eta", "Jet_phi"],
                                     step_size=args.step, library="ak"):
                pt, eta, phi = arrs["Jet_pt"], arrs["Jet_eta"], arrs["Jet_phi"]
                mask = (abs(eta) < args.eta_max) & (pt > args.pt_min)
                pt_m = pt[mask]
                phi_m = phi[mask]
                idx = ak.argmax(pt_m, axis=1, keepdims=True)
                lead = ak.flatten(phi_m[idx], axis=None)
                phis.extend(float(v) for v in lead)
                n += len(lead)
        manifest["events"].append({"uri": uri, "n": n,
                                   "wall_s": round(time.time() - t, 1)})
        print(f"[{i+1}/{len(uris)}] {os.path.basename(uri)} n={n} "
              f"{time.time()-t:.0f}s")
    arr = np.asarray(phis, dtype=np.float64)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    np.save(args.out + ".phis.npy", arr)
    manifest["n"] = int(len(arr))
    manifest["wall_s"] = round(time.time() - t0, 1)
    manifest["sha256"] = hashlib.sha256(arr.tobytes()).hexdigest()
    with open(args.out + ".phi-manifest.json", "w") as fh:
        json.dump(manifest, fh, indent=1)
    print("wrote", args.out + ".phis.npy", "n =", len(arr),
          "in", manifest["wall_s"], "s")


if __name__ == "__main__":
    main()
