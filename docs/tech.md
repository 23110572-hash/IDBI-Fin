# MSME Financial Health Card — Technology Stack

> Track 03, IDBI Innovate 2026. Technology choices and justifications for the MSME Financial
> Health Card. Every choice maps to a goal in `architecture.md` and respects the
> RBI / SEBI / DPDP + human-in-the-loop constraints from the explainer session (`information.md`).
> Companion document: `architecture.md` (system design).
> Last compiled: July 5, 2026.

---

## 1. Stack at a Glance

| Layer | Technology | Why |
|-------|-----------|-----|
| Frontend | **React + TypeScript + Vite** | Fast SPA, strong typing, mobile-responsive dashboard |
| UI / charts | **Recharts + D3** | Recharts: radar (sub-scores), line (trend), heat map; D3: SHAP force plot |
| State/data | **TanStack Query + Zustand** | Server-state caching + light client state |
| Backend API | **Python 3.11 + FastAPI** | Async, high-throughput, native OpenAPI, same language as ML |
| Async/queue | **Celery + Redis** | Parallel data pulls, background refresh jobs |
| ML — accuracy | **XGBoost** | Top tabular accuracy; AUC 0.80–0.90; stable SHAP |
| ML — scorecard | **scikit-learn + OptBinning (WOE Logistic Regression)** | Regulatory gold-standard, fully explainable points |
| ML — survival | **lifelines (Cox PH)** | Time-to-default overlay (post-MVP) |
| Explainability | **SHAP** | Top-5 reason codes; RBI explainability requirement |
| Feature tooling | **pandas, NumPy, scikit-learn, OptBinning** | WOE binning, IV, PSI, feature pipeline |
| Data validation | **Pydantic v2 + Great Expectations** | Schema enforcement at API + data-quality gates |
| OCR (electricity bills) | **AWS Textract** | Async extraction of units-consumed from uploaded power bills |
| Datastore | **PostgreSQL** | Consent registry, score ledger (append-only), feature metadata |
| Cache | **Redis (via AWS ElastiCache)** | Low-latency feature/raw cache + job broker |
| Object store | **AWS S3** | Bank statements, documents, model artifacts |
| ML platform | **AWS SageMaker** | Training, model registry, batch scoring |
| Compute | **AWS ECS Fargate** | Containerised stateless services, autoscaling |
| Edge | **CloudFront + API Gateway/ALB + WAF** | CDN, TLS, OAuth2, rate limiting |
| IaC | **Terraform** | Reproducible AWS provisioning |
| CI/CD | **GitHub Actions + Docker** | Build, test, deploy pipeline |
| Auth | **OAuth2 / JWT (AWS Cognito)** | RBAC, token lifecycle |
| Observability | **CloudWatch + OpenTelemetry** | Logs, traces, metrics, model monitoring (AWS-native dashboards) |
| Experiment tracking | **MLflow** | Model versions, metrics, reproducibility |

---

## 2. Frontend

**React + TypeScript (Vite)** — the dashboard is the human-in-the-loop decision surface, so it
must be fast and legible. TypeScript reduces defects across the three complex views.

- **Tailwind CSS** — utility-first styling for a clean, consistent, mobile-responsive layout
  (RMs are often field-based; borrower consent screens must work on low-end devices).
- **Recharts + D3.js** — covers the visualisation requirement in the problem statement:
  - Radar chart (Recharts) → 5 sub-scores vs sector average.
  - Heat map (Recharts) → portfolio colour-coded by score tier.
  - Line chart (Recharts) → 12-month score trend.
  - SHAP force plot (D3) → a true force-plot visual of the top-5 positive / negative drivers,
    for high-fidelity explainability in the demo.
- **TanStack Query** — caches scoring results, handles refetch/stale state for the alert feed.
- **Zustand** — minimal client-side state (filters, selected borrower).
- **WebSocket client** — live alert feed (tier crossings, score drops).

---

## 3. Backend & Orchestration

**Python 3.11 + FastAPI** — chosen so the API and ML code share one language and data model,
eliminating a serialization boundary between scoring and serving.

- **Async I/O** — the orchestrator fires the 7 real-time data-source pulls concurrently
  (electricity is async, off this path); FastAPI's async model keeps the <30s latency SLO achievable.
- **Pydantic v2** — request/response schemas, OCEN payload validation, config typing. Also the
  untrusted-input boundary for the external OCEN endpoint (strict schema validation).
- **Auto OpenAPI** — free, accurate API docs for the OCEN and scoring endpoints.
- **Celery + Redis** — background jobs for daily AA deltas, monthly recomputes, and any pull
  that shouldn't block the request path.
- **httpx** — async HTTP client for connector calls with per-source timeouts.

**Connector design:** each data source (AA, GST, EPFO, UPI, Udyam, Bureau, Macro) is an isolated
module implementing a common `fetch(consent_token) -> RawPayload | Unavailable` interface, so a
failing source degrades gracefully instead of failing the request. **AA (Sahamati) is the primary
live rail; ULI is future-ready** (the interface is ULI-shaped but the MVP has no hard ULI
dependency).

