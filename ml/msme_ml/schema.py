"""The 65-feature schema — the single source of truth for the feature vector.

Each feature declares its engineering category (one of 7), the data source it derives from
(so missingness can be modelled as "the source was unavailable"), unit, direction
(higher_is_better), and a short definition used to generate the data dictionary.

Missing-as-feature: when a source is unavailable, its features are emitted as NaN and XGBoost
handles them natively (never imputed with a penalty).
"""
from __future__ import annotations

from dataclasses import dataclass

from .config import (
    CATEGORY_BEHAVIOURAL,
    CATEGORY_BUREAU,
    CATEGORY_BUSINESS,
    CATEGORY_CASH_FLOW,
    CATEGORY_GST,
    CATEGORY_MACRO,
    CATEGORY_UTILITY,
)

# Data-source keys (align with backend connectors)
SRC_AA = "aa"
SRC_GST = "gst"
SRC_BUREAU = "bureau"
SRC_EPFO = "epfo"
SRC_UDYAM = "udyam"
SRC_UPI = "upi"
SRC_MACRO = "macro"
SRC_ELECTRICITY = "electricity"


@dataclass(frozen=True)
class FeatureSpec:
    name: str
    category: str
    source: str
    unit: str
    higher_is_better: bool
    description: str
    # actionability: can the borrower realistically change this in the short term?
    actionable: bool = False


# ---------------------------------------------------------------------------
# 1. Cash Flow Stability (15) — from AA bank statements
# ---------------------------------------------------------------------------
_CASH_FLOW = [
    FeatureSpec("avg_monthly_inflow", CATEGORY_CASH_FLOW, SRC_AA, "INR", True,
                "Average monthly credit inflow across the statement window."),
    FeatureSpec("avg_monthly_outflow", CATEGORY_CASH_FLOW, SRC_AA, "INR", False,
                "Average monthly debit outflow across the statement window."),
    FeatureSpec("inflow_outflow_ratio", CATEGORY_CASH_FLOW, SRC_AA, "ratio", True,
                "Mean monthly inflow divided by mean monthly outflow (>1 => surplus)."),
    FeatureSpec("inflow_volatility_cov", CATEGORY_CASH_FLOW, SRC_AA, "cov", False,
                "Coefficient of variation of monthly inflow (volatility of revenue)."),
    FeatureSpec("min_balance_6mo", CATEGORY_CASH_FLOW, SRC_AA, "INR", True,
                "Minimum end-of-day balance over the last 6 months."),
    FeatureSpec("min_balance_12mo", CATEGORY_CASH_FLOW, SRC_AA, "INR", True,
                "Minimum end-of-day balance over the last 12 months."),
    FeatureSpec("overdraft_utilisation", CATEGORY_CASH_FLOW, SRC_AA, "ratio", False,
                "Fraction of sanctioned OD/CC limit used on average."),
    FeatureSpec("emi_to_inflow", CATEGORY_CASH_FLOW, SRC_AA, "ratio", False,
                "Total EMI debits divided by inflow (debt-servicing burden).", actionable=True),
    FeatureSpec("cheque_bounce_count", CATEGORY_CASH_FLOW, SRC_AA, "count", False,
                "Number of returned/bounced cheques or auto-debit failures (12mo).", actionable=True),
    FeatureSpec("days_negative_balance", CATEGORY_CASH_FLOW, SRC_AA, "days", False,
                "Number of days the account balance was negative (12mo).", actionable=True),
    FeatureSpec("seasonality_index", CATEGORY_CASH_FLOW, SRC_AA, "index", True,
                "Strength/regularity of seasonal inflow pattern (0-1, higher=predictable)."),
    FeatureSpec("cash_buffer_days", CATEGORY_CASH_FLOW, SRC_AA, "days", True,
                "Average balance divided by average daily outflow (runway).", actionable=True),
    FeatureSpec("supplier_payment_velocity", CATEGORY_CASH_FLOW, SRC_AA, "days", True,
                "Average days between supplier invoice and payment (lower=prompt).", actionable=True),
    FeatureSpec("customer_concentration_top3", CATEGORY_CASH_FLOW, SRC_AA, "ratio", False,
                "Share of inflow from the top-3 counterparties (concentration risk)."),
    FeatureSpec("tax_payment_velocity", CATEGORY_CASH_FLOW, SRC_AA, "days", True,
                "Timeliness of GST/tax debits relative to due dates (lower=prompt).", actionable=True),
]

