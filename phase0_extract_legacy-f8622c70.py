#!/usr/bin/env python3
# phase0_extract.py — Collider Beacon Phase 0: extractor P (v1 frozen)
#
# P (v1): per event -> leading jet (max pT, |eta|<2.5, pT>50 GeV)
#         -> phi in (-pi,pi] -> uniform 2^b bins (default b=8)
#         -> emit bin index as b bits (MSB-first)
# Entropy accounting: Clopper-Pearson upper bound on max bin frequency
# with Bonferroni correction over 2^b bins -> per-event min-entropy bound.
#
# Usage:
#   python3 phase0_extract.py --files uris.txt --out run1 [options]
#   python3 phase0_extract.py --mc delphes.root --out mc1   (Delphes tree)
#
# uris.txt: one ROOT file URI per line (http(s) OK, HTTP-Range streaming).
import argparse, hashlib, json, math, os, sys, time
import numpy as np
import uproot
from scipy import stats

def shasum_bytes(b): return hashlib.sha256(b).hexdigest()

def iter_leading_phi(source, is_mc, pt_min, eta_max, batch, max_events, require_jetid):
    """Yield leading-jet phi per event; also yield per-event jet count kept."""
    n_seen = n_kept = 0
    if is_mc:
        branches = ["Jet.Phi", "Jet.PT", "Jet.Eta"]
        tree_key = "Delphes"
        rename = {"Jet.Phi": "phi", "Jet.PT": "pt", "Jet.Eta": "eta"}
    else:
        branches = ["Jet_phi", "Jet_pt", "Jet_eta"] + (["Jet_jetId"] if require_jetid else [])
        tree_key = "Events"
        rename = {"Jet_phi": "phi", "Jet_pt": "pt", "Jet_eta": "eta", "Jet_jetId": "jetId"}
    srcs = source if isinstance(source, list) else [source]
    for src in srcs:
        with uproot.open(src) as f:
            tree = f[tree_key]
            for arrs in tree.iterate(branches, step_size=batch, library="ak"):
                d = {rename[b]: arrs[b] for b in branches}
                pt, eta, phi = d["pt"], d["eta"], d["phi"]
                mask = (abs(eta) < eta_max) & (pt > pt_min)
                if require_jetid and "jetId" in d:
                    mask = mask & (d["jetId"] >= 2)  # tight ID bit (NanoAOD)
                pt_m = pt[mask]
                phi_m = phi[mask]
                # leading jet index per event (None if no jet passes)
                has = (pt_m.num if hasattr(pt_m, "num") else None)
                import awkward as ak
                idx = ak.argmax(pt_m, axis=1, keepdims=True)
                lead_phi = ak.flatten(phi_m[idx], axis=None)
                n_evt = len(pt)
                n_seen += n_evt
                got = ak.num(lead_phi, axis=0)
                for v in lead_phi:
                    yield float(v)
                    n_kept += 1
                    if max_events and n_kept >= max_events:
                        return
    return

def bits_of_phi(phi, b):
    """Quantize (-pi,pi] into 2^b bins; return bin index (b bits)."""
    u = (phi + math.pi) / (2 * math.pi)          # (0,1]
    u = min(max(u, 1e-15), 1.0 - 1e-15)
    return int(u * (1 << b))

def cp_upper_bound(x, n, alpha):
    """One-sided Clopper-Pearson upper confidence bound."""
    if x >= n: return 1.0
    return float(stats.beta.ppf(1 - alpha, x + 1, n - x))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--files", help="text file with URIs (one per line)")
    ap.add_argument("--mc", help="single local Delphes ROOT file")
    ap.add_argument("--out", required=True, help="output prefix")
    ap.add_argument("--b", type=int, default=8, help="bits per event (bins=2^b)")
    ap.add_argument("--pt-min", type=float, default=50.0)
    ap.add_argument("--eta-max", type=float, default=2.5)
    ap.add_argument("--batch", default="200 MB")
    ap.add_argument("--max-events", type=int, default=0)
    ap.add_argument("--require-jetid", action="store_true")
    ap.add_argument("--alpha", type=float, default=1e-6, help="per-bin confidence level (pre-Bonferroni)")
    a = ap.parse_args()

    is_mc = bool(a.mc)
    if is_mc:
        sources = [a.mc]
        files_meta = [{"path": a.mc, "size": os.path.getsize(a.mc),
                       "sha256": shasum_bytes(open(a.mc, "rb").read())}]
    else:
        sources = [l.strip() for l in open(a.files) if l.strip()]
        files_meta = [{"uri": u} for u in sources]

    t0 = time.time()
    nbins = 1 << a.b
    counts = np.zeros(nbins, dtype=np.int64)
    phis = []
    bitbuf = bytearray(); acc = 0; nacc = 0
    for phi in iter_leading_phi(sources, is_mc, a.pt_min, a.eta_max,
                                a.batch, a.max_events, a.require_jetid and not is_mc):
        k = bits_of_phi(phi, a.b)
        counts[k] += 1
        phis.append(phi)
        acc = (acc << a.b) | k; nacc += a.b
        while nacc >= 8:
            nacc -= 8
            bitbuf.append((acc >> nacc) & 0xFF)
        acc &= (1 << nacc) - 1
    n = int(counts.sum())
    assert n == len(phis), "count mismatch"

    # --- uniformity tests ---
    p_hat = counts / n
    chi2 = float(((counts - n / nbins) ** 2).sum() / (n / nbins))
    chi2_p = float(1 - stats.chi2.cdf(chi2, nbins - 1))
    u = (np.array(phis) + math.pi) / (2 * math.pi)
    ks = stats.kstest(u, "uniform")

    # --- conservative min-entropy ---
    x_max = int(counts.max())
    alpha_corr = a.alpha / nbins                      # Bonferroni over bins
    p_upper = cp_upper_bound(x_max, n, alpha_corr)
    h_min = -math.log2(p_upper)

    # --- outputs ---
    bits_path = a.out + ".bits.bin"
    with open(bits_path, "wb") as fh: fh.write(bytes(bitbuf))
    manifest = {
        "extractor": "P v1: leading jet (max pT, |eta|<2.5, pT>50) -> phi -> 2^b uniform bins, MSB-first",
        "params": vars(a),
        "files": files_meta,
        "events_with_bits": n,
        "bins": nbins,
        "bin_width_mrad": round(2 * math.pi / nbins * 1000, 3),
        "wall_time_s": round(time.time() - t0, 2),
        "results": {
            "chi2": chi2, "chi2_df": nbins - 1, "chi2_p": chi2_p,
            "ks_stat": float(ks.statistic), "ks_p": float(ks.pvalue),
            "max_bin_count": x_max,
            "p_max_upper_CP_bonferroni": p_upper,
            "min_entropy_bits_per_event": h_min,
            "total_bits": n * a.b,
            "total_min_entropy_bits_lower_bound": n * h_min,
        },
        "outputs": {"bits_file": bits_path,
                    "bits_sha256": shasum_bytes(bytes(bitbuf))},
        "code_sha256": shasum_bytes(open(os.path.abspath(__file__), "rb").read()),
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    mpath = a.out + ".manifest.json"
    with open(mpath, "w") as fh: json.dump(manifest, fh, indent=2, ensure_ascii=False)
    print(json.dumps(manifest["results"], indent=2))
    print(f"\nmanifest -> {mpath}\nbits     -> {bits_path}")
    print("next: NIST STS / dieharder on the bits file (sanity only); "
          "twin implementation must reproduce bits_sha256 exactly.")

if __name__ == "__main__":
    main()
