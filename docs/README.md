# Documentation Index

The authoritative design docs live at the repo root and are the single source of truth:

- [`../architecture.md`](../architecture.md) — system architecture (layers, modes, scoring pipeline,
  AWS deployment, security/compliance, MLOps).
- [`../tech.md`](../tech.md) — finalized technology stack and rationale.
- [`../README.md`](../README.md) — project overview + quick start.

This folder:

- [`RUNBOOK.md`](./RUNBOOK.md) — how to set up, train, run, and demo the system end-to-end.

Data documentation (in [`../data`](../data)):

- [`DATA_DICTIONARY.md`](../data/DATA_DICTIONARY.md) — every one of the 65 features (auto-generated
  from `ml/msme_ml/schema.py`).
- [`DATA_PROVENANCE.md`](../data/DATA_PROVENANCE.md) — public statistics used to calibrate the
  synthetic generator, with sources.
- [`LABEL_LOGIC.md`](../data/LABEL_LOGIC.md) — how the default label is generated (transparent
  latent-risk function + noise) and the no-leakage guarantees.

## Design invariants (must hold across all components)

1. **Single XGBoost decision model** → one PD. **PDs are never blended.**
2. **`Score = 100·(1 − PD)`** → 6 risk tiers.
3. **SHAP** → top-5 reason codes + 5 sub-scores (grouped by pillar, normalised 0–100).
4. **WOE scorecard** = parallel regulator-facing artifact; never feeds the PD.
5. **Dynamic pillar weighting** = dashboard-only renormalisation; the trained model is never
   re-weighted at inference.
6. **AA-first, ULI-ready**; **OCEN-compliant** output; electricity is **async OCR**, off the <30s path.
7. **Two separated modes**: A (origination, real-time) and B (portfolio monitoring, batch).
