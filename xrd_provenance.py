#!/usr/bin/env python3
# xrd_provenance.py — f01 provenance: local immutable copy vs portal metadata,
# plus the remote-read vs local-rerun determinism gate (bit-stream identity).
# Run AFTER: xrd_fetch_resume.py (copy done) and the local rerun manifest exists.
import hashlib, json, os, zlib

PORTAL = {
    "source": "opendata.cern.ch/api/records/31316 -> metadata._file_indices[0].files[0]",
    "record": 31316,
    "filename": "nano_data2016_1-1.root",
    "uri": "root://eospublic.cern.ch//eos/opendata/cms/derived-data/PFNano/29-Feb-24/ZeroBias/Run2016G-UL2016_MiniAODv2_PFNanoAODv1/240212_182529/0000/nano_data2016_1-1.root",
    "size": 1098499319,
    "published_checksum": "adler32:9a8ac2aa",
}

path = "data/nano_data2016_1-1.root"
size = os.path.getsize(path)
adler = 1  # NB: streaming seed must be 1 (zlib.adler32(data) == adler32(data, 1)); seed 0 gives a nonstandard digest
sha = hashlib.sha256()
with open(path, "rb") as fh:
    while True:
        buf = fh.read(1 << 22)
        if not buf:
            break
        adler = zlib.adler32(buf, adler)
        sha.update(buf)
adler_hex = format(adler & 0xFFFFFFFF, "08x")
sha_hex = sha.hexdigest()

remote = json.load(open("runG/f01.manifest.json"))["outputs"]["bits_sha256"]
local = json.load(open("runG/f01-local.manifest.json"))["outputs"]["bits_sha256"]

prov = {
    "portal": PORTAL,
    "local_copy": {
        "path": path,
        "size": size,
        "adler32": adler_hex,
        "sha256": sha_hex,
        "note": "portal publishes adler32 only; sha256 self-pinned here for future comparison",
    },
    "checks": {
        "size_match": size == PORTAL["size"],
        "adler32_match": adler_hex == PORTAL["published_checksum"].split(":")[1],
    },
    "determinism_gate": {
        "description": "same file, two independent I/O paths (XRootD remote read vs local copy), extractor v1, identical params",
        "remote_bits_sha256": remote,
        "local_bits_sha256": local,
        "bit_identical": remote == local,
    },
}
out = "runG/f01.provenance.json"
json.dump(prov, open(out, "w"), indent=2, ensure_ascii=False)
print(json.dumps({"size_match": prov["checks"]["size_match"],
                  "adler32_match": prov["checks"]["adler32_match"],
                  "bit_identical": prov["determinism_gate"]["bit_identical"],
                  "sha256": sha_hex[:16] + "…"}, indent=2))
print("->", out)
