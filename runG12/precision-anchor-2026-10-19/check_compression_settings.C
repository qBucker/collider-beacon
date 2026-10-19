void check_compression_settings(const char* path = "") {
  TFile f(path);
  printf("file settings=%d\n", f.GetCompressionSettings());
  TTree *t = (TTree*)f.Get("Events");
  const char* names[] = {"Jet_phi","Jet_pt","Jet_eta","Jet_mass","MET_pt","MET_phi"};
  for (auto n : names) {
    TBranch *b = t->GetBranch(n);
    if (!b) { printf("%s: missing\n", n); continue; }
    printf("%s: branch settings=%d\n", n, b->GetCompressionSettings());
  }
}
