# MSME Financial Health Card — System Architecture

> Track 03, IDBI Innovate 2026. Architecture blueprint for an AI/ML-driven MSME Financial
> Health Card that fuses alternate data (GST, UPI, AA, EPFO, electricity, etc.), computes a
> multidimensional 0–100 credit health score, and integrates with ULI / OCEN / AA.
>
> Companion documents: `information.md` (hackathon + track context), `tech.md` (technology stack).
> Last compiled: July 5, 2026.

---

## 1. Architecture Goals & Constraints

Derived from the problem statement (`information.md`) and the explainer-session video.

| # | Goal | Design driver |
|---|------|---------------|
| G1 | Score NTC/NTB MSMEs with **zero traditional documents** | Alternate-data-only feature pipeline; missing data treated as a signal |
| G2 | **Unified assessment framework** fusing GST + UPI + AA + EPFO (+ electricity) | Multi-source fusion layer → single borrower entity |
| G3 | **Multidimensional score** — composite 0–100 + 5 sub-scores | One XGBoost decision model; SHAP decomposes its output into 5 category sub-scores |
| G4 | **Near real-time** (< 30s consent-to-score) | Parallel data pulls, pre-computed/cached features, low-latency inference |
| G5 | **AA-first, ULI-ready** integration | AA (Sahamati) as the live consent+data rail today; OCEN-compliant score API; ULI as future interoperability layer |
| G6 | **Explainable + regulatory-compliant** (RBI, SEBI, DPDP) | Hybrid XGBoost + WOE scorecard, SHAP reason codes, consent-first data |
| G7 | **Human-in-the-loop** — AI assists, does not replace underwriters | Risk tiers with manual-review bands; RM dashboard as the decision surface |
| G8 | **Graceful degradation** when any data source is missing | Each layer independently consumable; fallback strategies per layer |
| G9 | Reusable **platform**, not a one-off tool | Stateless scoring microservices, OCEN API, white-label dashboard |

**Non-functional targets**
- Latency: p50 ≤ 30s, p95 ≤ 60s (consent → score).
- Model quality: AUC-ROC ≥ 0.80 on NTC/NTB population.
- Availability: 99.5% for the scoring API (POC target).
- Auditability: every score reproducible with feature snapshot + model version.

---

## 2. Logical Architecture (Layered View)

```
[ PRESENTATION LAYER ]
    RM / Credit-Officer Dashboard (React): Portfolio Heat Map · Drill-down · Alert Feed
    Borrower consent flow (mobile)
        │  REST/JSON over OAuth2   +   WebSocket for alerts
        ▼
[ API & ORCHESTRATION LAYER — FastAPI ]
    Auth/Consent · Scoring API · OCEN-compliant API · Orchestrator · Alert/Webhook
        │
        ▼
[ DATA ACQUISITION — AA-first, ULI-ready ]              [ ML / SCORING LAYER ]
    AA (live) · GST · EPFO · UPI · Bureau · Udyam          Feature pipeline (65 feats)
    · Macro                                       ──────►  XGBoost → PD  (single decision)
    Electricity (async OCR, off critical path)             SHAP → reason codes + 5 sub-scores
    ULI-ready (no hard dependency)                         WOE scorecard (parallel) · Cox (P2)
        │                                                      │
        ▼                                                      ▼
[ DATA & PERSISTENCE LAYER ]
    Feature Store · Consent Registry · Score Ledger (audit) ·
    Model Registry · Raw Data Cache (TTL) · Object store (S3)

[ CROSS-CUTTING ]  Security · Consent/DPDP governance · Observability · MLOps
```

---

## 3. Component Breakdown

### 3.1 Presentation Layer
- **RM Dashboard (React SPA)** — three primary views:
  - *Portfolio Heat Map* — all borrowers as score-colour-coded cards, sortable/filterable (watch-list, opportunity-list).
  - *Single Borrower Drill-down* — composite score + 12-month trend, sub-score radar (vs sector avg), SHAP force plot, raw-data summary, 90-day alert history.
  - *Alert Feed* — real-time tier crossings, score drops, missed GST filings, cheque bounces, with suggested actions.
- **Borrower Consent Flow** — mobile-first web flow that initiates AA consent (ULI-ready), collects Udyam Registration Number (URN), PAN, GSTIN.
- Mobile-responsive; borrower-facing screens optimised for low-end devices.

