#!/usr/bin/env python3
"""C5 hadronic extension: per-file azimuth extraction (pre-registered 2026-10-25).

Arms (see predictions/2026-10-25-c5-hadronic.md):
  A      leading jet azimuth (control, frozen selection)
  H1a    second-ranked jet
  H1b    third-ranked jet
  H2     highest-pt jet with Jet_btagDeepFlavB > 0.50
  H2s    same with > 0.80 (stability cross-check only)
  H3     azimuth of the two leading opposite-sign muons (pt>4, |eta|<2.4, tightId)
  H3'    secondary-vertex azimuth (SV_phi, all stored vertices; amendment 1)
         The muon arrays are kept for the record; the dimuon yield is reported
         as a limiting measurement.

Jet selection: |eta| < 2.5, pt > 20 GeV, ranked by pt descending; ties resolved
by first occurrence (iterated argmax with the selected entry masked), matching
the frozen leading-jet rule.

Output: one .npz per file (float32 azimuth arrays + dimuon masses + counters)
and a manifest with sha256 of the output and of this file.

Usage:
  python3 c5_extract.py --file URIS.txt --out c5G/f01
  (URIS.txt holds one URI; the batch driver writes one per file)
"""

import argparse
import hashlib
import json
import math
import os
import time

import numpy as np
import uproot

JET_PT_MIN = 20.0
JET_ETA_MAX = 2.5
BTAG_PRIMARY = 0.50
BTAG_SECONDARY = 0.80
MUON_PT_MIN = 4.0
MUON_ETA_MAX = 2.4
MUON_MASS = 0.10566


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _per_event_at(idx, values, has):
    """Gather values[idx] per event as an aligned float64 array (nan where absent)."""
    import awkward as ak

    picked = ak.fill_none(ak.flatten(values[idx], axis=1), np.nan)
    return ak.to_numpy(picked).astype(np.float64)


