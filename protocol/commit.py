#!/usr/bin/env python3
"""Two-stage commitment for the Collider Beacon protocol.

Stage 1 (before recording):
  C_plan = SHA256("collider-beacon/C_plan/v1" || canonical(plan))
  plan = {round, desc, params, files, schedule}

Stage 2 (after recording):
  H_RAW  = SHA256("collider-beacon/H_RAW/v1" || canonical(data))
  data   = {round, plan_sha256, entries}
  C_data = SHA256("collider-beacon/C_data/v1" || H_RAW)

`entries` is the recorded data identity: for the Phase 0 demonstration, the
67 portal entries (filename, size, checksum) published by CERN Open Data. A
production deployment can use SHA256 of the raw bytes instead of the portal
checksum.

The canonical encoding is deterministic JSON: sorted keys, no whitespace,
UTF-8. The plan is fixed before recording; C_plan removes the operator's
choice among outputs. C_data binds the recorded bytes. Structural bias
resistance still requires the k-of-4 combination of the paper (Theorem 2);
this tool makes misbehavior attributable, not a lone source trustless.

Usage:
  python3 protocol/commit.py plan --spec spec.json --out plan.json
  python3 protocol/commit.py data --round R --plan plan.json \
      --portal-index runG/portal-file-index.json --out data.json
  python3 protocol/commit.py verify --plan plan.json --data data.json
"""

import argparse
import hashlib
import json
import sys
import time

PLAN_TAG = b"collider-beacon/C_plan/v1"
HRAW_TAG = b"collider-beacon/H_RAW/v1"
CDATA_TAG = b"collider-beacon/C_data/v1"


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")


def sha256_hex(data):
    return hashlib.sha256(data).hexdigest()


def make_plan(spec):
    plan = {
        "v": "collider-beacon/plan/v1",
        "round": spec["round"],
        "desc": spec["desc"],
        "params": spec["params"],
        "files": sorted(spec["files"]),
        "schedule": spec["schedule"],
    }
    return plan, sha256_hex(PLAN_TAG + canonical(plan))


def make_data(round_id, plan_sha, entries):
    data = {
        "v": "collider-beacon/data/v1",
        "round": round_id,
        "plan_sha256": plan_sha,
        "entries": sorted(entries, key=lambda e: e["path"]),
    }
    h_raw = sha256_hex(HRAW_TAG + canonical(data))
    c_data = sha256_hex(CDATA_TAG + bytes.fromhex(h_raw))
    return data, h_raw, c_data


def entries_from_portal(path):
    idx = json.load(open(path))
    entries = []
    for f in idx["files"]:
        entries.append({"path": f["filename"], "size": f["size"],
                        "checksum": f["checksum"]})
    return entries


def cmd_plan(args):
    spec = json.load(open(args.spec))
    plan, c_plan = make_plan(spec)
    rec = {"plan": plan, "plan_sha256": c_plan,
           "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    json.dump(rec, open(args.out, "w"), indent=1)
    print("C_plan:", c_plan)


def cmd_data(args):
    plan_rec = json.load(open(args.plan))
    plan_sha = plan_rec["plan_sha256"]
    if args.entries:
        entries = json.load(open(args.entries))
    elif args.portal_index:
        entries = entries_from_portal(args.portal_index)
    else:
        raise SystemExit("provide --entries or --portal-index")
    data, h_raw, c_data = make_data(args.round, plan_sha, entries)
    rec = {"data": data, "h_raw": h_raw, "data_sha256": c_data,
           "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    json.dump(rec, open(args.out, "w"), indent=1)
    print("H_RAW :", h_raw)
    print("C_data:", c_data)


def cmd_verify(args):
    plan_rec = json.load(open(args.plan))
    data_rec = json.load(open(args.data))
    plan = plan_rec["plan"]
    data = data_rec["data"]

    c_plan = sha256_hex(PLAN_TAG + canonical(plan))
    h_raw = sha256_hex(HRAW_TAG + canonical(data))
    c_data = sha256_hex(CDATA_TAG + bytes.fromhex(h_raw))

    checks = [
        ("C_plan", c_plan == plan_rec["plan_sha256"]),
        ("H_RAW", h_raw == data_rec["h_raw"]),
        ("C_data", c_data == data_rec["data_sha256"]),
        ("plan link", data["plan_sha256"] == plan_rec["plan_sha256"]),
        ("round link", data["round"] == plan["round"]),
    ]
    ok = all(v for _, v in checks)
    for name, v in checks:
        print("%-12s %s" % (name, "PASS" if v else "FAIL"))
    return 0 if ok else 1


def selftest():
    spec = {"round": "selftest", "desc": "toy", "params": {"b": 8},
            "files": ["b", "a"], "schedule": "now"}
    plan, c_plan = make_plan(spec)
    entries = [{"path": "b", "size": 2, "checksum": "adler32:00000002"},
               {"path": "a", "size": 1, "checksum": "adler32:00000001"}]
    data, h_raw, c_data = make_data("selftest", c_plan, entries)
    assert sha256_hex(PLAN_TAG + canonical(plan)) == c_plan
    assert sha256_hex(HRAW_TAG + canonical(data)) == h_raw
    assert sha256_hex(CDATA_TAG + bytes.fromhex(h_raw)) == c_data
    tampered = json.loads(json.dumps(data))
    tampered["entries"][0]["checksum"] = "adler32:deadbeef"
    assert sha256_hex(HRAW_TAG + canonical(tampered)) != h_raw
    print("selftest: PASS")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("plan")
    p.add_argument("--spec", required=True)
    p.add_argument("--out", required=True)
    p.set_defaults(func=cmd_plan)

    d = sub.add_parser("data")
    d.add_argument("--round", required=True)
    d.add_argument("--plan", required=True)
    d.add_argument("--entries")
    d.add_argument("--portal-index")
    d.add_argument("--out", required=True)
    d.set_defaults(func=cmd_data)

    v = sub.add_parser("verify")
    v.add_argument("--plan", required=True)
    v.add_argument("--data", required=True)
    v.set_defaults(func=cmd_verify)

    s = sub.add_parser("selftest")
    s.set_defaults(func=lambda a: selftest())

    args = ap.parse_args()
    if args.cmd == "verify":
        sys.exit(args.func(args))
    args.func(args)


if __name__ == "__main__":
    main()
