# Data Dictionary — The 65 Features

> Auto-generated from `ml/msme_ml/schema.py` (the single source of truth). Regenerate with `python -m tools.gen_data_dictionary`.

Total features: **65** across 7 engineering categories, mapped to 5 Health-Card pillars. Missing sources are emitted as NaN (missing-as-feature) and handled natively by XGBoost.

## 1. Cash Flow Stability (AA)  (15 features)

*Health-Card pillar:* **Cash Flow Stability**

| # | Feature | Source | Unit | Higher is better | Actionable | Definition |
|---|---------|--------|------|------------------|------------|------------|
| 1 | `avg_monthly_inflow` | aa | INR | yes | - | Average monthly credit inflow across the statement window. |
| 2 | `avg_monthly_outflow` | aa | INR | no | - | Average monthly debit outflow across the statement window. |
| 3 | `inflow_outflow_ratio` | aa | ratio | yes | - | Mean monthly inflow divided by mean monthly outflow (>1 => surplus). |
| 4 | `inflow_volatility_cov` | aa | cov | no | - | Coefficient of variation of monthly inflow (volatility of revenue). |
| 5 | `min_balance_6mo` | aa | INR | yes | - | Minimum end-of-day balance over the last 6 months. |
| 6 | `min_balance_12mo` | aa | INR | yes | - | Minimum end-of-day balance over the last 12 months. |
| 7 | `overdraft_utilisation` | aa | ratio | no | - | Fraction of sanctioned OD/CC limit used on average. |
| 8 | `emi_to_inflow` | aa | ratio | no | yes | Total EMI debits divided by inflow (debt-servicing burden). |
| 9 | `cheque_bounce_count` | aa | count | no | yes | Number of returned/bounced cheques or auto-debit failures (12mo). |
| 10 | `days_negative_balance` | aa | days | no | yes | Number of days the account balance was negative (12mo). |
| 11 | `seasonality_index` | aa | index | yes | - | Strength/regularity of seasonal inflow pattern (0-1, higher=predictable). |
| 12 | `cash_buffer_days` | aa | days | yes | yes | Average balance divided by average daily outflow (runway). |
| 13 | `supplier_payment_velocity` | aa | days | yes | yes | Average days between supplier invoice and payment (lower=prompt). |
| 14 | `customer_concentration_top3` | aa | ratio | no | - | Share of inflow from the top-3 counterparties (concentration risk). |
| 15 | `tax_payment_velocity` | aa | days | yes | yes | Timeliness of GST/tax debits relative to due dates (lower=prompt). |

## 2. GST Compliance & Revenue  (12 features)

*Health-Card pillar:* **GST Compliance & Revenue**

| # | Feature | Source | Unit | Higher is better | Actionable | Definition |
|---|---------|--------|------|------------------|------------|------------|
| 1 | `gstr1_turnover_trend_12mo` | gst | slope | yes | - | 12-month linear trend of GSTR-1 declared turnover (normalised). |
| 2 | `gstr1_turnover_trend_24mo` | gst | slope | yes | - | 24-month linear trend of GSTR-1 declared turnover (normalised). |
| 3 | `gst_turnover_yoy_growth` | gst | pct | yes | - | Year-over-year turnover growth from GSTR-1. |
| 4 | `gstr3b_liability_trend` | gst | slope | yes | - | Trend of GSTR-3B net tax liability (normalised). |
| 5 | `gstr1_vs_3b_mismatch` | gst | ratio | no | yes | Average absolute mismatch between GSTR-1 sales and GSTR-3B liability. |
| 6 | `itc_ratio` | gst | ratio | yes | - | Input Tax Credit claimed as a share of output tax (supply-chain depth). |
| 7 | `filing_regularity` | gst | ratio | yes | yes | Fraction of due GST returns filed on time. |
| 8 | `gst_compliance_rating` | gst | score | yes | - | Composite GST compliance rating (0-100). |
| 9 | `sector_benchmark_deviation` | gst | zscore | yes | - | Turnover deviation from NIC-sector benchmark (z-score). |
| 10 | `annual_return_consistency` | gst | ratio | yes | - | Consistency of GSTR-9 annual return with monthly filings. |
| 11 | `gstr9c_reconciliation` | gst | ratio | yes | - | GSTR-9C reconciliation quality (books vs returns). |
| 12 | `gst_filing_gap` | gst | months | no | yes | Longest recent gap (months) in required GST filing. |

## 3. Bureau & Credit History  (8 features)

*Health-Card pillar:* **Bureau & Credit History**

| # | Feature | Source | Unit | Higher is better | Actionable | Definition |
|---|---------|--------|------|------------------|------------|------------|
| 1 | `cibil_msme_score` | bureau | score | yes | - | CIBIL MSME / commercial bureau score (300-900). Absent for NTC. |
| 2 | `obligation_count` | bureau | count | no | - | Number of active credit obligations. |
| 3 | `enquiries_6mo` | bureau | count | no | - | Hard credit enquiries in the last 6 months (credit-hungry signal). |
| 4 | `delinquency_depth` | bureau | dpd | no | yes | Worst delinquency depth in days-past-due over 24 months. |
| 5 | `bureau_utilisation_ratio` | bureau | ratio | no | yes | Aggregate credit utilisation across facilities. |
| 6 | `oldest_tradeline_age` | bureau | months | yes | - | Age of the oldest credit tradeline (credit experience). |
| 7 | `secured_unsecured_mix` | bureau | ratio | yes | - | Share of secured exposure in total exposure. |
| 8 | `writeoff_count` | bureau | count | no | - | Number of written-off / settled accounts. |

