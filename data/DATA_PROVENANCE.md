# Data Provenance — Synthetic MSME Dataset

> This dataset is **fully synthetic**. No real borrower data is used. However, the distributions,
> value ranges, missingness patterns, and inter-feature correlations are **calibrated to real,
> publicly reported Indian statistics** so the synthetic population behaves realistically. This file
> documents the sources used to calibrate the generator (`ml/msme_ml/generate.py`).
>
> *Content below was rephrased/summarised for compliance with source licensing.*

---

## 1. MSME classification (Udyam), effective April 1, 2025

Revised investment / annual-turnover thresholds used to segment micro / small / medium:

| Segment | Investment (plant & machinery) | Annual turnover |
|---------|-------------------------------|-----------------|
| Micro   | ≤ ₹2.5 crore | ≤ ₹10 crore |
| Small   | ≤ ₹25 crore  | ≤ ₹100 crore |
| Medium  | ≤ ₹125 crore | ≤ ₹500 crore |

Sources:
- [Ministry of MSME — Udyam Registration portal](http://udyamregistration.gov.in/) (official thresholds).
- [PIB factsheet — revised MSME classification](https://www.pib.gov.in/FactsheetDetails.aspx?Id=149117) (limits raised 2.5× investment / 2× turnover).

**Calibration decision:** the synthetic population is skewed heavily toward **micro** enterprises
(~80%), which mirrors the real MSME distribution in India, with turnover distributions truncated to
each band. Most micro firms sit far below the ceiling (median micro turnover set to ~₹35 lakh).

---

## 2. MSME credit quality / default rates

- MSME gross NPA ratio fell to **~3.59% (Mar 2025)** from ~11.03% in FY20
  ([CNBC-TV18, Jun 2025](https://www.cnbctv18.com/economy/indias-msme-sector-sees-sharp-drop-in-npas-credit-grows-record-pace-19628208.htm)).
- Another estimate placed the FY25 MSME NPA ratio at **~6%**, down from ~11% in FY21
  ([BusinessWorld](https://www.businessworld.in/article/msme-lending-hits-rs-40-lakh-cr-as-npas-fall-report-589748)).
- RBI flagged **nascent stress specifically in micro enterprises**
  ([Business Standard](https://www.business-standard.com/finance/news/rbi-flags-nascent-stress-in-micro-enterprises-retail-loans-need-monitoring-126063001396_1.html)).

**Calibration decision:** the target population is **NTC/NTB-skewed** (thin-file, higher observed
risk than the seasoned portfolio average), so the synthetic overall default rate is set to **~9%**
(configurable), with micro enterprises carrying a higher base rate than small/medium. This keeps
classes imbalanced but learnable.

---

## 3. GST filing behaviour

- **QRMP scheme**: taxpayers with turnover **≤ ₹5 crore** may file GSTR-1 / GSTR-3B **quarterly**
  while paying tax monthly ([ClearTax](https://cleartax.in/s/quarterly-return-monthly-payment-qrmp-scheme-gst)).
- **Composition scheme**: available to small taxpayers with turnover **≤ ₹1.5 crore** (goods) /
  **₹50 lakh** (services); no ITC ([ClearTax](https://cleartax.in/s/gst-composition-scheme)).
- **Monthly filers**: turnover **> ₹5 crore** file GSTR-1 by the 11th of the following month;
  nil returns still required ([ClearTax GSTR-1](https://cleartax.in/s/gstr-1)).
- **GSTR-1 vs GSTR-3B**: GSTR-1 = invoice-level outward supply; GSTR-3B = monthly summary of
  liability + ITC; mismatches trigger notices ([Razorpay](https://razorpay.com/learn/gstr-1-vs-gstr-3b/)).

**Calibration decision:** filing frequency (monthly vs quarterly) is derived from the firm's turnover
band; a `gstr1_vs_3b_mismatch` feature is generated with a small baseline and inflated for higher-risk
firms; composition-scheme micro firms have simplified/absent ITC signals.

---

## 4. Account Aggregator (AA) bank-statement structure

- AA ecosystem roles: **FIU** (data user), **FIP** (data provider), **AA** (consent manager);
  consent-driven data sharing ([Sahamati FIU](https://sahamati.org.in/fiu/),
  [Setu AA quickstart](https://docs.setu.co/data/account-aggregator/quickstart)).
- ReBIT FI schema for deposit accounts contains a **Summary** block (account type, current balance,
  opening details) and a **Transactions** block (transaction type, mode, narration, amount, balance)
  ([Setu FI data types](https://docs.setu.co/data/account-aggregator/fi-data-types),
  [Sahamati AA standards](https://github.com/Sahamati/account-aggregator-standards)).

**Calibration decision:** the synthetic AA payload (`data/raw_payloads/*/aa.json`) mimics the ReBIT
`Summary` + `Transactions` shape (CREDIT/DEBIT type, running balance, narration codes such as
`UPI/`, `EMI/`, `SAL/`, `GST/`, `CHQ-RET/`). Cash-flow features are computed from these transactions.

---

## 5. Other sources (calibration ranges)

| Signal | Calibration basis |
|--------|-------------------|
| **EPFO** | Establishments with **20+ employees** must register; micro firms typically below this → EPFO absent (a feature, not an error). |
| **UPI** | Merchant UPI monthly transaction counts scale with retail/B2C activity; B2B firms often have negligible UPI. Value ranges set from public NPCI monthly transaction scales. |
| **Electricity** | Manufacturing units draw materially more kWh than services; tariffs/consumption bands set from typical LT/HT commercial-industrial ranges. Async OCR path only. |
| **Bureau (CIBIL MSME)** | Score range ~300–900; **absent for NTC** (majority of this population). |
| **Macro** | Sector PMI, RBI sector outlook, regional GDP growth — public, pre-cached context signals. |

---

## 6. Optional real-data methodology check

The pipeline can optionally validate methodology against a **real public proxy** — the
[U.S. SBA 7(a)/504 national small-business loans dataset](https://data.sba.gov/dataset/7-a-504-foia)
(has real `default/charge-off` labels) — to report an honest AUC on real defaults and demonstrate the
approach is not overfit to synthetic structure. See `ml/msme_ml/real_proxy.py`. This is a methodology
sanity check only; the SBA feature space differs from the Indian alternate-data feature space.

---

## 7. Reproducibility

All randomness is seeded (`--seed`, default `42`). The generator, dictionary, and label logic are
version-controlled. Regenerating with the same seed produces an identical dataset.
