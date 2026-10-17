#!/usr/bin/env python3
# atlas_extract.py — Collider Beacon Phase 0: ATLAS adapter for extractor P (v1 semantics)
# v2 (2026-10-17): resumable per-file workers (partial results on disk, per-file timeout,
#   https -> root:// fallback). Extraction semantics unchanged from v1.
#
# Cross-detector check of effect 1 (localized phi acceptance deficit, CMS bins 227-234).
# This script mirrors phase0_extract.py (R3 semantics) with ATLAS branch names:
#   tree "analysis": jet_pt, jet_eta, jet_phi (RVec<float>, pT in GeV)
# The algorithm is unchanged:
#   per event -> leading jet (max pT, |eta| < eta_max, pT > pt_min; first maximum kept)
#             -> phi in (-pi, pi] -> uniform 2^b bins -> emit bin index as b bits (MSB-first)
#   entropy accounting: Clopper-Pearson upper bound on max bin frequency with
#   Bonferroni correction over 2^b bins -> per-event min-entropy bound.
#
# The frozen extractor (phase0_extract.py) is not modified; this file is the ATLAS variant.
#
# ATLAS sample: CERN Open Data record 93933
#   "ATLAS ROOT ntuple format Run 2 2015+2016 proton-proton collision data beta release, no skim"
#   DOI 10.7483/OPENDATA.ATLAS.VV3I.0WJE, license CC0-1.0
#   16 files, 5,770,706,892 events, 1.35 TB (portal metadata)
#
# Usage:
#   python3 atlas_extract.py --files urls-noskim.https.txt --out smoke \
#       --per-file-events 50000 --file-timeout 300
#
# Output: <out>.manifest.json, <out>.bits.bin; per-file partials under <out>.partial/
import argparse
import hashlib
import json
import math
import os
import subprocess
import sys
import time

import numpy as np

PARTIAL_SUFFIX = ".partial.json"


def shasum_bytes(b):
    return hashlib.sha256(b).hexdigest()


def root_fallback(url):
    """Map a portal https URL to the equivalent eospublic XRootD URL."""
    marker = "https://opendata.cern.ch/eos/"
    if url.startswith(marker):
        return "root://eospublic.cern.ch:1094//eos/" + url[len(marker):]
    return None


