#!/usr/bin/env python3
"""B5 secondary-vertex stratification: offline aggregation (pre-registered
2026-10-27, predictions/2026-10-27-b5-sv-stratified.md).

Reads b5G/fNN.npz + manifests, applies the fixed strata, and computes the
fixed statistics: b=12 Fourier amplitudes, significances and phases, the
local continuum and excess, b=8 robustness, per-file phases for the
coherence test, the eta-phi occupancy map, and the leading-jet reference in
each eta band.

Conventions match c5_analyze.py: bits_of_phi on [-pi, pi), counts from
np.bincount, c_k = rfft(counts)[k]/n, A_k = |c_k|, z = sqrt(n) A_k,
phase = arg(c_k). The JSON carries no timestamp so that a re-run is
byte-identical (gate G3).

Usage:
  python3 b5_analyze.py --glob 'b5G/f[0-9][0-9].npz' --out b5-aggregate.json
"""

import argparse
import glob
import hashlib
import json
import math
import os

import numpy as np

B8, B12 = 8, 12
K_LIST = (7, 12, 17, 18, 19, 24, 33, 34, 35, 36, 37, 38, 39, 54)
NEIGH = 4
ETA_EDGES = ((0.0, 0.9), (0.9, 1.5), (1.5, 2.5))
MAP_NETA, MAP_NPHI = 36, 72


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def bits_of_phi(phi, b):
    u = (phi + math.pi) / (2 * math.pi)
    u = np.clip(u, 1e-15, 1.0 - 1e-15)
    return np.minimum((u * (1 << b)).astype(np.int64), (1 << b) - 1)


def fourier(phi, b):
    n = int(phi.size)
    if n == 0:
        return None
    counts = np.bincount(bits_of_phi(phi, b), minlength=1 << b).astype(np.float64)
    spec = np.fft.rfft(counts) / counts.sum()
    kmax = max(K_LIST)
    out = {"n": n, "bins": 1 << b, "counts": counts.astype(np.int64).tolist(),
           "amp": {}, "z": {}, "phase_deg": {}}
    for k in K_LIST:
        if k >= spec.size:
            continue
        a = float(abs(spec[k]))
        out["amp"][str(k)] = a
        out["z"][str(k)] = math.sqrt(n) * a
        out["phase_deg"][str(k)] = math.degrees(float(np.angle(spec[k])))
    return out


def continuum(amp, k):
    vals = [amp[str(j)] for j in range(k - NEIGH, k + NEIGH + 1)
            if j != k and str(j) in amp]
    return float(np.median(vals)) if vals else None


