"""Realistic raw per-source payload builders.

These mimic the *shape* of real Indian alternate-data payloads so the backend orchestrator +
feature pipeline can be exercised end-to-end on synthetic data:

  * AA  -> ReBIT-style deposit FI schema (Summary + Transactions).
  * GST -> GSTR-1 / GSTR-3B monthly filing records.
  * UPI -> NPCI merchant transaction summary.
  * EPFO -> monthly ECR employee-count/payroll records.
  * Electricity -> power-bill text (for OCR) + structured extract.

Shapes are calibrated from public references (see data/DATA_PROVENANCE.md). Values are synthetic.
"""
from __future__ import annotations

from datetime import date, timedelta

import numpy as np


def _month_labels(n: int, end: date) -> list[str]:
    """Return n YYYY-MM labels ending at `end` (most recent last)."""
    labels = []
    y, m = end.year, end.month
    for _ in range(n):
        labels.append(f"{y:04d}-{m:02d}")
        m -= 1
        if m == 0:
            m = 12
            y -= 1
    return list(reversed(labels))


def build_aa_statement(
    rng: np.random.Generator,
    *,
    avg_monthly_inflow: float,
    inflow_outflow_ratio: float,
    inflow_cov: float,
    emi_amount: float,
    n_bounces: int,
    seasonality: float,
    months: int = 12,
    account_age_months: int = 36,
    end: date | None = None,
) -> dict:
    """Build a ReBIT-style AA deposit-account payload (Summary + Transactions)."""
    end = end or date(2026, 6, 30)
    labels = _month_labels(months, end)
    avg_outflow = avg_monthly_inflow / max(inflow_outflow_ratio, 0.05)

    transactions: list[dict] = []
    balance = max(avg_monthly_inflow * 0.4, 5000.0)
    txn_id = 0
    for i, label in enumerate(labels):
        season = 1.0 + seasonality * np.sin(2 * np.pi * (i % 12) / 12.0)
        inflow = max(rng.normal(avg_monthly_inflow * season, avg_monthly_inflow * inflow_cov), 0)
        outflow = max(rng.normal(avg_outflow * season, avg_outflow * inflow_cov * 0.8), 0)
        y, m = int(label[:4]), int(label[5:7])
        # a handful of credits (customers) and debits (suppliers, salary, EMI, GST)
        n_credits = int(rng.integers(4, 12))
        for _ in range(n_credits):
            amt = round(inflow / n_credits * rng.uniform(0.5, 1.5), 2)
            balance += amt
            txn_id += 1
            transactions.append({
                "txnId": f"T{txn_id:07d}",
                "type": "CREDIT",
                "mode": rng.choice(["UPI", "NEFT", "IMPS", "CASH"], p=[0.5, 0.25, 0.15, 0.10]),
                "amount": amt,
                "currentBalance": round(balance, 2),
                "transactionTimestamp": f"{y:04d}-{m:02d}-{int(rng.integers(1, 28)):02d}T10:00:00",
                "narration": rng.choice(["UPI/CUST", "NEFT/CUST", "SALES/RCPT"]),
            })
        # EMI debit
        if emi_amount > 0:
            balance -= emi_amount
            txn_id += 1
            transactions.append({
                "txnId": f"T{txn_id:07d}", "type": "DEBIT", "mode": "ACH",
                "amount": round(emi_amount, 2), "currentBalance": round(balance, 2),
                "transactionTimestamp": f"{y:04d}-{m:02d}-05T09:00:00", "narration": "EMI/LOAN",
            })
        # supplier + salary + gst debits
        for narr, share in [("SUPPLIER/PAY", 0.5), ("SAL/PAYROLL", 0.3), ("GST/PMT", 0.2)]:
            amt = round(outflow * share * rng.uniform(0.7, 1.3), 2)
            balance -= amt
            txn_id += 1
            transactions.append({
                "txnId": f"T{txn_id:07d}", "type": "DEBIT", "mode": "NEFT",
                "amount": amt, "currentBalance": round(balance, 2),
                "transactionTimestamp": f"{y:04d}-{m:02d}-{int(rng.integers(1, 28)):02d}T14:00:00",
                "narration": narr,
            })
    # cheque bounces
    for _ in range(n_bounces):
        idx = int(rng.integers(0, max(len(transactions), 1)))
        transactions.insert(idx, {
            "txnId": f"TB{int(rng.integers(0, 99999)):05d}", "type": "DEBIT", "mode": "CHEQUE",
            "amount": 0.0, "currentBalance": round(balance, 2),
            "transactionTimestamp": transactions[min(idx, len(transactions) - 1)]["transactionTimestamp"]
            if transactions else f"{end.isoformat()}T00:00:00",
            "narration": "CHQ-RET/INSUFF-FUNDS",
        })

    return {
        "fiType": "DEPOSIT",
        "Summary": {
            "currentBalance": round(balance, 2),
            "type": "SAVINGS" if avg_monthly_inflow < 150000 else "CURRENT",
            "branch": "SYNTH-BR",
            "openingDate": (end - timedelta(days=account_age_months * 30)).isoformat(),
            "currency": "INR",
        },
        "Transactions": {"startDate": labels[0] + "-01", "endDate": labels[-1] + "-28",
                         "Transaction": transactions},
    }


