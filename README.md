# MSME Financial Health Card

> **IDBI Innovate 2026 — Track 03 (Financial Health Score).**
> An AI/ML system that scores New-to-Credit (NTC) and New-to-Bank (NTB) Indian MSMEs using
> **alternate data** (GST, UPI, Account Aggregator bank statements, EPFO, electricity), producing a
> 0–100 credit-health score with 5 pillar sub-scores, top-5 SHAP reason codes, and a parallel
> WOE regulatory scorecard — exposed via APIs and an RM dashboard.

The authoritative design specs are [`architecture.md`](./architecture.md) and [`tech.md`](./tech.md).

---

## Core design (finalized — do not deviate)

- **Single XGBoost decision model** → one probability of default (PD). **PDs are never blended.**
- **`Score = 100·(1 − PD)`** → mapped to 6 risk tiers.
- **SHAP (TreeExplainer)** does two jobs: (a) top-5 actionable reason codes; (b) the **5 sub-scores**
  = SHAP contributions grouped by category, normalised 0–100 (pillars always agree with composite).
- **WOE Logistic scorecard (OptBinning)** is a **parallel, regulator-facing** transparency artifact.
  It does **NOT** feed into or alter the PD.
- **Dynamic pillar weighting is a DASHBOARD concern only** — the trained model is never re-weighted
  at inference. The dashboard renormalises *displayed* pillar weights to sum to 100% when a pillar
  is empty (e.g. NTC → Bureau 10% redistributes +6% Cash Flow / +4% GST).
- **AA-first, ULI-ready**; **OCEN-compliant** output endpoint; electricity is **async OCR**, off the
  <30s critical path.
- **Two separated modes:** A (origination, real-time) and B (portfolio monitoring, batch).

---

## Monorepo layout

```
/ml         Python: synthetic data generator, feature pipeline, seven-gate selection,
            XGBoost training, SHAP, WOE scorecard, evaluation, MLflow
/backend    Python 3.11 + FastAPI: scoring API, OCEN API, orchestrator, connectors,
            consent svc, alert svc, persistence (Postgres/SQLite), auth.
            Ships the trained model in backend/model_artifacts (served directly).
/frontend   React + TypeScript + Vite + Tailwind + Recharts + D3: RM dashboard (3 views)
/data       generated synthetic datasets + data dictionary + provenance + label logic
/docs       kept in sync with architecture.md / tech.md
```

## Deployment

- **Frontend → Vercel.** Root `frontend/`, build `npm run build`, output `dist/`. Set
  `VITE_API_BASE` to the Render backend URL.
- **Backend → Render.** Root = repo root. Build: `pip install ./ml && pip install -r backend/requirements.txt`.
  Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT --app-dir backend`. Set `MSME_DATABASE_URL`
  to the Neon connection string and `MSME_JWT_SECRET` to a strong secret.
- **Database → Neon (Postgres).** Create a database and paste its `postgresql+psycopg2://...` URL
  into the backend's `MSME_DATABASE_URL`. Tables are created automatically on startup.

---

## Quick start (local, end-to-end)

### 0. Prerequisites
- Python 3.11+ (3.12 works), Node 18+, and (optional) Docker + docker-compose.

### Windows — one command

```bat
start.bat
```

First run installs dependencies; every run launches the backend (:8000) + frontend (:5173) and
opens Chrome. Sign in as `rm / rm123!`. The trained model is **bundled** in
`backend/model_artifacts/`, so there is nothing to train — the backend uses it directly. Full demo
script: [`docs/RUNBOOK.md`](./docs/RUNBOOK.md).

The manual steps below are the cross-platform equivalents.

### Run backend / frontend standalone (any OS)

```bash
# backend (installs the ml package for its runtime scorer, then serves the bundled model)
pip install -e ./ml
pip install -r backend/requirements.txt
cd backend && uvicorn app.main:app --reload      # http://localhost:8000/docs

# frontend
cd frontend && npm install && npm run dev         # http://localhost:5173
```

### Retraining (optional — only if you change features/data)

The model is already trained and bundled. To rebuild it and refresh the bundled copy:

```bash
cd ml
pip install -r requirements.txt                   # full training stack (adds optbinning, mlflow, ...)
python -m msme_ml.generate --n 50000 --seed 42
python -m msme_ml.train                           # -> ml/artifacts (prints held-out AUC-ROC)
# then copy the new artifacts into the backend so it serves them:
copy ml\artifacts\*.json backend\model_artifacts\    # Windows
```

---

## Definition of Done (tracked)

- [x] Synthetic data realistic + documented (dictionary + provenance + label logic).
- [x] Single XGBoost, no PD blend; `Score = 100·(1−PD)`; 6 tiers.
- [x] SHAP top-5 reasons + 5 grouped sub-scores; parallel WOE scorecard.
- [x] AUC ≥ 0.80 on held-out NTC/NTB synthetic + fairness check.
- [x] Backend orchestrator + `/score` + OCEN endpoint + consent + append-only ledger + auth.
- [x] Frontend 3 views + consent flow; live-score on demand (no canned data).
- [x] Trained model bundled in the backend; CI (lint/test/build); deploy to Vercel/Render/Neon.

See [`docs/RUNBOOK.md`](./docs/RUNBOOK.md) for the full end-to-end demo script.