### 3.2 API & Orchestration Layer (FastAPI)
- **Consent & Auth Service** — issues/validates OAuth2 tokens; manages AA consent lifecycle (requested → granted → active → expired → revoked); ULI-ready.
- **Orchestrator** — fires parallel data pulls after consent, enforces per-source timeouts, assembles the unified borrower record, degrades gracefully on partial failure.
- **Scoring API** — `POST /score` → composite score, 5 sub-scores, risk tier, SHAP top-5, confidence, model version.
- **OCEN Credit-Assessment API** — standardised endpoint any LSP on ONDC can call (URN/PAN/GSTIN in → assessment out).
- **Alert/Webhook Service** — pushes score-change events to the dashboard (WebSocket) and to downstream systems.

### 3.3 Data Acquisition Layer (8 data sources: 7 real-time + electricity async)
See Section 5 for the full layer/latency/fallback matrix. Each source is an isolated module with a common interface: `fetch(consent_token) -> RawPayload | Unavailable`. **AA (Sahamati) is the primary live rail**; direct connectors (GST, EPFO, UPI, Bureau, Udyam) run in parallel; **ULI is future-ready** (interface is ULI-shaped, no hard dependency). Electricity is handled asynchronously via bill upload + OCR, off the real-time path.

### 3.4 ML / Scoring Layer
- **Feature Pipeline** — transforms raw multi-source payloads into the 65-feature vector; missing data is handled **natively by XGBoost as a feature** (no imputation penalty), plus normalisation.
- **XGBoost — the single decision model** — produces one probability of default (PD) that drives the decision. Handles NTC missing data natively. **PDs are not blended**, so the decision has one clear, fully explainable source.
- **SHAP Explainer** — explains the XGBoost PD end-to-end: (a) top-5 reason codes per decision (actionable features prioritised), and (b) the 5 sub-scores, computed as **SHAP contributions grouped by category** so the pillars always agree with the composite.
- **WOE Logistic scorecard — parallel regulatory view (not blended)** — a transparent points-based scorecard on the top SHAP features, presented *alongside* the decision as an independent RBI-facing transparency artifact. It does **not** feed into or alter the PD.
- **Cox Proportional Hazards** (Phase 2) — expected time-to-default overlay.
- **Score Composer** — `Score = 100·(1−PD)` from the single XGBoost PD; maps to 6 risk tiers; sub-scores are SHAP-grouped (§7.1).

> **Hybrid retained, no PD blend:** XGBoost + SHAP is the decision engine — built and demoed first,
> handles missing data natively (ideal for NTC), fully explainable. The WOE scorecard is a
> **parallel** RBI-facing transparency view, not averaged into the PD. Cox is Phase 2. The two models
> play distinct roles instead of being blended, so SHAP always explains 100% of the decision.

### 3.5 Data & Persistence Layer
- **Feature Store** — pre-computed/cached features (monthly GST, Udyam), online serving for low latency.
- **Consent Registry** — immutable consent records (purpose, scope, TTL) for DPDP audit.
- **Score Ledger** — append-only audit of every score with feature snapshot + model version (reproducibility).
- **Model Registry** — versioned model artifacts, scorecards, calibration params, PSI baselines.
- **Raw Data Cache** — TTL-bound cache of raw pulls to avoid re-fetch within a session.
- **Object Store** — bank statement blobs, documents.

---

## 4. Data Sources & Signals

| Source | Category | Key signals | Notes |
|--------|----------|-------------|-------|
| Account Aggregator (AA) | Cash flow | Inflow/outflow, balances, EMI, bounces | Foundation of cash-flow analysis (12–24 mo) |
| GST Network | Revenue + compliance | Turnover trend, GSTR-1 vs 3B mismatch, filing regularity | Strongest objective revenue signal for NTC |
| UPI (NPCI merchant) | Behavioural | Txn count/value, customer concentration, seasonality | Only if merchant UPI ID exists |
| EPFO | Business stability | Employee count trend, payroll regularity | Unavailable < 20 employees → micro-size signal |
| **Electricity / Power** | **Business activity** | **Consumption trend, units drawn for manufacturing units** | **Async — via bill upload + OCR (no real-time API exists); proxy for real activity** |
| Udyam Registration | Classification | Enterprise type, vintage, NIC code | Mandatory; routes to model segment |
| Bureau (CIBIL/Experian/Equifax) | Credit history | Score, obligations, delinquency | Empty = NTC signal (a feature itself) |
| Macro (RBI/PMI) | Context | Sector outlook, PMI, inflation | Public, pre-cached; score modulator only |

