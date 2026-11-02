# Multi-branch precision scan of the CMS PFNanoAOD product (2026-11-02)

Question: is the 12-bit mantissa lattice a leading-jet property, or a
product-wide storage convention? The audit is repeated on three additional
branches read from 20 files of record 31316 (MET, muons, electrons), plus the
previously measured jets and secondary vertices.

Extraction: `multibranch_extract.py` (through `xrd_run.py`), 20 files,
MET_phi / Muon_phi / Electron_phi; wall 446.9 s; manifest in
`multibranch-2026-11-02/manifest.json`. Audit: `pp_audit` (commit `ec19d6a`,
tag `pp-v0.1.0`); raw values in `met_phi.npy`, `muon_phi.npy`,
`electron_phi.npy` (regenerable, not archived).

| branch | n | b per octave | on-grid | h_floor(8) | h_floor(12) | h_floor(16) |
|---|---|---|---|---|---|---|
| leading jet | 5,211,771 | 12 | 1.0000 | 7.8413 | 11.3098 | 12.9425 |
| secondary vertex | 4,468,841 | 12 | 1.0000 | 7.7584 | 11.2638 | 12.8912 |
| MET | 8,592,169 | 12 | 1.0000 | 7.8599 | 11.3540 | 13.0652 |
| muons | 489,942 | 12 | 1.0000 | 7.5096 | 10.3447 | 11.7378 |
| electrons | 310,683 | 12 | 1.0000 | 7.5921 | 10.5388 | 11.4932 |

All five branches show the same 12-bit lattice in every octave e = -8..1,
with on-grid fraction 1.0000. The floors differ because the sample size and
the source density differ, not because the lattice differs: the muon and
electron samples are 11-27 times smaller than the jet sample, so their
sample boundary is lower and their floors at b = 12 and b = 16 are
sample-limited. The lattice boundary b_lat is a product constant; the sample
boundary b_stat - log2 n is the branch-dependent part.

This answers the "leading-jet only" concern: the storage convention is
product-wide, and the audit separates the product constant (b = 12) from the
branch-dependent sample boundary.
