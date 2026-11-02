# Audit scaling benchmark (2026-11-02)

The pooled CMS leading-jet array (5,211,771 values) was tiled ten times to
52,117,710 values and audited with pp-audit v0.1.0 (same profile, b = 12).

| n | wall (s) | peak RSS (GB) | verdict |
|---|---|---|---|
| 5,211,771 | 2.1 | 0.26 | pass |
| 52,117,710 | 10.4 | 2.18 | pass |

The time is linear in n. The memory is dominated by the in-memory array and
the per-value temporary arrays (about 42 bytes per value at this chunking);
a streaming reader would remove the array term but is not implemented in
v0.1.0. The audit result is unchanged by tiling (b = 12, on-grid 1.0000;
the floor at b = 12 moves from 11.3098 to 11.4512 because the tiled sample
is ten times larger, which is the expected sample-boundary shift).

Command:
  python -m pp_audit verify --input /tmp/pp_tile50.npy \
    --profile examples/profile_cms_lead.json --out /tmp/pp_tile50.json
