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
| `H_RAW` | `3e14a083730bed40d2ec161c29280bf38288fb782f54e94aa21692ab1f268aa6` |
| `C_data` | `a7a49e0139c07faa41b7cf01337027d863f725da38244374d1af812af2677057` |

`entries` uses the recorded product of this open-data round: the 67 extracted
bit files and their SHA256 from the runG12 manifests. The portal tuple
`(filename, size, adler32)` is retained as a fetch-integrity check, not as the
commitment: adler32 is not collision-resistant. A raw-tier production round
would hash the raw bytes with SHA256 instead.

## Usage

```bash
python3 protocol/commit.py plan --spec protocol/examples/phase0-b12-plan-spec.json \
    --out protocol/examples/phase0-b12-plan.json
python3 protocol/commit.py data --round phase0-b12-2026-10-19 \
    --plan protocol/examples/phase0-b12-plan.json \
    --manifests runG12 \
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
