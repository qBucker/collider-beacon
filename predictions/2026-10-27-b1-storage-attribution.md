# Pre-registration — B1 storage-layer attribution (per-jet crossmatch)

- Date (UTC): 2026-10-27
- Run / sample: PFNanoAOD `nano_data2016_1-1.root` (record 31316, 153,011
  events) and its parent MiniAOD file(s) from record 30516 (Run2016G
  ZeroBias, UL2016 MiniAODv2-v1)
- Analysis code: `b1_crossmatch.py` (this pass)
- Status: frozen before the MiniAOD jet branches are read; the commit of this
  file is the timestamp

## Purpose

The 2026-10-19 precision anchor established, on samples of each product, that
PFNanoAOD jet branches carry reduced precision (Jet_phi/Jet_eta: at least 11
trailing mantissa zeros; Jet_pt/Jet_mass: at least 13; MET_pt: none), that the
upstream MiniAOD `pat::Jet` components are full float32, that file and branch
compression is lossless (209 = LZMA 9), and that the production configuration
sets no precision option (`runG12/precision-anchor-2026-10-19/`).

That anchor compares marginal distributions. This pass makes the attribution
per jet: every stored PFNano jet is matched to its MiniAOD counterpart in the
same event, and the exact storage rule is identified from the pair.

## Data

- PFNano: local copy of `nano_data2016_1-1.root`.
- MiniAOD: the parent file set of the same events. Identification rule, fixed
  here: scan the `50000` file index of record 30516 in listed order and take
  the file containing the first PFNano event; take the file containing the
  last PFNano event; the parent set is every file between them in the index
  (inclusive). A file is accepted if it contains at least one PFNano event.
- Branches read: MiniAOD `patJets_slimmedJets__PAT.obj.m_state.p4Polar_
  .fCoordinates.f{Pt,Phi,Eta,M}` and `(run, luminosityBlock, event)`;
  PFNano `Jet_{pt,eta,phi,mass}`, `MET_pt`, `(run, luminosityBlock, event)`.

## Matching (fixed)

- **Event:** exact match on `(run, luminosityBlock, event)`. PFNano events not
  found in the parent set are excluded and counted (prediction P1 is 100%).
- **Jet:** index matching inside an event, used only when the per-event jet
  counts agree. Events with unequal counts are excluded and counted; no
  proximity matching is used for the primary result. A nearest-phi cross-check
  (radius 0.01 rad) is reported as a secondary validation only.

## Candidate storage rules (tested against the MiniAOD value)

For each matched jet and branch, the PFNano float32 value is compared with four
candidates computed from the MiniAOD float32 value:

- **R1** mantissa truncation to k explicit bits (mask the low 23-k bits),
  k fixed per branch;
- **R2** mantissa rounding to k explicit bits (round to nearest);
- **R3** fixed-point grid 2^-g, round to nearest;
- **R4** fixed-point grid 2^-g, truncation.

The rule and parameter with the largest exact-reproduction share are selected
per branch. If no rule reaches the gate, the share of each is reported and the
mechanism statement is downgraded (see Falsifiers).

## Predictions (fixed before the read)

| ID | quantity | prediction | basis |
|---|---|---|---|
| P1 | event match rate | 100% of PFNano events found in the parent set | the two datasets have equal total event counts (27,123,616) and the PFNano set is declared a child of the MiniAOD set |
| P2 | per-event jet-count agreement | >= 99.9% of matched events | both use the standard `slimmedJets` collection, copied in order |
| P3 | exact reproduction share, Jet_phi | >= 99.9% under one candidate rule | the production copies the four-vector and reduces precision |
| P3b | same for Jet_eta, Jet_pt, Jet_mass | >= 99.9% each | same |
| P4 | rule shape | angles and kinematics differ: the trailing-zero pattern of Jet_phi varies with octave (min 11, 24% at >= 13), while Jet_pt is concentrated at 13-14 | pilot census on f01 (2026-10-19 capture) |
| P5 | MET_pt control | bit-exact match with the MiniAOD MET_pt for >= 99% of events | MET_pt is full float32 in PFNano |
| P6 | residuals | confined to one quantum of the selected rule | the production performs a rounding or truncation only |

## Falsifiers

- **P3/P3b miss:** the PFNano jets are not value-level derived from the MiniAOD
  jets under any candidate rule. The "rounding at the NanoAOD production
  layer" statement is then downgraded to "reduced precision at that layer,
  mechanism unidentified", and the residual structure is reported.
- **P2 miss with a documented selection:** the production applied a jet
  selection or reordering; the selection is reported and the affected events
  excluded, with the exclusion counted.
- **P5 miss:** MET is not a straight copy; the control is void and is reported
  as such.

## Gates

- **G1** event matching: 100% of PFNano events found (or a documented reason
  for the shortfall).
- **G2** rule gate: the selected rule reproduces >= 99.9% of matched jets on
  each of the four branches.
- **G3** determinism: a re-run of the analysis reproduces the JSON bit for bit
  (no timestamp in the JSON).
- **G4** sample size: >= 10^5 matched jets; otherwise the pass is repeated on
  another file pair.

## Planned outputs

- `b1G/f01-match.json`: per-branch rule selection, reproduction shares,
  residual quantiles, exclusion counts, matched-jet counts.
- `diagnostics/b1-result-<date>.md`: the pass/miss ledger against this card.
- `SHA256SUMS` for the outputs. No per-jet arrays are committed (size rule);
  the script regenerates them from the public files.

## Amendments

(none before the run)

### Amendment 1 — 2026-10-28, before the crossmatch run

The parent-file identification rule in "Data" assumed an index-contiguous
relation between PFNano and MiniAOD files. The f01 file is a re-chunked merge:
153,011 events spanning six runs (278822-279794) and 257 luminosity sections,
i.e. it draws events from many MiniAOD files in a non-chronological order. The
first MiniAOD file tested (50000/00C7CA02...) shares no events with f01 (exact
event-ID intersection, 0 of 153,011).

The parent set is therefore defined as the set of MiniAOD files that contain at
least one f01 event, determined by exact event-ID intersection. The crossmatch
is performed on the files processed in index order until the matched-jet gate
(G4, >= 1e5 matched jets) is met; the event-match rate (P1) is evaluated over
the processed events and reported together with the number of files processed.
The jet matching and the four candidate storage rules are unchanged.
