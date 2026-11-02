#!/usr/bin/env python3
"""Random-offset resampling of the ATLAS Open Data leading-jet azimuths.

The effect-1 smoke read the first 50,000 entries of each file. This script
draws an independent random 50,000-entry window per file and repeats the
leading-jet extraction, to test that the azimuthal spectrum and the entropy
floor do not depend on the entry range.

Usage:
  python3 atlas_resample.py --urls urls-noskim.https.txt --events 50000 \
      --seed 20261102 --out ../diagnostics/atlas-resample-2026-11-02
"""

import argparse
import json
import math
import os
import time

import awkward as ak
import numpy as np
import uproot

from parallel_http_source import ParallelHTTPSource

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--urls", default=os.path.join(HERE, "urls-noskim.https.txt"))
    ap.add_argument("--events", type=int, default=50000)
    ap.add_argument("--seed", type=int, default=20261102)
    ap.add_argument("--out", required=True)
    ap.add_argument("--pt-min", type=float, default=20.0)
    ap.add_argument("--eta-max", type=float, default=2.5)
    ap.add_argument("--workers", type=int, default=16)
    ap.add_argument("--timeout", type=float, default=120.0)
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    system_ca = "/etc/ssl/certs/ca-certificates.crt"
    if os.path.exists(system_ca):
        os.environ["SSL_CERT_FILE"] = system_ca
    urls = [u.strip().replace("simplecache::", "")
            for u in open(args.urls) if u.strip()]
    rng = np.random.default_rng(args.seed)
    phis = []
    manifest = {"seed": args.seed, "events_per_file": args.events,
                "files": [], "wall_s": None}
    t0 = time.time()
    for i, url in enumerate(urls):
        t = time.time()
        try:
            with uproot.open(url, handler=ParallelHTTPSource,
                            num_workers=args.workers,
                            timeout=args.timeout) as f:
                tree = f["analysis"]
                n_total = int(tree.num_entries)
                if n_total <= args.events:
                    start = 0
                else:
                    start = int(rng.integers(0, n_total - args.events))
                n_kept = 0
                for arrs in tree.iterate(
                        ["jet_pt", "jet_eta", "jet_phi"],
                        entry_start=start, entry_stop=start + args.events,
                        step_size=25000, library="ak"):
                    pt, eta, phi = arrs["jet_pt"], arrs["jet_eta"], arrs["jet_phi"]
                    mask = (abs(eta) < args.eta_max) & (pt > args.pt_min)
                    pt_m = pt[mask]
                    phi_m = phi[mask]
                    idx = ak.argmax(pt_m, axis=1, keepdims=True)
                    lead = ak.flatten(phi_m[idx], axis=None)
                    phis.extend(float(v) for v in lead)
                    n_kept += len(lead)
        except Exception as exc:
            manifest["files"].append({"url": url, "error": repr(exc)})
            print(f"[{i+1}/{len(urls)}] ERROR {os.path.basename(url)}: {exc}")
            continue
        manifest["files"].append({"url": url, "start": start,
                                  "n_total": n_total, "n_kept": n_kept,
                                  "wall_s": round(time.time() - t, 1)})
        print(f"[{i+1}/{len(urls)}] {os.path.basename(url)} "
              f"start={start} kept={n_kept} {time.time()-t:.0f}s")
    arr = np.asarray(phis, dtype=np.float64)
    np.save(os.path.join(args.out, "lead_phi.npy"), arr)
    manifest["n"] = int(len(arr))
    manifest["wall_s"] = round(time.time() - t0, 1)
    with open(os.path.join(args.out, "manifest.json"), "w") as fh:
        json.dump(manifest, fh, indent=1)
    print("wrote", args.out, "n =", len(arr), "in", manifest["wall_s"], "s")


if __name__ == "__main__":
    main()
