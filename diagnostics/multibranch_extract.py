#!/usr/bin/env python3
"""Extract MET, muon and electron azimuths from the CMS PFNanoAOD product.

Reads record 31316 files through the portal index and stores, per branch, the
delivered float32 azimuth values:

  met_phi.npy      one value per event (MET_phi)
  muon_phi.npy     all muons, flattened (Muon_phi)
  electron_phi.npy all electrons, flattened (Electron_phi)

Missing branches are recorded in the manifest, not silently dropped.

Run through the XRootD compatibility wrapper:
  python3 ../beacon-paper/phase0/xrd_run.py multibranch_extract.py \
      --index ../beacon-paper/phase0/runG/portal-file-index.json \
      --files 10 --out multibranch-2026-11-02
"""

import argparse
import json
import os
import time

import awkward as ak
import numpy as np
import uproot


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", required=True)
    ap.add_argument("--files", type=int, default=10)
    ap.add_argument("--out", required=True)
    ap.add_argument("--step", type=int, default=100000)
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    idx = json.load(open(args.index))
    uris = [f["uri"] for f in idx["files"]][: args.files]

    buffers = {"MET_phi": [], "Muon_phi": [], "Electron_phi": []}
    manifest = {"index": os.path.basename(args.index), "files": [],
                "branches": {}, "wall_s": None}
    t0 = time.time()
    for i, uri in enumerate(uris):
        t = time.time()
        counts = {}
        try:
            with uproot.open(uri) as f:
                tree = f["Events"]
                keys = set(tree.keys())
                available = [b for b in buffers if b in keys]
                for b in buffers:
                    if b not in keys:
                        manifest["branches"][b] = "missing"
                if available:
                    for arrs in tree.iterate(available, step_size=args.step,
                                             library="ak"):
                        for b in available:
                            a = arrs[b]
                            if a.ndim > 1:
                                a = ak.flatten(a, axis=None)
                            vals = ak.to_numpy(a).astype(np.float64)
                            buffers[b].append(vals)
                            counts[b] = counts.get(b, 0) + len(vals)
        except Exception as exc:
            manifest["files"].append({"uri": uri, "error": repr(exc)})
            print(f"[{i+1}/{len(uris)}] ERROR {uri}: {exc}")
            continue
        manifest["files"].append({"uri": uri, "counts": counts,
                                  "wall_s": round(time.time() - t, 1)})
        print(f"[{i+1}/{len(uris)}] {os.path.basename(uri)} "
              f"{counts} {time.time()-t:.0f}s")

    for b, chunks in buffers.items():
        if chunks:
            arr = np.concatenate(chunks)
            np.save(os.path.join(args.out, b.lower() + ".npy"), arr)
            manifest["branches"][b] = {"n": int(len(arr))}
    manifest["wall_s"] = round(time.time() - t0, 1)
    with open(os.path.join(args.out, "manifest.json"), "w") as fh:
        json.dump(manifest, fh, indent=1)
    print("wrote", args.out, "in", manifest["wall_s"], "s")


if __name__ == "__main__":
    main()
