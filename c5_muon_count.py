#!/usr/bin/env python3
"""C5 dimuon arm, corrected: muon branches only.

The first C5 pass stored dimuon pair masses computed with E = sqrt(pT^2 + m^2),
which omits the longitudinal momentum; forward pairs therefore came out with
negative m^2 clipped to zero. This pass re-reads only the muon branches and
applies the correct four-vector: E = sqrt((pT cosh eta)^2 + m^2), pz = pT sinh eta.

Selection (as in the pre-registration): pT > 4 GeV, |eta| < 2.4, tightId == 1,
two leading muons by pT, opposite charge. Output per file: pair azimuths,
pair masses, and content counters (events with >= 2 selected muons).

Usage: python3 c5_muon_count.py --file URIS.txt --out muonG/f01
"""

import argparse
import hashlib
import json
import os
import time

import numpy as np
import uproot

MUON_PT_MIN = 4.0
MUON_ETA_MAX = 2.4


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def gather(idx, values):
    import awkward as ak
    picked = ak.fill_none(ak.flatten(values[idx], axis=1), np.nan)
    return ak.to_numpy(picked).astype(np.float64)


def extract(uri, batch):
    import awkward as ak

    branches = ["Muon_pt", "Muon_eta", "Muon_phi", "Muon_mass",
                "Muon_charge", "Muon_tightId"]
    counters = {"events": 0, "muons_pass": 0, "events_ge2": 0, "os_pairs": 0}
    phis, masses = [], []

    with uproot.open(uri) as f:
        tree = f["Events"]
        for a in tree.iterate(branches, step_size=batch, library="ak"):
            m = (a["Muon_pt"] > MUON_PT_MIN) & (abs(a["Muon_eta"]) < MUON_ETA_MAX) \
                & (a["Muon_tightId"] == 1)
            pt, eta, phi = a["Muon_pt"][m], a["Muon_eta"][m], a["Muon_phi"][m]
            mass, chg = a["Muon_mass"][m], a["Muon_charge"][m]
            npass = ak.to_numpy(ak.num(pt, axis=1))
            counters["events"] += len(npass)
            counters["muons_pass"] += int(npass.sum())
            counters["events_ge2"] += int((npass >= 2).sum())

            j1 = ak.argmax(pt, axis=1, keepdims=True)
            rest = ak.where(ak.local_index(pt, axis=1) == j1, -1.0, pt)
            j2 = ak.argmax(rest, axis=1, keepdims=True)

            p1, f1, e1, q1, m1 = (gather(j1, pt), gather(j1, phi), gather(j1, eta),
                                  gather(j1, chg), gather(j1, mass))
            p2, f2, e2, q2, m2 = (gather(j2, pt), gather(j2, phi), gather(j2, eta),
                                  gather(j2, chg), gather(j2, mass))
            ok = (npass >= 2) & ~np.isnan(p2) & (p2 > 0) & (q1 * q2 < 0)
            if not ok.any():
                continue
            px = p1[ok] * np.cos(f1[ok]) + p2[ok] * np.cos(f2[ok])
            py = p1[ok] * np.sin(f1[ok]) + p2[ok] * np.sin(f2[ok])
            pz = p1[ok] * np.sinh(e1[ok]) + p2[ok] * np.sinh(e2[ok])
            E1 = np.sqrt((p1[ok] * np.cosh(e1[ok])) ** 2 + m1[ok] ** 2)
            E2 = np.sqrt((p2[ok] * np.cosh(e2[ok])) ** 2 + m2[ok] ** 2)
            m2p = np.maximum((E1 + E2) ** 2 - px ** 2 - py ** 2 - pz ** 2, 0.0)
            phis.append(np.arctan2(py, px))
            masses.append(np.sqrt(m2p))
            counters["os_pairs"] += int(ok.sum())

    return phis, masses, counters


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--batch", type=int, default=50000)
    args = ap.parse_args()

    sources = [l.strip() for l in open(args.file) if l.strip()]
    if len(sources) != 1:
        raise SystemExit("expected exactly one URI")
    uri = sources[0]
    t0 = time.time()
    phis, masses, counters = extract(uri, args.batch)

    res = {"dimuon_phi": np.concatenate(phis).astype(np.float32) if phis else np.zeros(0, np.float32),
           "dimuon_mass": np.concatenate(masses).astype(np.float32) if masses else np.zeros(0, np.float32)}
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    npz = args.out + ".npz"
    tmp = npz + ".tmp"
    with open(tmp, "wb") as fh:
        np.savez_compressed(fh, **res)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, npz)

    man = {"experiment": "C5 dimuon arm (corrected four-vector)",
           "card": "predictions/2026-10-25-c5-hadronic.md",
           "source_uri": uri, "counters": counters,
           "outputs": {"npz": os.path.basename(npz), "npz_sha256": sha256_file(npz)},
           "code_sha256": sha256_file(os.path.abspath(__file__)),
           "wall_time_s": round(time.time() - t0, 2),
           "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    mtmp = args.out + ".manifest.json.tmp"
    with open(mtmp, "w") as fh:
        json.dump(man, fh, indent=1)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(mtmp, args.out + ".manifest.json")
    print(json.dumps(counters))


if __name__ == "__main__":
    main()
