# Pre-registration — B5 secondary-vertex stratification

- Date (UTC): 2026-10-27
- Run / sample: 67 CMS ZeroBias Run2016G PFNanoAOD files (`uris.txt`), the same
  list as the phase-0 audit and C5
- Analysis code: `b5_extract.py`, `b5_analyze.py`, `xrd_batch_b5.sh`,
  `xrd_b5_sweep.sh` (this pass)
- Status: frozen before any B5 quantity is computed; the commit of this file
  is the timestamp

## Purpose

The C5 hadronic extension reported a high-order Fourier line in the
secondary-vertex azimuth that is absent from the leading-jet azimuth on the
same events: k=18 (20-degree period), amplitude 0.0162, z=34.3, with 53/67
files individually above 3 sigma; the jet control gives 0.0010 (z=2.0)
(`diagnostics/c5-result-2026-10-26.md`, F2).

This pass characterizes that structure. It stratifies secondary vertices by
vertex properties, tests phase coherence across files, the harmonic content of
the line, and the eta dependence of amplitude and phase. No hardware
attribution is made here; that is a separate line of work.

Scope note carried from the paper and from C5: released data carry no entropy.
This pass is an audit and pipeline demonstration; no entropy claim is made.

## Pilot disclosure (before this card)

On the local full copy of f01 the following were inspected, and nothing else:

- the SV branch list (16 branches) and the property distributions of
  `SV_ntracks`, `SV_dlenSig`, `SV_dxySig`, `SV_mass`, `SV_pt`, `SV_eta`,
  `SV_chi2`, `SV_ndof`, `SV_pAngle`;
- the trailing-zero precision census of every SV branch.

No azimuth histogram, Fourier coefficient, stratum amplitude or stratum phase
was computed. The pilot fixed the stratum cut points below so that every
stratum is populated.

Pilot result carried into this pass (descriptive): the product truncates every
SV branch, with a per-branch-class depth. Explicit mantissa bits, from the
modal trailing-zero count: 12 for angles (`SV_phi`, `SV_eta`), 10 for
kinematics and displacement (`SV_pt`, `SV_mass`, `SV_dlen`, `SV_dlenSig`,
`SV_dxy`, `SV_dxySig`, `SV_pAngle`, `SV_x`, `SV_y`), 8 for fit quality
(`SV_chi2`, `SV_ndof`), 14 for `SV_z`. 100% of stored values sit at or above
their class depth. This extends the branch-level storage-floor statement of
the C5 note from angular branches to the full SV record.

## Dataset and pass

- Same 67 files and the same event content as C5; new extraction pass
  (`b5_extract.py`) reading the `SV_*` branches and the jet branches.
- Per secondary vertex: `phi, eta, pt, mass, ntracks, dlenSig, dxySig, chi2,
  ndof` (float32 except `ntracks` uint8); rows with a non-finite `SV_phi` are
  dropped from all arrays together.
- Per event: the leading jet (frozen rule: `|eta| < 2.5`, `pt > 20 GeV`, first
  maximum) with `phi` and `eta`, used as the same-event azimuth reference in
  each eta band.
- Output: one `.npz` and one manifest per file under `b5G/`; the manifest
  records counters, the npz sha256, the code sha256 and the source URI.

## Strata (fixed here)

| group | strata |
|---|---|
| S0 control | all stored secondary vertices, no selection |
| E (eta) | E1 `abs(eta) < 0.9`; E2 `0.9 <= abs(eta) < 1.5`; E3 `1.5 <= abs(eta) < 2.5` |
| T (multiplicity) | T2 `ntracks = 2`; T3 `ntracks = 3`; T4 `ntracks >= 4` |
| D (displacement) | D1 `dlenSig < 4`; D2 `4 <= dlenSig < 10`; D3 `dlenSig >= 10` |
| M (mass) | M1 `mass < 0.4`; M2 `0.4 <= mass < 1.0`; M3 `mass >= 1.0` GeV |
| P (pt) | P1 `pt < 2`; P2 `2 <= pt < 5`; P3 `pt >= 5` GeV |
| Q (fit quality) | Q1 `0 < chi2/ndof < 2`; Q2 `2 <= chi2/ndof < 5`; Q3 `chi2/ndof >= 5`; QX `chi2 <= 0` or `ndof <= 0` (counted, excluded) |
| J (reference) | leading jet in the same eta band as E1, E2, E3 |

