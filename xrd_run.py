#!/usr/bin/env python3
# xrd_run.py — run a frozen phase0 script with the XRootD int-coercion shim.
# Usage: python3 xrd_run.py phase0_extract.py --files uris-xrd.txt --out runG/f01 --pt-min 20
import sys
import runpy

import xrd_compat  # noqa: F401  (import side-effect: patches fsspec-xrootd read paths)

script = sys.argv[1]
del sys.argv[1]
runpy.run_path(script, run_name="__main__")
