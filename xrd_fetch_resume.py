#!/usr/bin/env python3
# xrd_fetch_resume.py — resumable, chunked, audited fetch of one EOS file (slow mode).
#
# Reality check (2026-10-15/16): the CERN->home link runs ~100 KB/s class, and
# cold starts / large reads can stall for minutes under contention. Small chunks
# (512 KiB), a per-chunk watchdog, retries and offset-resume turn "hangs" into
# auditable slow progress. Never run in parallel with a batch extraction.
# Usage: python3 xrd_fetch_resume.py <root://.../file.root> <local/path> [chunk_bytes]
import os, signal, sys, time

import xrd_compat  # noqa: F401  (int-coercion shim for fsspec-xrootd + XRootD 6.x)
import fsspec

src, dst = sys.argv[1], sys.argv[2]
CH = int(sys.argv[3]) if len(sys.argv) > 3 else (512 << 10)

fs, path = fsspec.core.url_to_fs(src)
total = fs.info(path)["size"]
print(f"src: {src}\ntotal: {total:,} bytes -> {dst}  (chunk {CH>>10} KiB)", flush=True)


class ChunkTimeout(Exception):
    pass


def _alarm(signum, frame):
    raise ChunkTimeout()


signal.signal(signal.SIGALRM, _alarm)

for attempt in range(1, 31):
    done = os.path.getsize(dst) if os.path.exists(dst) else 0
    if done >= total:
        break
    print(f"[{time.strftime('%H:%M:%S')}] attempt {attempt}: resume at {done:,} bytes", flush=True)
    try:
        with open(dst, "r+b" if done else "wb") as out:
            pos = done
            t0 = time.time()
            base = done
            while pos < total:
                end = min(pos + CH, total)
                signal.alarm(480)  # per-chunk watchdog: 8 min (cold start can be slow)
                try:
                    data = fs.cat_file(path, start=pos, end=end)
                finally:
                    signal.alarm(0)
                if len(data) != end - pos:
                    raise IOError(f"short read at {pos}: {len(data)} != {end - pos}")
                out.seek(pos)
                out.write(data)
                pos = end
                if time.time() - t0 >= 15:
                    rate = (pos - base) / (time.time() - t0) / 1024
                    print(f"[{time.strftime('%H:%M:%S')}] {pos/1e6:.1f}/{total/1e6:.1f} MB "
                          f"({rate:.0f} KB/s)", flush=True)
                    t0 = time.time(); base = pos
    except (Exception, ChunkTimeout) as e:
        print(f"[{time.strftime('%H:%M:%S')}] attempt {attempt} broke: {type(e).__name__}: {e} "
              f"-> retry in 20 s", flush=True)
        time.sleep(20)
        continue
else:
    raise SystemExit("gave up after 30 attempts")

import hashlib, zlib
adler = 1  # NB: streaming seed must be 1 (zlib.adler32(data) == adler32(data, 1)); seed 0 gives a nonstandard digest
sha = hashlib.sha256()
with open(dst, "rb") as fh:
    while True:
        b = fh.read(1 << 22)
        if not b:
            break
        adler = zlib.adler32(b, adler)
        sha.update(b)
print(f"DONE {os.path.getsize(dst):,} bytes | sha256={sha.hexdigest()} "
      f"| adler32={format(adler & 0xFFFFFFFF, '08x')}", flush=True)