def build_gst_filings(
    rng: np.random.Generator,
    *,
    annual_turnover: float,
    filing_regularity: float,
    mismatch: float,
    itc_ratio: float,
    months: int = 24,
    end: date | None = None,
) -> dict:
    """Build GSTR-1 / GSTR-3B monthly (or quarterly for QRMP) filing records."""
    end = end or date(2026, 6, 30)
    # QRMP eligibility: turnover <= 5 crore -> quarterly; else monthly (see DATA_PROVENANCE.md)
    frequency = "QUARTERLY" if annual_turnover <= 5e7 else "MONTHLY"
    labels = _month_labels(months, end)
    monthly_turnover = annual_turnover / 12.0
    filings = []
    for _i, label in enumerate(labels):
        # some months skipped if low filing regularity
        filed = rng.random() < filing_regularity
        gstr1_sales = max(rng.normal(monthly_turnover, monthly_turnover * 0.2), 0)
        gstr3b_liability = gstr1_sales * 0.18 * (1 - itc_ratio) * (1 + rng.normal(0, mismatch))
        filings.append({
            "period": label,
            "frequency": frequency,
            "gstr1_filed": bool(filed),
            "gstr3b_filed": bool(filed and rng.random() < 0.97),
            "gstr1_taxable_value": round(gstr1_sales, 2),
            "gstr3b_tax_liability": round(max(gstr3b_liability, 0), 2),
            "itc_claimed": round(gstr1_sales * 0.18 * itc_ratio, 2),
        })
    return {
        "gstin_status": "ACTIVE",
        "registration_date": (end - timedelta(days=int(rng.integers(365, 365 * 8)))).isoformat(),
        "filing_frequency": frequency,
        "returns": filings,
    }


def build_upi_summary(rng: np.random.Generator, *, txn_freq: float, avg_value: float,
                      unique_customers: float) -> dict:
    """NPCI-style merchant UPI monthly summary."""
    return {
        "vpa_active": True,
        "monthly_txn_count": int(max(txn_freq, 0)),
        "monthly_unique_payers": int(max(unique_customers, 0)),
        "avg_txn_value": round(max(avg_value, 0), 2),
        "p2m_share": round(float(rng.uniform(0.6, 0.98)), 3),
    }


def build_epfo_record(rng: np.random.Generator, *, employees: int, trend: float,
                     months: int = 24) -> dict:
    """EPFO ECR monthly establishment record."""
    counts = []
    e = max(employees, 20)
    for _ in range(months):
        e = max(int(e * (1 + trend / 12.0 + rng.normal(0, 0.03))), 20)
        counts.append(e)
    return {"establishment_status": "ACTIVE", "monthly_employee_count": counts,
            "coverage": "20+"}


def build_electricity_bill(rng: np.random.Generator, *, avg_kwh: float, trend: float,
                          sanctioned_load_kw: float) -> dict:
    """Power-bill structured extract + OCR-able text block."""
    kwh = max(rng.normal(avg_kwh, avg_kwh * 0.15), 0)
    amount = kwh * rng.uniform(7.5, 9.5)  # LT/HT commercial tariff band (INR/kWh)
    bill_text = (
        "STATE ELECTRICITY BOARD - TAX INVOICE\n"
        f"Consumer No: {int(rng.integers(1000000, 9999999))}\n"
        f"Sanctioned Load: {sanctioned_load_kw:.1f} kW\n"
        f"Units Consumed: {kwh:.0f} kWh\n"
        f"Bill Amount: Rs. {amount:,.2f}\n"
        "Due Date: 2026-07-15\n"
    )
    return {
        "ocr_text": bill_text,
        "extracted": {
            "units_consumed_kwh": round(kwh, 1),
            "sanctioned_load_kw": round(sanctioned_load_kw, 1),
            "bill_amount": round(amount, 2),
            "consumption_trend": round(trend, 4),
        },
    }