**Electricity is different — it is asynchronous, not a real-time connector.** No unified
consent-based electricity API exists in India today, so a power bill is uploaded and processed by
OCR (**AWS Textract**) off the critical <30s path; the extracted units-consumed enrich the score
after the initial decision.

---

## 4. Machine Learning

Implements a **hybrid architecture** that balances predictive accuracy with regulatory
explainability. **XGBoost is the single decision model; the WOE scorecard is a parallel
regulatory-transparency view — the two are never blended into one PD.**

### 4.1 XGBoost — the single decision model
- Gradient-boosted trees on the full 65-feature vector → one probability of default (PD) that
  **drives the decision**. PDs are **not blended** with any other model, so SHAP explains 100% of it.
- Handles non-linearities, feature interactions, mixed types, outliers, and **missing data natively**
  (ideal for NTC — an empty source is just a feature value, never an imputation penalty).
- Target AUC-ROC 0.80–0.90 on NTC/NTB. Chosen over LightGBM for **more stable SHAP**
  (regulatory defensibility).

### 4.2 WOE Logistic Regression — parallel regulatory scorecard (not blended)
- **scikit-learn + OptBinning** — OptBinning handles Weight-of-Evidence binning, Information
  Value, and a `Scorecard` built on scikit-learn's `LogisticRegression`.
- Trained on the top 15–20 features (by SHAP importance) → a transparent point-based scorecard
  presented **alongside** the XGBoost decision as an independent RBI-facing transparency view. It
  does **not** feed into or alter the XGBoost PD. (The scorecard points are self-explaining, so no
  SHAP is needed for it.)

### 4.3 Cox Proportional Hazards — Phase 2
- **lifelines** — expected time-to-default overlay ("high PD, expected within 6 months" vs
  "moderate PD, only after 18 months") for tenure/pricing decisions. Parallel to the PD, not blended.

### 4.4 Score composition
- **Single decision PD from XGBoost** → `Score = 100·(1 − PD)`, mapped to 6 risk tiers. **No PD
  blend** — one model decides, so SHAP explains it end-to-end.
- **5 sub-scores** are SHAP contributions **grouped by category** (normalised 0–100), so they always
  agree with the composite. Missing data is handled natively by XGBoost — an empty Bureau for an NTC
  borrower is just a feature value, never a penalty.
- **Dynamic weighting is a dashboard concern, not the model.** The Health Card renormalises the
  *displayed* pillar weights to 100% when a pillar is empty (Bureau 10% → Cash Flow +6% / GST +4%);
  the trained model is never re-weighted at inference. Macro stays a 5% context signal.
- **Hybrid retained, no blend:** XGBoost + SHAP is the decision engine; the WOE scorecard is a
  **parallel** RBI-facing transparency artifact (not mixed into the PD); Cox is Phase 2.

### 4.5 Explainability
- **SHAP** (TreeExplainer on XGBoost) → top-5 reason codes per decision, actionable features
  prioritised for the reason-code ranking (the actionability gate, see §4.6).

### 4.6 Feature engineering & selection
- **pandas / NumPy** — feature computation from raw payloads.
- **OptBinning** — WOE + IV (Gate 1), PSI (Gate 4).
- **Great Expectations** — data-quality gates (schema, ranges, null rates) before scoring.
- Seven-gate selection (IV, Regulatory, Availability, Stability, Actionability, Fairness,
  Cost-Benefit) narrows 65 → ~40–50 features.

---

## 5. Data & Persistence

- **PostgreSQL (RDS)** — three logical stores:
  - *Consent Registry* — immutable, DPDP-audit-ready (purpose, scope, TTL, revocation).
  - *Score Ledger* — append-only; every score + feature snapshot + model version (reproducibility).
  - *Feature metadata* — bin definitions, scorecard points, PSI baselines.
- **Redis (ElastiCache)** — online feature cache, raw-payload session cache (TTL), Celery broker.
- **S3** — bank-statement blobs, documents, versioned model artifacts.
- **Feature Store** — a **Postgres + Redis** pattern serves pre-computed slowly-changing
  features (monthly GST, Udyam, macro) online to protect the latency SLO.

---

## 6. Cloud & Deployment (AWS + ACC)

Maps directly to the hackathon-provided AWS + Applied Cloud Computing toolkit.

- **ECS Fargate** — containerised FastAPI, scoring service, connector workers;
  horizontal autoscaling on the scoring service.
- **SageMaker** — training, model registry, batch scoring; models served in-container for
  low-latency online inference.
- **CloudFront + S3** — SPA static hosting/CDN.
- **API Gateway / ALB + WAF** — TLS termination, OAuth2, rate limiting, the untrusted-input edge
  for the external OCEN API.
