"""Synthetic per-source connectors (AA, GST, UPI, EPFO, Bureau, Udyam, Macro, Electricity).

Each connector independently derives the borrower firm from identifiers and returns its own source's
raw payload (or UNAVAILABLE, mirroring real missingness). Payloads carry a ``features`` hint block so
the feature pipeline can assemble the full 65-vector; the pipeline still recomputes hard cash-flow /
GST / UPI / EPFO / electricity features directly from the raw records.
"""
from __future__ import annotations

import math

import numpy as np
from msme_ml import raw_payloads as rp
from msme_ml.schema import (
    SRC_AA,
    SRC_BUREAU,
    SRC_ELECTRICITY,
    SRC_EPFO,
    SRC_GST,
    SRC_MACRO,
    SRC_UDYAM,
    SRC_UPI,
)

from .base import UNAVAILABLE, firm_for_identifiers, source_hints


def _present(firm: dict, feature: str) -> bool:
    v = firm.get(feature)
    return v is not None and not (isinstance(v, float) and math.isnan(v))


def _rng(firm: dict) -> np.random.Generator:
    return np.random.default_rng(int(abs(hash(firm["msme_id"])) % (2**32)))


class AAConnector:
    source = SRC_AA

    async def fetch(self, consent_token, identifiers):
        firm = firm_for_identifiers(identifiers)
        rng = _rng(firm)
        payload = rp.build_aa_statement(
            rng,
            avg_monthly_inflow=float(firm["avg_monthly_inflow"]),
            inflow_outflow_ratio=float(firm["inflow_outflow_ratio"]),
            inflow_cov=float(firm["inflow_volatility_cov"]),
            emi_amount=float(firm["emi_to_inflow"]) * float(firm["avg_monthly_inflow"]) / 12.0,
            n_bounces=int(firm["cheque_bounce_count"]),
            seasonality=float(firm["seasonality_index"]),
            account_age_months=int(firm.get("bank_account_age", 36) or 36),
        )
        payload["features"] = source_hints(firm, SRC_AA)
        return payload


class GSTConnector:
    source = SRC_GST

    async def fetch(self, consent_token, identifiers):
        firm = firm_for_identifiers(identifiers)
        if not _present(firm, "filing_regularity"):
            return UNAVAILABLE
        rng = _rng(firm)
        payload = rp.build_gst_filings(
            rng, annual_turnover=float(firm["annual_turnover"]),
            filing_regularity=float(firm["filing_regularity"]),
            mismatch=float(firm["gstr1_vs_3b_mismatch"]),
            itc_ratio=float(firm["itc_ratio"]),
        )
        payload["features"] = source_hints(firm, SRC_GST)
        return payload


class UPIConnector:
    source = SRC_UPI

    async def fetch(self, consent_token, identifiers):
        firm = firm_for_identifiers(identifiers)
        if not _present(firm, "upi_txn_frequency"):
            return UNAVAILABLE
        rng = _rng(firm)
        payload = rp.build_upi_summary(
            rng, txn_freq=float(firm["upi_txn_frequency"]),
            avg_value=float(firm["upi_avg_txn_value"]),
            unique_customers=float(firm["upi_unique_customers"]))
        payload["features"] = source_hints(firm, SRC_UPI)
        return payload


class EPFOConnector:
    source = SRC_EPFO

    async def fetch(self, consent_token, identifiers):
        firm = firm_for_identifiers(identifiers)
        if not _present(firm, "epfo_employee_trend_12mo"):
            return UNAVAILABLE
        rng = _rng(firm)
        payload = rp.build_epfo_record(rng, employees=int(firm.get("employees", 25)),
                                       trend=float(firm["epfo_employee_trend_12mo"]))
        payload["features"] = source_hints(firm, SRC_EPFO)
        return payload


class BureauConnector:
    source = SRC_BUREAU

    async def fetch(self, consent_token, identifiers):
        firm = firm_for_identifiers(identifiers)
        if not _present(firm, "cibil_msme_score"):
            return UNAVAILABLE  # NTC -> empty bureau (a signal, not an error)
        return {"bureau_type": "commercial", "features": source_hints(firm, SRC_BUREAU)}


class UdyamConnector:
    source = SRC_UDYAM

    async def fetch(self, consent_token, identifiers):
        firm = firm_for_identifiers(identifiers)
        return {
            "urn": identifiers.get("urn"),
            "enterprise_type": firm.get("segment"),
            "nic_sector": firm.get("sector"),
            "registration_status": "ACTIVE",
            "features": source_hints(firm, SRC_UDYAM),
        }


class MacroConnector:
    source = SRC_MACRO

    async def fetch(self, consent_token, identifiers):
        firm = firm_for_identifiers(identifiers)
        return {"region": firm.get("region"), "features": source_hints(firm, SRC_MACRO)}


class ElectricityConnector:
    """Async / off-critical-path in reality; here it can enrich on demand via bill upload."""
    source = SRC_ELECTRICITY

    async def fetch(self, consent_token, identifiers):
        firm = firm_for_identifiers(identifiers)
        if not _present(firm, "electricity_consumption_trend"):
            return UNAVAILABLE
        rng = _rng(firm)
        avg_kwh = firm.get("_avg_kwh")
        payload = rp.build_electricity_bill(
            rng, avg_kwh=float(avg_kwh) if avg_kwh and not math.isnan(avg_kwh) else 1000.0,
            trend=float(firm["electricity_consumption_trend"]),
            sanctioned_load_kw=(float(avg_kwh) / 200.0) if avg_kwh and not math.isnan(avg_kwh) else 5.0)
        payload["features"] = source_hints(firm, SRC_ELECTRICITY)
        return payload


# Real-time connectors fired in parallel by the orchestrator (electricity handled off-path).
REALTIME_CONNECTORS = [
    AAConnector(), GSTConnector(), EPFOConnector(), UPIConnector(),
    BureauConnector(), UdyamConnector(), MacroConnector(),
]
ELECTRICITY_CONNECTOR = ElectricityConnector()
