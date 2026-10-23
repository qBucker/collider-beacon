# Geant4 audit demonstration — Z and Higgs mass peaks

Full Geant4 simulation of a simplified audit detector, fed with generator-level
Z→μμ and H→γγ four-vectors from the Delphes samples. The reconstructed mass
peaks are the audit observable: a uniform calibration drift moves them by the
drift fraction, while the peak positions are stable in the nominal sample.

## Detector

- 3.8 T solenoidal field along z.
- Six silicon tracker layers at r = 20, 40, 60, 80, 100, 120 cm, 0.3 cm thick,
  |z| < 3 m.
- PbWO4 electromagnetic calorimeter at r = 130–155 cm (25 cm, ≈28 X0),
  72 φ × 60 z crystals, |z| < 3 m.
- No hadronic calorimeter or muon system; the detector is an audit demonstrator,
  not a realistic experiment.

## Inputs

`make_events.py` selects the two highest-pT final-state particles of the
requested type from the Delphes `Particle` tree and writes one line per primary:

```
event_id pid E px py pz
```

The 2,000-event files in `events/` were produced from the Delphes samples in
the development environment (`delphes_output.root` for Z→μμ,
`delphes_HToGG.root` for H→γγ). The Delphes ROOT files are not included here;
the selection is documented in `make_events.py`.

## Reconstruction

- **Muons:** for each track, take the hit in each silicon layer, fit a circle
  through the origin and the hits, convert the radius to pT = 0.3 B R, take φ
  from the tangent at the origin, and η from the z-versus-r slope.
- **Photons:** sum the hit energy per crystal, cluster adjacent crystals, take
  the two highest-energy clusters, and form the diphoton mass from the cluster
  energies and directions. An optional split of merged clusters by crystal
  seeds was tested and not used: it mis-assigned clusters and degraded the
  mass closure, so the default keeps one cluster per photon candidate.

## Results

| channel | reconstructed | in window | peak [GeV] | sigma68 [GeV] | 5% shift [GeV] | significance |
|---|---|---|---|---|---|---|
| Z→μμ | 1742/2000 | 1253 | 90.82 | 3.31 | 4.53 | 38.6σ |
| H→γγ | 801/2000 | 729 | 124.24 | 0.27 | 6.21 | 492σ |

The H 2,000-event production was run in four 500-event chunks (a local
15-minute job limit); `run_audit.sh` runs 2,000 in one go. The 68% width is
half the 16–84% interval (one standard deviation for a Gaussian). The
38.6σ/492σ are shifts in units of the median statistical uncertainty: a
controlled simulated shift, not an experimental discovery. Mass closure against
the generator-level four-vectors: Z median difference 0.04 GeV, RMS 0.61 GeV
(1742 events); H median −0.77 GeV, 90% within 1.44 GeV (801 events, no split;
a small mis-clustered tail remains). The generator-level Z events in the window
have median 90.78 GeV (FSR, off-shell, acceptance), so the 0.37 GeV difference
from the nominal Z pole is a sample property, not a reconstruction bias; the H
reconstruction carries a −0.61% bias from calorimeter energy leakage and
clustering. The H width of 0.27 GeV (0.22%) is consistent with an ECAL constant
term of ≈0.4% without noise or pileup; the audit uses relative peak positions.

## Audit interpretation

The tampered sample applies a 5% calibration drift: the tracker field is taken
as 3.99 T instead of 3.8 T, and the ECAL energy scale is 1.05. The
reconstruction is rerun on the same Geant4 hits. The peak shift is compared with
the median uncertainty `1.253 sigma68 / sqrt(N)`.

## Build and run

Geant4 11.4 was used from CVMFS
(`/cvmfs/geant4.cern.ch/geant4/11.4/x86_64-el9-gcc13-optdeb`) with g++ 13:

```bash
source /path/to/geant4/11.4/bin/geant4.sh
mkdir -p build && cd build
cmake .. -DGeant4_DIR=/path/to/geant4/11.4/lib64/cmake/Geant4
make -j4
cd ..
bash run_audit.sh
```

The H→γγ sample is slower (~2 minutes per 100 events) because of the crystal
calorimeter; the Z sample is ~25 s for 2,000 events.

## Caveats

- The detector is simplified; the Z mass width is dominated by the six-layer
  circle fit (σ68 ≈ 3.3 GeV), and the H reconstruction efficiency is limited by
  cluster merging at small photon separation.
- The absolute peak positions carry a −0.04% closure bias (Z) and a −0.61%
  reconstruction bias (H, energy leakage and clustering); the audit uses
  relative positions.
- The 5% drift is an analysis-level calibration model, not an injection of
  tampered detector data. A production audit would define the tamper model
  before data taking.
