// g4audit.cc — simplified full-simulation audit detector for Z->mu mu and
// H->gamma gamma.  A 3.8 T solenoid, six silicon tracker layers, and a
// PbWO4 crystal calorimeter.  Primaries are generator-level four-vectors from
// the Delphes samples; the output is a per-hit CSV consumed by reconstruct.py.
//
// Build: source ../scripts/g4env.sh; cmake .. $G4CMAKE_FLAGS; make -j
// Run:   ./g4audit events/z_events.txt out/z_hits.csv 100

#include "G4Box.hh"
#include "G4ChordFinder.hh"
#include "G4Event.hh"
#include "G4FieldManager.hh"
#include "G4HCofThisEvent.hh"
#include "G4ios.hh"
#include "G4LogicalVolume.hh"
#include "G4Material.hh"
#include "G4NistManager.hh"
#include "G4ParticleDefinition.hh"
#include "G4PhysListFactory.hh"
#include "G4PrimaryParticle.hh"
#include "G4PrimaryVertex.hh"
#include "G4PVPlacement.hh"
#include "G4RunManager.hh"
#include "G4SDManager.hh"
#include "G4Step.hh"
#include "G4SystemOfUnits.hh"
#include "G4THitsCollection.hh"
#include "G4TouchableHistory.hh"
#include "G4Track.hh"
#include "G4TransportationManager.hh"
#include "G4Tubs.hh"
#include "G4UImanager.hh"
#include "G4UniformMagField.hh"
#include "G4UserEventAction.hh"
#include "G4VHit.hh"
#include "G4VModularPhysicsList.hh"
#include "G4VPhysicalVolume.hh"
#include "G4VUserActionInitialization.hh"
#include "G4VUserDetectorConstruction.hh"
#include "G4VUserPrimaryGeneratorAction.hh"
#include "G4VSensitiveDetector.hh"

#include <CLHEP/Units/SystemOfUnits.h>

#include <algorithm>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <map>
#include <sstream>
#include <string>
#include <utility>
#include <vector>

std::ofstream gOut;

// ---------------------------------------------------------------- hit class
class AuditHit : public G4VHit {
public:
  G4int det = 0;      // 0 tracker, 1 ecal
  G4int id = 0;       // layer / crystal copy number
  G4double x = 0, y = 0, z = 0;
  G4double edep = 0;
  G4int track = 0;
  G4int pid = 0;
};
using AuditHitsCollection = G4THitsCollection<AuditHit>;

// ---------------------------------------------------------------- sensitive
class AuditSD : public G4VSensitiveDetector {
public:
  AuditSD(const G4String& name, G4int det) : G4VSensitiveDetector(name), fDet(det) {
    collectionName.insert(name + "Hits");
  }
  void Initialize(G4HCofThisEvent* hce) override {
    fHits = new AuditHitsCollection(SensitiveDetectorName, collectionName[0]);
    G4int id = G4SDManager::GetSDMpointer()->GetCollectionID(fHits);
    hce->AddHitsCollection(id, fHits);
  }
  G4bool ProcessHits(G4Step* step, G4TouchableHistory*) override {
    G4double edep = step->GetTotalEnergyDeposit();
    if (edep <= 0) return false;
    AuditHit* h = new AuditHit();
    h->det = fDet;
    h->id = step->GetPreStepPoint()->GetTouchable()->GetCopyNumber();
    G4ThreeVector p = step->GetPreStepPoint()->GetPosition();
    h->x = p.x(); h->y = p.y(); h->z = p.z();
    h->edep = edep;
    h->track = step->GetTrack()->GetTrackID();
    h->pid = step->GetTrack()->GetDefinition()->GetPDGEncoding();
    fHits->insert(h);
    return true;
  }
private:
  G4int fDet;
  AuditHitsCollection* fHits = nullptr;
};

