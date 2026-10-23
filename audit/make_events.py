#!/usr/bin/env python3
"""Write Geant4 primary events from a Delphes sample.

Selects the two highest-pT final-state particles of the requested PID
(|PID| = 13 for Z->mu mu, PID = 22 for H->gamma gamma) and writes one line per
primary:

    event_id pid E px py pz

The four-vectors are the generator-level Delphes Particle values (GeV), with
the interaction point at the origin.

Usage:
  python3 make_events.py --root ../out/delphes_output.root --pid 13 \
      --n 2000 --out events/z_events.txt
  python3 make_events.py --root ../out/delphes_HToGG.root --pid 22 \
      --n 2000 --out events/h_events.txt
"""

import argparse

import numpy as np
import uproot


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--pid", type=int, required=True,
                    help="13 selects |PID|=13; 22 selects PID=22")
    ap.add_argument("--n", type=int, default=2000)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    t = uproot.open(args.root)["Delphes"]
    ids = t["Particle/Particle.PID"].array(library="np")
    st = t["Particle/Particle.Status"].array(library="np")
    pt = t["Particle/Particle.PT"].array(library="np")
    px = t["Particle/Particle.Px"].array(library="np")
    py = t["Particle/Particle.Py"].array(library="np")
    pz = t["Particle/Particle.Pz"].array(library="np")
    e = t["Particle/Particle.E"].array(library="np")

    lines = []
    written = 0
    for i in range(len(ids)):
        sel = (np.abs(ids[i]) == args.pid) & (st[i] == 1)
        if sel.sum() < 2:
            continue
        cand = np.where(sel)[0]
        cand = cand[np.argsort(pt[i][cand])[::-1][:2]]
        for j in cand:
            lines.append("%d %d %.10g %.10g %.10g %.10g" %
                         (written, int(ids[i][j]), e[i][j], px[i][j],
                          py[i][j], pz[i][j]))
        written += 1
        if written >= args.n:
            break

    with open(args.out, "w") as fh:
        fh.write("\n".join(lines) + "\n")
    print("wrote %d events (%d primaries) to %s" % (written, len(lines), args.out))


if __name__ == "__main__":
    main()