## Statistics (fixed)

- Histogram at b=12 (4096 bins over [-pi, pi), the phase-0 encoding).
- Complex coefficient `c_k = rfft(counts)[k]/n`; amplitude `A_k = abs(c_k)`;
  significance `z = sqrt(n) * A_k`; phase `arg(c_k)`. Same convention as
  `c5_analyze.py`.
- Local continuum at k: median of `A_j` over the eight neighbours
  `k-4..k-1, k+1..k+4`; excess `E_k = A_k - C_k`.
- b=8 (256 bins) repeated as a robustness check for every stratum.
- Jet contrast in an eta band: `A18(SV, band) - A18(jet, band)`.

## Predictions (fixed before the run)

| ID | quantity | prediction | basis |
|---|---|---|---|
| P0 | S0 pooled: n, A7, A18 at b=12 | n = 4,468,841; A7 = 0.00635; A18 = 0.01623, each within 1e-4 | exact reproduction of the C5 SV arm from the same stored values |
| P1 | phase coherence at k=18 across the 67 files | circular resultant R18 >= 0.95 | the pooled z (34.3) equals sqrt(67) times the per-file median z (4.32), which requires coherent phases |
| P1b | same at k=7 (control) | R7 >= 0.95 | the storage-comb phase is fixed by the float lattice |
| P2 | harmonic ladder in S0: A36/A18 and E36/A18 | A36/A18 <= 0.25 | a 1.6% modulation is more consistent with a smooth 18-fold acceptance warp than with 18 sharp sector boundaries; a sector lattice would give A36 of order A18/2 |
| P3 | eta dependence: A18(E3)/A18(E1) | outside [0.8, 1.25] | subdetector-specific geometry differs between barrel and endcap; a global phi segmentation would be eta-uniform |
| P4 | phase difference `abs(arg c18(E3) - arg c18(E1))` | < 30 degrees | a fixed lab-frame segmentation has eta-independent boundaries |
| P5 | multiplicity dilution: A18(T3+T4)/A18(T2) | < 0.8 | averaging over more tracks dilutes a track-level acceptance modulation; no dilution points to a collection-level (efficiency) modulation |
| P6 | displacement: A18(D3)/A18(D1) | in [0.6, 1.4] | a reconstruction-acceptance effect is shared by genuine displaced vertices; outside the band the structure would be specific to low-significance vertices |
| P7 | mass, pt, chi2ndof strata; eta-phi map | no band, descriptive | no basis for a directional prediction |

## Decision rules

1. Pass = inside the stated band; miss = outside. A miss is reported with its
   diagnosis and is not re-banded after the fact (same practice as E1).
2. A P0 miss, or a per-file SV count that differs from the C5 arm, is a
   pipeline fault: the batch is invalid until the extractor is fixed and the
   full pass is re-run.
3. Any stratum with pooled n < 1e5 reports A18 and z only; its band prediction
   is void and is marked void, not pass or miss. Gate G4 is the authority on
   which strata can carry a verdict.
4. A k=18 amplitude above 3 sigma is a "structure present in this stratum"
   statement. No detector attribution follows from it in this pass.
5. No entropy certification is made in this pass.

## Gates

- **G1 integrity:** 67/67 manifests and npz files; npz sha256 verified against
  the manifests; per-file SV counts equal to the C5 arm (`c5G/`).
- **G2 control:** P0 holds.
- **G3 determinism:** re-running the analyzer reproduces the aggregate JSON
  bit for bit (the JSON carries no timestamp).
- **G4 liveness:** every stratum with a band prediction has pooled n >= 1e5;
  otherwise the prediction is void by rule 3.

## Planned outputs

- `b5G/` per-file arrays and manifests.
- `b5-aggregate.json` with per-stratum counts, b=12 and b=8 histograms,
  amplitudes and phases at k = 7, 12, 17, 18, 19, 24, 33..39 and 54, the
  local continuum and excess, per-file phases for the coherence test, and the
  eta-phi occupancy map.
- `diagnostics/b5-result-<date>.md` with the pass/miss ledger against this
  card.

## Amendments

(none before the run)
