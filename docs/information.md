# IDBI Innovate 2026 — Reference Notes

> Consolidated reference for the IDBI Innovate 2026 hackathon and our chosen challenge (Track 03).
> Source: [Hack2skill event page](https://hack2skill.com/event/idbinnovate) and `Problem Statement.md`.
> Last compiled: July 5, 2026.

---

## 1. Hackathon Overview

IDBI Innovate 2026 is a national-level innovation challenge run by IDBI Bank on the
Hack2skill platform. It brings together startups, FinTechs, and professionals to solve
real-world banking problems with solutions scalable enough for deployment inside IDBI Bank.

This is **not** a sandbox-only exercise — selected solutions follow a structured roadmap,
with the best teams earning a direct path to submitting a Proof of Concept (POC) within the
bank's actual sandbox environment.

### Key Facts
| Item | Detail |
|------|--------|
| Format | Hybrid |
| Team size | 1–4 members |
| Cost | Free |
| Total prize pool | ₹15,00,000 (across all tracks) |
| Per-track prize | ₹2 Lakhs (Winner), ₹1 Lakh (Runner-up) |
| Novel Idea Track prize | ₹1 Lakh (standalone) |
| Last date to register | Thursday, July 9, 2026 |

### Core Principles
1. **AI & Data Analytics at the Core** — solutions must leverage AI/ML and data-driven methods.
2. **Real Problems, Real Stakes** — every problem statement comes from IDBI's business units.
3. **Open to Professionals, Startups & FinTechs** — teams at any maturity stage welcome.
4. **Prizes and Rewards** — winners may unlock a co-development/implementation roadmap with IDBI.

### Strict Participation Rules
- **Exclusive Track Constraint:** each team may select and participate in **only one** track
  for the entire challenge (including the Novel Idea track).
- **Originality Requirement:** Novel Idea Track submissions must be completely distinct from
  the 4 defined problem statements.

---

## 2. Timeline (tentative)

| Date | Milestone | Status |
|------|-----------|--------|
| Jun 10, 2026 | Launch & Registrations Open | On-going |
| Jun 23, 2026 | Orientation Session (walkthroughs, APIs, mentorship briefing) | Concluded |
| Jun 30, 2026 | Problem Statement Explainer Session (live Q&A with IDBI leaders) | Concluded |
| **Jul 09, 2026** | **Initial Submissions** (first-round deadline; also last date to register) | Upcoming |
| Jul 21, 2026 | Shortlist Announced | — |
| Jul 22–31, 2026 | Finalists gain API sandbox access | — |
| Jul 31, 2026 | Final Submissions (deployment of finalized solution) | — |
| Aug 1–12, 2026 | Refined Prototype Evaluations | — |
| Aug 13, 2026 | Demo Day & Winner Announcements | — |
| Aug 21, 2026 | Grand Finale & Felicitation Ceremony | — |

> **Immediate target:** the July 9, 2026 initial submission (concept/prototype pitch — the
> PPTX deck fits this). Real sandbox/API access only comes *after* being shortlisted.

---

## 3. What Participants Get

- **Sandbox Banking APIs** — simulate real banking workflows and transactions.
- **Synthetic Datasets** — anonymised data on transactions, MSME financials, UPI patterns.
- **Cloud Infrastructure** — AWS + Applied Cloud Computing (ACC) tooling.
- **Reference Architecture** — starter kits, API docs, architecture guides.
- **Demo Walkthroughs** — product walkthroughs and orientation sessions.
- **Expert Mentors** — mentorship hours with IDBI Business Heads & Digital Transformation Leaders.

### Post-Hackathon Pathways
- **Talent Pipeline** — IDBI may engage directly with winning teams.
- **Implementation** — top POCs may gain sandbox access leading to a POC within IDBI.
- **Senior Mentorship** — finalists guided by senior management & transformation leaders.
- **Collaboration** — mature startups/FinTechs may be invited into formal collaboration.

---

## 4. The Five Tracks

| Track | Theme | Focus |
|-------|-------|-------|
| 01 | Digital Wealth Management | AI-powered (avatar-based) wealth advisory integrated into the bank's mobile app |
| 02 | Prospect Assist AI | — |
| **03** | **Financial Health Score** | **MSME credit decisioning using alternate data (OUR TRACK)** |
| 04 | Default Prediction Model | — |
| 05 | Open Track: Novel Banking Innovation | Wildcard — must be distinct from Tracks 01–04 |

---

## 5. Track 03 — Financial Health Score (OUR CHALLENGE)

**Tags:** Financial Inclusion · Digital Lending · Credit Decisioning

### Problem Statement
IDBI's MSME credit evaluation relies on traditional financial documents, which many
**New-to-Credit (NTC)** and **New-to-Bank (NTB)** enterprises lack or maintain inadequately.
Despite the availability of rich alternate data (GST, UPI, AA, EPFO, etc.), the absence of a
unified assessment framework leads to:
- High rejection rates
- Missed viable borrowers
- Limited portfolio diversification
- Slower financial inclusion progress

### Expected Outcome
Design an **AI/ML-driven MSME Financial Health Card** that:
1. **Aggregates alternate data** — GST, UPI, Account Aggregator (AA), EPFO, etc.
2. **Computes a multidimensional financial health score** — across dimensions such as cash
   flow, business stability, compliance, and growth (not a single number).
3. **Visualizes strengths and risks** — a readable "card" a credit officer can act on.
4. **Integrates with ULI / OCEN / AA ecosystems** — India's digital lending rails.
5. **Enables near real-time credit assessment** — fast, not weeks of manual document review.
6. **Expands onboarding of credit-invisible MSMEs** while improving portfolio quality.

### Key Terms / Data Sources
- **NTC (New-to-Credit)** — no credit history / bureau record.
- **NTB (New-to-Bank)** — no prior relationship with IDBI.
- **GST data** — reveals actual business turnover and filing discipline.
- **UPI / AA data** — real cash-flow patterns, income regularity, banking behavior.
- **EPFO** — proxy for employee count and payroll stability (business legitimacy).
- **ULI (Unified Lending Interface)** — RBI-backed platform for consented borrower data & digital disbursal.
- **OCEN (Open Credit Enablement Network)** — open protocol connecting lenders, borrowers, and loan service providers.
- **AA (Account Aggregator)** — consent-based financial data sharing framework.

> Integrating with ULI/OCEN/AA signals the solution is deployment-ready within India's
> digital lending infrastructure.

---

## 6. Supporting Files in This Workspace

- `Problem Statement.md` — the Track 03 problem statement and hackathon summary.
- `IDBI_Track03_Financial_Health_Score_Research_Brief.docx` — research brief.
- `NTC_MSME_Cold_Start_Credit_Scoring_Critical_Review_2026-06-26.docx` — critical review of
  NTC/MSME cold-start credit scoring.
- `Prototype Submission Deck _ IDBI Innovate.pptx` — prototype submission deck.

---

## 7. Video Session — Explainer Notes (Track 03)

Referenced YouTube links 
- https://www.youtube.com/watch?v=sDGX-QvMyQo

### Track 03 — Financial Health Score (video explanation)

- **Move beyond traditional creditworthiness assessment** — don't rely solely on balance
  sheets. *(13:10–13:30)*
- **Target segment:** evaluate **new-to-bank / new-to-credit** customers by leveraging
  alternative digital data and footprints available in the digital environment. *(13:20–13:50)*
- **Alternative data sources highlighted:**
  - **Electricity / power consumption data** for manufacturing units *(13:35–13:37, 13:45–14:00)*
  - **EPFO contributions** *(13:39–13:40)*
  - Other supplementary digital data and power consumption patterns *(13:45–14:00)*
- **Goal:** categorize customers into segments such as **'disciplined,' 'non-disciplined,'**
  or **yes/no go-to-credit** categories, enabling **quicker and more reliable decisions.**
  *(14:00–14:15)*

### Cross-Cutting Requirements (from the session)

- **Regulatory Compliance:** all solutions must adhere to **RBI, SEBI, and DPDP** guidelines. *(20:53)*
- **AI Role:** AI is intended to **assist, not replace, human underwriters.** *(35:10)*
- **Data Usage:** participants are encouraged to use diverse data sources, but must ensure
  **data reliability and privacy.**

> **Design implications for our solution:**
> - Include a **power/electricity consumption signal** (strong proxy for manufacturing MSME activity).
> - Output should support **segment labels** (disciplined / non-disciplined / go / no-go),
>   not just a raw score.
> - Keep a **human-in-the-loop** underwriting workflow — position AI as decision *support*.
> - Build in **RBI / SEBI / DPDP compliance** and consent/privacy handling from the start.

---

## 8. Contact

- Support: support@hack2skill.com
- Event page: https://hack2skill.com/event/idbinnovate
