# JetHT PFNanoAOD — second CMS product (2026-11-02)

Question: is the 12-bit lattice specific to the ZeroBias product, or a
convention of the PFNanoAOD product family?

Data: CERN Open Data record 31308 (JetHT, Run2016G PFNanoAOD), five files
`nano_data2016_1-{1,10,11,12,13}.root`; leading jets with pT > 20 GeV,
|eta| < 2.5. The frozen extractor reported 444,973 events with bits; the raw
phi extraction (`jetht_extract.py`) gives the same 444,973 values.

Audit (`jetht_audit.py`, pp-audit core):

| quantity | value |
|---|---|
| n | 444,973 |
| b per octave (e = -8..1) | 12 |
| on-grid fraction | 1.0000 |
| h_floor(8) | 7.6343 |
| h_floor(12) | 10.6918 |
| h_floor(16) | 11.7792 |

The b = 8 floor matches the frozen extractor's independent minimum-entropy
estimate (7.6343 bit) computed from the 8-bit bits file: two paths, same
answer. The floors are below the ZeroBias values because the JetHT sample is
an order of magnitude smaller (444,973 vs 5,211,771), not because the lattice
differs.

Conclusion: the 12-bit mantissa lattice is a convention of the PFNanoAOD
product family (two primary datasets), on top of the five-branch evidence
within ZeroBias and the ATLAS full-float32 contrast.

Evidence: `jetht-2026-11-02/{jetht5.manifest.json,jetht5.phi-manifest.json,
audit.json}`; the bits file `jetht5.bits.bin` (sha256 in the manifest); the
raw phi array is regenerable and not archived.