# ---------------------------------------------------------------------------
# 2. GST Compliance & Revenue (12) — from GST Network
# ---------------------------------------------------------------------------
_GST = [
    FeatureSpec("gstr1_turnover_trend_12mo", CATEGORY_GST, SRC_GST, "slope", True,
                "12-month linear trend of GSTR-1 declared turnover (normalised)."),
    FeatureSpec("gstr1_turnover_trend_24mo", CATEGORY_GST, SRC_GST, "slope", True,
                "24-month linear trend of GSTR-1 declared turnover (normalised)."),
    FeatureSpec("gst_turnover_yoy_growth", CATEGORY_GST, SRC_GST, "pct", True,
                "Year-over-year turnover growth from GSTR-1."),
    FeatureSpec("gstr3b_liability_trend", CATEGORY_GST, SRC_GST, "slope", True,
                "Trend of GSTR-3B net tax liability (normalised)."),
    FeatureSpec("gstr1_vs_3b_mismatch", CATEGORY_GST, SRC_GST, "ratio", False,
                "Average absolute mismatch between GSTR-1 sales and GSTR-3B liability.", actionable=True),
    FeatureSpec("itc_ratio", CATEGORY_GST, SRC_GST, "ratio", True,
                "Input Tax Credit claimed as a share of output tax (supply-chain depth)."),
    FeatureSpec("filing_regularity", CATEGORY_GST, SRC_GST, "ratio", True,
                "Fraction of due GST returns filed on time.", actionable=True),
    FeatureSpec("gst_compliance_rating", CATEGORY_GST, SRC_GST, "score", True,
                "Composite GST compliance rating (0-100)."),
    FeatureSpec("sector_benchmark_deviation", CATEGORY_GST, SRC_GST, "zscore", True,
                "Turnover deviation from NIC-sector benchmark (z-score)."),
    FeatureSpec("annual_return_consistency", CATEGORY_GST, SRC_GST, "ratio", True,
                "Consistency of GSTR-9 annual return with monthly filings."),
    FeatureSpec("gstr9c_reconciliation", CATEGORY_GST, SRC_GST, "ratio", True,
                "GSTR-9C reconciliation quality (books vs returns)."),
    FeatureSpec("gst_filing_gap", CATEGORY_GST, SRC_GST, "months", False,
                "Longest recent gap (months) in required GST filing.", actionable=True),
]

# ---------------------------------------------------------------------------
# 3. Bureau & Credit History (8) — from Credit Bureau (EMPTY for NTC = a feature)
# ---------------------------------------------------------------------------
_BUREAU = [
    FeatureSpec("cibil_msme_score", CATEGORY_BUREAU, SRC_BUREAU, "score", True,
                "CIBIL MSME / commercial bureau score (300-900). Absent for NTC."),
    FeatureSpec("obligation_count", CATEGORY_BUREAU, SRC_BUREAU, "count", False,
                "Number of active credit obligations."),
    FeatureSpec("enquiries_6mo", CATEGORY_BUREAU, SRC_BUREAU, "count", False,
                "Hard credit enquiries in the last 6 months (credit-hungry signal)."),
    FeatureSpec("delinquency_depth", CATEGORY_BUREAU, SRC_BUREAU, "dpd", False,
                "Worst delinquency depth in days-past-due over 24 months.", actionable=True),
    FeatureSpec("bureau_utilisation_ratio", CATEGORY_BUREAU, SRC_BUREAU, "ratio", False,
                "Aggregate credit utilisation across facilities.", actionable=True),
    FeatureSpec("oldest_tradeline_age", CATEGORY_BUREAU, SRC_BUREAU, "months", True,
                "Age of the oldest credit tradeline (credit experience)."),
    FeatureSpec("secured_unsecured_mix", CATEGORY_BUREAU, SRC_BUREAU, "ratio", True,
                "Share of secured exposure in total exposure."),
    FeatureSpec("writeoff_count", CATEGORY_BUREAU, SRC_BUREAU, "count", False,
                "Number of written-off / settled accounts."),
]

# ---------------------------------------------------------------------------
# 4. Business Stability (10) — Udyam, EPFO, bank vintage
# ---------------------------------------------------------------------------
_BUSINESS = [
    FeatureSpec("udyam_age", CATEGORY_BUSINESS, SRC_UDYAM, "months", True,
                "Months since Udyam registration (business vintage)."),
    FeatureSpec("epfo_employee_trend_12mo", CATEGORY_BUSINESS, SRC_EPFO, "slope", True,
                "12-month trend of EPFO-reported employee count. Absent < 20 employees."),
    FeatureSpec("epfo_employee_trend_24mo", CATEGORY_BUSINESS, SRC_EPFO, "slope", True,
                "24-month trend of EPFO-reported employee count."),
    FeatureSpec("payroll_regularity", CATEGORY_BUSINESS, SRC_EPFO, "ratio", True,
                "Fraction of months with on-time EPFO payroll remittance."),
    FeatureSpec("salary_growth", CATEGORY_BUSINESS, SRC_EPFO, "pct", True,
                "Average wage growth reported to EPFO."),
    FeatureSpec("bank_account_age", CATEGORY_BUSINESS, SRC_AA, "months", True,
                "Age of the primary current account (banking vintage)."),
    FeatureSpec("gst_vintage", CATEGORY_BUSINESS, SRC_GST, "months", True,
                "Months since GST registration."),
    FeatureSpec("location_stability", CATEGORY_BUSINESS, SRC_UDYAM, "score", True,
                "Stability of registered business address (0-1)."),
    FeatureSpec("ownership_stability", CATEGORY_BUSINESS, SRC_UDYAM, "score", True,
                "Stability of ownership/directors (0-1)."),
    FeatureSpec("active_registrations_count", CATEGORY_BUSINESS, SRC_UDYAM, "count", True,
                "Count of active statutory registrations (Udyam, GST, EPFO, licences)."),
]

