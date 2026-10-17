# Pre-registered predictions

Rule: before any official run, a prediction card is committed to this directory.
The commit hash is the timestamp; the card is not edited after the run starts.
Revisions are new cards that reference the previous hash.

Purpose: the project's claims rest on predictions fixed before data inspection. A card
records the hypotheses, the exact analysis choices (bins, baselines, gates), the sample,
and the decision rule, so that a later result can be checked against it without ambiguity.

Card format: `TEMPLATE.md`. File name: `YYYY-MM-DD-<run-id>.md`.

Status 2026-10-16: the Phase 0 prediction cards (honest-tail rates, effect-1 shape
integrity, finite-sample entropy scaling) were recorded in the working session on
2026-10-16. The cross-detector decision criteria for the ATLAS check (band bins,
sideband and Fourier baselines, uniformity gates) were fixed before the ATLAS data were
inspected; the paper's method note records this. No retrospective card is created: a card
written after the data is not a pre-registration.

From 2026-10-17: cards are committed before the run; the commit hash is cited in the
result manifest.