def stratum(phi, b=12):
    f = fourier(phi, b)
    if f is None:
        return None
    c18 = continuum(f["amp"], 18)
    c36 = continuum(f["amp"], 36)
    f["continuum"] = {"18": c18, "36": c36}
    f["excess"] = {"18": f["amp"]["18"] - c18 if c18 is not None else None,
                   "36": f["amp"]["36"] - c36 if c36 is not None else None}
    return f


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--glob", default="b5G/f[0-9][0-9].npz")
    ap.add_argument("--out", default="b5-aggregate.json")
    args = ap.parse_args()

    files = sorted(glob.glob(args.glob))
    if not files:
        raise SystemExit("no files match %s" % args.glob)

    cols = {k: [] for k in ("sv_phi", "sv_eta", "sv_pt", "sv_mass",
                            "sv_ntracks", "sv_dlensig", "sv_dxysig",
                            "sv_chi2", "sv_ndof", "lead_phi", "lead_eta")}
    per_file = []
    integrity = []
    counters_total = {}
    file_phase = {"18": [], "7": []}
    file_n = []

    for path in files:
        z = np.load(path)
        man_path = path[:-4] + ".manifest.json"
        man = json.load(open(man_path))
        for k, v in man.get("counters", {}).items():
            counters_total[k] = counters_total.get(k, 0) + int(v)
        npz_sha = sha256_file(path)
        ok = npz_sha == man.get("outputs", {}).get("npz_sha256")
        integrity.append(ok)
        c5man = os.path.join("c5G", os.path.basename(path)[:-4] + ".manifest.json")
        c5_sv = None
        if os.path.exists(c5man):
            c5_sv = json.load(open(c5man)).get("counters", {}).get("sv")
        sv_n = int(z["sv_phi"].size)
        per_file.append({"file": os.path.basename(path), "sv": sv_n,
                         "c5_sv": c5_sv, "npz_sha256": npz_sha,
                         "manifest_match": bool(ok)})
        for k in cols:
            cols[k].append(z[k])
        # per-file Fourier phase at k=7 and k=18 (b=12)
        f = fourier(z["sv_phi"].astype(np.float64), B12)
        file_n.append(sv_n)
        if f is not None:
            file_phase["18"].append((f["amp"]["18"], f["phase_deg"]["18"]))
            file_phase["7"].append((f["amp"]["7"], f["phase_deg"]["7"]))

    arr = {k: np.concatenate(v) for k, v in cols.items()}
    phi = arr["sv_phi"].astype(np.float64)
    eta = arr["sv_eta"].astype(np.float64)
    pt = arr["sv_pt"].astype(np.float64)
    mass = arr["sv_mass"].astype(np.float64)
    nt = arr["sv_ntracks"].astype(np.int64)
    dl = arr["sv_dlensig"].astype(np.float64)
    dx = arr["sv_dxysig"].astype(np.float64)
    chi2 = arr["sv_chi2"].astype(np.float64)
    ndof = arr["sv_ndof"].astype(np.float64)
    nond = np.abs(eta)

    with np.errstate(divide="ignore", invalid="ignore"):
        c2 = np.where(ndof > 0, chi2 / ndof, np.nan)
    valid_fit = (chi2 > 0) & (ndof > 0)
    q1 = valid_fit & (c2 < 2)
    q2 = valid_fit & (c2 >= 2) & (c2 < 5)
    q3 = valid_fit & (c2 >= 5)
    qx = ~valid_fit

    masks = {
        "S0": np.ones(phi.size, bool),
        "E1": nond < 0.9, "E2": (nond >= 0.9) & (nond < 1.5),
        "E3": (nond >= 1.5) & (nond < 2.5),
        "T2": nt == 2, "T3": nt == 3, "T4": nt >= 4,
        "T34": nt >= 3,
        "D1": dl < 4, "D2": (dl >= 4) & (dl < 10), "D3": dl >= 10,
        "M1": mass < 0.4, "M2": (mass >= 0.4) & (mass < 1.0), "M3": mass >= 1.0,
        "P1": pt < 2, "P2": (pt >= 2) & (pt < 5), "P3": pt >= 5,
        "Q1": q1, "Q2": q2, "Q3": q3,
    }

    strata = {}
    for name, m in masks.items():
        f12 = stratum(phi[m], B12)
        f8 = stratum(phi[m], B8)
        strata[name] = {"n": int(m.sum()), "b12": f12, "b8": f8}

    # leading-jet reference in the same eta bands
    jet_phi = arr["lead_phi"].astype(np.float64)
    jet_eta = np.abs(arr["lead_eta"].astype(np.float64))
    jet = {}
    for name, (lo, hi) in zip(("E1", "E2", "E3"), ETA_EDGES):
        m = (jet_eta >= lo) & (jet_eta < hi)
        f = fourier(jet_phi[m], B12)
        if f is not None:
            f["continuum"] = {"18": continuum(f["amp"], 18)}
            f["excess"] = {"18": f["amp"]["18"] - f["continuum"]["18"]}
        jet[name] = {"n": int(m.sum()), "b12": f}

    # phase coherence across files (unit phasors; standard circular resultant)
    def resultant(pairs):
        if not pairs:
            return None
        ph = np.radians(np.array([p[1] for p in pairs]))
        a = np.array([p[0] for p in pairs])
        r_unit = float(abs(np.mean(np.exp(1j * ph))))
        r_amp = float(abs(np.sum(a * np.exp(1j * ph))) / np.sum(a))
        return {"files": len(pairs), "R_unweighted": r_unit,
                "R_amplitude_weighted": r_amp}

    coherence = {"k18": resultant(file_phase["18"]),
                 "k7": resultant(file_phase["7"]),
                 "per_file": [{"file": os.path.basename(p).split(".")[0],
                               "sv": n,
                               "a18": file_phase["18"][i][0],
                               "phase18_deg": file_phase["18"][i][1],
                               "a7": file_phase["7"][i][0],
                               "phase7_deg": file_phase["7"][i][1]}
                              for i, (p, n) in enumerate(zip(files, file_n))]}

    # eta-phi occupancy map
    hm, _, _ = np.histogram2d(
        nond, (phi + math.pi) / (2 * math.pi),
        bins=(MAP_NETA, MAP_NPHI), range=((0.0, 2.5), (0.0, 1.0)))
    occupancy = hm.astype(np.int64).tolist()

    def a18(name, b=12):
        d = strata[name]["b%d" % b]
        return None if d is None else d["amp"]["18"]

    ratios = {
        "E3_over_E1": a18("E3") / a18("E1") if a18("E1") else None,
        "T34_over_T2": a18("T34") / a18("T2") if a18("T2") else None,
        "D3_over_D1": a18("D3") / a18("D1") if a18("D1") else None,
        "A36_over_A18": (a18("S0") and
                         strata["S0"]["b12"]["amp"]["36"] / a18("S0")),
        "E36_over_A18": (a18("S0") and
                         strata["S0"]["b12"]["excess"]["36"] / a18("S0")),
        "jet_contrast": {b: (a18(b) - jet[b]["b12"]["amp"]["18"])
                         if a18(b) is not None and jet[b]["b12"] else None
                         for b in ("E1", "E2", "E3")},
        "phase_diff_E3_E1_deg": (strata["E3"]["b12"]["phase_deg"]["18"] -
                                 strata["E1"]["b12"]["phase_deg"]["18"])
                                if strata["E3"]["b12"] and strata["E1"]["b12"] else None,
    }
    if ratios["phase_diff_E3_E1_deg"] is not None:
        d = ratios["phase_diff_E3_E1_deg"]
        d = (d + 180.0) % 360.0 - 180.0
        ratios["phase_diff_E3_E1_deg"] = d

    results = {
        "card": "predictions/2026-10-27-b5-sv-stratified.md",
        "files": len(files),
        "counters": counters_total,
        "integrity": {"npz_manifest_ok": int(sum(integrity)),
                      "files": len(integrity),
                      "sv_counts_match_c5": int(sum(
                          1 for r in per_file
                          if r["c5_sv"] is not None and r["c5_sv"] == r["sv"])),
                      "per_file": per_file},
        "strata": strata,
        "jet_reference": jet,
        "coherence": coherence,
        "ratios": ratios,
        "eta_phi_occupancy": {"n_eta": MAP_NETA, "n_phi": MAP_NPHI,
                              "eta_range": [0.0, 2.5], "counts": occupancy},
    }

    tmp = args.out + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(results, fh)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, args.out)
    print(json.dumps({
        "files": len(files),
        "integrity_ok": results["integrity"]["npz_manifest_ok"],
        "sv_counts_match_c5": results["integrity"]["sv_counts_match_c5"],
        "n_S0": strata["S0"]["n"],
        "A18_S0": a18("S0"), "A7_S0": strata["S0"]["b12"]["amp"]["7"],
        "R18": coherence["k18"]["R_unweighted"] if coherence["k18"] else None,
        "R7": coherence["k7"]["R_unweighted"] if coherence["k7"] else None,
        "ratios": {k: v for k, v in ratios.items() if not isinstance(v, dict)},
    }, indent=1))


if __name__ == "__main__":
    main()
