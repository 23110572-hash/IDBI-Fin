# IDBIFin

**AI-powered credit intelligence for India's MSMEs.**

IDBIFin turns everyday business data into a clear, trustworthy credit decision. It scores
New-to-Credit (NTC) and New-to-Bank (NTB) micro, small, and medium enterprises using the data they
already generate — GST filings, UPI activity, bank statements shared through the Account Aggregator
framework, EPFO records, and electricity usage — and returns a 0–100 financial health score in
seconds, complete with the reasons behind every decision.

Repository: <https://github.com/23110572-hash/IDBI-Fin>

---

## The opportunity

India has more than 63 million MSMEs. They power roughly a third of the economy and nearly half of
exports, yet most of them are effectively invisible to traditional credit systems. They have no
bureau history, no audited statements, and no collateral — so lenders either decline them or spend
days on manual underwriting. The result is a financing gap estimated in the tens of lakhs of crores
of rupees.

IDBIFin closes that gap. It reads the signals a healthy business already produces and translates
them into a decision a lender can act on with confidence — instantly, transparently, and within the
rules.

---

## What IDBIFin delivers

- **A single, decisive credit score (0–100).** One model, one probability of default, one number.
  Every score maps to a clear risk tier and a recommended action, from straight-through approval to
  manual review.
- **Five financial-health pillars.** Cash Flow Stability, GST Compliance & Revenue, Business
  Stability, Credit History, and Macroeconomic Context — each scored and visualised so an
  underwriter sees exactly where a business is strong and where it needs attention.
- **A reason for every decision.** The top five drivers behind each score are surfaced in plain
  language, so decisions are explainable to the borrower, the underwriter, and the regulator.
- **A regulator-ready scorecard.** A transparent, points-based scorecard runs alongside every
  decision as an independent, auditable view.
- **Alternate data, fused.** GST, UPI, Account Aggregator bank data, EPFO, Udyam, bureau, and macro
  signals are combined into one borrower profile. A power-bill upload adds electricity-consumption
  evidence for manufacturing units.
- **Two modes of intelligence.** Origination scores a new applicant on demand. Portfolio monitoring
  continuously watches existing borrowers and raises early-warning alerts the moment risk shifts.

---

## How it works

1. **Consent first.** The borrower shares their identifiers (Udyam number, PAN, GSTIN) and grants
   consent through the Account Aggregator framework — privacy and permission come before any data
   is pulled.
2. **Data fusion.** IDBIFin gathers the available signals in parallel and assembles them into a
   single, unified borrower record. Missing a source is never a blocker — it is treated as
   information in its own right.
3. **Scoring.** A gradient-boosted model produces the probability of default and converts it into
   the 0–100 health score and five pillar sub-scores.
4. **Explanation.** The engine ranks the strongest positive and negative drivers and presents them
   as clear reason codes next to the score.
5. **Decision.** The result is delivered to the relationship manager's dashboard and is also
   available to lending partners through a standard credit-assessment API.

The whole journey — from consent to a fully explained score — happens in seconds.

---

## The dashboard

IDBIFin gives relationship managers and credit officers a workspace built for fast, confident
decisions:

- **Portfolio Heat Map** — every borrower as a colour-coded card, sortable and filterable, so risk
  and opportunity across the book are visible at a glance.
- **Borrower Drill-down** — the full health card: composite score, score trend, the five-pillar
  radar, the reason-code breakdown, the data-source coverage, and alert history.
- **Alert Feed** — live notifications for tier changes, score drops, and other early-warning
  signals, each with a suggested next action.

A borrower with no bureau record is not shown an empty, misleading view. The dashboard intelligently
rebalances how it presents the pillars so credit-invisible businesses are judged on the evidence
they do have.

---

## Built for trust and compliance

Credit is a regulated business, and IDBIFin is designed for it from the ground up:

- **Explainable by design** — every score carries its reasons, and a transparent scorecard sits
  beside it for independent review.
- **Consent-driven and privacy-first** — data is accessed only with the borrower's permission,
  for a stated purpose, for a limited time.
- **Fully auditable** — every decision is recorded with the exact data and model version used, so
  any score can be reproduced and defended.
- **Human-in-the-loop** — IDBIFin assists underwriters with sharper, faster insight; people stay in
  control of the lending decision.

---

## Business impact

- **A larger, previously unreachable market.** IDBIFin makes it possible to lend confidently to NTC
  and NTB MSMEs that traditional scoring simply cannot assess — expanding the qualified borrower base
  instead of turning good businesses away.
- **Decisions in seconds, not days.** Automated data fusion and scoring collapse underwriting from a
  multi-day manual exercise to a real-time result, cutting cost-to-serve and letting teams handle far
  more applications.
- **Lower risk, fewer surprises.** Continuous portfolio monitoring flags deterioration early, so
  action can be taken before a healthy loan becomes a bad one — protecting the book and reducing
  provisioning.
- **Higher approval quality.** Transparent, reason-backed scores mean fewer wrongful declines of good
  borrowers and better-justified declines of risky ones.
- **Reusable lending infrastructure.** Because assessments are exposed through a standard API, the
  same engine can power multiple products and partners rather than being locked to one workflow.
- **Compliance as a feature.** Built-in explainability, consent handling, and audit trails turn
  regulatory expectations into a competitive advantage instead of an afterthought.

The outcome: more good loans, made faster, at lower risk — and credit reaching the businesses that
drive the economy.

---

## Technology

- **Frontend** — a fast, responsive dashboard built with React, TypeScript, and Vite, with rich
  visualisations for scores, trends, and portfolio views.
- **Backend** — a high-throughput Python API (FastAPI) that handles consent, data orchestration,
  scoring, alerts, and a standards-based assessment endpoint.
- **Intelligence** — a gradient-boosted decision model with model-driven explanations and a
  parallel, transparent scorecard.
- **Data** — a managed cloud Postgres database backs the consent registry, the append-only score
  ledger, and user accounts.

---

© 2026 IDBI Innovate. IDBIFin — credit intelligence for every enterprise.
