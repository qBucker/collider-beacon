# ATLAS leg — cross-detector check of effect 1

Purpose: repeat the Phase 0 leading-jet azimuth extraction on ATLAS Open Data and check
whether the localized acceptance deficit found in CMS (bins 227-234, phi ~ +139..+150 deg,
-10.5%) is present in a second detector. Outcome decides whether the effect is
CMS-specific (detector geometry / trigger acceptance) or common to both experiments.

## Sample verification (2026-10-17)

| Item | Result |
|---|---|
| Record | CERN Open Data **93933** (parent 93910): *ATLAS ROOT ntuple format Run 2 2015+2016 proton-proton collision data beta release, no skim* |
| DOI | 10.7483/OPENDATA.ATLAS.VV3I.0WJE |
| License | **CC0-1.0** (portal API metadata) |
| Release | `2025e-13tev-beta` (accessed via `atlasopenmagic` 1.10.1) |
| Files | 16 ROOT files, **5,770,706,892 events**, 1.35 TB total |
| Tree / branches | `analysis`; `jet_n` (int32), `jet_pt`/`jet_eta`/`jet_phi` (RVec<float>) |
| Units / range | pT in **GeV** (observed 20.0-1073 GeV), phi in (-pi, pi], abs(eta) < 2.5 (preselected by the ntuple) |
| Access | `https://opendata.cern.ch/eos/opendata/atlas/rucio/user/egramsta/<file>.noskim.root`, fallback `root://eospublic.cern.ch:1094//eos/...` |

The branch verification was performed by opening `data15_periodD.noskim.root` remotely
(45,094,640 events) and listing the tree: 117 branches, jet branches as above.

## Method

`atlas_extract.py` mirrors the frozen extractor `phase0_extract.py` (R3 semantics):
leading jet by max pT among jets with `|eta| < 2.5` and `pT > 20 GeV` (first maximum kept);
phi -> 256 uniform bins; MSB-first packing; Clopper-Pearson min-entropy bound with
Bonferroni correction. Only the branch names and the file reader differ. The frozen
extractor and its evidence remain unchanged.

## Access engineering (2026-10-17)

Measured on the current CERN link:

- Portal proxy (`https://opendata.cern.ch/eos/...`): 20-34 kB/s per connection.
- Direct EOS (`https://eospublic.cern.ch//eos/...`): 307 redirect to a storage server
  (`st-*.cern.ch:8443`) with a capability URL; per-connection speed is the same order.
- 16 parallel range requests aggregate to ~280-330 kB/s.
- The per-file TTree metadata object (`analysis`) is **14,193,299 B compressed**
  (35,251,401 B uncompressed) for `data15_periodE`; a single-connection read of this
  object dominates the open time.
- `parallel_http_source.py` implements an uproot Source that resolves the EOS redirect
  once and fetches every requested range with N parallel connections. Measured with
  N = 16: open 7.0 s, TTree metadata 62.5 s, first 1,000 events 64.9 s.

TLS: the EOS endpoint uses the CERN Grid Certification Authority; `cern-ca-bundle.pem`
was extracted from the server chain on 2026-10-17 for this access path. Replace with the
official CERN CA distribution if this workflow is published.

## Run (2026-10-17)

`smoke2`: first 50,000 entries from each of the 16 files; **16/16 files, 597,965 events**.
Command:

```bash
python3 atlas_extract.py --files urls-noskim.https.txt --out smoke2 \
    --per-file-events 50000 --concurrency 4 --http-workers 8 --file-timeout 600
```

Outputs: `smoke2.manifest.json`, `smoke2.bits.bin` (checksums in `SHA256SUMS`).

**Result** (details in `RESULTS-2026-10-17.md`): effect-1 band (bins 227-234,
phi = +139..+150 deg) local ratio = **1.0024 +/- 0.0072**, stable under sideband and
Fourier baselines (0.999-1.007). The CMS value (0.895, -10.5%) is excluded at
**14.1 sigma** (pooled, conservative estimator comparison; same-estimator checks give
7.2-16.9 sigma). The ATLAS sample fails the global uniformity gates (chi-squared p < 1e-300,
KS p = 4e-10) because it is trigger-selected; the localized-band test is insensitive to
the broad acceptance modulation.

## Caveats

- The ATLAS "no skim" release is not a minimum-bias sample: in the first 2,000 events of
  `data15_periodD`, 72% have at least one jet with pT > 20 GeV, consistent with
  trigger-selected events. The comparison relies on azimuthal symmetry of the selection;
  this assumption is recorded explicitly.
- Current read strategy uses the first N entries of each file (not a random subsample);
  per-file entry counts are recorded in the manifest. A random or run-stratified sample
  can replace it for the final measurement.
- ATLAS small-R jets are anti-kT R=0.4 (vs CMS AK4 R=0.4 in the reference analysis);
  the leading-jet phi definition is identical in form.
