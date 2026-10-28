# Reading MiniAOD event identifiers with CMSSW from CVMFS

Purpose: obtain `(run, luminosityBlock, event)` from CMS Open Data MiniAOD files
without a CMSSW container, when pure-Python tooling cannot decode the EDM
auxiliary objects.

## Why the pure-Python path fails

- `uproot` 5.7.7 fails on the `EventAuxiliary` branch (`edm::EventAuxiliary`
  version 11 contains an `edm::Hash<2>` member) with a `DeserializationError`.
- `pat::MET` is stored as a `std::vector<pat::MET>` object without exposed
  sub-branches; it cannot be read without the CMSSW dictionaries.
- The jet four-vectors are exposed as separate `p4Polar` sub-branches and remain
  readable with `uproot`.

## Environment

Release: `CMSSW_10_6_30` (slc7_amd64_gcc700) from CVMFS, set up as a scram
project (the externals, including ROOT, are assembled by `scram runtime`):

```bash
export SCRAM_ARCH=slc7_amd64_gcc700
source /cvmfs/cms.cern.ch/cmsset_default.sh
cd <workdir> && scramv1 project CMSSW CMSSW_10_6_30
cd CMSSW_10_6_30/src && eval "$(scramv1 runtime -sh)"
```

Two host-compatibility shims are required on a modern Ubuntu host:

- `libtinfo.so.5`: copy `libtinfo.so.5.9` from the slc7 unpacked container
  (`/cvmfs/unpacked.cern.ch/registry.hub.docker.com/cmsopendata/
  cmssw_10_6_30-slc7_amd64_gcc700:latest/lib64/`) into a local directory and
  prepend that directory to `LD_LIBRARY_PATH`.
- freetype/fontconfig mismatch: preload the host freetype,
  `LD_PRELOAD=/lib/x86_64-linux-gnu/libfreetype.so.6`, so that the host
  `libfontconfig` and a matching `libfreetype` are used together.

## Reading pattern

```cpp
TFile *f = TFile::Open(uri);
TTree *t = (TTree*)f->Get("Events");
t->SetBranchStatus("*", 0);
t->SetBranchStatus("EventAuxiliary", 1);
edm::EventAuxiliary *aux = 0;
TBranch *b = t->GetBranch("EventAuxiliary");
b->SetAddress(&aux);
b->GetEntry(i);            // branch-level read
// aux->id().run(), aux->luminosityBlock(), aux->id().event()
```

Two details matter:

- A tree-level `t->GetEntry(i)` throws `InvalidReference` (a `reco::Vertex`
  product cannot be resolved without an `EDProductGetter`) on the second entry;
  the branch-level read with all other branches disabled does not.
- The event identifiers are `UInt_t run`, `UInt_t luminosityBlock`,
  `ULong64_t event` in the NanoAOD convention.

Per-file luminosity-block lists come from the `LuminosityBlocks` tree and the
`LuminosityBlockAuxiliary` branch with the same pattern; that tree is small and
its read is fast once the file is open.

## Cost

- `scramv1 project` and the first ROOT start: a few minutes on a cold CVMFS
  cache; about one minute warm.
- One MiniAOD file open over XRootD plus a full `EventAuxiliary` loop: about
  one to three minutes on a slow link.
- A full-file jet read with `uproot` (four `p4Polar` branches) is independent of
  this recipe and remains the recommended path for the jet content.

## Verification

For `00C7CA02-901E-B142-BAB9-5366EEA099E4.root` (record 30516): 280,744 event
identifiers dumped; first event `(278820, 52, 84930127)`. The `LuminosityBlocks`
tree of the same file lists 472 (run, lumi) pairs across 15 runs.
