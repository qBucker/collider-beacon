#!/usr/bin/env python3
"""B1 storage-layer attribution: per-jet crossmatch (pre-registered 2026-10-27).

Card: predictions/2026-10-27-b1-storage-attribution.md.

The MiniAOD event identifiers are read with CMSSW ROOT (dump_ids.C, one CSV per
file: entry run lumi event); the jet four-vectors are read with uproot from the
same files. PFNano is read locally. Events are matched exactly on
(run, luminosityBlock, event); jets are matched by index inside an event, only
when the per-event jet counts agree. Four candidate storage rules per branch are
tested against the MiniAOD value on the pooled matched jets.

Usage:
  python3 b1_crossmatch.py --pf <nano.root> --ids <ids_dir> --uris <uris.txt> \
      --out b1G/f01-match.json
"""

import argparse
import hashlib
import json
import os

import awkward as ak
import numpy as np
import uproot

import xrd_compat  # noqa: F401  (patches fsspec-xrootd integer coercion)

JET_BASE = ("patJets_slimmedJets__PAT./patJets_slimmedJets__PAT.obj/"
            "patJets_slimmedJets__PAT.obj.m_state.p4Polar_.fCoordinates.f")
COMPONENTS = {"Jet_pt": "Pt", "Jet_eta": "Eta", "Jet_phi": "Phi", "Jet_mass": "M"}


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _mant_bits(x, k):
    return np.uint32(1 << (23 - k))


def mant_trunc(x, k):
    b = x.astype(np.float32).view(np.uint32).copy()
    drop = _mant_bits(x, k)
    b &= np.uint32(~(drop - 1) & 0xFFFFFFFF)
    return b.view(np.float32)


def mant_round(x, k):
    x = x.astype(np.float32)
    sign = np.signbit(x)
    mag = np.abs(x)
    b = mag.view(np.uint32).copy()
    b += _mant_bits(x, k) >> np.uint32(1)
    b &= np.uint32(~(_mant_bits(x, k) - 1) & 0xFFFFFFFF)
    out = b.view(np.float32)
    return np.where(sign, -out, out).astype(np.float32)


def fixed_round(x, g):
    q = 2.0 ** g
    return (np.round(x.astype(np.float64) * q) / q).astype(np.float32)


def fixed_trunc(x, g):
    q = 2.0 ** g
    return (np.trunc(x.astype(np.float64) * q) / q).astype(np.float32)


RULES = (
    ("R1_mant_trunc", mant_trunc, range(8, 17)),
    ("R2_mant_round", mant_round, range(8, 17)),
    ("R3_fixed_round", fixed_round, range(6, 15)),
    ("R4_fixed_trunc", fixed_trunc, range(6, 15)),
)


