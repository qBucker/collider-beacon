#!/usr/bin/env python3
"""B5 secondary-vertex stratification: per-file extraction (pre-registered 2026-10-27).

One pass per file. Per secondary vertex the azimuth and the stratification
variables are stored together; per event the leading jet azimuth and eta are
stored as the same-event reference.

Strata, predictions and statistics are fixed in
predictions/2026-10-27-b5-sv-stratified.md. The jet selection is the frozen
leading-jet rule of the phase-0 extractor: |eta| < 2.5, pt > 20 GeV, first
maximum. Rows with a non-finite SV_phi are dropped from every SV array
together, so the arrays stay index-aligned.

Output: one .npz per file (SV arrays + leading-jet arrays + counters) and a
manifest with sha256 of the output and of this file.

Usage:
  python3 b5_extract.py --file URIS.txt --out b5G/f01
  (URIS.txt holds one URI or one local path; the batch driver writes one per file)
"""

import argparse
import hashlib
import json
import os
import time

import numpy as np
import uproot

JET_PT_MIN = 20.0
JET_ETA_MAX = 2.5

SV_BRANCHES = ("SV_phi", "SV_eta", "SV_pt", "SV_mass", "SV_ntracks",
               "SV_dlenSig", "SV_dxySig", "SV_chi2", "SV_ndof")
SV_FLOAT = ("SV_phi", "SV_eta", "SV_pt", "SV_mass",
            "SV_dlenSig", "SV_dxySig", "SV_chi2", "SV_ndof")
OUT_NAMES = {"SV_phi": "sv_phi", "SV_eta": "sv_eta", "SV_pt": "sv_pt",
             "SV_mass": "sv_mass", "SV_ntracks": "sv_ntracks",
             "SV_dlenSig": "sv_dlensig", "SV_dxySig": "sv_dxysig",
             "SV_chi2": "sv_chi2", "SV_ndof": "sv_ndof"}


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def extract_file(uri, batch):
    import awkward as ak

    branches = list(SV_BRANCHES) + ["Jet_pt", "Jet_eta", "Jet_phi"]
    out = {name: [] for name in OUT_NAMES.values()}
    out["lead_phi"] = []
    out["lead_eta"] = []
    counters = {"events": 0, "sv": 0, "sv_chi2_invalid": 0,
                "jets_pass": 0, "lead": 0}

    with uproot.open(uri) as f:
        tree = f["Events"]
        for arrs in tree.iterate(branches, step_size=batch, library="ak"):
            n_evt = len(arrs["Jet_pt"])
            counters["events"] += n_evt

            # secondary vertices: flatten every branch in the same list order,
            # drop rows with a non-finite phi in all arrays together
            flats = {}
            for br in SV_BRANCHES:
                flats[br] = ak.to_numpy(ak.flatten(arrs[br], axis=None))
            sel = np.isfinite(flats["SV_phi"])
            for br in SV_BRANCHES:
                v = flats[br][sel]
                out[OUT_NAMES[br]].append(
                    v.astype(np.uint8 if br == "SV_ntracks" else np.float32))
            n_sv = int(sel.sum())
            counters["sv"] += n_sv
            chi2 = flats["SV_chi2"][sel].astype(np.float64)
            ndof = flats["SV_ndof"][sel].astype(np.float64)
            counters["sv_chi2_invalid"] += int(np.sum((chi2 <= 0) | (ndof <= 0)))

            # leading jet (frozen rule)
            pt, eta, phi = arrs["Jet_pt"], arrs["Jet_eta"], arrs["Jet_phi"]
            mask = (abs(eta) < JET_ETA_MAX) & (pt > JET_PT_MIN)
            pt_m, eta_m, phi_m = pt[mask], eta[mask], phi[mask]
            counters["jets_pass"] += int(ak.sum(ak.num(pt_m, axis=1)))
            i1 = ak.argmax(pt_m, axis=1, keepdims=True)
            lead_phi = ak.to_numpy(ak.fill_none(
                ak.flatten(phi_m[i1], axis=1), np.nan)).astype(np.float64)
            lead_eta = ak.to_numpy(ak.fill_none(
                ak.flatten(eta_m[i1], axis=1), np.nan)).astype(np.float64)
            has1 = np.isfinite(lead_phi)
            out["lead_phi"].append(lead_phi[has1].astype(np.float32))
            out["lead_eta"].append(lead_eta[has1].astype(np.float32))
            counters["lead"] += int(has1.sum())

    res = {}
    for name, chunks in out.items():
        if chunks:
            dtype = np.uint8 if name == "sv_ntracks" else np.float32
            res[name] = np.concatenate(chunks).astype(dtype)
        else:
            res[name] = np.zeros(0, np.uint8 if name == "sv_ntracks" else np.float32)
    res["counters"] = np.array([counters[k] for k in sorted(counters)], dtype=np.int64)
    return res, counters


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True, help="text file with one URI or path")
    ap.add_argument("--out", required=True, help="output prefix (writes .npz/.manifest.json)")
    ap.add_argument("--batch", type=int, default=50000)
    args = ap.parse_args()

    sources = [line.strip() for line in open(args.file) if line.strip()]
    if len(sources) != 1:
        raise SystemExit("expected exactly one source per file, got %d" % len(sources))
    uri = sources[0]

    t0 = time.time()
    res, counters = extract_file(uri, args.batch)

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    npz_path = args.out + ".npz"
    tmp = npz_path + ".tmp"
    with open(tmp, "wb") as fh:
        np.savez_compressed(fh, **res)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, npz_path)

    manifest = {
        "experiment": "B5 secondary-vertex stratification",
        "card": "predictions/2026-10-27-b5-sv-stratified.md",
        "source_uri": uri,
        "params": {"jet_pt_min": JET_PT_MIN, "jet_eta_max": JET_ETA_MAX,
                   "batch": args.batch},
        "counters": counters,
        "outputs": {"npz": os.path.basename(npz_path),
                    "npz_sha256": sha256_file(npz_path)},
        "code_sha256": sha256_file(os.path.abspath(__file__)),
        "wall_time_s": round(time.time() - t0, 2),
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    mtmp = args.out + ".manifest.json.tmp"
    with open(mtmp, "w") as fh:
        json.dump(manifest, fh, indent=1)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(mtmp, args.out + ".manifest.json")
    print(json.dumps(counters, indent=1))


if __name__ == "__main__":
    main()