## 4. Business Stability  (10 features)

*Health-Card pillar:* **Business Stability**

| # | Feature | Source | Unit | Higher is better | Actionable | Definition |
|---|---------|--------|------|------------------|------------|------------|
| 1 | `udyam_age` | udyam | months | yes | - | Months since Udyam registration (business vintage). |
| 2 | `epfo_employee_trend_12mo` | epfo | slope | yes | - | 12-month trend of EPFO-reported employee count. Absent < 20 employees. |
| 3 | `epfo_employee_trend_24mo` | epfo | slope | yes | - | 24-month trend of EPFO-reported employee count. |
| 4 | `payroll_regularity` | epfo | ratio | yes | - | Fraction of months with on-time EPFO payroll remittance. |
| 5 | `salary_growth` | epfo | pct | yes | - | Average wage growth reported to EPFO. |
| 6 | `bank_account_age` | aa | months | yes | - | Age of the primary current account (banking vintage). |
| 7 | `gst_vintage` | gst | months | yes | - | Months since GST registration. |
| 8 | `location_stability` | udyam | score | yes | - | Stability of registered business address (0-1). |
| 9 | `ownership_stability` | udyam | score | yes | - | Stability of ownership/directors (0-1). |
| 10 | `active_registrations_count` | udyam | count | yes | - | Count of active statutory registrations (Udyam, GST, EPFO, licences). |

## 5. Behavioural & Digital (UPI)  (8 features)

*Health-Card pillar:* **Cash Flow Stability**

| # | Feature | Source | Unit | Higher is better | Actionable | Definition |
|---|---------|--------|------|------------------|------------|------------|
| 1 | `upi_txn_frequency` | upi | count/mo | yes | - | Average monthly UPI transaction count. Absent for non-merchant/B2B. |
| 2 | `upi_unique_customers` | upi | count/mo | yes | - | Average monthly unique paying customers via UPI. |
| 3 | `upi_avg_txn_value` | upi | INR | yes | - | Average UPI transaction value. |
| 4 | `upi_customer_concentration` | upi | ratio | no | - | Share of UPI inflow from the top-5 customers. |
| 5 | `digital_payment_adoption_pct` | upi | pct | yes | - | Share of receipts collected digitally vs cash. |
| 6 | `ecommerce_presence` | upi | binary | yes | - | Indicator of e-commerce / online marketplace presence. |
| 7 | `payment_timing_regularity` | upi | ratio | yes | - | Regularity/entropy of transaction timing (predictable operations). |
| 8 | `reminder_response` | upi | ratio | yes | yes | Historic responsiveness to payment reminders (0-1). |

## 6. Macroeconomic Context  (7 features)

*Health-Card pillar:* **Macroeconomic Context**

| # | Feature | Source | Unit | Higher is better | Actionable | Definition |
|---|---------|--------|------|------------------|------------|------------|
| 1 | `rbi_sector_outlook` | macro | score | yes | - | RBI qualitative sector outlook (0-1, higher=favourable). |
| 2 | `regional_gdp_growth` | macro | pct | yes | - | Regional/state GDP growth rate. |
| 3 | `sector_pmi` | macro | index | yes | - | Sector Purchasing Managers' Index (>50 = expansion). |
| 4 | `input_cost_inflation` | macro | pct | no | - | Input-cost inflation faced by the sector. |
| 5 | `supply_chain_stress` | macro | index | no | - | Sector supply-chain stress index (0-1). |
| 6 | `regulatory_change_exposure` | macro | index | no | - | Exposure to recent/expected regulatory change (0-1). |
| 7 | `currency_exposure` | macro | index | no | - | Exposure to FX volatility (import/export dependence, 0-1). |

## 7. Utility & Infrastructure (Electricity)  (5 features)

*Health-Card pillar:* **Business Stability**

| # | Feature | Source | Unit | Higher is better | Actionable | Definition |
|---|---------|--------|------|------------------|------------|------------|
| 1 | `electricity_consumption_trend` | electricity | slope | yes | - | Trend of monthly electricity consumption (kWh) — activity proxy. |
| 2 | `consumption_volatility` | electricity | cov | no | - | Coefficient of variation of monthly electricity consumption. |
| 3 | `bill_payment_regularity` | electricity | ratio | yes | yes | Fraction of electricity bills paid on time. |
| 4 | `sanctioned_load_utilisation` | electricity | ratio | yes | - | Actual consumption vs sanctioned load (capacity utilisation). |
| 5 | `consumption_vs_turnover_consistency` | electricity | ratio | yes | - | Consistency of electricity use with declared turnover (fraud/authenticity check). |