> **Note on the electricity signal (deployable reality):** the IDBI explainer session called out
> electricity/power consumption for manufacturing units as an alternate signal. However, **there is
> no unified, consent-based, real-time electricity API in India today** — DISCOMs are state-run and
> fragmented. We therefore treat electricity as an **asynchronous signal**: the RM (or borrower)
> uploads a recent power bill, OCR extracts units-consumed, and the score is enriched/updated after
> the initial decision. It contributes a Utility & Infrastructure Signals feature group that folds
> into the Business Stability sub-score, but it is **never on the critical <30s origination path**.
> This distinguishes *ideal* data from *deployable* data.

---

## 5. Data Acquisition — Latency & Fallback Matrix

| Layer | Source | Target latency | Fallback strategy |
|-------|--------|----------------|-------------------|
| 0 | Identity & Consent (URN, PAN, GSTIN, AA token) | 5–10 s | Cannot proceed without consent |
| 1 | Udyam Registration | ~2 s | No Udyam → not classifiable as MSME; redirect |
| 2 | GST (GSTR-1/3B/2B, 24 mo) | 5–15 s | Not registered → rely on AA + UPI |
| 3 | AA bank statements (12–24 mo) | 10–30 s | Critical; cannot proceed without AA |
| 4 | EPFO | 5–10 s | Unavailable → micro-size feature; weight GST/AA higher |
| 5 | UPI merchant | 5–10 s | Non-merchant → use AA transaction patterns |
| 6 | Bureau | 5–15 s | Empty → NTC signal (feature) |
| 7 | Electricity / Power | **async (OCR, off critical path)** | Bill upload + OCR; enriches score post-decision. Unavailable → skip; non-manufacturing tolerates absence |
| 8 | Macro context | pre-cached | Always available |

Orchestration: Layers 1–6 and 8 fire concurrently once Layer 0 consent completes; Layer 8 is served
from cache. **Layer 7 (electricity) is asynchronous** — it is not part of the real-time origination
pull and enriches the score afterwards. Any layer failure → proceed with available data, record the
gap as a feature.

---

## 6. End-to-End Request Flow — Mode A: Origination (real-time, on-demand)

> **The system operates in two distinct modes — do not conflate them:**
> - **Mode A — Origination (this section):** on-demand, single data pull, score in <30s, **at the
>   moment a loan is applied for**. This is the near-real-time path.
> - **Mode B — Portfolio Monitoring (§12):** batch, scheduled, **after a loan is disbursed**, to
>   watch the health of existing borrowers. This is *not* real-time and runs only for customers the
>   bank already lends to.
>
> The flow below is **Mode A**.


```
Mode A — Origination (target < 30s; p95 60s)

  1. Borrower submits application + URN / PAN / GSTIN.
  2. System issues an AA consent request.
  3. Borrower approves in their AA app → consent token returned.
  4. Orchestrator fires the 7 real-time source pulls in parallel
     (AA, GST, EPFO, UPI, Bureau, Udyam, Macro).
  5. Connectors return raw payloads → one unified borrower record → 65-feature vector.
  6. XGBoost produces the PD → Score = 100·(1−PD);
     SHAP produces the top-5 reason codes + 5 sub-scores.
  7. Result persisted to the append-only Score Ledger (feature snapshot + model version).
  8. Health Card rendered on the RM dashboard; also returned via the OCEN API to LSPs.

  Electricity: if a power bill is uploaded later, OCR enriches the score asynchronously
  (never on this < 30s path).
```

Target: the full flow completes within 30 s (p95 60 s). Also exposed synchronously via the OCEN API for LSP consumers.

---

## 7. Scoring Pipeline (Model View)

```
Raw payloads
   │
   ▼
Feature Pipeline (65 feats, missing-as-feature — XGBoost-native)
   │
   ▼
XGBoost ──► single PD ──► Score = 100·(1−PD) ──► 6 risk tiers
   │
   ▼
SHAP explainer
   ├─► top-5 reason codes
   └─► 5 sub-scores (SHAP grouped by category — always consistent with the composite)

Parallel views (NOT blended into the PD):
   • WOE Logistic scorecard        ──► RBI-facing transparency (points-based)
   • Cox Proportional Hazards (P2)  ──► expected time-to-default
```

### 7.1 Sub-scores and the Health Card composite

**Two distinct things — do not confuse them:**

**(a) The decision score (ML).** The composite `Score = 100·(1−PD)` comes from the **single XGBoost
PD**. XGBoost handles missing data **natively as a feature** — nothing is reweighted at inference.
An NTC borrower with no bureau data is not penalised; "no bureau" is simply a feature value.