def load_pf(path):
    f = uproot.open(path)
    t = f["Events"]
    ids = t.arrays(["run", "luminosityBlock", "event"], library="ak")
    run = np.asarray(ids["run"], dtype=np.int64)
    lumi = np.asarray(ids["luminosityBlock"], dtype=np.int64)
    evt = np.asarray(ids["event"], dtype=np.int64)
    jets = t.arrays(list(COMPONENTS), library="ak")
    per_event = {c: [ak.to_numpy(jets[c][i]).astype(np.float32)
                     for i in range(len(run))]
                 for c in COMPONENTS}
    return {"run": run, "lumi": lumi, "evt": evt, "jets": per_event}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pf", required=True)
    ap.add_argument("--ids", required=True, help="directory with <basename>.ids.txt dumps")
    ap.add_argument("--uris", required=True, help="text file with the MiniAOD URIs")
    ap.add_argument("--out", required=True)
    ap.add_argument("--min-pt", type=float, default=15.0,
                    help="pT selection applied to the MiniAOD jets (Amendment 2)")
    args = ap.parse_args()

    pf = load_pf(args.pf)
    key = {(int(r), int(l), int(e)): i
           for i, (r, l, e) in enumerate(zip(pf["run"], pf["lumi"], pf["evt"]))}

    uris = [u.strip() for u in open(args.uris) if u.strip()]
    per_file = []
    acc = {c: {"m": [], "q": []} for c in COMPONENTS}
    n_count_mismatch = 0
    n_matched_events = 0
    n_matched_jets = 0

    for uri in uris:
        base = os.path.basename(uri)[:-5]
        id_path = os.path.join(args.ids, base + ".ids.txt")
        if not os.path.exists(id_path):
            per_file.append({"file": base, "status": "no_ids"})
            continue
        ids = np.loadtxt(id_path, dtype=np.int64, ndmin=2)
        if ids.size == 0:
            per_file.append({"file": base, "status": "empty_ids"})
            continue
        keys = [(int(r), int(l), int(e)) for _, r, l, e in ids]
        matched = [k for k, kk in enumerate(keys) if kk in key]
        if not matched:
            per_file.append({"file": base, "status": "no_overlap",
                             "n_events": int(ids.shape[0])})
            continue

        f = uproot.open(uri)
        t = f["Events"]
        min_name = {c: JET_BASE + v for c, v in COMPONENTS.items()}
        mj = t.arrays(list(min_name.values()), library="ak")

        for k in matched:
            pidx = key[keys[k]]
            n_matched_events += 1
            mp = {c: ak.to_numpy(mj[min_name[c]][k]).astype(np.float32)
                  for c in COMPONENTS}
            if mp["Jet_pt"].size:
                sel = mp["Jet_pt"] > args.min_pt
                mp = {c: v[sel] for c, v in mp.items()}
            n_q = pf["jets"]["Jet_pt"][pidx].size
            if mp["Jet_pt"].size != n_q:
                n_count_mismatch += 1
                continue
            n_matched_jets += mp["Jet_pt"].size
            for c in COMPONENTS:
                acc[c]["m"].append(mp[c])
                acc[c]["q"].append(pf["jets"][c][pidx])

        per_file.append({"file": base, "status": "used",
                         "n_events": int(ids.shape[0]),
                         "n_matched_events": len(matched)})
        print("%s: %d/%d events matched" % (base, len(matched), ids.shape[0]))

    out = {"pf": os.path.basename(args.pf), "pf_sha256": sha256_file(args.pf),
           "n_matched_events": n_matched_events,
           "n_count_mismatch_events": n_count_mismatch,
           "n_matched_jets": n_matched_jets,
           "files": per_file, "branches": {}}

    for c in COMPONENTS:
        m = np.concatenate(acc[c]["m"]) if acc[c]["m"] else np.zeros(0, np.float32)
        q = np.concatenate(acc[c]["q"]) if acc[c]["q"] else np.zeros(0, np.float32)
        entry = {"n_jets": int(m.size), "top5": [], "best": None}
        if m.size:
            scored = []
            for rname, fn, params in RULES:
                for p in params:
                    share = float(np.mean(fn(m, p) == q))
                    scored.append({"rule": "%s_%d" % (rname, p), "share": share})
            scored.sort(key=lambda x: -x["share"])
            entry["top5"] = scored[:5]
            entry["best"] = scored[0]
            best_rule, best_p = scored[0]["rule"].rsplit("_", 1)
            fn = dict((r[0], r[1]) for r in RULES)[best_rule]
            resid = (q - fn(m, int(best_p))).astype(np.float64)
            entry["residual_quantiles"] = {
                "p0": float(np.min(resid)), "p1": float(np.percentile(resid, 1)),
                "p50": float(np.median(resid)), "p99": float(np.percentile(resid, 99)),
                "p100": float(np.max(resid))}
        out["branches"][c] = entry

    tmp = args.out + ".tmp"
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(tmp, "w") as fh:
        json.dump(out, fh, indent=1)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, args.out)
    print(json.dumps({"matched_events": n_matched_events,
                      "matched_jets": n_matched_jets,
                      "count_mismatch": n_count_mismatch,
                      "best": {c: out["branches"][c]["best"] for c in COMPONENTS}},
                     indent=1))


if __name__ == "__main__":
    main()
