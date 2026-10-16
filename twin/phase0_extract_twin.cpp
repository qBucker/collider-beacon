// phase0_extract_twin.cpp — C++/ROOT twin of phase0_extract.py (extractor P v1, R3 semantics)
// Goal: BIT-IDENTICAL <out>.bits.bin vs the Python extractor for identical parameters
//       (dual-reproduction matrix, "implementation" axis, first cell).
//
// Semantics mirrored line-by-line against phase0_extract.py:
//   L30   branches Jet_phi/Jet_pt/Jet_eta (+Jet_jetId only when --require-jetid): Float32 reads
//   L54   Float32 -> double EXACT widening; EVERYTHING after is double arithmetic
//   L40   mask FIRST: (|eta| < eta_max) & (pt > pt_min); NaN -> comparison false (filtered)
//   L43   mask applied BEFORE argmax (NaN can never reach the argmax)
//   L48   leading = FIRST argmax of pt over masked jets (ak.argmax keeps first occurrence;
//         std-ish max_element semantics: strict '>' update keeps the first maximum)
//   L52   events with no passing jet are dropped (ak.flatten drops None)
//   L62-64 quantization: u=(phi+pi)/(2*pi); clamp to [1e-15, 1-1e-15]; k=int(u*2^b)
//         (same IEEE doubles as Python: math.pi == the C++ literal below; 1e-15 identical)
//   L104-108 MSB-first packing: acc=(acc<<b)|k; emit top bytes of full 8-bit groups;
//         residual sub-byte bits at the END are DISCARDED (no zero-pad flush) — do not flush.
//
// Usage:  ./phase0_extract_twin <file.root> <out_prefix> [--b N] [--pt-min X] [--eta-max Y] [--require-jetid]
// Then:   sha256sum <out_prefix>.bits.bin   -> must equal the Python run's bits_sha256
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <memory>
#include <vector>

#include <TFile.h>
#include <TTreeReader.h>
#include <TTreeReaderArray.h>

int main(int argc, char** argv) {
  if (argc < 3) {
    std::fprintf(stderr,
                 "usage: %s file.root out_prefix [--b N] [--pt-min X] [--eta-max Y] [--require-jetid]\n",
                 argv[0]);
    return 2;
  }
  const char* fname = argv[1];
  const std::string out = argv[2];
  int b = 8;
  double pt_min = 20.0, eta_max = 2.5;
  bool require_jetid = false, is_mc = false;
  for (int i = 3; i < argc; ++i) {
    if (!std::strcmp(argv[i], "--b") && i + 1 < argc) b = std::atoi(argv[++i]);
    else if (!std::strcmp(argv[i], "--pt-min") && i + 1 < argc) pt_min = std::atof(argv[++i]);
    else if (!std::strcmp(argv[i], "--eta-max") && i + 1 < argc) eta_max = std::atof(argv[++i]);
    else if (!std::strcmp(argv[i], "--require-jetid")) require_jetid = true;
    else if (!std::strcmp(argv[i], "--mc")) is_mc = true;   // Delphes tree mode (python --mc path)
  }
  // Same IEEE double as Python math.pi (0x400921FB54442D18)
  const double PI = 3.14159265358979323846;
  const uint64_t nbins = 1ull << b;

  TFile* f = TFile::Open(fname);
  if (!f || f->IsZombie()) { std::fprintf(stderr, "cannot open %s\n", fname); return 1; }
  TTreeReader r(is_mc ? "Delphes" : "Events", f);
  TTreeReaderArray<float> phi(r, is_mc ? "Jet.Phi" : "Jet_phi");
  TTreeReaderArray<float> pt(r, is_mc ? "Jet.PT" : "Jet_pt");
  TTreeReaderArray<float> eta(r, is_mc ? "Jet.Eta" : "Jet_eta");
  std::unique_ptr<TTreeReaderArray<int>> jid;   // optional; NanoAOD Jet_jetId (Int_t); never for MC
  if (require_jetid && !is_mc) jid.reset(new TTreeReaderArray<int>(r, "Jet_jetId"));

  std::vector<unsigned char> bitbuf;
  bitbuf.reserve(1u << 20);
  uint64_t acc = 0;
  int nacc = 0;
  uint64_t n = 0, n_seen = 0;

  while (r.Next()) {
    ++n_seen;
    const auto njet = pt.GetSize();
    double best = 0.0;
    long best_i = -1;
    for (size_t j = 0; j < njet; ++j) {
      const double p = static_cast<double>(pt[j]);    // Float32 -> double, exact
      const double e = static_cast<double>(eta[j]);
      if (!(std::fabs(e) < eta_max)) continue;        // NaN-safe: comparison false
      if (!(p > pt_min)) continue;                    // NaN-safe: NaN filtered here (mask first)
      if (jid) {                                      // v1.1 semantics: bit test on tight bit
        const int jv = (*jid)[j];
        if (!((jv & 2) == 2)) continue;
      }
      if (best_i < 0 || p > best) {                   // strict '>' => FIRST maximum kept
        best = p;
        best_i = static_cast<long>(j);
      }
    }
    if (best_i < 0) continue;                         // no passing jet -> event dropped
    const double phif = static_cast<double>(phi[best_i]);
    if (!std::isfinite(phif)) {                       // undefined input: Python raises on NaN-phi
      std::fprintf(stderr,
                   "twin: non-finite leading phi encountered (undefined input; Python extractor raises) -- aborting\n");
      return 3;
    }
    double u = (phif + PI) / (2.0 * PI);              // same expression order as Python
    if (u < 1e-15) u = 1e-15;                         // == min(max(u, 1e-15), 1-1e-15)
    if (u > 1.0 - 1e-15) u = 1.0 - 1e-15;
    const uint64_t k = static_cast<uint64_t>(u * static_cast<double>(nbins));  // int(u*2^b)
    acc = (acc << b) | k;
    nacc += b;
    while (nacc >= 8) {
      nacc -= 8;
      bitbuf.push_back(static_cast<unsigned char>((acc >> nacc) & 0xFF));
    }
    acc &= (1ull << nacc) - 1ull;                     // keep residual bits only (nacc < 8 here)
    ++n;
  }

  const std::string bits_path = out + ".bits.bin";
  FILE* fh = std::fopen(bits_path.c_str(), "wb");
  if (!fh) { std::fprintf(stderr, "cannot write %s\n", bits_path.c_str()); return 1; }
  // NO tail flush: residual bits at end-of-stream are discarded (matches Python bytearray emit)
  if (!bitbuf.empty()) std::fwrite(bitbuf.data(), 1, bitbuf.size(), fh);
  std::fclose(fh);

  std::printf("twin: events_seen=%llu events_with_bits=%llu bytes=%zu (b=%d, pt_min=%g, eta_max=%g, jetid=%d)\n",
              (unsigned long long)n_seen, (unsigned long long)n, bitbuf.size(), b, pt_min, eta_max,
              require_jetid ? 1 : 0);
  std::printf("bits -> %s\n", bits_path.c_str());
  return 0;
}