# ---------------------------------------------------------------- worker (one file)
def worker(args):
    import uproot
    import awkward as ak

    # Direct EOS endpoint: the portal proxy is throttled; eospublic redirects to a
    # storage server that the parallel source can address.
    url = args.url
    if url.startswith("https://opendata.cern.ch/eos/"):
        url = "https://eospublic.cern.ch//eos/" + url[len("https://opendata.cern.ch/eos/"):]

    ca = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cern-ca-bundle.pem")
    if os.path.exists(ca):
        os.environ.setdefault("SSL_CERT_FILE", ca)

    t0 = time.time()
    phis = []
    opener = None
    if url.startswith("https://"):
        from parallel_http_source import ParallelHTTPSource

        opener = lambda u: uproot.open(u, handler=ParallelHTTPSource,
                                        num_workers=args.http_workers, timeout=args.timeout)
    else:
        opener = uproot.open
    with opener(url) as f:
        tree = f["analysis"]
        n_total = int(tree.num_entries)
        stop = n_total if args.per_file_events <= 0 else min(args.per_file_events, n_total)
        n_seen = 0
        for arrs in tree.iterate(
            ["jet_pt", "jet_eta", "jet_phi"],
            entry_start=0,
            entry_stop=stop,
            step_size=args.batch,
            library="ak",
        ):
            pt, eta, phi = arrs["jet_pt"], arrs["jet_eta"], arrs["jet_phi"]
            mask = (abs(eta) < args.eta_max) & (pt > args.pt_min)
            pt_m = pt[mask]
            phi_m = phi[mask]
            idx = ak.argmax(pt_m, axis=1, keepdims=True)
            lead_phi = ak.flatten(phi_m[idx], axis=None)
            n_seen += len(pt)
            phis.extend(float(v) for v in lead_phi)

    nbins = 1 << args.b
    counts = np.zeros(nbins, dtype=np.int64)
    bitbuf = bytearray()
    acc = 0
    nacc = 0
    for phi in phis:
        u = (phi + math.pi) / (2 * math.pi)
        u = min(max(u, 1e-15), 1.0 - 1e-15)
        k = int(u * nbins)
        counts[k] += 1
        acc = (acc << args.b) | k
        nacc += args.b
        while nacc >= 8:
            nacc -= 8
            bitbuf.append((acc >> nacc) & 0xFF)
        acc &= (1 << nacc) - 1

    prefix = args.partial_prefix
    os.makedirs(os.path.dirname(prefix) or ".", exist_ok=True)
    with open(prefix + ".bits.bin", "wb") as fh:
        fh.write(bytes(bitbuf))
    np.save(prefix + ".phis.npy", np.asarray(phis, dtype=np.float64))
    partial = {
        "uri": url,
        "entries": n_total,
        "entries_read": n_seen,
        "events_with_bits": len(phis),
        "counts": counts.tolist(),
        "bins": nbins,
        "bits_file": prefix + ".bits.bin",
        "bits_sha256": shasum_bytes(bytes(bitbuf)),
        "wall_time_s": round(time.time() - t0, 2),
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    with open(prefix + PARTIAL_SUFFIX, "w") as fh:
        json.dump(partial, fh, indent=2)
    print(
        f"[worker] {os.path.basename(url)} entries_read={n_seen} events_with_bits={len(phis)} "
        f"time={time.time()-t0:.1f}s",
        file=sys.stderr,
        flush=True,
    )


# ---------------------------------------------------------------- combine
def cp_upper_bound(x, n, alpha):
    from scipy import stats

    if x >= n:
        return 1.0
    return float(stats.beta.ppf(1 - alpha, x + 1, n - x))


def band_report(counts, nbins):
    """Effect-1 band ratio: bins 227-234 (phi ~ +139..+150 deg) vs surrounding sidebands."""
    lo, hi = 227, 234
    band = float(counts[lo : hi + 1].sum())
    n_band = hi - lo + 1
    side = float(np.concatenate([counts[lo - 8 : lo], counts[hi + 1 : hi + 9]]).mean()) * n_band
    rest_mask = np.ones(nbins, dtype=bool)
    rest_mask[lo : hi + 1] = False
    rest_mean = float(counts[rest_mask].mean())
    return {
        "band_bins": [lo, hi],
        "band_phi_deg": [round((lo / nbins) * 360 - 180, 1), round(((hi + 1) / nbins) * 360 - 180, 1)],
        "band_count": band,
        "local_sideband_expected": side,
        "local_ratio": band / side if side else None,
        "global_ratio": (band / n_band) / rest_mean if rest_mean else None,
    }


def combine(args, sources, partial_dir):
    from scipy import stats

    nbins = 1 << args.b
    counts = np.zeros(nbins, dtype=np.int64)
    all_phis = []
    bitbuf = bytearray()
    files_meta = []
    failed = []
    for src in sources:
        name = os.path.basename(src)
        prefix = os.path.join(partial_dir, name)
        pp = prefix + PARTIAL_SUFFIX
        if not os.path.exists(pp):
            failed.append({"uri": src, "reason": "no partial result"})
            continue
        with open(pp) as fh:
            p = json.load(fh)
        pcounts = np.asarray(p["counts"], dtype=np.int64)
        counts += pcounts
        all_phis.extend(np.load(prefix + ".phis.npy").tolist())
        bitbuf.extend(open(prefix + ".bits.bin", "rb").read())
        files_meta.append(
            {
                "uri": src,
                "entries": p["entries"],
                "entries_read": p["entries_read"],
                "events_with_bits": p["events_with_bits"],
                "protocol": "root" if p["uri"].startswith("root://") else "https",
                "wall_time_s": p["wall_time_s"],
                "partial_bits_sha256": p["bits_sha256"],
                "effect1_band_local_ratio": band_report(pcounts, nbins)["local_ratio"],
            }
        )
        print(
            f"[combine] {name} n={p['events_with_bits']} local_band_ratio="
            f"{band_report(pcounts, nbins)['local_ratio']:.4f}",
            file=sys.stderr,
            flush=True,
        )

    n = int(counts.sum())
    if n == 0:
        raise SystemExit("no events combined")

    p_hat = counts / n
    chi2 = float(((counts - n / nbins) ** 2).sum() / (n / nbins))
    chi2_p = float(1 - stats.chi2.cdf(chi2, nbins - 1))
    u = (np.asarray(all_phis) + math.pi) / (2 * math.pi)
    ks = stats.kstest(u, "uniform")

    x_max = int(counts.max())
    alpha_corr = args.alpha / nbins
    p_upper = cp_upper_bound(x_max, n, alpha_corr)
    h_min = -math.log2(p_upper)

    bits_path = args.out + ".bits.bin"
    with open(bits_path, "wb") as fh:
        fh.write(bytes(bitbuf))

    manifest = {
        "extractor": (f"P v1 ATLAS adapter: leading jet (max pT, |eta|<{args.eta_max:g}, pT>{args.pt_min:g} GeV) "
                      "-> phi -> 2^b uniform bins, MSB-first"),
        "sample": {
            "record": "93933",
            "title": "ATLAS ROOT ntuple format Run 2 2015+2016 proton-proton collision data beta release, no skim",
            "doi": "10.7483/OPENDATA.ATLAS.VV3I.0WJE",
            "license": "CC0-1.0",
            "release": "2025e-13tev-beta",
            "tree": "analysis",
            "branches": ["jet_pt (GeV)", "jet_eta", "jet_phi"],
        },
        "params": {
            "b": args.b, "pt_min": args.pt_min, "eta_max": args.eta_max,
            "per_file_events": args.per_file_events, "batch": args.batch, "alpha": args.alpha,
        },
        "files": files_meta,
        "failed_files": failed,
        "events_with_bits": n,
        "bins": nbins,
        "bin_width_mrad": round(2 * math.pi / nbins * 1000, 3),
        "wall_time_s": round(time.time() - args.t_start, 2),
        "results": {
            "chi2": chi2, "chi2_df": nbins - 1, "chi2_p": chi2_p,
            "ks_stat": float(ks.statistic), "ks_p": float(ks.pvalue),
            "max_bin_count": x_max,
            "p_max_upper_CP_bonferroni": p_upper,
            "min_entropy_bits_per_event": h_min,
            "total_bits": n * args.b,
            "total_min_entropy_bits_lower_bound": n * h_min,
            "counts": counts.tolist(),
            "effect1_band": band_report(counts, nbins),
        },
        "outputs": {"bits_file": bits_path, "bits_sha256": shasum_bytes(bytes(bitbuf))},
        "code_sha256": shasum_bytes(open(os.path.abspath(__file__), "rb").read()),
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    mpath = args.out + ".manifest.json"
    with open(mpath, "w") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False)
    print(json.dumps({k: v for k, v in manifest["results"].items() if k != "counts"}, indent=2))
    print(f"\nmanifest -> {mpath}\nbits     -> {bits_path}\nfailed   -> {len(failed)} file(s)")


# ---------------------------------------------------------------- parent
def process_one(args, i, src, partial_dir, n_sources):
    """Run retries for one file; writes <name>.partial.json on success."""
    name = os.path.basename(src)
    prefix = os.path.join(partial_dir, name)
    candidates = [src]
    fb = root_fallback(src)
    if fb:
        candidates.append(fb)
    for attempt in range(args.retries):
        url = candidates[0] if attempt < args.retries - 1 else candidates[-1]
        cmd = [
            sys.executable, os.path.abspath(__file__), "--worker",
            "--url", url,
            "--partial-prefix", prefix,
            "--per-file-events", str(args.per_file_events),
            "--batch", str(args.batch),
            "--b", str(args.b),
            "--pt-min", str(args.pt_min),
            "--eta-max", str(args.eta_max),
            "--http-workers", str(args.http_workers),
            "--timeout", str(args.timeout),
        ]
        log = prefix + f".attempt{attempt}.log"
        t0 = time.time()
        try:
            with open(log, "w") as lf:
                r = subprocess.run(cmd, stdout=lf, stderr=subprocess.STDOUT,
                                   timeout=args.file_timeout)
            if r.returncode == 0 and os.path.exists(prefix + PARTIAL_SUFFIX):
                print(
                    f"[file {i}/{n_sources}] {name} done ({time.time()-t0:.1f}s, "
                    f"{'root' if url.startswith('root://') else 'https'})",
                    file=sys.stderr, flush=True,
                )
                return True
            tail = open(log).read()[-300:].replace("\n", " ")
            print(f"[retry {attempt+1}/{args.retries}] {name} rc={r.returncode}: {tail}",
                  file=sys.stderr, flush=True)
        except subprocess.TimeoutExpired:
            print(f"[retry {attempt+1}/{args.retries}] {name} timeout after {args.file_timeout}s",
                  file=sys.stderr, flush=True)
    print(f"[fail {i}/{n_sources}] {name} — kept out of the combined sample",
          file=sys.stderr, flush=True)
    return False


def parent(args):
    args.t_start = time.time()
    sources = [l.strip().replace("simplecache::", "") for l in open(args.files) if l.strip()]
    partial_dir = args.out + ".partial"
    os.makedirs(partial_dir, exist_ok=True)

    pending = []
    for i, src in enumerate(sources, 1):
        name = os.path.basename(src)
        prefix = os.path.join(partial_dir, name)
        if os.path.exists(prefix + PARTIAL_SUFFIX):
            print(f"[skip {i}/{len(sources)}] {name} (partial exists)", file=sys.stderr, flush=True)
        else:
            pending.append((i, src))

    if pending:
        from concurrent.futures import ThreadPoolExecutor, as_completed

        with ThreadPoolExecutor(max_workers=args.concurrency) as ex:
            futures = [ex.submit(process_one, args, i, src, partial_dir, len(sources))
                       for i, src in pending]
            for fut in as_completed(futures):
                fut.result()

    combine(args, sources, partial_dir)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--files", help="text file with ROOT URIs (one per line)")
    ap.add_argument("--out", help="output prefix")
    ap.add_argument("--b", type=int, default=8)
    ap.add_argument("--pt-min", type=float, default=20.0, help="GeV; same value as the CMS round-1 run")
    ap.add_argument("--eta-max", type=float, default=2.5)
    ap.add_argument("--per-file-events", type=int, default=50000,
                    help="entries read from the start of each file (0 = all)")
    ap.add_argument("--batch", type=int, default=200000, help="entries per read batch")
    ap.add_argument("--alpha", type=float, default=1e-6)
    ap.add_argument("--retries", type=int, default=2, help="attempts per file")
    ap.add_argument("--file-timeout", type=int, default=300, help="seconds per attempt")
    ap.add_argument("--concurrency", type=int, default=4, help="files processed in parallel")
    ap.add_argument("--http-workers", type=int, default=16, help="parallel HTTP range connections per file")
    ap.add_argument("--timeout", type=int, default=120, help="per-request HTTP timeout (s)")
    # worker mode
    ap.add_argument("--worker", action="store_true")
    ap.add_argument("--url")
    ap.add_argument("--partial-prefix")
    a = ap.parse_args()

    if a.worker:
        if not (a.url and a.partial_prefix):
            raise SystemExit("--worker requires --url and --partial-prefix")
        worker(a)
    else:
        if not (a.files and a.out):
            raise SystemExit("--files and --out are required")
        parent(a)


if __name__ == "__main__":
    main()
