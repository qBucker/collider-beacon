#!/usr/bin/env python3
"""Toeplitz extraction with a chained public seed.

Implements Stage 2 of the Collider Beacon protocol for the b=8 and b=12 runs:

  s_0 = SHAKE256("collider-beacon/s0/v1" || params) expanded to the first block's
        seed length;
  s_r = SHAKE256("collider-beacon/chain/v1" || pack(output_{r-1})) expanded to
        the block's seed length.

Each block of N bits (an integer number of events) is extracted with a Toeplitz
matrix over GF(2), using m = floor(n_events * h_inf) - 128 output bits (the
128-bit leftover-hash margin). The Toeplitz matrix-vector product is computed by
exact integer convolution via FFT; the convolution coefficients are bounded by
the block size (< 2^53), so float64 FFT is exact after rounding.

Input formats:
  b=8  : one byte per symbol (0..255), as written by the extractor;
  b=12 : 12-bit symbols packed MSB-first, as written by the extractor.

Usage:
  python3 conditioning/toeplitz_extract.py --run-dir runG12 --b 12 \
      --hinf 11.3098 --block-events 100000 \
      --out conditioning/out/b12-toeplitz.bits.bin \
      --manifest conditioning/out/b12-toeplitz.manifest.json
"""

import argparse
import glob
import hashlib
import json
import math
import os
import time

import numpy as np
from scipy.fft import next_fast_len, rfft, irfft

LEFTOVER_MARGIN = 128
CHAIN_TAG = b"collider-beacon/chain/v1"
S0_TAG = b"collider-beacon/s0/v1"


def pack_bits(bits):
    """Pack a 0/1 uint8 array MSB-first into bytes."""
    pad = (-len(bits)) % 8
    if pad:
        bits = np.concatenate([bits, np.zeros(pad, dtype=np.uint8)])
    return np.packbits(bits).tobytes()


def expand_seed(tag, payload, nbits):
    """SHAKE256 expansion to nbits bits."""
    digest = hashlib.shake_256(tag + payload).digest((nbits + 7) // 8)
    return np.unpackbits(np.frombuffer(digest, dtype=np.uint8))[:nbits]


def decode_run(run_dir, b):
    """Decode the canonical 67 bit files into one 0/1 bitstream."""
    files = sorted(glob.glob(os.path.join(run_dir, "f[0-9][0-9].bits.bin")))
    if len(files) != 67:
        raise SystemExit("expected 67 bit files, found %d" % len(files))
    parts = []
    for f in files:
        raw = np.fromfile(f, dtype=np.uint8)
        if b == 8:
            bits = np.unpackbits(raw)
        elif b == 12:
            bits = np.unpackbits(raw)
            nsym = len(bits) // 12
            bits = bits[:nsym * 12]
        else:
            raise SystemExit("unsupported b=%d" % b)
        parts.append(bits)
    out = np.concatenate(parts)
    if len(out) % b:
        out = out[:len(out) - (len(out) % b)]
    return files, out


def toeplitz_fft(seed, x, m):
    """Toeplitz matrix-vector product over GF(2) via exact FFT convolution.

    The Toeplitz matrix is T[i,j] = seed[i-j+n-1] for i<m, j<n. Then
    y_i = (seed * x)[n-1+i] mod 2.
    """
    n = len(x)
    L = m + n - 1
    if len(seed) != L:
        raise ValueError("seed length %d != m+n-1=%d" % (len(seed), L))
    size = next_fast_len(L + n - 1)
    conv = np.rint(irfft(rfft(seed.astype(np.float64), size) *
                         rfft(x.astype(np.float64), size), size)[:L + n - 1])
    return (conv[n - 1:n - 1 + m].astype(np.int64) & 1).astype(np.uint8)


def selftest():
    rng = np.random.default_rng(0)
    for n, m in [(8, 5), (16, 9), (100, 37), (1200, 700)]:
        seed = rng.integers(0, 2, m + n - 1)
        x = rng.integers(0, 2, n)
        T = np.array([[seed[i - j + n - 1] for j in range(n)] for i in range(m)])
        direct = (T @ x) % 2
        fast = toeplitz_fft(seed, x, m)
        if not np.array_equal(direct, fast):
            raise SystemExit("selftest failed at n=%d m=%d" % (n, m))
    print("selftest: pass")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--b", type=int, required=True)
    ap.add_argument("--hinf", type=float, required=True)
    ap.add_argument("--block-events", type=int, default=100000)
    ap.add_argument("--seed-salt", default="0")
    ap.add_argument("--timestamp", default="2026-10-23T00:00:00Z")
    ap.add_argument("--out", required=True)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        selftest()
        return

    files, stream = decode_run(args.run_dir, args.b)
    n_total = len(stream)
    block_bits = args.block_events * args.b
    nblocks = (n_total + block_bits - 1) // block_bits

    params = {
        "run_dir": os.path.basename(os.path.normpath(args.run_dir)),
        "b": args.b,
        "hinf": args.hinf,
        "block_events": args.block_events,
        "leftover_margin_bits": LEFTOVER_MARGIN,
        "seed_salt": args.seed_salt,
        "timestamp": args.timestamp,
        "files": [os.path.basename(f) for f in files],
        "input_bits": int(n_total),
    }
    s0_payload = json.dumps(params, sort_keys=True).encode()

    outputs = []
    blocks = []
    prev = None
    t0 = time.time()
    for bi in range(nblocks):
        block = stream[bi * block_bits:(bi + 1) * block_bits]
        n = len(block)
        events = n // args.b
        k = events * args.hinf
        m = int(math.floor(k)) - LEFTOVER_MARGIN
        if m <= 0 or m > n:
            raise SystemExit("invalid m=%d for block %d (n=%d)" % (m, bi, n))
        L = m + n - 1
        if bi == 0:
            seed = expand_seed(S0_TAG, s0_payload, L)
            seed_rule = "s0"
        else:
            seed = expand_seed(CHAIN_TAG, pack_bits(prev), L)
            seed_rule = "chain"
        y = toeplitz_fft(seed, block, m)
        outputs.append(y)
        blocks.append({"block": bi, "events": int(events), "n_bits": int(n),
                       "m_bits": int(m), "seed_bits": int(L), "seed_rule": seed_rule,
                       "output_sha256": hashlib.sha256(pack_bits(y)).hexdigest()})
        prev = y
        if bi % 10 == 0:
            print("block %2d/%d: events=%d m=%d" % (bi, nblocks, events, m))

    out_bits = np.concatenate(outputs)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "wb") as fh:
        fh.write(pack_bits(out_bits))
    out_sha = hashlib.sha256(open(args.out, "rb").read()).hexdigest()

    manifest = {
        "protocol": "Stage-2 Toeplitz extraction, chained public seed",
        "params": params,
        "seed_rule": "s0 = SHAKE256(tag || sorted params); s_r = SHAKE256(tag || pack(output_{r-1}))",
        "leftover_hash": "m = floor(n_events * hinf) - 128",
        "n_blocks": nblocks,
        "input_bits": int(n_total),
        "output_bits": int(len(out_bits)),
        "output_sha256": out_sha,
        "wall_time_s": round(time.time() - t0, 2),
        "blocks": blocks,
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    with open(args.manifest, "w") as fh:
        json.dump(manifest, fh, indent=1)
    print("output bits: %d" % len(out_bits))
    print("output sha256: %s" % out_sha)
    print("manifest: %s" % args.manifest)


if __name__ == "__main__":
    main()
