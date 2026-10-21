#!/bin/bash
# Runtime environment for the Herwig++ 2.7.1 prediction-side sample.
#
# The CVMFS LCG build (x86_64-slc6-gcc49-opt) is relocated with LCG wrapper
# scripts that depend on lcgenv, which requires Python 2. This file sets the
# same paths explicitly. Two compatibility items are required:
#   - libreadline.so.6 is not shipped by the build; the system readline 8 is
#     linked under that soname (compat-libs/), sufficient for the generator's
#     prompt handling;
#   - the GCC 4.9.1 runtime (libstdc++, libgfortran.so.3) is taken from the
#     matching LCG compiler release.
# The repository file must be the locally patched copy (see
# prepare_herwig_share.sh): the shipped HerwigDefaults.rpo names a
# non-existent "MCGenerators/herwig++/2.7.1-da362" path.

BASE=/cvmfs/sft.cern.ch/lcg/releases
HERWIGPP_HOME=$BASE/MCGenerators/herwigpp/2.7.1-da362/x86_64-slc6-gcc49-opt
THEPEG_HOME=$BASE/MCGenerators/thepeg/1.9.2p1-d84d2/x86_64-slc6-gcc49-opt
HERWIG_GSL=$BASE/GSL/1.10-a0511/x86_64-slc6-gcc49-opt
HERWIG_BOOST=$BASE/Boost/1.55.0_python2.7-70d89/x86_64-slc6-gcc49-opt
HERWIG_FASTJET=$BASE/fastjet/3.1.1-ae989/x86_64-slc6-gcc49-opt
HERWIG_HEPMC=$BASE/HepMC/2.06.09-0a23a/x86_64-slc6-gcc49-opt
HERWIG_LHAPDF=$BASE/MCGenerators/lhapdf/6.1.4-1dbae/x86_64-slc6-gcc49-opt
HERWIG_GCC=$BASE/gcc/4.9.1/x86_64-slc6/lib64

LEG_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
COMPAT_LIBS=$LEG_DIR/compat-libs

export HERWIG_HOME=$HERWIGPP_HOME
export THEPEG_HOME
export LHAPDF_HOME=$HERWIG_LHAPDF
export HERWIGPATH=$LEG_DIR/hpp-share
export THEPEGPATH=$THEPEG_HOME/share/ThePEG
export LHAPDF_DATA_PATH=/cvmfs/sft.cern.ch/lcg/external/lhapdfsets/current

export PATH=$HERWIGPP_HOME/bin:$THEPEG_HOME/bin:$HERWIG_GSL/bin:$HERWIG_FASTJET/bin:$HERWIG_LHAPDF/bin:$PATH
export LD_LIBRARY_PATH=$HERWIGPP_HOME/lib/Herwig++:$THEPEG_HOME/lib/ThePEG:$HERWIG_GSL/lib:$HERWIG_BOOST/lib:$HERWIG_FASTJET/lib:$HERWIG_HEPMC/lib:$HERWIG_LHAPDF/lib:$COMPAT_LIBS:$HERWIG_GCC
