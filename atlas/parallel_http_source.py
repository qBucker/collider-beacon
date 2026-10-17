#!/usr/bin/env python3
# parallel_http_source.py — uproot Source with parallel HTTP range reads.
#
# Motivation: CERN EOS redirects GET (307) to a storage server; uproot's default
# fsspec source does not handle that path and reads sequentially, which is too slow
# on the current link (~20-50 kB/s per connection). This source resolves the
# redirect once, then fetches every requested range with N parallel connections
# (measured aggregate ~280-330 kB/s).
#
# Usage:
#   from parallel_http_source import ParallelHTTPSource
#   f = uproot.open(url, handler=ParallelHTTPSource, num_workers=16, timeout=60)
import http.client
import os
import ssl
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

import uproot.source.chunk as chunk_mod
from uproot.source.futures import TrivialFuture

MIN_PART_BYTES = 256 * 1024


def _ssl_context():
    cafile = os.environ.get("SSL_CERT_FILE")
    if cafile and os.path.exists(cafile):
        return ssl.create_default_context(cafile=cafile)
    return ssl.create_default_context()


def _conn(url, timeout):
    p = urlparse(url)
    if p.scheme == "https":
        return http.client.HTTPSConnection(p.hostname, p.port or 443, timeout=timeout, context=_ssl_context())
    return http.client.HTTPConnection(p.hostname, p.port or 80, timeout=timeout)


def _path(url):
    p = urlparse(url)
    return p.path + (("?" + p.query) if p.query else "")


def _resolve(url, timeout):
    """Return (final_url, total_size). Follows one redirect from EOS."""
    conn = _conn(url, timeout)
    conn.request("HEAD", _path(url))
    r = conn.getresponse()
    total = r.getheader("Content-Length")
    r.read()
    conn.close()
    total = int(total) if total else None

    conn = _conn(url, timeout)
    conn.request("GET", _path(url), headers={"Range": "bytes=0-0"})
    r = conn.getresponse()
    loc = r.getheader("Location")
    status = r.status
    r.read()
    conn.close()
    if loc and status in (301, 302, 303, 307, 308):
        final = loc
        # total size from the final target
        conn = _conn(final, timeout)
        conn.request("get", _path(final), headers={"Range": "bytes=0-0"})
        r = conn.getresponse()
        cr = r.getheader("Content-Range")  # bytes 0-0/N
        if cr and "/" in cr:
            total = int(cr.split("/")[-1])
        r.read()
        conn.close()
        return final, total
    return url, total


def _fetch_range(url, start, stop, timeout, retries=3):
    last = None
    for _ in range(retries):
        try:
            conn = _conn(url, timeout)
            conn.request("GET", _path(url), headers={"Range": f"bytes={start}-{stop - 1}"})
            r = conn.getresponse()
            data = r.read()
            status = r.status
            conn.close()
            if status not in (206, 200):
                raise OSError(f"HTTP {status} for range {start}-{stop - 1}")
            if len(data) != stop - start:
                raise OSError(f"short read {len(data)} != {stop - start}")
            return data
        except Exception as e:  # noqa: BLE001
            last = e
    raise OSError(f"range fetch failed after {retries} attempts: {last}")


class ParallelHTTPSource(chunk_mod.Source):
    """uproot Source: parallel range GETs against a (possibly redirected) URL."""

    def __init__(self, file_path, num_workers=16, timeout=60, **kwargs):
        super().__init__()
        self._file_path = file_path
        self._num_workers = max(1, int(num_workers))
        self._timeout = timeout
        self._final_url, self._num_bytes = _resolve(file_path, timeout)

    @property
    def num_bytes(self):
        return self._num_bytes

    @property
    def closed(self):
        # uproot's base Source reports closed when no executor is attached;
        # this source closes per-request connections and holds no pool.
        return False

    def chunk(self, start, stop):
        n = stop - start
        if n <= 0:
            return chunk_mod.Chunk(self, start, stop, TrivialFuture(b""))
        nparts = max(1, min(self._num_workers, (n + MIN_PART_BYTES - 1) // MIN_PART_BYTES))
        if nparts == 1:
            data = _fetch_range(self._final_url, start, stop, self._timeout)
        else:
            step = (n + nparts - 1) // nparts
            ranges = []
            pos = start
            while pos < stop:
                end = min(pos + step, stop)
                ranges.append((pos, end))
                pos = end
            with ThreadPoolExecutor(max_workers=len(ranges)) as ex:
                parts = list(ex.map(
                    lambda ab: _fetch_range(self._final_url, ab[0], ab[1], self._timeout),
                    ranges,
                ))
            data = b"".join(parts)
        return chunk_mod.Chunk(self, start, stop, TrivialFuture(data))

    def chunks(self, ranges, notifications):
        out = []
        for start, stop in ranges:
            c = self.chunk(start, stop)
            out.append(c)
            notifications.put(c)
        return out

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        pass