# ---------------------------------------------------------------------------
# 5. Behavioural & Digital (8) — from UPI (merchant)
# ---------------------------------------------------------------------------
_BEHAVIOURAL = [
    FeatureSpec("upi_txn_frequency", CATEGORY_BEHAVIOURAL, SRC_UPI, "count/mo", True,
                "Average monthly UPI transaction count. Absent for non-merchant/B2B."),
    FeatureSpec("upi_unique_customers", CATEGORY_BEHAVIOURAL, SRC_UPI, "count/mo", True,
                "Average monthly unique paying customers via UPI."),
    FeatureSpec("upi_avg_txn_value", CATEGORY_BEHAVIOURAL, SRC_UPI, "INR", True,
                "Average UPI transaction value."),
    FeatureSpec("upi_customer_concentration", CATEGORY_BEHAVIOURAL, SRC_UPI, "ratio", False,
                "Share of UPI inflow from the top-5 customers."),
    FeatureSpec("digital_payment_adoption_pct", CATEGORY_BEHAVIOURAL, SRC_UPI, "pct", True,
                "Share of receipts collected digitally vs cash."),
    FeatureSpec("ecommerce_presence", CATEGORY_BEHAVIOURAL, SRC_UPI, "binary", True,
                "Indicator of e-commerce / online marketplace presence."),
    FeatureSpec("payment_timing_regularity", CATEGORY_BEHAVIOURAL, SRC_UPI, "ratio", True,
                "Regularity/entropy of transaction timing (predictable operations)."),
    FeatureSpec("reminder_response", CATEGORY_BEHAVIOURAL, SRC_UPI, "ratio", True,
                "Historic responsiveness to payment reminders (0-1).", actionable=True),
]

# ---------------------------------------------------------------------------
# 6. Macroeconomic Context (7) — RBI / PMI (context only, pre-cached)
# ---------------------------------------------------------------------------
_MACRO = [
    FeatureSpec("rbi_sector_outlook", CATEGORY_MACRO, SRC_MACRO, "score", True,
                "RBI qualitative sector outlook (0-1, higher=favourable)."),
    FeatureSpec("regional_gdp_growth", CATEGORY_MACRO, SRC_MACRO, "pct", True,
                "Regional/state GDP growth rate."),
    FeatureSpec("sector_pmi", CATEGORY_MACRO, SRC_MACRO, "index", True,
                "Sector Purchasing Managers' Index (>50 = expansion)."),
    FeatureSpec("input_cost_inflation", CATEGORY_MACRO, SRC_MACRO, "pct", False,
                "Input-cost inflation faced by the sector."),
    FeatureSpec("supply_chain_stress", CATEGORY_MACRO, SRC_MACRO, "index", False,
                "Sector supply-chain stress index (0-1)."),
    FeatureSpec("regulatory_change_exposure", CATEGORY_MACRO, SRC_MACRO, "index", False,
                "Exposure to recent/expected regulatory change (0-1)."),
    FeatureSpec("currency_exposure", CATEGORY_MACRO, SRC_MACRO, "index", False,
                "Exposure to FX volatility (import/export dependence, 0-1)."),
]

# ---------------------------------------------------------------------------
# 7. Utility & Infrastructure Signals (5) — electricity (async OCR)
# ---------------------------------------------------------------------------
_UTILITY = [
    FeatureSpec("electricity_consumption_trend", CATEGORY_UTILITY, SRC_ELECTRICITY, "slope", True,
                "Trend of monthly electricity consumption (kWh) — activity proxy."),
    FeatureSpec("consumption_volatility", CATEGORY_UTILITY, SRC_ELECTRICITY, "cov", False,
                "Coefficient of variation of monthly electricity consumption."),
    FeatureSpec("bill_payment_regularity", CATEGORY_UTILITY, SRC_ELECTRICITY, "ratio", True,
                "Fraction of electricity bills paid on time.", actionable=True),
    FeatureSpec("sanctioned_load_utilisation", CATEGORY_UTILITY, SRC_ELECTRICITY, "ratio", True,
                "Actual consumption vs sanctioned load (capacity utilisation)."),
    FeatureSpec("consumption_vs_turnover_consistency", CATEGORY_UTILITY, SRC_ELECTRICITY, "ratio", True,
                "Consistency of electricity use with declared turnover (fraud/authenticity check)."),
]

FEATURES: list[FeatureSpec] = (
    _CASH_FLOW + _GST + _BUREAU + _BUSINESS + _BEHAVIOURAL + _MACRO + _UTILITY
)

# Sanity: exactly 65 features
assert len(FEATURES) == 65, f"expected 65 features, got {len(FEATURES)}"

FEATURE_NAMES: list[str] = [f.name for f in FEATURES]
FEATURE_BY_NAME: dict[str, FeatureSpec] = {f.name: f for f in FEATURES}


def features_for_source(source: str) -> list[str]:
    return [f.name for f in FEATURES if f.source == source]


def features_for_category(category: str) -> list[str]:
    return [f.name for f in FEATURES if f.category == category]