- **RDS Postgres**, **ElastiCache Redis**, **S3** — as in Section 5.
- **Terraform** — all infra as code, reproducible across environments.
- **Networking** — compute/data in private subnets; public only at CDN/ALB; VPC endpoints for
  AWS service traffic.

---

## 7. Security & Compliance Tooling

| Need | Tooling |
|------|---------|
| AuthN/AuthZ | OAuth2 + JWT via AWS Cognito; RBAC (RM / credit officer / admin) |
| Secrets | AWS Secrets Manager (no secrets in code/config) |
| Encryption | KMS (RDS/S3 at rest); TLS 1.2+ in transit; mTLS between internal services |
| PII protection | Field-level encryption + tokenisation for PAN/account numbers; masked in logs/UI |
| Consent/DPDP | Consent Registry service + purpose/TTL enforcement middleware |
| Fairness | Fairlearn disparate-impact tests across protected classes + size buckets |
| Audit | Append-only Score Ledger; structured audit logs |
| Dependency hygiene | Pinned versions; `pip-audit` (Python) + Dependabot (JS) for CVEs |

---

## 8. MLOps & Observability

- **MLflow** — experiment tracking, model versions, metrics, artifact lineage.
- **SageMaker Model Registry** — promotion/approval workflow for production models.
- **PSI monitoring job** — monthly feature + score-distribution drift; alert on PSI > 0.25.
- **OpenTelemetry + CloudWatch** — distributed tracing across orchestrator → connectors → scoring
  to pinpoint latency-SLO breaches; CloudWatch dashboards for service and model metrics.
- **Refresh schedulers** — Celery beat drives daily AA delta, monthly full recompute, and
  quarterly retrain jobs.

---

## 9. Development & Delivery

- **Monorepo** — `frontend/` (React), `backend/` (FastAPI), `ml/` (training + pipeline),
  `infra/` (Terraform), `docs/`.
- **Docker + docker-compose** — local parity (Postgres, Redis, API, ML) for the 4-person team.
- **GitHub Actions** — lint (ruff, eslint) → test (pytest, vitest) → build images → deploy.
- **Testing** — pytest (backend/ML), vitest + React Testing Library (frontend), Great
  Expectations (data), model eval report per training run.
- **Pre-commit** — ruff, black, mypy, eslint, prettier.

---

## 10. Technology Choice Rationale (Key Decisions)

| Decision | Chosen | Rejected alternatives | Rationale |
|----------|--------|-----------------------|-----------|
| API framework | FastAPI | Flask, Django REST | Async for parallel pulls; shares Python with ML; auto OpenAPI |
| Primary model | XGBoost (decision) + WOE LR (parallel regulatory view, no PD blend) | Pure XGBoost, pure LR, LSTM | Accuracy with RBI explainability; SHAP explains 100% of the single-model decision; LSTM needs data + is opaque |
| Boosting lib | XGBoost | LightGBM | More stable SHAP for regulatory defensibility |
| Explainability | SHAP | LIME | Consistent, theoretically grounded, tree-optimised |
| DB | PostgreSQL | MongoDB | Relational integrity for consent/audit ledger; append-only patterns |
| Compute | ECS Fargate | Raw EC2, Lambda | Serverless containers, autoscaling, no cold-start penalty on scoring |
| Frontend | React + TS | Angular, Vue | Ecosystem + charting maturity; team familiarity |
| IaC | Terraform | CloudFormation | Cloud-portable (supports ACC alongside AWS) |

---

## 11. Phased Adoption (MVP → POC)

| Component | MVP (by Jul 9) | Full POC (post-shortlist) |
|-----------|----------------|---------------------------|
| Models | XGBoost + WOE LR | + Cox survival, federated-learning R&D |
| Data | AA + GST + Udyam + Bureau (synthetic) | + EPFO, UPI, Electricity, live ULI |
| Serving | In-container inference | SageMaker endpoints + autoscaling |
| Integration | OCEN stub, AA flow | Live ULI/OCEN sandbox |
| Infra | Single-region ECS/RDS/S3 | Multi-AZ, full observability, DR |
| Monitoring | Basic CloudWatch + MLflow | PSI drift, fairness dashboards, alerting |

---

## 12. Dependencies Summary (indicative)

```
Backend:   fastapi, uvicorn, pydantic, httpx, celery, redis, sqlalchemy, psycopg2, boto3 (Textract/S3/Cognito)
ML:        xgboost, scikit-learn, optbinning, lifelines, shap,
           pandas, numpy, mlflow, great-expectations
Frontend:  react, typescript, vite, tailwindcss, recharts, d3, @tanstack/react-query, zustand
Infra:     terraform, docker, aws-cli
Quality:   pytest, vitest, ruff, black, mypy, eslint, prettier, pip-audit
```

> Pin exact versions in `requirements.txt` / `package.json` before submission; avoid open ranges
> and verify package names to prevent typosquatting.
