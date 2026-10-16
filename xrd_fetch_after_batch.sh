#!/bin/bash
# xrd_fetch_after_batch.sh — serialized fetch: wait for the round-1 batch unit to
# finish, then pull the f01 immutable copy (never compete for the ~100 KB/s link).
# Launched via: systemd-run --user --unit=phase0-xrd-fetch --collect ...
set -u
cd /home/shuix/projects/deepseekharness/beacon-paper/phase0 || exit 1
echo "$(date -Is) [wait] for phase0-xrd-batch to finish" >> data/fetch.log
while systemctl --user is-active --quiet phase0-xrd-batch; do
  sleep 30
done
echo "$(date -Is) [go] batch inactive; starting fetch" >> data/fetch.log
python3 xrd_fetch_resume.py \
  "root://eospublic.cern.ch//eos/opendata/cms/derived-data/PFNano/29-Feb-24/ZeroBias/Run2016G-UL2016_MiniAODv2_PFNanoAODv1/240212_182529/0000/nano_data2016_1-1.root" \
  "data/nano_data2016_1-1.root" >> data/fetch.log 2>&1
echo "$(date -Is) [end] fetch exited rc=$?" >> data/fetch.log
