"""Feature pipeline: raw multi-source payloads -> the 65-feature vector.

Used by the backend orchestrator at inference time. Missing sources are emitted as NaN
(missing-as-feature) so XGBoost handles them natively.

A `record` maps source-key -> payload. Each payload may carry a pre-derived ``features`` block
(how the connectors deliver source-level contributions). For the Account Aggregator payload we
ALSO recompute the core cash-flow aggregates directly from the ReBIT ``Transactions`` list to
demonstrate a genuine parsing pipeline; computed values override the hint block.
"""
from __future__ import annotations

import math
from datetime import date

import numpy as np

from .schema import (
    FEATURE_NAMES,
    SRC_AA,
    SRC_BUREAU,
    SRC_ELECTRICITY,
    SRC_EPFO,
    SRC_GST,
    SRC_MACRO,
    SRC_UDYAM,
    SRC_UPI,
    features_for_source,
)

SOURCE_ORDER = [SRC_AA, SRC_GST, SRC_BUREAU, SRC_EPFO, SRC_UPI, SRC_UDYAM, SRC_MACRO,
                SRC_ELECTRICITY]


def _month_key(ts: str) -> str:
    return ts[:7]  # YYYY-MM


def compute_aa_cashflow(aa: dict) -> dict[str, float]:
    """Compute core cash-flow features directly from AA ReBIT transactions."""
    txns = aa.get("Transactions", {}).get("Transaction", [])
    if not txns:
        return {}
    monthly_in: dict[str, float] = {}
    monthly_out: dict[str, float] = {}
    emi_total = 0.0
    bounce = 0
    balances = []
    neg_days = set()
    for t in txns:
        month = _month_key(t.get("transactionTimestamp", ""))
        amt = float(t.get("amount", 0) or 0)
        bal = float(t.get("currentBalance", 0) or 0)
        balances.append(bal)
        narration = str(t.get("narration", ""))
        if t.get("type") == "CREDIT":
            monthly_in[month] = monthly_in.get(month, 0.0) + amt
        else:
            monthly_out[month] = monthly_out.get(month, 0.0) + amt
            if narration.startswith("EMI"):
                emi_total += amt
            if "CHQ-RET" in narration:
                bounce += 1
        if bal < 0:
            neg_days.add((month, t.get("transactionTimestamp", "")[:10]))

    in_vals = np.array(list(monthly_in.values()), dtype=float)
    out_vals = np.array(list(monthly_out.values()), dtype=float)
    avg_in = float(in_vals.mean()) if in_vals.size else 0.0
    avg_out = float(out_vals.mean()) if out_vals.size else 0.0
    cov = float(in_vals.std() / (in_vals.mean() + 1e-9)) if in_vals.size else 0.0
    ratio = avg_in / (avg_out + 1e-9)
    total_in = float(in_vals.sum()) + 1e-9
    return {
        "avg_monthly_inflow": avg_in,
        "avg_monthly_outflow": avg_out,
        "inflow_outflow_ratio": ratio,
        "inflow_volatility_cov": cov,
        "min_balance_12mo": float(min(balances)) if balances else 0.0,
        "min_balance_6mo": float(min(balances[-len(balances) // 2:])) if balances else 0.0,
        "emi_to_inflow": emi_total / total_in,
        "cheque_bounce_count": float(bounce),
        "days_negative_balance": float(len(neg_days)),
    }


def _bank_account_age(aa: dict) -> float | None:
    opening = aa.get("Summary", {}).get("openingDate")
    if not opening:
        return None
    try:
        y, m, d = (int(x) for x in opening[:10].split("-"))
        today = date(2026, 6, 30)
        return (today.year - y) * 12 + (today.month - m)
    except Exception:
        return None


def compute_gst(gst: dict) -> dict[str, float]:
    """Compute GST features from filing records where derivable."""
    returns = gst.get("returns", [])
    if not returns:
        return {}
    filed = [r for r in returns]
    reg = sum(1 for r in filed if r.get("gstr1_filed")) / max(len(filed), 1)
    sales = np.array([r.get("gstr1_taxable_value", 0) for r in filed], dtype=float)
    liab = np.array([r.get("gstr3b_tax_liability", 0) for r in filed], dtype=float)
    itc = np.array([r.get("itc_claimed", 0) for r in filed], dtype=float)
    # mismatch: |0.18*sales - liab| / (0.18*sales)
    expected = 0.18 * sales
    mismatch = float(np.mean(np.abs(expected - liab) / (expected + 1e-9))) if sales.size else 0.0
    out = {"filing_regularity": reg, "gstr1_vs_3b_mismatch": min(mismatch, 1.0)}
    if sales.size >= 2:
        x = np.arange(len(sales))
        slope = float(np.polyfit(x, sales / (sales.mean() + 1e-9), 1)[0])
        out["gstr1_turnover_trend_12mo"] = slope
    if itc.sum() > 0 and expected.sum() > 0:
        out["itc_ratio"] = float(min(itc.sum() / (expected.sum() + 1e-9), 0.95))
    return out


def compute_upi(upi: dict) -> dict[str, float]:
    out = {}
    if "monthly_txn_count" in upi:
        out["upi_txn_frequency"] = float(upi["monthly_txn_count"])
    if "monthly_unique_payers" in upi:
        out["upi_unique_customers"] = float(upi["monthly_unique_payers"])
    if "avg_txn_value" in upi:
        out["upi_avg_txn_value"] = float(upi["avg_txn_value"])
    return out


def compute_epfo(epfo: dict) -> dict[str, float]:
    counts = epfo.get("monthly_employee_count", [])
    if len(counts) < 2:
        return {}
    arr = np.array(counts, dtype=float)
    x = np.arange(len(arr))
    slope = float(np.polyfit(x, arr / (arr.mean() + 1e-9), 1)[0])
    return {"epfo_employee_trend_12mo": slope, "epfo_employee_trend_24mo": slope}


def compute_electricity(elec: dict) -> dict[str, float]:
    ex = elec.get("extracted", {})
    out = {}
    if "consumption_trend" in ex:
        out["electricity_consumption_trend"] = float(ex["consumption_trend"])
    if "units_consumed_kwh" in ex and "sanctioned_load_kw" in ex and ex["sanctioned_load_kw"]:
        # crude utilisation proxy
        out["sanctioned_load_utilisation"] = float(
            min(ex["units_consumed_kwh"] / (ex["sanctioned_load_kw"] * 730 + 1e-9), 1.0))
    return out


def extract_features(record: dict) -> dict[str, float]:
    """Assemble the full 65-feature vector from a multi-source record.

    Precedence per feature:
      1. value computed directly from raw payload (AA/GST/UPI/EPFO/electricity), else
      2. value from the payload's ``features`` hint block, else
      3. NaN (source unavailable -> missing-as-feature).
    """
    vec: dict[str, float] = {name: math.nan for name in FEATURE_NAMES}

    # 1) hint blocks (source-level contributions)
    for src in SOURCE_ORDER:
        payload = record.get(src)
        if not payload or payload == "UNAVAILABLE":
            continue
        hints = payload.get("features", {}) if isinstance(payload, dict) else {}
        for name in features_for_source(src):
            if name in hints and hints[name] is not None:
                vec[name] = float(hints[name])

    # 2) genuine computation overrides (demonstrates the pipeline)
    aa = record.get(SRC_AA)
    if isinstance(aa, dict) and aa != "UNAVAILABLE":
        vec.update(compute_aa_cashflow(aa))
        age = _bank_account_age(aa)
        if age is not None:
            vec["bank_account_age"] = float(age)
    gst = record.get(SRC_GST)
    if isinstance(gst, dict) and gst != "UNAVAILABLE":
        for k, v in compute_gst(gst).items():
            vec[k] = v
    upi = record.get(SRC_UPI)
    if isinstance(upi, dict) and upi != "UNAVAILABLE":
        vec.update(compute_upi(upi))
    epfo = record.get(SRC_EPFO)
    if isinstance(epfo, dict) and epfo != "UNAVAILABLE":
        vec.update(compute_epfo(epfo))
    elec = record.get(SRC_ELECTRICITY)
    if isinstance(elec, dict) and elec != "UNAVAILABLE":
        vec.update(compute_electricity(elec))

    return vec


def to_ordered_vector(feature_dict: dict[str, float]) -> list[float]:
    """Return features in canonical schema order (for model input)."""
    return [float(feature_dict.get(name, math.nan)) for name in FEATURE_NAMES]


def availability_map(record: dict) -> dict[str, bool]:
    """Which of the 8 sources were available (for dashboard pillar renormalisation)."""
    return {src: bool(record.get(src) and record.get(src) != "UNAVAILABLE")
            for src in SOURCE_ORDER}