// ---------------------------------------------------------------- geometry
class DetectorConstruction : public G4VUserDetectorConstruction {
public:
  G4VPhysicalVolume* Construct() override {
    G4NistManager* nist = G4NistManager::Instance();
    G4Material* air = nist->FindOrBuildMaterial("G4_AIR");
    G4Material* si = nist->FindOrBuildMaterial("G4_Si");
    G4Material* pbwo4 = new G4Material("PbWO4", 8.28 * g / cm3, 3);
    pbwo4->AddElement(nist->FindOrBuildElement("Pb"), 1);
    pbwo4->AddElement(nist->FindOrBuildElement("W"), 1);
    pbwo4->AddElement(nist->FindOrBuildElement("O"), 4);

    auto* world = new G4Box("world", 8 * m, 8 * m, 8 * m);
    auto* worldLV = new G4LogicalVolume(world, air, "world");
    auto* worldPV = new G4PVPlacement(nullptr, {}, worldLV, "world", nullptr, false, 0);

    // six silicon layers
    G4double radii[6] = {20, 40, 60, 80, 100, 120};
    for (int i = 0; i < 6; ++i) {
      auto* tube = new G4Tubs("tracker", (radii[i] - 0.15) * cm, (radii[i] + 0.15) * cm,
                              300 * cm, 0, 2 * CLHEP::pi);
      auto* lv = new G4LogicalVolume(tube, si, "tracker");
      fTrackerLV.push_back(lv);
      new G4PVPlacement(nullptr, {}, lv, "tracker", worldLV, false, i);
    }

    // PbWO4 calorimeter: 72 phi x 60 z crystals, r 130..155 cm
    for (int ip = 0; ip < 72; ++ip) {
      for (int iz = 0; iz < 60; ++iz) {
        G4double zc = (-300 + 10 * iz + 5) * cm;
        auto* xtal = new G4Tubs("ecal", 130 * cm, 155 * cm, 5 * cm,
                                ip * 5 * deg, 5 * deg);
        auto* lv = new G4LogicalVolume(xtal, pbwo4, "ecal");
        fEcalLV.push_back(lv);
        new G4PVPlacement(nullptr, {0, 0, zc}, lv, "ecal", worldLV, false, ip * 60 + iz);
      }
    }
    return worldPV;
  }

  void ConstructSDandField() override {
    G4SDManager* sdm = G4SDManager::GetSDMpointer();
    auto* trk = new AuditSD("TrackerSD", 0);
    auto* ecal = new AuditSD("EcalSD", 1);
    sdm->AddNewDetector(trk);
    sdm->AddNewDetector(ecal);
    for (auto* lv : fTrackerLV) lv->SetSensitiveDetector(trk);
    for (auto* lv : fEcalLV) lv->SetSensitiveDetector(ecal);

    auto* field = new G4UniformMagField(G4ThreeVector(0, 0, 3.8 * tesla));
    G4FieldManager* fm = G4TransportationManager::GetTransportationManager()->GetFieldManager();
    fm->SetDetectorField(field);
    fm->CreateChordFinder(field);
  }
private:
  std::vector<G4LogicalVolume*> fTrackerLV;
  std::vector<G4LogicalVolume*> fEcalLV;
};

// ---------------------------------------------------------------- generator
class PrimaryGeneratorAction : public G4VUserPrimaryGeneratorAction {
public:
  explicit PrimaryGeneratorAction(const G4String& file) : fFile(file) { Read(); }
  void GeneratePrimaries(G4Event* ev) override {
    if (fIndex >= fEvents.size()) return;
    G4PrimaryVertex* v = new G4PrimaryVertex(G4ThreeVector(0, 0, 0), 0);
    for (const auto& p : fEvents[fIndex]) {
      // Use the PDG mass and the momentum; the generator energy differs from
      // sqrt(p^2 + m^2) by less than 0.01% for muons and is exact for photons.
      v->SetPrimary(new G4PrimaryParticle(p.pid, p.px * GeV, p.py * GeV, p.pz * GeV));
    }
    ev->AddPrimaryVertex(v);
    ++fIndex;
  }
  size_t N() const { return fEvents.size(); }
private:
  struct P { G4int pid; G4double e, px, py, pz; };
  void Read() {
    std::ifstream in(fFile);
    int evid, pid;
    double e, px, py, pz;
    while (in >> evid >> pid >> e >> px >> py >> pz) {
      if (evid >= (int)fEvents.size()) fEvents.resize(evid + 1);
      fEvents[evid].push_back({pid, e, px, py, pz});
    }
  }
  G4String fFile;
  std::vector<std::vector<P>> fEvents;
  size_t fIndex = 0;
};