def extract_file(uri, batch):
    import awkward as ak

    branches = [
        "Jet_pt", "Jet_eta", "Jet_phi", "Jet_btagDeepFlavB",
        "Muon_pt", "Muon_eta", "Muon_phi", "Muon_mass", "Muon_charge",
        "Muon_tightId", "SV_phi",
    ]
    out = {k: [] for k in
           ("lead_phi", "sub_phi", "third_phi", "btag_phi", "btag080_phi",
            "dimuon_phi", "dimuon_mass", "sv_phi")}
    counters = {"events": 0, "lead": 0, "sub": 0, "third": 0,
                "btag050": 0, "btag080": 0, "dimuon": 0, "jets_pass": 0,
                "muons_pass": 0, "sv": 0}

    with uproot.open(uri) as f:
        tree = f["Events"]
        for arrs in tree.iterate(branches, step_size=batch, library="ak"):
            pt, eta, phi = arrs["Jet_pt"], arrs["Jet_eta"], arrs["Jet_phi"]
            btag = arrs["Jet_btagDeepFlavB"]
            mask = (abs(eta) < JET_ETA_MAX) & (pt > JET_PT_MIN)
            pt_m, phi_m, btag_m = pt[mask], phi[mask], btag[mask]

            n_evt = len(pt)
            counters["events"] += n_evt
            counters["jets_pass"] += int(ak.sum(ak.num(pt_m, axis=1)))

            # leading jet (frozen rule)
            i1 = ak.argmax(pt_m, axis=1, keepdims=True)
            lead = _per_event_at(i1, phi_m, None)
            has1 = ~np.isnan(lead)
            out["lead_phi"].append(lead[has1])
            counters["lead"] += int(has1.sum())

            # second-ranked: mask the leading entry, take the max of the rest
            rest1 = ak.where(ak.local_index(pt_m, axis=1) == i1, -1.0, pt_m)
            i2 = ak.argmax(rest1, axis=1, keepdims=True)
            sub = _per_event_at(i2, phi_m, None)
            has2 = (~np.isnan(sub)) & (ak.to_numpy(ak.num(pt_m, axis=1)) >= 2)
            out["sub_phi"].append(sub[has2])
            counters["sub"] += int(has2.sum())

            rest2 = ak.where((ak.local_index(pt_m, axis=1) == i2) | (ak.local_index(pt_m, axis=1) == i1),
                             -1.0, pt_m)
            i3 = ak.argmax(rest2, axis=1, keepdims=True)
            third = _per_event_at(i3, phi_m, None)
            has3 = (~np.isnan(third)) & (ak.to_numpy(ak.num(pt_m, axis=1)) >= 3)
            out["third_phi"].append(third[has3])
            counters["third"] += int(has3.sum())

            # b-tagged arms
            for thr, key, cnt in ((BTAG_PRIMARY, "btag_phi", "btag050"),
                                  (BTAG_SECONDARY, "btag080_phi", "btag080")):
                mb = mask & (btag > thr)
                pt_b, phi_b = pt[mb], phi[mb]
                ib = ak.argmax(pt_b, axis=1, keepdims=True)
                bphi = _per_event_at(ib, phi_b, None)
                hb = ~np.isnan(bphi)
                out[key].append(bphi[hb])
                counters[cnt] += int(hb.sum())

            # dimuon arm
            mpt, meta, mphi = arrs["Muon_pt"], arrs["Muon_eta"], arrs["Muon_phi"]
            mmass, mchg, mtight = arrs["Muon_mass"], arrs["Muon_charge"], arrs["Muon_tightId"]
            mmask = (mpt > MUON_PT_MIN) & (abs(meta) < MUON_ETA_MAX) & (mtight == 1)
            pt_u, phi_u, eta_u = mpt[mmask], mphi[mmask], meta[mmask]
            chg_u, mass_u = mchg[mmask], mmass[mmask]
            counters["muons_pass"] += int(ak.sum(ak.num(pt_u, axis=1)))

            j1 = ak.argmax(pt_u, axis=1, keepdims=True)
            rest_u = ak.where(ak.local_index(pt_u, axis=1) == j1, -1.0, pt_u)
            j2 = ak.argmax(rest_u, axis=1, keepdims=True)

            p1 = _per_event_at(j1, pt_u, None)
            f1 = _per_event_at(j1, phi_u, None)
            e1 = _per_event_at(j1, eta_u, None)
            q1 = _per_event_at(j1, chg_u, None)
            m1 = _per_event_at(j1, mass_u, None)
            p2 = _per_event_at(j2, pt_u, None)
            f2 = _per_event_at(j2, phi_u, None)
            e2 = _per_event_at(j2, eta_u, None)
            q2 = _per_event_at(j2, chg_u, None)
            m2 = _per_event_at(j2, mass_u, None)

            npass = ak.to_numpy(ak.num(pt_u, axis=1))
            ok = (npass >= 2) & ~np.isnan(p2) & (q1 * q2 < 0) & (p2 > 0)
            if ok.any():
                px = p1[ok] * np.cos(f1[ok]) + p2[ok] * np.cos(f2[ok])
                py = p1[ok] * np.sin(f1[ok]) + p2[ok] * np.sin(f2[ok])
                pair_phi = np.arctan2(py, px)
                # invariant mass with the stored muon masses
                e_1 = np.sqrt(p1[ok] ** 2 + m1[ok] ** 2)
                e_2 = np.sqrt(p2[ok] ** 2 + m2[ok] ** 2)
                pz = np.sqrt(np.maximum(e_1 ** 2 - m1[ok] ** 2, 0)) * np.sinh(e1[ok]) \
                    + np.sqrt(np.maximum(e_2 ** 2 - m2[ok] ** 2, 0)) * np.sinh(e2[ok])
                m2_pair = np.maximum((e_1 + e_2) ** 2 - px ** 2 - py ** 2 - pz ** 2, 0.0)
                out["dimuon_phi"].append(pair_phi.astype(np.float64))
                out["dimuon_mass"].append(np.sqrt(m2_pair))
                counters["dimuon"] += int(ok.sum())

            # secondary vertices (H3'): all stored, no further selection
            sv = ak.flatten(arrs["SV_phi"], axis=None)
            sv = ak.to_numpy(sv).astype(np.float64)
            sv = sv[~np.isnan(sv)]
            out["sv_phi"].append(sv)
            counters["sv"] += int(sv.size)

    res = {k: (np.concatenate(v).astype(np.float32) if v else np.zeros(0, np.float32))
           for k, v in out.items()}
    res["counters"] = np.array([counters[k] for k in sorted(counters)], dtype=np.int64)
    return res, counters


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True, help="text file with one URI")
    ap.add_argument("--out", required=True, help="output prefix (writes .npz/.manifest.json)")
    ap.add_argument("--batch", type=int, default=50000)
    args = ap.parse_args()

    sources = [line.strip() for line in open(args.file) if line.strip()]
    if len(sources) != 1:
        raise SystemExit("expected exactly one URI per file, got %d" % len(sources))
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
        "experiment": "C5 hadronic extension",
        "card": "predictions/2026-10-25-c5-hadronic.md",
        "source_uri": uri,
        "params": {
            "jet_pt_min": JET_PT_MIN, "jet_eta_max": JET_ETA_MAX,
            "btag_primary": BTAG_PRIMARY, "btag_secondary": BTAG_SECONDARY,
            "muon_pt_min": MUON_PT_MIN, "muon_eta_max": MUON_ETA_MAX,
            "batch": args.batch,
        },
        "counters": counters,
        "outputs": {"npz": os.path.basename(npz_path), "npz_sha256": sha256_file(npz_path)},
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
