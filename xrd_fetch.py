#!/usr/bin/env python3
# xrd_fetch.py — fetch one EOS file to local disk over XRootD (via fsspec-xrootd).
#
# Pitfall record (2026-10-15): raw XRootD.client.File.read() sync path hangs
# indefinitely in this WSL env (0 bytes, 0 CPU). The fsspec-xrootd layer —
# the same read path uproot uses — works, so the fetch goes through it too.
# Usage: python3 xrd_fetch.py <root://.../file.root> <local/path>
import sys, time

import xrd_compat  # noqa: F401  (int-coercion shim for fsspec-xrootd + XRootD 6.x)
import fsspec

src, dst = sys.argv[1], sys.argv[2]
# url_to_fs parses host -> hostid for XRootDFileSystem (direct construction needs hostid explicitly)
fs, path = fsspec.core.url_to_fs(src)
info = fs.info(path)
total = info["size"]
print(f"size: {total:,} bytes -> {dst}", flush=True)

CH = 2 << 20  # 2 MB per cat_file: basket-scale reads are the proven-working size on this link
pos = 0
t0 = time.time()
last = t0
with open(dst, "wb") as out:
    while pos < total:
        end = min(pos + CH, total)
        t1 = time.time()
        out.write(fs.cat_file(path, start=pos, end=end))
        dt1 = time.time() - t1
        if dt1 > 90:
            raise SystemExit(f"WATCHDOG: chunk at {pos:,} took {dt1:.0f}s — aborting")
        pos = end
        now = time.time()
        if now - last >= 5:
            print(f"  {pos/1e6:,.0f} MB / {total/1e6:,.0f} MB  ({pos/1e6/(now-t0):.1f} MB/s)", flush=True)
            last = now
dt = time.time() - t0
print(f"DONE {pos:,} bytes in {dt:.1f}s ({pos/1e6/dt:.1f} MB/s)", flush=True)