**(b) The 5 pillar sub-scores (explainability + UI).** Computed from **SHAP contributions grouped
by category**, each normalised to 0–100. Because they are derived from the same model output, the
pillars **always agree with the composite** (no "all-green-but-declined" contradiction).

| Pillar | Display weight (all sources present) | Primary source |
|--------|--------------------------------------|----------------|
| Cash Flow Stability | 35% | AA |
| GST Compliance & Revenue | 30% | GST |
| Business Stability | 20% | Udyam, EPFO, Electricity |
| Bureau & Credit History | 10% | Bureau |
| Macroeconomic Context | 5% (context only) | RBI/PMI |

**Dynamic weighting is a DASHBOARD concern, not an ML-model concern.** The percentages above govern
only how the **Health Card visualises** pillar contributions. When a pillar has no data (e.g. an NTC
borrower → empty Bureau pillar), the dashboard **renormalises the visible weights to sum to 100%**
(Bureau's 10% spreads to Cash Flow +6% / GST +4%) so the underwriter is never shown a misleading
empty pillar. **The XGBoost PD is unchanged** — you cannot and do not re-weight a trained model at
inference; the model already handles the missing source natively.

- **Macroeconomic Context** stays a small context signal (5%), surfaced to the human underwriter,
  never a primary basis for decline (sector/geography-generic).

> Pitch line: *"The model treats missing data as a feature; the Health Card dynamically renormalises
> its visible pillars so credit-invisible MSMEs are shown the evidence they do have — not confused by
> empty pillars."*

### 7.2 Risk-tier → action mapping
| Score | Tier | PD | Action |
|-------|------|----|--------|
| 90–100 | Excellent | <2% | Auto-approve (STP) |
| 75–89 | Good | 2–5% | Approve w/ standard conditions |
| 60–74 | Fair | 5–10% | **Manual review by RM (human-in-loop)** |
| 40–59 | Watch | 10–20% | Decline w/ improvement feedback |
| 20–39 | Risk | 20–40% | Decline; refer to secured product |
| 0–19 | High Risk | >40% | Decline; fraud review if warranted |

---

## 8. Ecosystem Integration — "AA-first, ULI-ready"

The Account Aggregator ecosystem is the **live, working rail today**; ULI is still in its scaling
phase and standardises APIs while consent continues to flow through AAs. We therefore build
**AA-first** for the POC and treat ULI as the **future-state interoperability layer**.

- **AA (inbound, data — PRIMARY, live today)** — native consent-token consumption via the FIU API,
  built to Sahamati standards; supports all licensed AAs; handles the full consent lifecycle
  including mid-loan revocation → flag for manual review. This is the backbone of the MVP.
- **ULI (inbound, data — future-ready)** — designed so that when ULI matures, a single ULI
  consent can aggregate AA + GST + EPFO. The connector interface is ULI-shaped, but the POC does
  not depend on ULI being available. No hard dependency on ULI for launch.
- **OCEN (outbound, product)** — score, sub-scores, tier, SHAP, confidence exposed as an
  OCEN-compliant credit-assessment endpoint so any LSP on ONDC can consume it. This makes the
  engine reusable infrastructure, not a single-bank tool.

> Positioning: AA is what makes the solution **deployable now**; ULI is what makes it
> **future-proof**. This shows judges we understand the difference between ideal and deployable.

---

## 9. Deployment Architecture (AWS)

```
        Internet
           │
           ▼
        CloudFront (CDN) ──▶ S3 (React SPA static build)
           │
           ▼
        API Gateway / ALB  (OAuth2, WAF, rate limiting)
           │
           ▼
        ┌───────────────────────────────────────┐
        │  ECS Fargate (containerised)           │
        │  • FastAPI (API + orchestrator)        │
        │  • Scoring service (model server)      │
        │  • Connector workers                   │
        └───────────────────────────────────────┘
             │            │             │
             ▼            ▼             ▼
        RDS (Postgres) ElastiCache   S3 (statements,
        Consent/Ledger  (Redis:       model artifacts)
        /Feature meta   cache/queue)
             │
             ▼
        SageMaker (training, model registry, batch scoring)  +  CloudWatch (obs)
```

- **Compute:** ECS Fargate for stateless services; horizontal autoscaling on the scoring service.
- **Data:** RDS Postgres (consent registry, score ledger, feature metadata); Redis for cache + async job queue; S3 for blobs + model artifacts.
- **ML:** SageMaker for training/registry/batch; models served in-container for low-latency online inference.
- **Edge:** CloudFront + S3 for the SPA; API Gateway/ALB with WAF, OAuth2, rate limiting.
- **Networking:** private subnets for compute/data; public only at CDN/ALB; VPC endpoints for AWS services.
- The hackathon toolkit provides AWS + ACC — this maps directly onto that.

---

## 10. Security, Privacy & Compliance

| Concern | Control |
|---------|---------|
| **Consent (DPDP)** | Consent-first design; immutable Consent Registry; purpose-limited, time-bound, revocable; data minimisation |
| **RBI (credit/model risk)** | WOE scorecard as regulatory-facing model; SHAP reason codes; audit ledger; PSI drift monitoring |
| **SEBI** | Relevant where investment/securities data touched; scoped access + audit |
| **Data in transit** | TLS 1.2+ everywhere; mTLS between internal services |
| **Data at rest** | KMS-encrypted RDS/S3; field-level encryption for PII (PAN, account numbers) |
| **Access control** | OAuth2 + RBAC (RM vs credit officer vs admin); least privilege IAM |
| **Secrets** | AWS Secrets Manager; no secrets in code/config |
| **PII handling** | Tokenise/mask PAN & account numbers in logs and dashboards; never echo secrets |
| **Auditability** | Append-only Score Ledger with feature snapshot + model version per decision |
| **Fairness** | Disparate-impact testing across protected classes and enterprise-size buckets (fairness gate in feature selection) |

> Network-exposed APIs (Scoring, OCEN) must sit behind authentication (OAuth2) and rate limiting.
> The OCEN endpoint is deliberately external — treat it as an untrusted-input boundary (strict
> schema validation, throttling).

---

## 11. MLOps & Model Lifecycle

- **Training:** offline on synthetic data (MVP) → retrain on real sandbox data post-shortlisting (Jul 22–31).
- **Validation:** time-based split (no leakage), held-out NTC/NTB test set, target AUC ≥ 0.80.
- **Registry:** every model + scorecard + calibration versioned; scores tagged with the version used.
- **Monitoring:** PSI on features (monthly) + score distribution; alert on PSI > 0.25.
- **Refresh cadence:** governed by Mode B — Portfolio Monitoring (see §12). Applies to disbursed borrowers only; not part of Mode A origination.

---

## 12. Score Refresh & Alerting — Mode B: Portfolio Monitoring (batch, post-disbursal)

> This mode applies **only to already-onboarded borrowers** (loan disbursed). It is batch, not
> real-time, and is completely separate from Mode A origination scoring. A new applicant is scored
> once in Mode A; ongoing daily/monthly refresh begins only *after* they become a customer.

```
Daily   ─▶ AA delta pull ─▶ recompute if Δfeature >5% ─▶ alert if Δscore >10 or tier change
Monthly ─▶ full recompute (GST/EPFO/bureau refresh)
Quarterly ─▶ retrain + recalibrate + PSI review
```

Alerts flow to the RM Alert Feed (WebSocket) and to subscribed downstream systems via webhook.

---

## 13. Degradation & Resilience

- Each connector isolated; per-source timeout; partial data → proceed + record gap as feature.
- AA is the primary rail; a single connector failing never fails the request. When ULI is adopted later, ULI-down simply falls back to the direct AA/GST/EPFO connectors already in place.
- Model server unhealthy → circuit-breaker returns "manual review" tier rather than a wrong score.
- Cache-first for slowly-changing data (Udyam, monthly GST, macro) to protect latency SLO.

---

## 14. MVP vs Full-POC Scope

| Capability | MVP (Jul 9) | Full POC (post-shortlist) |
|------------|-------------|---------------------------|
| Data sources | AA + GST + Udyam + Bureau (synthetic) | + EPFO, UPI, Electricity, ULI live |
| Model | XGBoost + SHAP as the single decision engine; WOE scorecard as a **parallel** regulatory view (no PD blend) | + Cox survival, federated-learning exploration |
| Integration | OCEN API stub + AA flow | Live ULI/OCEN sandbox integration |
| Dashboard | 3 views, 3 demo personas | Real portfolio data, alert automation |
| Deployment | Single-region ECS + RDS + S3 | Multi-AZ, autoscaling, full observability |

---

## 15. Open Questions / To Confirm

- Which bill-fetch / DISCOM aggregators to integrate for the electricity signal in Phase 2 (the MVP approach is fixed: async power-bill upload + OCR).
- ULI sandbox access timing (post-shortlist) — the build stays AA-first, ULI-ready regardless.
- Exact OCEN spec version to target for the credit-assessment endpoint.
- Synthetic dataset realism vs real sandbox data (flag accuracy caveat in submission).