// ---------------------------------------------------------------- actions
class EventAction : public G4UserEventAction {
public:
  void EndOfEventAction(const G4Event* ev) override {
    G4HCofThisEvent* hce = ev->GetHCofThisEvent();
    if (!hce) return;
    G4int eid = ev->GetEventID();

    struct EcalAgg { G4double e = 0, x = 0, y = 0, z = 0; };
    std::map<G4int, EcalAgg> ecal;
    std::map<std::pair<G4int, G4int>, AuditHit> trk;

    for (int i = 0; i < hce->GetNumberOfCollections(); ++i) {
      auto* hc = dynamic_cast<AuditHitsCollection*>(hce->GetHC(i));
      if (!hc) continue;
      for (size_t j = 0; j < hc->entries(); ++j) {
        const AuditHit* h = (*hc)[j];
        if (h->det == 1) {
          EcalAgg& a = ecal[h->id];
          a.e += h->edep;
          a.x += h->edep * h->x;
          a.y += h->edep * h->y;
          a.z += h->edep * h->z;
        } else {
          auto key = std::make_pair(h->track, h->id);
          auto it = trk.find(key);
          if (it == trk.end() || h->edep > it->second.edep) trk[key] = *h;
        }
      }
    }

    for (auto& kv : ecal) {
      const EcalAgg& a = kv.second;
      if (a.e <= 0) continue;
      gOut << eid << ",1," << kv.first << ','
           << a.x / a.e / cm << ',' << a.y / a.e / cm << ',' << a.z / a.e / cm << ','
           << a.e / GeV << ",0,0\n";
    }
    for (auto& kv : trk) {
      const AuditHit& h = kv.second;
      gOut << eid << ",0," << h.id << ','
           << h.x / cm << ',' << h.y / cm << ',' << h.z / cm << ','
           << h.edep / GeV << ',' << h.track << ',' << h.pid << '\n';
    }
  }
};

class ActionInitialization : public G4VUserActionInitialization {
public:
  explicit ActionInitialization(const G4String& file) : fFile(file) {}
  void Build() const override {
    SetUserAction(new PrimaryGeneratorAction(fFile));
    SetUserAction(new EventAction());
  }
private:
  G4String fFile;
};

// ---------------------------------------------------------------- main
int main(int argc, char** argv) {
  if (argc < 4) {
    std::cerr << "usage: " << argv[0] << " events.txt out.csv n_events\n";
    return 1;
  }
  G4String events = argv[1];
  G4String out = argv[2];
  int n = std::atoi(argv[3]);

  gOut.open(out);
  gOut << "event,det,id,x,y,z,edep,track,pid\n";

  auto* run = new G4RunManager;
  run->SetUserInitialization(new DetectorConstruction());

  G4PhysListFactory factory;
  G4VModularPhysicsList* phys = factory.GetReferencePhysList("FTFP_BERT_EMZ");
  if (!phys) phys = factory.GetReferencePhysList("FTFP_BERT");
  run->SetUserInitialization(phys);
  run->SetUserInitialization(new ActionInitialization(events));

  run->Initialize();
  G4UImanager* ui = G4UImanager::GetUIpointer();
  std::ostringstream cmd;
  cmd << "/run/beamOn " << n;
  ui->ApplyCommand(cmd.str());

  gOut.close();
  delete run;
  return 0;
}
