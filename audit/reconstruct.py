#!/usr/bin/env python3
"""Reconstruct Z->mu mu and H->gamma gamma masses from the Geant4 hit CSV.

Tracker: for each muon track, take the hit in each silicon layer, fit a circle
through the origin and the hits, and convert the radius to pT in a 3.8 T field.
The azimuth is the tangent at the origin; eta is the slope of z versus r.

Calorimeter: sum the hit energy per crystal, cluster adjacent crystals, take
the two highest-energy clusters, and form the diphoton mass from the cluster
energies and the directions from the origin.

Usage:
  python3 reconstruct.py --hits ../out/z_hits.csv --channel z --out ../out/z_reco.csv
  python3 reconstruct.py --hits ../out/h_hits.csv --channel h --out ../out/h_reco.csv
"""

import argparse
import csv
import math
from collections import defaultdict

import numpy as np

B_FIELD = 3.8  # tesla
M_MU = 0.105658  # GeV


def circle_fit(points):
    """Fit x^2+y^2 + D x + E y = 0 through the origin and the points."""
    pts = [(0.0, 0.0)] + list(points)
    A = np.array([[x, y] for x, y in pts], dtype=float)
    b = -np.array([x * x + y * y for x, y in pts], dtype=float)
    D, E = np.linalg.lstsq(A, b, rcond=None)[0]
    a, c = -D / 2.0, -E / 2.0
    R = math.hypot(a, c)
    return a, c, R


def muon_from_hits(hits, bfield=B_FIELD):
    """hits: list of (layer, x, y, z, edep). Returns (pt, eta, phi) or None."""
    by_layer = {}
    for layer, x, y, z, edep in hits:
        if layer not in by_layer or edep > by_layer[layer][4]:
            by_layer[layer] = (layer, x, y, z, edep)
    if len(by_layer) < 3:
        return None
    pts = sorted(by_layer.values())
    a, b, R = circle_fit([(p[1], p[2]) for p in pts])
    if R <= 0:
        return None
    pt = 0.3 * bfield * (R / 100.0)  # GeV
    # tangent at the origin; choose the direction toward the first hit
    x1, y1 = pts[0][1], pts[0][2]
    t1 = (-b, a)
    t2 = (b, -a)
    t = t1 if (t1[0] * x1 + t1[1] * y1) > (t2[0] * x1 + t2[1] * y1) else t2
    phi = math.atan2(t[1], t[0])
    # z slope versus transverse radius
    s = sum(p[3] * math.hypot(p[1], p[2]) for p in pts)
    q = sum(p[1] ** 2 + p[2] ** 2 for p in pts)
    eta = math.asinh(s / q) if q > 0 else 0.0
    return pt, eta, phi


def invariant(ps):
    e = sum(p[0] for p in ps)
    px = sum(p[1] for p in ps)
    py = sum(p[2] for p in ps)
    pz = sum(p[3] for p in ps)
    m2 = e * e - px * px - py * py - pz * pz
    return math.sqrt(m2) if m2 > 0 else float("nan")


def reconstruct_z(rows, bfield=B_FIELD):
    by_event = defaultdict(list)
    for r in rows:
        if r["det"] != "0":
            continue
        if abs(int(r["pid"])) != 13:
            continue
        by_event[r["event"]].append((int(r["id"]), float(r["x"]), float(r["y"]),
                                     float(r["z"]), float(r["edep"]), int(r["track"])))
    out = []
    for ev, hits in by_event.items():
        tracks = defaultdict(list)
        for layer, x, y, z, edep, track in hits:
            tracks[track].append((layer, x, y, z, edep))
        mus = []
        for track, hs in tracks.items():
            r = muon_from_hits(hs, bfield)
            if r is None:
                continue
            pt, eta, phi = r
            pz = pt * math.sinh(eta)
            e = math.sqrt(pt * pt + pz * pz + M_MU * M_MU)
            mus.append((e, pt * math.cos(phi), pt * math.sin(phi), pz))
        if len(mus) < 2:
            continue
        mus.sort(key=lambda p: -math.hypot(p[1], p[2]))
        m = invariant(mus[:2])
        out.append((int(ev), m, math.hypot(mus[0][1], mus[0][2]),
                    math.hypot(mus[1][1], mus[1][2])))
    return out


