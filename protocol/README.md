# Two-stage commitment — Stage 1/2 of the protocol

This directory implements the two-stage commitment of Section 6 of the paper:

- **Stage 1, before recording:** `C_plan = SHA256(tag || canonical(plan))`,
  where `plan = {round, desc, params, files, schedule}`. The file list and the
  rule are fixed before the data exist.
- **Stage 2, after recording:** `H_RAW = SHA256(tag || canonical(data))` and
  `C_data = SHA256(tag || H_RAW)`, where `data = {round, plan_sha256, entries}`
  and `entries` is the recorded data identity. The data record carries the plan
  hash, so the two stages are linked.

Canonical encoding: deterministic JSON, sorted keys, no whitespace, UTF-8.
Tags: `collider-beacon/C_plan/v1`, `collider-beacon/H_RAW/v1`,
`collider-beacon/C_data/v1`.

## Phase 0 example

`examples/phase0-b12-plan-spec.json` fixes the b=12 round:

- round `phase0-b12-2026-10-19`;
- 67 CMS ZeroBias raw-file URIs from the portal index;
- extractor code hash `9272d4df…`;
- prediction card `61b1518`, release at `T_rel`.

The generated records:

| field | value |
|---|---|
| `C_plan` | `0b8ff375e4c4b98aa1e6733a6519f65ef482d450898bd3120cf7d1a5d02da9ed` |
| `H_RAW` | `0ef787d74df3ff4b703b51d29f40c386b844c510d6d8f71587ca40dbf6851ac5` |
| `C_data` | `857c293c5665aea77c99a08e4046ec5ee06cc44f601059dc01835a5faf8c8b45` |

`entries` uses the portal identity: `(filename, size, adler32)` for all 67
files (`runG/portal-file-index.json`). A production deployment can use SHA256
of the raw bytes instead; the CLI does not enforce the checksum algorithm.

## Usage

```bash
python3 protocol/commit.py plan --spec protocol/examples/phase0-b12-plan-spec.json \
    --out protocol/examples/phase0-b12-plan.json
python3 protocol/commit.py data --round phase0-b12-2026-10-19 \
    --plan protocol/examples/phase0-b12-plan.json \
    --portal-index runG/portal-file-index.json \
    --out protocol/examples/phase0-b12-data.json
python3 protocol/commit.py verify --plan protocol/examples/phase0-b12-plan.json \
    --data protocol/examples/phase0-b12-data.json
```

`verify` recomputes `C_plan`, `H_RAW`, and `C_data`, checks both hashes against
the records, and checks the plan/round links. Tampering with either the plan or
any data entry fails the corresponding check; `selftest` covers the toy case.

## What this does and does not do

- `C_plan` removes the operator's choice among outputs: the rule, file list,
  parameters, and schedule are fixed before recording. An operator can still
  omit a whole round, which is a publicly visible liveness failure, but cannot
  select among outputs without finding a collision.
- `C_data` binds the recorded identity after the fact. Structural bias
  resistance against a corrupted operator requires the k-of-4 combination of
  the paper (Theorem 2); this tool makes misbehavior attributable, not a lone
  source trustless.
- The release calendar, operational key management, and deployment are outside
  this tool. The records are demonstrations of the commitment discipline.
