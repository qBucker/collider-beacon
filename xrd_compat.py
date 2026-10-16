#!/usr/bin/env python3
# xrd_compat.py — int-coercion shim for fsspec-xrootd 0.5.5 + XRootD >= 6
#
# Symptom: TypeError: integer argument expected for offset
# Cause: uproot hands numpy.int64 byte offsets to fsspec-xrootd, which passes
#        them straight into XRootD's File.read().  XRootD 5.x used SWIG
#        bindings that silently coerced numpy ints; 6.x uses pybind11 with
#        strict type checks, so numpy.int64 is rejected.
# Scope: patches only the byte-range read paths of fsspec_xrootd.
#        No behavioral change beyond int() coercion. Does NOT touch the
#        frozen extractor (phase0_extract.py) — code_sha256 stays valid.
import fsspec_xrootd.xrootd as _m

_XFS = _m.XRootDFileSystem
_orig_cat_file = _XFS._cat_file
_orig_cat_ranges = _XFS._cat_ranges


def _c(v):
    return None if v is None else int(v)


async def _cat_file(self, path, start, end, **kwargs):
    return await _orig_cat_file(self, path, _c(start), _c(end), **kwargs)


async def _cat_ranges(self, paths, starts, ends, max_gap=None, batch_size=None, **kwargs):
    starts = [_c(s) for s in starts]
    ends = [_c(e) for e in ends]
    return await _orig_cat_ranges(self, paths, starts, ends, max_gap, batch_size, **kwargs)


_XFS._cat_file = _cat_file
_XFS._cat_ranges = _cat_ranges