def make_cluster(members, crystals):
    e = sum(crystals[c][0] for c in members)
    if e <= 0:
        return None
    x = sum(crystals[c][0] * crystals[c][1] for c in members) / e
    y = sum(crystals[c][0] * crystals[c][2] for c in members) / e
    z = sum(crystals[c][0] * crystals[c][3] for c in members) / e
    return (e, x, y, z, members)


def split_cluster(cluster, crystals):
    """Split one cluster into two by assigning crystals to the two seeds."""
    _, _, _, _, members = cluster
    if len(members) < 2:
        return None
    seeds = sorted(members, key=lambda c: -crystals[c][0])[:2]
    groups = {0: [], 1: []}
    for cid in members:
        ip, iz = divmod(cid, 60)
        d = []
        for s in seeds:
            sp, sz = divmod(s, 60)
            dp = min(abs(ip - sp), 72 - abs(ip - sp))
            d.append(dp * dp + (iz - sz) ** 2)
        groups[0 if d[0] <= d[1] else 1].append(cid)
    parts = [make_cluster(g, crystals) for g in groups.values()]
    parts = [p for p in parts if p is not None and p[0] > 2.0]
    return parts if len(parts) == 2 else None


def reconstruct_h(rows, ecal_scale=1.0, split=False):
    by_event = defaultdict(dict)
    for r in rows:
        if r["det"] != "1":
            continue
        e = float(r["edep"]) * ecal_scale
        if e <= 0.001:
            continue
        by_event[r["event"]][int(r["id"])] = (
            e, float(r["x"]), float(r["y"]), float(r["z"]))
    out = []
    for ev, crystals in by_event.items():
        seen = set()
        clusters = []
        for cid in sorted(crystals, key=lambda c: -crystals[c][0]):
            if cid in seen:
                continue
            # BFS over neighbouring crystals
            stack = [cid]
            seen.add(cid)
            members = []
            while stack:
                c = stack.pop()
                members.append(c)
                ip, iz = divmod(c, 60)
                for dp in (-1, 0, 1):
                    for dz in (-1, 0, 1):
                        if dp == 0 and dz == 0:
                            continue
                        np_ = (ip + dp) % 72
                        nz = iz + dz
                        if nz < 0 or nz >= 60:
                            continue
                        nid = np_ * 60 + nz
                        if nid in crystals and nid not in seen:
                            seen.add(nid)
                            stack.append(nid)
            c = make_cluster(members, crystals)
            if c is not None and c[0] >= 1.0:
                clusters.append(c)
        if split and len(clusters) < 2 and clusters:
            big = max(clusters, key=lambda c: c[0])
            parts = split_cluster(big, crystals)
            if parts:
                clusters = [c for c in clusters if c is not big] + parts
        if len(clusters) < 2:
            continue
        clusters.sort(key=lambda c: -c[0])
        c1, c2 = clusters[0], clusters[1]
        def four(c):
            e, x, y, z, _ = c
            r = math.sqrt(x * x + y * y + z * z)
            return (e, e * x / r, e * y / r, e * z / r)
        m = invariant([four(c1), four(c2)])
        out.append((int(ev), m, c1[0], c2[0]))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hits", required=True)
    ap.add_argument("--channel", choices=["z", "h"], required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--bfield", type=float, default=B_FIELD)
    ap.add_argument("--ecal-scale", type=float, default=1.0)
    ap.add_argument("--split", action="store_true")
    args = ap.parse_args()

    rows = list(csv.DictReader(open(args.hits)))
    if args.channel == "z":
        rec = reconstruct_z(rows, args.bfield)
    else:
        rec = reconstruct_h(rows, args.ecal_scale, args.split)
    with open(args.out, "w") as fh:
        fh.write("event,mass,e1,e2\n")
        for ev, m, a, b in rec:
            fh.write("%d,%.6f,%.6f,%.6f\n" % (ev, m, a, b))
    print("%s: %d events reconstructed -> %s" % (args.channel, len(rec), args.out))


if __name__ == "__main__":
    main()
